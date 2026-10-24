"""Optional event/chat sources feeding the same serialized, durable agent queue."""
import asyncio
import json
import os
from pathlib import Path
import re

from harness.handoff.channel import HumanChannel
from harness.handoff.telegram import TelegramTransport
from harness.tools.files import FileTools
from harness.triggers.events import EmailTrigger, FileWatcher, WebhookTrigger


class ReplyRouter:
    def __init__(self, manager):
        self.manager=manager

    def reply(self, request_id, value):
        for path in self.manager.runs.root.glob('*/handoff.json'):
            if HumanChannel(path).reply(request_id,value):
                return True
        return False


class TriggerService:
    def __init__(self, settings, manager):
        self.settings,self.manager=settings,manager
        self.tasks=[];self.sources=[];self.webhooks={};self.transport=None;self.errors={}
        configs=json.loads(Path(settings.triggers_file).read_text(encoding='utf-8-sig')) if settings.triggers_file else []
        if not isinstance(configs,list):raise ValueError('Trigger configuration must be a JSON array')
        workspace=FileTools(settings.data_dir/'workspace')
        names=set()
        for cfg in configs:
            name=cfg.get('id','') if isinstance(cfg,dict) else ''
            if not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,79}',name) or name in names:
                raise ValueError('Trigger IDs must be unique lowercase names')
            names.add(name)
            if not isinstance(cfg.get('goal'),str) or not cfg['goal'].strip():raise ValueError('Every trigger needs a goal')
            kind=cfg.get('type');state=settings.data_dir/'trigger-state'/(name+'.json')
            cfg=dict(cfg)
            if kind=='file':
                directory=workspace.resolve(cfg.get('directory','inbox'));directory.mkdir(parents=True,exist_ok=True)
                pattern=cfg.get('pattern','*')
                if not isinstance(pattern,str) or '..' in Path(pattern).parts or Path(pattern).is_absolute():
                    raise ValueError('File trigger pattern must stay inside its directory')
                source=FileWatcher(directory,state,cfg['goal'],pattern)
            elif kind=='email':
                if not all(cfg.get(k) for k in ('host','username_env','password_env','subject')):
                    raise ValueError('Email trigger needs host, credential environment references and subject')
                source=EmailTrigger(state)
            elif kind=='webhook':
                secret=os.getenv(cfg.get('secret_env',''))
                if not secret:raise ValueError('Set the webhook signing-secret environment variable')
                source=WebhookTrigger(state,secret,bind_event_id=True)
                self.webhooks[name]=(cfg,source)
            else:raise ValueError('Trigger type must be file, email or webhook')
            cfg['interval']=max(5 if kind=='email' else .1,float(cfg.get('interval',30 if kind=='email' else 1)))
            self.sources.append((cfg,source))

    async def dispatch(self, cfg, goal, inputs):
        # Prefix external IDs by configured source so independent sources cannot collide.
        inputs=dict(inputs)
        trigger_id='source:'+cfg['id']+':'+inputs.pop('trigger_id')
        return self.manager.submit(goal,cfg.get('skill'),inputs,cfg.get('provider'),'agent',trigger_id)

    async def poll_once(self, cfg, source):
        async def dispatch(goal,inputs):return await self.dispatch(cfg,goal,inputs)
        if cfg['type']=='file':
            return await source.poll_once(dispatch)
        return await source.poll_imap(cfg['host'],os.environ[cfg['username_env']],os.environ[cfg['password_env']],
                                      cfg['subject'],cfg['goal'],dispatch,cfg.get('mailbox','INBOX'))

    async def poll(self, cfg, source):
        while True:
            try:
                await self.poll_once(cfg,source);self.errors.pop(cfg['id'],None)
            except Exception as error:
                self.errors[cfg['id']]=type(error).__name__
            await asyncio.sleep(cfg['interval'])

    async def start(self):
        if self.settings.telegram_enabled:
            token=os.getenv('TELEGRAM_BOT_TOKEN')
            if not token or not self.settings.telegram_chat_id:
                raise ValueError('Telegram requires TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID')
            self.transport=TelegramTransport(token,self.settings.telegram_chat_id,state_path=self.settings.data_dir/'telegram-offset.json')
            self.manager.transport=self.transport
            self.tasks.append(asyncio.create_task(self.poll_telegram()))
        for cfg,source in self.sources:
            if cfg['type']!='webhook':self.tasks.append(asyncio.create_task(self.poll(cfg,source)))

    async def poll_telegram(self):
        async def dispatch(goal,inputs):
            return self.manager.submit(goal,inputs=inputs,trigger_id=inputs['trigger_id'])
        while True:
            try:
                await self.transport.poll_once(ReplyRouter(self.manager),dispatch)
                self.errors.pop('telegram',None)
            except Exception as error:self.errors['telegram']=type(error).__name__
            await asyncio.sleep(1)

    async def webhook(self, name, body, signature, event_id):
        cfg,source=self.webhooks[name]
        async def dispatch(goal,inputs):return await self.dispatch(cfg,goal,inputs)
        return await source.receive(body,signature,event_id,cfg['goal'],dispatch)

    def status(self):
        return {'sources':[{'id':c['id'],'type':c['type'],'error':self.errors.get(c['id'])} for c,_ in self.sources],
                'telegram_enabled':self.settings.telegram_enabled,'telegram_error':self.errors.get('telegram')}

    async def close(self):
        for task in self.tasks:task.cancel()
        await asyncio.gather(*self.tasks,return_exceptions=True)
        if self.transport:await self.transport.close()
