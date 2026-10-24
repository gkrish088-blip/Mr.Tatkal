import asyncio
from dataclasses import asdict
import importlib
import json
from pathlib import Path
import time

from harness.cli import run_goal
from harness.core.run_manager import RunStore
from harness.handoff.channel import HumanChannel
from harness.log.redact import Redactor
from harness.log.runlog import RunLog
from harness.web.store import SessionStore


class RunManager:
    def __init__(self, settings, runner=None):
        self.settings=settings
        self.store=SessionStore(settings.data_dir/'sessions.sqlite3')
        self.runs=RunStore(settings.data_dir/'runs')
        self.queue=asyncio.Queue()
        self.runner=runner or run_goal
        self.active=None
        self.execution=None
        self.worker=None
        self.closing=False
        self.transport=None
        self.demo=importlib.import_module('mock.gui_demo').DemoPlugin()

    async def start(self):
        for row in reversed(self.store.list()):
            if row['status']=='queued':
                if row['mode']=='demo':
                    self.demo.prepare(row['id'],self.settings.internal_url)
                self.queue.put_nowait(row['id'])
            elif row['status']=='running':
                state=self.runs.load(row['id'])
                state.status='needs_reconciliation'
                self.runs.save(state)
                self.store.update(row['id'],status=state.status,finished=time.time(),error='Server restarted during execution; inspect artifacts before retrying')
        self.worker=asyncio.create_task(self._work())

    async def close(self):
        self.closing=True
        if self.execution: self.execution.cancel()
        if self.worker: self.worker.cancel()
        await asyncio.gather(*[t for t in (self.execution,self.worker) if t],return_exceptions=True)

    def submit(self, goal, skill=None, inputs=None, provider=None, mode='agent', trigger_id=None):
        if trigger_id:
            existing=self.store.by_trigger(trigger_id)
            if existing: return existing
        provider=provider or self.settings.provider
        if mode=='agent':
            self.settings.runtime(provider)
            if skill:
                from harness.skillrt.loader import SkillLoader
                SkillLoader(self.settings.skills_dir, self.settings.data_dir/'skills').load(skill)
        state=self.runs.create(goal,inputs or {})
        if mode=='demo':
            demo=self.demo.prepare(state.run_id,self.settings.internal_url)
            state.inputs=demo['inputs'];skill=demo['skill'];self.runs.save(state)
        state.status='queued';self.runs.save(state)
        row=self.store.create(state.run_id,goal,skill,provider,mode,trigger_id)
        self.queue.put_nowait(state.run_id)
        return row

    def detail(self, run_id):
        row=self.store.get(run_id)
        state=self.runs.load(run_id)
        row.update(step=state.step,handoffs=state.handoffs,macro_index=state.macro_index,
                   runtime_status=state.status, pending_action=bool(state.pending_action),
                   events=state.history[-100:], answer=state.answer, blocked_reason=state.blocked_reason,
                   messages=state.messages, active_skills=state.active_skills)
        path=self.runs._path(run_id).parent
        channel=HumanChannel(path/'handoff.json')
        row['requests']=channel.pending()
        row['artifacts']=[p.relative_to(path).as_posix() for p in path.rglob('*')
                          if p.is_file() and p.suffix.lower() in {'.png','.jpg','.jpeg'}]
        row['has_replay']=(path/'replay.html').exists()
        return row

    async def _work(self):
        while not self.closing:
            run_id=await self.queue.get()
            try:
                if self.store.get(run_id)['status']!='queued': continue
                self.active=run_id
                self.execution=asyncio.create_task(self._execute(run_id))
                try: await self.execution
                except asyncio.CancelledError:
                    if self.closing: raise
            finally:
                self.active=None;self.execution=None;self.queue.task_done()

    async def _execute(self, run_id):
        row=self.store.get(run_id)
        self.store.update(run_id,status='running',started=time.time(),error=None)
        try:
            config=self.settings.runtime(row['provider'],demo=row['mode']=='demo')
            if row['mode']=='agent' and self.transport:
                config['handoff_transport']=self.transport
            state=await self.runner(config,row['goal'],run_id=run_id,skill_name=row['skill'])
            self.store.update(run_id,status=state.status,finished=time.time())
        except BaseException as error:
            state=self.runs.load(run_id)
            state.status='needs_reconciliation' if state.pending_action else ('cancelled' if isinstance(error,asyncio.CancelledError) else 'failed')
            self.runs.save(state)
            import os
            redactor=Redactor([v for k,v in os.environ.items() if any(w in k for w in ('KEY','PASSWORD','TOKEN','SECRET')) and v])
            message='Stopped by operator' if isinstance(error,asyncio.CancelledError) else redactor.redact(f'{type(error).__name__}: {error}')
            state.blocked_reason=message[:1000]
            self.runs.save(state)
            self.store.update(run_id,status=state.status,finished=time.time(),error=message[:1000])
            RunLog(self.runs.root,run_id,redactor).summary(state)
            if isinstance(error,asyncio.CancelledError): raise

    def cancel(self, run_id):
        row=self.store.get(run_id)
        if row['status']=='queued':
            self.store.update(run_id,status='cancelled',finished=time.time())
            state=self.runs.load(run_id);state.status='cancelled';self.runs.save(state)
        elif self.active==run_id and self.execution:
            self.execution.cancel()
        else: raise ValueError('Only queued or running sessions can be stopped')

    def resume(self, run_id):
        row=self.store.get(run_id);state=self.runs.load(run_id)
        if row['status'] not in {'blocked','failed','cancelled','limit_reached'} or state.pending_action:
            raise ValueError('This session cannot be automatically resumed; uncertain actions need reconciliation')
        if row['mode']=='demo' and not self.demo.exists(run_id):
            raise ValueError('Start a new local test; the mock service restarted')
        self.store.update(run_id,status='queued',finished=None,error=None)
        state.status='queued';self.runs.save(state);self.queue.put_nowait(run_id)

    def followup(self, run_id, text):
        row=self.store.get(run_id);state=self.runs.load(run_id)
        if row['mode']!='agent' or row['status'] not in {'completed','blocked','failed','cancelled','limit_reached'} or state.pending_action:
            raise ValueError('Wait for this agent turn to finish; uncertain actions require reconciliation')
        if not text.strip():
            raise ValueError('Message cannot be blank')
        self.settings.runtime(row['provider'])
        if not state.messages:
            state.messages=[{'role':'user','text':state.goal}]
        state.messages.append({'role':'user','text':text.strip()})
        state.goal=text.strip();state.answer='';state.blocked_reason='';state.status='queued'
        self.runs.save(state)
        self.store.update(run_id,status='queued',started=None,finished=None,error=None,skill=None)
        self.queue.put_nowait(run_id)
        return self.store.get(run_id)

    async def reply(self, run_id, request_id, value):
        row=self.store.get(run_id)
        channel=HumanChannel(self.runs._path(run_id).parent/'handoff.json')
        request=next((r for r in channel.pending() if r['id']==request_id),None)
        if not request: raise ValueError('Request is expired or already answered')
        # Only the isolated demo plugin translates approval into a fictional payment.
        if row['mode']=='demo' and request['kind']=='external_approval' and value.lower() in {'yes','approve','approved','done'}:
            await self.demo.approve(run_id)
        if not channel.reply(request_id,value): raise ValueError('Reply rejected or request expired')
