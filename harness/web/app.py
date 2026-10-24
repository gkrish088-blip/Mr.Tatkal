"""Single-worker self-hosted operator API and GUI."""
import asyncio
from contextlib import asynccontextmanager
from datetime import datetime
import hashlib
import hmac
import json
import os
from pathlib import Path
import secrets
import time
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field
from starlette.middleware.trustedhost import TrustedHostMiddleware

from harness.handoff.channel import atomic_json
from harness.log.redact import Redactor
from harness.models.adapter import HTTPModel, ModelConfig
from harness.skillrt.loader import SkillLoader
from harness.triggers.schedule import Scheduler, timestamp
from harness.web.manager import RunManager
from harness.web.settings import Settings
from harness.web.triggers import TriggerService


class Task(BaseModel):
    model_config=ConfigDict(extra='forbid')
    goal: str=Field(min_length=1,max_length=10000)
    skill: str | None=None
    provider: Literal['claude','deepseek'] | None=None
    mode: Literal['agent','demo']='agent'
    inputs: dict=Field(default_factory=dict)


class Schedule(Task):
    kind: Literal['once','cron']='once'
    when: str | None=None
    cron: str | None=None
    timezone: str='Asia/Kolkata'


class Login(BaseModel):
    password: str=Field(max_length=1000)


class Reply(BaseModel):
    value: str=Field(min_length=1,max_length=10000)


def create_app(settings=None, runner=None):
    settings=settings or Settings.from_env()
    settings.validate();settings.data_dir.mkdir(parents=True,exist_ok=True)
    keyfile=settings.data_dir/'auth-secret'
    if not keyfile.exists():
        keyfile.write_bytes(secrets.token_bytes(32))
        try: keyfile.chmod(0o600)
        except OSError: pass
    key=keyfile.read_bytes()
    # Invalidate login cookies when the operator rotates the server password.
    key=hmac.digest(key,settings.password.encode(),'sha256')
    manager=RunManager(settings,runner)
    triggers=TriggerService(settings,manager)
    scheduler=Scheduler(settings.data_dir/'schedules.json')
    schedule_lock=asyncio.Lock()
    errors=[]
    attempts={}
    lockfile=settings.data_dir/'server.lock'
    lock_handle=None

    def authenticated(request):
        if not settings.password: return True
        cookie=request.cookies.get('agent_session','')
        try:
            expiry,signature=cookie.split('.',1)
            return int(expiry)>time.time() and hmac.compare_digest(signature,hmac.new(key,expiry.encode(),'sha256').hexdigest())
        except (ValueError,TypeError): return False

    def acquire_lock():
        nonlocal lock_handle
        lock_handle=lockfile.open('a+b')
        lock_handle.seek(0);lock_handle.write(b'0');lock_handle.flush();lock_handle.seek(0)
        try:
            if os.name=='nt':
                import msvcrt
                msvcrt.locking(lock_handle.fileno(),msvcrt.LK_NBLCK,1)
            else:
                import fcntl
                fcntl.flock(lock_handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except (OSError,BlockingIOError):
            lock_handle.close();lock_handle=None
            raise RuntimeError('Another server already owns DATA_DIR; run one worker only')

    async def dispatch(goal, inputs):
        payload=inputs['task']
        manager.submit(goal,payload.get('skill'),payload.get('inputs'),payload.get('provider'),payload.get('mode','agent'),inputs['trigger_id'])

    async def scheduling():
        while True:
            try:
                async with schedule_lock: await scheduler.tick(dispatch)
            except Exception as error:
                # Failed dispatch stays uncertain; do not repeatedly submit a booking task.
                errors.append(type(error).__name__)
                del errors[:-10]
            await asyncio.sleep(.05)

    @asynccontextmanager
    async def lifespan(app):
        acquire_lock()
        ticker=None
        try:
            await manager.start()
            await triggers.start()
            ticker=asyncio.create_task(scheduling())
            yield
        finally:
            if ticker:
                ticker.cancel();await asyncio.gather(ticker,return_exceptions=True)
            await triggers.close()
            await manager.close()
            if lock_handle: lock_handle.close()

    app=FastAPI(title='Agent control room',lifespan=lifespan,docs_url=None,redoc_url=None,openapi_url=None)
    app.state.manager=manager;app.state.scheduler=scheduler;app.state.settings=settings;app.state.triggers=triggers
    app.add_middleware(TrustedHostMiddleware,allowed_hosts=list(settings.allowed_hosts))

    @app.middleware('http')
    async def protect(request, call_next):
        path=request.url.path
        public=path in {'/api/access','/api/login','/health'} or not path.startswith('/api/')
        if path.startswith('/lab/'):
            # Sandboxed demo service is used by the server's own browser, without operator cookies.
            if request.client.host not in {'127.0.0.1','::1','localhost','testclient'}:
                return JSONResponse({'detail':'Local demo only'},403)
        elif not public and not authenticated(request):
            return JSONResponse({'detail':'Sign in to the control room'},401)
        if path.startswith('/api/') and request.method not in {'GET','HEAD','OPTIONS'}:
            if request.headers.get('X-Agent-Request')!='1':
                return JSONResponse({'detail':'Missing request protection header'},403)
            origin=request.headers.get('origin')
            if origin and origin.rstrip('/')!=str(request.base_url).rstrip('/'):
                return JSONResponse({'detail':'Cross-origin request refused'},403)
        response=await call_next(request)
        response.headers['X-Content-Type-Options']='nosniff'
        response.headers['Referrer-Policy']='same-origin'
        response.headers['Cache-Control']='no-store' if path.startswith('/api/') else 'no-cache'
        if path.endswith('/artifacts/replay.html'):
            response.headers['Content-Security-Policy']="default-src 'none'; img-src 'self'; style-src 'unsafe-inline'; frame-ancestors 'self'"
        elif not path.startswith('/lab/'):
            response.headers['Content-Security-Policy']="default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-src 'self'; frame-ancestors 'self'; object-src 'none'; base-uri 'self'"
        return response

    @app.exception_handler(ValueError)
    async def invalid(request,error):
        redactor=Redactor([v for k,v in os.environ.items() if any(w in k for w in ('KEY','PASSWORD','TOKEN','SECRET')) and v])
        return JSONResponse({'detail':redactor.redact(str(error))},422)

    @app.exception_handler(KeyError)
    async def missing(request,error): return JSONResponse({'detail':'Session not found'},404)

    @app.get('/health')
    async def health(): return {'ok':True}

    @app.post('/hooks/{name}',status_code=202)
    async def webhook(name: str,request: Request):
        if name not in triggers.webhooks:raise HTTPException(404,'Unknown event source')
        body=bytearray()
        async for chunk in request.stream():
            body.extend(chunk)
            if len(body)>1000000:raise HTTPException(413,'Webhook payload is too large')
        event_id=request.headers.get('X-Event-ID','')
        if not event_id or len(event_id)>200:raise ValueError('Supply X-Event-ID with at most 200 characters')
        try:
            accepted=await triggers.webhook(name,bytes(body),request.headers.get('X-Signature',''),event_id)
        except PermissionError:
            raise HTTPException(403,'Invalid event signature') from None
        return {'accepted':accepted}

    @app.get('/api/access')
    async def access(request: Request):
        return {'required':bool(settings.password),'authenticated':authenticated(request)}

    @app.post('/api/login')
    async def login(payload: Login,request: Request):
        peer=request.client.host
        recent=[t for t in attempts.get(peer,[]) if t>time.time()-60]
        if len(recent)>=10: raise HTTPException(429,'Too many attempts; try again in one minute')
        attempts[peer]=recent+[time.time()]
        if not hmac.compare_digest(payload.password.encode(),settings.password.encode()):
            raise HTTPException(401,'Incorrect server password')
        expiry=str(int(time.time()+86400))
        response=JSONResponse({'ok':True})
        response.set_cookie('agent_session',expiry+'.'+hmac.new(key,expiry.encode(),'sha256').hexdigest(),
                            httponly=True,samesite='strict',secure=settings.cookie_secure,max_age=86400)
        return response

    @app.post('/api/logout')
    async def logout():
        response=JSONResponse({'ok':True});response.delete_cookie('agent_session');return response

    @app.get('/api/status')
    async def status():
        return {'providers':settings.available(),'default_provider':settings.provider,
                'timezone':settings.timezone,'browser':{'mode':settings.browser_mode,'headless':settings.browser_headless},
                'storage':'Server local disk','active':manager.active,'scheduler_running':True,
                'scheduler_errors':errors[-3:],'password_enabled':bool(settings.password),
                'capabilities':{'desktop':settings.desktop_enabled,'browser_hosts':list(settings.browser_hosts),
                                'workspace':str(settings.data_dir/'workspace'),
                                'skill_writes':settings.skill_writes_enabled and not bool(settings.freeze_manifest)},
                'triggers':triggers.status(),
                'skills':SkillLoader(settings.skills_dir, settings.data_dir/'skills').index()}

    @app.post('/api/check-model')
    async def check_model(payload: dict):
        provider=payload.get('provider',settings.provider)
        config=settings.runtime(provider)['models'][0]
        model=HTTPModel(ModelConfig(**config))
        started=time.monotonic()
        try:
            await model.decide({'goal':'Reply DONE. This is a connection check; do not use tools.'},[])
        except Exception as error:
            # Provider HTTP errors may include key-bearing URLs. Never echo them to users/logs.
            raise HTTPException(502,'Provider check failed ('+type(error).__name__+'). Check the server key, model and provider account.') from None
        return {'ok':True,'provider':provider,'latency_ms':round((time.monotonic()-started)*1000),'usage':model.usage}

    @app.get('/api/sessions')
    async def sessions(): return manager.store.list()

    @app.post('/api/sessions',status_code=202)
    async def submit(payload: Task):
        if not payload.goal.strip(): raise ValueError('Task cannot be blank')
        return manager.submit(**payload.model_dump())

    @app.get('/api/sessions/{run_id}')
    async def detail(run_id: str): return manager.detail(run_id)

    @app.post('/api/sessions/{run_id}/stop')
    async def stop(run_id: str): manager.cancel(run_id);return {'ok':True}

    @app.post('/api/sessions/{run_id}/resume',status_code=202)
    async def resume(run_id: str): manager.resume(run_id);return {'ok':True}

    @app.post('/api/sessions/{run_id}/messages',status_code=202)
    async def followup(run_id: str, payload: Reply):
        return manager.followup(run_id, payload.value)

    @app.post('/api/sessions/{run_id}/reply/{request_id}')
    async def reply(run_id: str,request_id: str,payload: Reply):
        await manager.reply(run_id,request_id,payload.value);return {'ok':True}

    @app.get('/api/sessions/{run_id}/artifacts/{filename:path}')
    async def artifact(run_id: str,filename: str):
        manager.store.get(run_id)
        root=manager.runs._path(run_id).parent.resolve();target=(root/filename).resolve()
        allowed=target.suffix.lower() in {'.png','.jpg','.jpeg'} or filename in {'replay.html','summary.md','run.jsonl'}
        document=target.suffix.lower()=='.pdf' and target.parent==root/'steps'/'downloads'
        allowed=allowed or document
        if not target.is_relative_to(root) or not target.is_file() or not allowed:
            raise HTTPException(404,'Artifact not found')
        return FileResponse(target, filename=target.name if document else None,
                            media_type='application/pdf' if document else None)

    @app.get('/api/schedules')
    async def schedules(): return list(scheduler.jobs().values())

    @app.post('/api/schedules',status_code=201)
    async def add_schedule(payload: Schedule):
        from croniter import croniter
        try: zone=ZoneInfo(payload.timezone)
        except (ZoneInfoNotFoundError,ValueError): raise ValueError('Unknown timezone')
        if not payload.goal.strip(): raise ValueError('Task cannot be blank')
        if payload.mode=='agent': settings.runtime(payload.provider)
        if payload.skill: SkillLoader(settings.skills_dir).load(payload.skill)
        if payload.kind=='cron':
            if not payload.cron or len(payload.cron.split())!=5 or not croniter.is_valid(payload.cron):
                raise ValueError('Enter a valid five-field cron expression')
            when=croniter(payload.cron,datetime.now(zone)).get_next(float)
        else:
            if not payload.when: raise ValueError('Choose a future date and time')
            dt=datetime.fromisoformat(payload.when)
            when=timestamp(dt if dt.tzinfo else dt.replace(tzinfo=zone))
            if when<=time.time(): raise ValueError('Schedule must be in the future')
        task=payload.model_dump(exclude={'kind','when','cron','timezone'})
        async with schedule_lock:
            job_id=scheduler.add(payload.goal,when,{'task':task},payload.cron if payload.kind=='cron' else None,payload.timezone)
        return scheduler.jobs()[job_id]

    @app.post('/api/schedules/{job_id}/{action}')
    async def schedule_action(job_id: str,action: str):
        if action not in {'pause','resume','delete'}: raise HTTPException(404,'Unknown schedule action')
        async with schedule_lock:
            jobs=scheduler.jobs()
            if job_id not in jobs: raise HTTPException(404,'Schedule not found')
            job=jobs[job_id]
            if job['status']=='dispatching': raise HTTPException(409,'Dispatch is uncertain; inspect sessions before changing it')
            if action=='delete': del jobs[job_id]
            elif action=='pause':
                if job['status']!='pending': raise ValueError('Only pending schedules can be paused')
                job['status']='paused'
            else:
                if job['status']!='paused': raise ValueError('Only paused schedules can be resumed')
                if job['cron']:
                    from croniter import croniter
                    job['when']=croniter(job['cron'],datetime.now(ZoneInfo(job.get('timezone','UTC')))).get_next(float)
                elif job['when']<=time.time(): raise ValueError('One-time schedule is past due; create a new future schedule')
                job['status']='pending'
            atomic_json(scheduler.path,jobs)
        return {'ok':True}

    app.mount('/lab',manager.demo)
    static=Path(__file__).with_name('static')
    app.mount('/assets',StaticFiles(directory=static),name='assets')

    @app.get('/')
    async def index(): return FileResponse(static/'index.html')
    return app
