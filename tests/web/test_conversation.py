from pathlib import Path
import time

from fastapi.testclient import TestClient

from harness.core.run_manager import RunStore
from harness.web.app import create_app
from harness.web.settings import Settings


HEADERS={'X-Agent-Request':'1'}


def test_followup_persists_transcript_and_refuses_uncertain_or_active_runs(tmp_path,monkeypatch):
    monkeypatch.setenv('ANTHROPIC_API_KEY','fixture-only')
    monkeypatch.delenv('DEEPSEEK_API_KEY',raising=False)
    settings=Settings(tmp_path/'data',Path(__file__).resolve().parents[2]/'skills',allowed_hosts=('testserver','localhost','127.0.0.1'))
    async def runner(config,goal,run_id=None,skill_name=None):
        store=RunStore(config['runs']);state=store.load(run_id)
        state.answer='Answer to '+state.goal
        state.messages.append({'role':'assistant','text':state.answer})
        state.status='completed';store.save(state);return state
    def wait(client,run_id):
        for _ in range(200):
            detail=client.get('/api/sessions/'+run_id).json()
            if detail['status']=='completed':return detail
            time.sleep(.01)
        raise AssertionError(detail)
    with TestClient(create_app(settings,runner)) as client:
        run=client.post('/api/sessions',json={'goal':'First question'},headers=HEADERS).json()['id']
        assert wait(client,run)['answer']=='Answer to First question'
        assert client.post('/api/sessions/'+run+'/messages',json={'value':'Next question'},headers=HEADERS).status_code==202
        detail=wait(client,run)
        assert [m['role'] for m in detail['messages']]==['user','assistant','user','assistant']
        assert detail['answer']=='Answer to Next question'
        assert client.post('/api/sessions/'+run+'/messages',json={'value':'  '},headers=HEADERS).status_code==422
    with TestClient(create_app(settings,runner)) as client:
        assert client.get('/api/sessions/'+run).json()['answer']=='Answer to Next question'
        manager=client.app.state.manager
        state=manager.runs.load(run);state.pending_action={'name':'uncertain'};manager.runs.save(state)
        assert client.post('/api/sessions/'+run+'/messages',json={'value':'Try again'},headers=HEADERS).status_code==422


def test_freeze_disables_runtime_skill_writes(tmp_path):
    cfg=Settings(tmp_path/'data',tmp_path/'skills',freeze_manifest='freeze_manifest.json')
    assert cfg.runtime(demo=True)['skill_writes_enabled'] is False
