"""Event sources feed the real queue; all email/Telegram transports are local fixtures."""
import asyncio
import hashlib
import hmac
import json
from pathlib import Path
import time

from fastapi.testclient import TestClient
import httpx
import pytest

from harness.core.run_manager import RunStore
from harness.handoff.channel import HumanChannel
from harness.handoff.telegram import TelegramTransport
from harness.triggers.events import EmailTrigger,EventTrigger
from harness.web.app import create_app
from harness.web.settings import Settings


def config(tmp_path,sources,**kwargs):
    path=tmp_path/'triggers.json';path.write_text(json.dumps(sources))
    return Settings(tmp_path/'data',Path(__file__).resolve().parents[2]/'skills',
                    triggers_file=str(path),allowed_hosts=('testserver','localhost','127.0.0.1'),**kwargs)


async def runner(config,goal,run_id=None,skill_name=None):
    store=RunStore(config['runs']);state=store.load(run_id)
    state.answer=Path(state.inputs['path']).read_text() if 'path' in state.inputs else 'Event handled'
    state.status='completed';store.save(state);return state


def wait_runs(client,count):
    for _ in range(200):
        rows=client.get('/api/sessions').json()
        if len(rows)==count and all(r['status']=='completed' for r in rows):return rows
        time.sleep(.02)
    raise AssertionError(rows)


def test_file_events_survive_restart_and_preserve_inputs(tmp_path,monkeypatch):
    monkeypatch.setenv('ANTHROPIC_API_KEY','fixture-only')
    cfg=config(tmp_path,[{'id':'inbox','type':'file','directory':'inbox','pattern':'*.txt','goal':'Read arriving note','interval':.1}])
    with TestClient(create_app(cfg,runner)) as client:
        path=cfg.data_dir/'workspace/inbox/note.txt';path.write_text('First note')
        rows=wait_runs(client,1)
        detail=client.get('/api/sessions/'+rows[0]['id']).json()
        assert detail['answer']=='First note'
        assert rows[0]['trigger_id'].startswith('source:inbox:file:')
    with TestClient(create_app(cfg,runner)) as client:
        time.sleep(.2);assert len(client.get('/api/sessions').json())==1
        path.write_text('Changed note');wait_runs(client,2)
        assert client.get('/api/status').json()['triggers']['sources']==[{'id':'inbox','type':'file','error':None}]


def test_signed_webhook_replay_identity_authentication_and_limits(tmp_path,monkeypatch):
    secret='fixture-webhook-secret'
    monkeypatch.setenv('ANTHROPIC_API_KEY','fixture-only');monkeypatch.setenv('WEBHOOK_TEST_SECRET',secret)
    cfg=config(tmp_path,[{'id':'updates','type':'webhook','secret_env':'WEBHOOK_TEST_SECRET','goal':'Record update'}],password='fixture-operator-password')
    body=b'{"value":42}'
    def headers(event_id='one',data=body):
        return {'X-Event-ID':event_id,'X-Signature':hmac.new(secret.encode(),event_id.encode()+b'.'+data,hashlib.sha256).hexdigest()}
    with TestClient(create_app(cfg,runner)) as client:
        # Signatures authorize this incoming endpoint without an operator login or browser CSRF header.
        assert client.get('/api/status').status_code==401
        assert client.post('/hooks/updates',content=body,headers={'X-Event-ID':'one'}).status_code==403
        assert client.post('/hooks/updates',content=body,headers=headers()).json()=={'accepted':True}
        assert client.post('/hooks/updates',content=body,headers=headers()).json()=={'accepted':False}
        assert client.post('/hooks/updates',content=body,headers={**headers(),'X-Event-ID':'tampered'}).status_code==403
        assert client.post('/hooks/updates',content=b'[]',headers=headers('two',b'[]')).status_code==422
        assert client.post('/hooks/updates',content=b'x'*1000001,headers=headers()).status_code==413
        assert client.post('/hooks/missing',content=body,headers=headers()).status_code==404
        assert secret not in client.get('/health').text
        rows=client.app.state.manager.store.list();assert len(rows)==1
        state=client.app.state.manager.runs.load(rows[0]['id']);assert state.inputs['value']==42


async def test_concurrent_event_intents_are_not_lost(tmp_path):
    trigger=EventTrigger(tmp_path/'events.json');seen=[]
    async def dispatch(goal,inputs):
        await asyncio.sleep(.01);seen.append(inputs['trigger_id'])
    await asyncio.gather(*(trigger.emit(str(i),'Record',{},dispatch) for i in range(5)))
    assert set(seen)==set(map(str,range(5)))
    assert len(json.loads(trigger.path.read_text()))==5


async def test_imap_reads_message_text_without_marking_read(tmp_path,monkeypatch):
    class Mailbox:
        def __init__(self,host):assert host=='mail.fixture.invalid'
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def login(self,user,password):assert (user,password)==('fixture-user','fixture-password')
        def select(self,mailbox,readonly):assert readonly is True
        def uid(self,method,*args):
            if method=='search':return 'OK',[b'7']
            assert args[-1]=='(BODY.PEEK[])'
            return 'OK',[(b'7',b'Subject: Summary\r\nFrom: example@example.test\r\nContent-Type: text/plain; charset=utf-8\r\n\r\nFictional message content.')]
    monkeypatch.setattr('imaplib.IMAP4_SSL',Mailbox)
    source=EmailTrigger(tmp_path/'mail.json');dispatched=[]
    async def dispatch(goal,inputs):dispatched.append(inputs)
    assert await source.poll_imap('mail.fixture.invalid','fixture-user','fixture-password','Summary','Summarize',dispatch)==1
    assert dispatched[0]['message']['text']=='Fictional message content.'
    assert await source.poll_imap('mail.fixture.invalid','fixture-user','fixture-password','Summary','Summarize',dispatch)==0


def test_telegram_idle_chat_dispatch_and_reply_share_one_transport(tmp_path,monkeypatch):
    monkeypatch.setenv('ANTHROPIC_API_KEY','fixture-only');monkeypatch.setenv('TELEGRAM_BOT_TOKEN','fixture-token')
    emitted={'run':False,'reply':False};sent=[];transport=[]
    def http(request):
        if request.url.path.endswith('/sendMessage'):
            message=json.loads(request.content);sent.append(message['text'])
            return httpx.Response(200,json={'ok':True})
        updates=[]
        if not emitted['run']:
            updates=[{'update_id':1,'message':{'chat':{'id':'123'},'text':'/run Choose a color'}}];emitted['run']=True
        elif sent and not emitted['reply']:
            request_id=sent[0].split()[1]
            updates=[{'update_id':2,'message':{'chat':{'id':'123'},'text':f'/reply {request_id} blue'}}];emitted['reply']=True
        return httpx.Response(200,json={'ok':True,'result':updates})
    def factory(token,chat_id,**kwargs):
        result=TelegramTransport(token,chat_id,client=httpx.AsyncClient(transport=httpx.MockTransport(http)),**kwargs)
        transport.append(result);return result
    monkeypatch.setattr('harness.web.triggers.TelegramTransport',factory)
    cfg=config(tmp_path,[],telegram_enabled=True,telegram_chat_id='123')
    async def asking(config,goal,run_id=None,skill_name=None):
        store=RunStore(config['runs']);state=store.load(run_id)
        reply=await HumanChannel(store._path(run_id).parent/'handoff.json',config['handoff_transport']).ask('text','Which color?',timeout=5)
        state.answer=reply['value'];state.status='completed';store.save(state);return state
    with TestClient(create_app(cfg,asking)) as client:
        rows=wait_runs(client,1)
        assert client.get('/api/sessions/'+rows[0]['id']).json()['answer']=='blue'
        assert len(transport)==1 and len(sent)==1
        assert 'fixture-token' not in client.get('/api/status').text
    assert json.loads((cfg.data_dir/'telegram-offset.json').read_text())['offset']==3


def test_bad_trigger_configuration_rejected_without_network(tmp_path,monkeypatch):
    with pytest.raises(ValueError,match='type'):
        create_app(config(tmp_path,[{'id':'unknown','type':'bad','goal':'Test'}]),runner)
    with pytest.raises(PermissionError):
        create_app(config(tmp_path,[{'id':'escaped','type':'file','directory':'../outside','goal':'Test'}]),runner)
    monkeypatch.delenv('WEBHOOK_UNSET_SECRET',raising=False)
    with pytest.raises(ValueError,match='signing-secret'):
        create_app(config(tmp_path,[{'id':'updates','type':'webhook','secret_env':'WEBHOOK_UNSET_SECRET','goal':'Test'}]),runner)
