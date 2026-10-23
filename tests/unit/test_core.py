import json
from pathlib import Path
import pytest
import httpx
from harness.core.types import Decision, ToolCall, ToolRegistry
from harness.core.run_manager import RunStore
from harness.core.loop import Engine
from harness.core.macro import MacroRunner, bind
from harness.skillrt.loader import SkillLoader
from harness.log.runlog import RunLog
from harness.log.redact import Redactor
from harness.models.adapter import HTTPModel, ModelConfig, ModelError
from harness.models.failover import FailoverModel


def skill(root, macro=None):
    folder = root / "skills" / "example"
    folder.mkdir(parents=True)
    (folder / "SKILL.md").write_text('---\nname: example\ndescription: Example task\ngates: []\n---\n# Goal\nDo a task\n', encoding='utf-8')
    if macro:
        import yaml
        (folder / "macro.yaml").write_text(yaml.safe_dump(macro), encoding='utf-8')
    return SkillLoader(root / "skills")


def engine(tmp_path, model=None, capture=None):
    registry = ToolRegistry()
    registry.capture = capture
    store = RunStore(tmp_path / "runs")
    state = store.create("test")
    loader = skill(tmp_path)
    log = RunLog(tmp_path / "runs", state.run_id, Redactor(["canary-value"]))
    return Engine(registry, store, log, loader, model, max_steps=12), state


def test_skill_loader_and_bind(tmp_path):
    loader = skill(tmp_path)
    assert loader.index() == [{"name": "example", "description": "Example task"}]
    assert loader.load("example").body.startswith("# Goal")
    with pytest.raises(ValueError): loader.load("../escape")
    (tmp_path / 'skills/example/SKILL.md').write_text('malformed')
    with pytest.raises(ValueError): loader.index()
    assert bind({'age': '${inputs.age}', 'text':'Hi ${inputs.name}'}, {'inputs': {'age': 23, 'name':'Test'}}) == {'age':23,'text':'Hi Test'}


async def test_state_crash_reconciliation_and_redaction(tmp_path):
    eng, state = engine(tmp_path)
    async def echo(text): return {'text':text}
    eng.registry.register('echo',echo)
    assert eng.registry.schemas()[-1]['function']['parameters']['required'] == ['text']
    assert (await eng.act(state,ToolCall('echo',{'text':'canary-value'}),'Record test')).ok
    assert 'canary-value' not in eng.store._path(state.run_id).read_text()
    state.pending_action = {'name':'uncertain'}
    eng.store.save(state)
    restored = eng.store.load(state.run_id)
    assert (await eng.run(restored)).status == 'needs_reconciliation'


async def test_macro_failed_checkpoint_recovers_then_resumes(tmp_path):
    observation = {'text':'before'}
    async def capture(): return observation.copy()
    class Recovery:
        async def decide(self,*args): return Decision('Repair checkpoint',[ToolCall('repair')])
    eng, state = engine(tmp_path, Recovery(), capture)
    async def no_op(): return {}
    async def repair(): observation['text']='ready'; return {}
    async def finish(): observation['text']='done'; return {}
    for name,fn in [('noop',no_op),('repair',repair),('finish',finish)]: eng.registry.register(name,fn)
    sk = eng.loader.load('example')
    sk.macro = [{'tool':'noop','assert':{'text':'ready'}},{'tool':'finish','assert':{'text':'done'}}]
    assert (await MacroRunner(eng).run(state,sk)).status == 'completed'
    assert state.macro_index == 2 and state.step == 3


async def test_stuck_guard_is_bounded(tmp_path):
    class Repeater:
        async def decide(self,*args): return Decision('Try unchanged action',[ToolCall('noop')])
    eng,state = engine(tmp_path,Repeater())
    async def noop(): return {}
    eng.registry.register('noop',noop)
    assert (await eng.run(state)).status == 'blocked'
    assert state.step < 12


async def test_model_failover_and_malformed_repair(monkeypatch):
    monkeypatch.setenv('TEST_MODEL_KEY','dummy')
    calls=[]
    def transport(request):
        calls.append(request.url.host)
        if request.url.host == 'primary.test': return httpx.Response(429)
        return httpx.Response(200,json={'choices':[{'message':{'content':'Verified result','tool_calls':[{'function':{'name':'file_read','arguments':'{"path":"note.txt"}'}}]}}]})
    async with httpx.AsyncClient(transport=httpx.MockTransport(transport)) as client:
        p=HTTPModel(ModelConfig('https://primary.test/v1','test','TEST_MODEL_KEY'),client)
        f=HTTPModel(ModelConfig('https://fallback.test/v1','test','TEST_MODEL_KEY'),client)
        decision=await FailoverModel(p,f,retries=1,base_delay=0).decide({},[])
        assert decision.calls[0].arguments == {'path':'note.txt'}
        assert calls == ['primary.test','primary.test','fallback.test']


async def test_budget_and_gate_prevent_action(tmp_path):
    eng,state=engine(tmp_path)
    count=[]
    async def gated(): count.append(1); return {}
    eng.registry.register('gated',gated)
    eng.gates.add('gated')
    assert not (await eng.act(state,ToolCall('gated'),'Needs permission')).ok
    assert not count
    eng.max_steps=0
    assert not (await eng.act(state,ToolCall('use_skill',{'name':'example'}),'Load')).ok


async def test_action_deadline_preserves_uncertain_intent(tmp_path):
    import asyncio
    eng,state=engine(tmp_path)
    async def slow(): await asyncio.sleep(1); return {}
    eng.registry.register('slow',slow)
    eng.max_seconds=.02
    assert not (await eng.act(state,ToolCall('slow'),'Test bounded deadline')).ok
    assert state.status=='needs_reconciliation'
    assert eng.store.load(state.run_id).pending_action['name']=='slow'


async def test_denied_handoff_stops_following_actions(tmp_path):
    eng,state=engine(tmp_path)
    class Denier:
        async def ask(self,*args,**kwargs): return {'status':'replied','approved':False,'value':'deny'}
    eng.human=Denier()
    eng.registry.register('ask_human',eng.ask_human)
    class Planner:
        async def decide(self,*args):
            return Decision('Ask before continuing',[ToolCall('ask_human',{'kind':'approve','text':'Proceed?'}),ToolCall('unsafe')])
    eng.model=Planner()
    count=[]
    async def unsafe(): count.append(1); return {}
    eng.registry.register('unsafe',unsafe)
    assert (await eng.run(state)).status=='rejected'
    assert not count and state.handoffs==1


def test_pending_state_survives_process_termination(tmp_path):
    import subprocess,sys,time
    store=RunStore(tmp_path/'runs')
    state=store.create('crash test')
    code='from harness.core.run_manager import RunStore; import time; s=RunStore('+repr(str(tmp_path/'runs'))+'); r=s.load('+repr(state.run_id)+'); r.pending_action={"name":"in-flight"}; s.save(r); time.sleep(60)'
    process=subprocess.Popen([sys.executable,'-c',code])
    try:
        deadline=time.monotonic()+10
        while time.monotonic()<deadline:
            if store.load(state.run_id).pending_action: break
            time.sleep(.02)
        assert store.load(state.run_id).pending_action
    finally:
        process.kill();process.wait(timeout=5)
    assert store.load(state.run_id).pending_action['name']=='in-flight'
