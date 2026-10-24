import asyncio
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import time

from fastapi.testclient import TestClient
import pytest

from harness.core.run_manager import RunStore
from harness.web.app import create_app
from harness.web.settings import Settings
from harness.triggers.schedule import Scheduler

ROOT=Path(__file__).resolve().parents[2]
HEADERS={'X-Agent-Request':'1'}


def settings(tmp_path,**kwargs):
    return Settings(tmp_path/'data',ROOT/'skills',browser_mode='none',allowed_hosts=('testserver','127.0.0.1'),**kwargs)


async def fixture_runner(config,goal,run_id=None,skill_name=None):
    store=RunStore(config['runs']);state=store.load(run_id)
    await asyncio.sleep(.03)
    state.status='completed';state.step+=1;store.save(state);return state


def wait_status(client,run_id,status='completed'):
    deadline=time.monotonic()+5
    while time.monotonic()<deadline:
        result=client.get('/api/sessions/'+run_id).json()
        if result['status']==status:return result
        time.sleep(.02)
    raise AssertionError(result)


def test_server_demo_sessions_persist_and_no_key_required(tmp_path,monkeypatch):
    monkeypatch.delenv('ANTHROPIC_API_KEY',raising=False);monkeypatch.delenv('DEEPSEEK_API_KEY',raising=False)
    cfg=settings(tmp_path)
    with TestClient(create_app(cfg,fixture_runner)) as client:
        assert client.get('/').status_code==200
        assert client.get('/assets/app.js').status_code==200
        result=client.post('/api/sessions',json={'goal':'Local test','mode':'demo'},headers=HEADERS)
        assert result.status_code==202,result.text
        run_id=result.json()['id']
        detail=wait_status(client,run_id)
        assert detail['step']==1 and detail['mode']=='demo'
        assert 'inputs' not in detail
        assert client.get('/api/sessions/'+run_id+'/artifacts/state.json').status_code==404
        # No model key is accepted from the browser; server ownership is enforced by schema.
        assert client.post('/api/sessions',json={'goal':'x','mode':'demo','api_key':'ignored-key'},headers=HEADERS).status_code==422
        assert client.post('/api/sessions',json={'goal':'Agent task'},headers=HEADERS).status_code==422
    with TestClient(create_app(cfg,fixture_runner)) as client:
        assert client.get('/api/sessions').json()[0]['id']==run_id
        assert client.get('/api/sessions/'+run_id).json()['status']=='completed'


def test_auth_csrf_and_credential_non_disclosure(tmp_path,monkeypatch):
    secret='fixture-provider-canary-983456'
    monkeypatch.setenv('ANTHROPIC_API_KEY',secret)
    cfg=settings(tmp_path,password='fixture-operator-password')
    with TestClient(create_app(cfg,fixture_runner)) as client:
        assert client.get('/api/status').status_code==401
        assert client.post('/api/login',json={'password':cfg.password}).status_code==403
        assert client.post('/api/login',json={'password':'wrong'},headers=HEADERS).status_code==401
        response=client.post('/api/login',json={'password':cfg.password},headers=HEADERS)
        assert response.status_code==200
        assert 'HttpOnly' in response.headers['set-cookie'] and 'SameSite=strict' in response.headers['set-cookie']
        response=client.get('/api/status')
        assert secret not in response.text and 'key_env' not in response.text
        assert response.json()['providers']['claude']['configured']
        assert client.post('/api/sessions',json={'goal':'x','mode':'demo'},headers={**HEADERS,'Origin':'https://untrusted.test'}).status_code==403
        assert client.get('/api/status',headers={'Host':'evil.test'}).status_code==400
        assert client.post('/api/logout',headers=HEADERS).status_code==200
        assert client.get('/api/sessions').status_code==401
    with pytest.raises(ValueError,match='GUI_PASSWORD'):
        settings(tmp_path,host='0.0.0.0').validate()


def test_schedule_cron_timezone_pause_resume_and_persistence(tmp_path):
    cfg=settings(tmp_path)
    with TestClient(create_app(cfg,fixture_runner)) as client:
        payload={'goal':'Scheduled demo','mode':'demo','kind':'cron','cron':'0 11 * * *','timezone':'Asia/Kolkata'}
        response=client.post('/api/schedules',json=payload,headers=HEADERS)
        assert response.status_code==201,response.text
        job=response.json();job_id=job['id']
        from zoneinfo import ZoneInfo
        assert datetime.fromtimestamp(job['when'],ZoneInfo('Asia/Kolkata')).hour==11
        assert client.post(f'/api/schedules/{job_id}/pause',headers=HEADERS).status_code==200
        assert client.get('/api/schedules').json()[0]['status']=='paused'
    with TestClient(create_app(cfg,fixture_runner)) as client:
        assert client.get('/api/schedules').json()[0]['status']=='paused'
        assert client.post(f'/api/schedules/{job_id}/resume',headers=HEADERS).status_code==200
        assert client.post('/api/schedules',json={**payload,'cron':'invalid'},headers=HEADERS).status_code==422
        assert client.post('/api/schedules',json={**payload,'timezone':'Not/AZone'},headers=HEADERS).status_code==422
        assert client.post('/api/schedules',json={**payload,'kind':'once','when':'2020-01-01T11:00:00'},headers=HEADERS).status_code==422
        assert client.post(f'/api/schedules/{job_id}/delete',headers=HEADERS).status_code==200
        assert client.get('/api/schedules').json()==[]


def test_due_schedule_queues_exactly_once(tmp_path):
    cfg=settings(tmp_path)
    # An overdue persisted schedule fires after restart; a stable trigger ID prevents duplicate sessions.
    scheduler=Scheduler(cfg.data_dir/'schedules.json')
    job_id=scheduler.add('Due local test',time.time()-1,{'task':{'mode':'demo','provider':'claude'}})
    with TestClient(create_app(cfg,fixture_runner)) as client:
        deadline=time.monotonic()+5
        while not client.get('/api/sessions').json() and time.monotonic()<deadline:time.sleep(.03)
        rows=client.get('/api/sessions').json();assert len(rows)==1
        wait_status(client,rows[0]['id'])
        assert client.get('/api/schedules').json()[0]['status']=='done'
    with TestClient(create_app(cfg,fixture_runner)) as client:
        time.sleep(.1);assert len(client.get('/api/sessions').json())==1


def test_restart_does_not_repeat_uncertain_action(tmp_path):
    cfg=settings(tmp_path)
    app=create_app(cfg,fixture_runner);manager=app.state.manager
    row=manager.submit('In-flight operation',mode='demo')
    manager.store.update(row['id'],status='running')
    state=manager.runs.load(row['id']);state.pending_action={'name':'browser_click'};manager.runs.save(state)
    with TestClient(create_app(cfg,fixture_runner)) as client:
        detail=client.get('/api/sessions/'+row['id']).json()
        assert detail['status']=='needs_reconciliation'
        assert client.post('/api/sessions/'+row['id']+'/resume',headers=HEADERS).status_code==422


def test_server_owned_provider_selection(tmp_path,monkeypatch):
    monkeypatch.setenv('ANTHROPIC_API_KEY','fixture-claude')
    monkeypatch.setenv('DEEPSEEK_API_KEY','fixture-deepseek')
    cfg=settings(tmp_path)
    primary,fallback=cfg.runtime('deepseek')['models']
    assert primary['key_env']=='DEEPSEEK_API_KEY' and primary['protocol']=='chat'
    assert fallback['key_env']=='ANTHROPIC_API_KEY' and fallback['protocol']=='messages'
    assert cfg.runtime(demo=True)['models']==[]


def test_run_owned_handoff_images_and_pdf_downloads_only(tmp_path):
    from harness.handoff.channel import atomic_json
    cfg=settings(tmp_path)
    app=create_app(cfg,fixture_runner)
    with TestClient(app) as client:
        run=client.post('/api/sessions',json={'goal':'Artifacts fixture','mode':'demo'},headers=HEADERS).json()['id']
        wait_status(client,run)
        root=app.state.manager.runs._path(run).parent
        folder=root/'steps'/'downloads';folder.mkdir(parents=True)
        (folder/'ticket.pdf').write_bytes(b'%PDF-test-document')
        (root/'private.pdf').write_bytes(b'PRIVATE')
        image=root/'steps'/'payment.png';image.write_bytes(b'fixture-image')
        outside=tmp_path/'outside.png';outside.write_bytes(b'PRIVATE-OUTSIDE')
        atomic_json(root/'handoff.json',{'image-request':{'id':'image-request','kind':'external_approval',
                    'text':'Fictional payment only','status':'pending','deadline':time.time()+120,
                    'attachments':[str(image),str(outside),str(root/'state.json'),'https://example.test/image.png']}})
        detail=client.get('/api/sessions/'+run).json()
        assert detail['downloads']==['steps/downloads/ticket.pdf']
        assert detail['requests'][0]['attachments']==['steps/payment.png']
        response=client.get('/api/sessions/'+run+'/artifacts/steps/downloads/ticket.pdf')
        assert response.content==b'%PDF-test-document'
        assert response.headers['content-type']=='application/pdf'
        assert 'attachment;' in response.headers['content-disposition']
        assert client.get('/api/sessions/'+run+'/artifacts/private.pdf').status_code==404
        assert client.get('/api/sessions/'+run+'/artifacts/state.json').status_code==404


def test_installed_browser_channel_is_explicit_configuration(tmp_path,monkeypatch):
    monkeypatch.setenv('BROWSER_CHANNEL','chrome')
    monkeypatch.setenv('DATA_DIR',str(tmp_path/'data'))
    cfg=Settings.from_env(env_file=tmp_path/'absent.env')
    assert cfg.browser_channel=='chrome'
    assert cfg.runtime(demo=True)['browser']['channel']=='chrome'


async def test_cron_recurrence_keeps_india_timezone(tmp_path):
    from zoneinfo import ZoneInfo
    zone=ZoneInfo('Asia/Kolkata')
    now=datetime(2026,10,24,11,0,tzinfo=zone).timestamp()
    scheduler=Scheduler(tmp_path/'schedules.json',clock=lambda:now)
    job_id=scheduler.add('Daily task',now,cron='0 11 * * *',timezone_name='Asia/Kolkata')
    async def dispatch(*args):pass
    await scheduler.tick(dispatch)
    next_run=datetime.fromtimestamp(scheduler.jobs()[job_id]['when'],zone)
    assert next_run==datetime(2026,10,25,11,0,tzinfo=zone)


def test_queue_serialization_and_cancelled_task_not_executed(tmp_path):
    cfg=settings(tmp_path);executed=[];active=0;peak=0
    async def serial(config,goal,run_id=None,skill_name=None):
        nonlocal active,peak
        active+=1;peak=max(peak,active)
        try:
            await asyncio.sleep(.15);executed.append(goal)
            store=RunStore(config['runs']);state=store.load(run_id);state.status='completed';store.save(state);return state
        finally:active-=1
    with TestClient(create_app(cfg,serial)) as client:
        first=client.post('/api/sessions',json={'goal':'First','mode':'demo'},headers=HEADERS).json()
        second=client.post('/api/sessions',json={'goal':'Cancelled before start','mode':'demo'},headers=HEADERS).json()
        assert client.post('/api/sessions/'+second['id']+'/stop',headers=HEADERS).status_code==200
        wait_status(client,first['id'])
        assert client.get('/api/sessions/'+second['id']).json()['status']=='cancelled'
    assert executed==['First'] and peak==1


def test_queued_session_is_recovered_after_restart(tmp_path):
    cfg=settings(tmp_path);app=create_app(cfg,fixture_runner)
    row=app.state.manager.submit('Saved queued task',mode='demo')
    with TestClient(create_app(cfg,fixture_runner)) as client:
        assert wait_status(client,row['id'])['status']=='completed'
