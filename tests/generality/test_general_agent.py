"""Real runtime and file/skill adapters; model HTTP responses here are local fixtures."""
import asyncio
import json
from pathlib import Path

import httpx
import pytest
import yaml

from harness.core.loop import Engine
from harness.core.run_manager import RunStore
from harness.core.types import Decision, ToolCall, ToolRegistry
from harness.log.redact import Redactor
from harness.log.runlog import RunLog
from harness.models.adapter import HTTPModel, ModelConfig
from harness.skillrt.loader import SkillLoader
from harness.skillrt.writer import SkillWriter
from harness.tools import install_tools


def runtime(tmp_path, model=None, human=None, **kwargs):
    store=RunStore(tmp_path/'runs');state=store.create('List the skills you have')
    loader=SkillLoader(Path(__file__).resolve().parents[2]/'skills',tmp_path/'learned')
    registry=ToolRegistry();install_tools(registry,tmp_path/'workspace')
    log=RunLog(store.root,state.run_id,Redactor(['secret-canary-value']))
    return Engine(registry,store,log,loader,model,human,**kwargs),state


@pytest.mark.parametrize('protocol',['chat','messages'])
async def test_natural_answer_saved_with_usage_and_replay(tmp_path,monkeypatch,protocol):
    monkeypatch.setenv('FIXTURE_KEY','fixture-only')
    def handler(request):
        payload=json.loads(request.content)
        context=json.loads(payload['messages'][-1]['content'])
        assert context['skills'] and context['capabilities']['workspace']
        assert context['messages'][0]['text']=='List the skills you have'
        answer='Available skills include '+context['skills'][0]['name']+'. secret-canary-value'
        data={'content':[{'type':'text','text':answer}]} if protocol=='messages' else {'choices':[{'message':{'content':answer}}]}
        return httpx.Response(200,json={**data,'usage':{'input_tokens':25,'output_tokens':12}})
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        model=HTTPModel(ModelConfig('https://fixture.invalid','fixture-model','FIXTURE_KEY',protocol),client)
        engine,state=runtime(tmp_path,model)
        await engine.run(state)
    assert state.status=='completed' and state.step==0
    assert 'Available skills include' in state.answer and 'secret-canary-value' not in state.answer
    restored=engine.store.load(state.run_id)
    assert restored.answer==state.answer and restored.messages[-1]['role']=='assistant'
    summary=(engine.log.path/'summary.md').read_text()
    assert 'Tokens: 37' in summary and state.answer in summary
    assert 'secret-canary-value' not in (engine.log.path/'run.jsonl').read_text()
    assert 'fixture-model' in (engine.log.path/'replay.html').read_text()


async def test_empty_model_response_has_explanation_and_budget_is_bounded(tmp_path):
    class Empty:
        async def decide(self,*args):return Decision('')
    engine,state=runtime(tmp_path,Empty())
    await engine.run(state)
    assert state.status=='blocked' and 'empty response' in state.blocked_reason
    class Slow:
        async def decide(self,*args):await asyncio.sleep(5)
    engine.model=Slow();engine.max_seconds=.02
    with pytest.raises(asyncio.TimeoutError):await engine.run(state)


@pytest.mark.parametrize('protocol',['chat','messages'])
async def test_empty_http_response_is_not_success(monkeypatch,protocol):
    monkeypatch.setenv('FIXTURE_KEY','fixture-only')
    response={'content':[]} if protocol=='messages' else {'choices':[{'message':{'content':None}}]}
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda req:httpx.Response(200,json=response))) as client:
        decision=await HTTPModel(ModelConfig('https://fixture.invalid','fixture','FIXTURE_KEY',protocol),client).decide({},[])
    assert not decision.done and not decision.calls and not decision.answer


async def test_observer_keeps_desktop_and_browser_evidence():
    from harness.tools.observe import observe_computer
    class Browser:
        async def snapshot(self):return {'text':'Page text','url':'http://localhost'}
        async def screenshot(self):return {'screenshot':'browser.png','state_hash':'browser'}
    class Desktop:
        async def screenshot(self):return {'screenshot':'desktop.png','state_hash':'desktop'}
    result=await observe_computer(Browser(),Desktop())
    assert result['screenshot']=='desktop.png' and result['browser_screenshot']=='browser.png'
    assert result['text']=='Page text' and result['state_hash']=='desktop'
    assert (await observe_computer())['observer']=='unconfigured'


async def test_learn_then_execute_new_skill_with_same_harness(tmp_path):
    engine,state=runtime(tmp_path)
    body='# Goal\nWrite a greeting.\n\n## Procedure\n1. Write hello.txt.\n   Verify: read it back.\n\n## Definition of done\nThe saved note matches the requested greeting.'
    calls=iter([
        Decision('Learn the user-described task',[ToolCall('create_skill',{'name':'greeting','description':'Save a greeting','body':body})]),
        Decision('Load the new procedure',[ToolCall('use_skill',{'name':'greeting'})]),
        Decision('Follow the new task instructions',[ToolCall('file_write',{'path':'hello.txt','text':'Hello from a learned skill.'})]),
        Decision('Verify the saved result',[ToolCall('file_read',{'path':'hello.txt'})]),
        Decision('Saved and verified hello.txt.',done=True)
    ])
    class Planner:
        async def decide(self,context,tools):
            decision=next(calls)
            if decision.done:
                assert context['history'][-1]['result']['data']['text']=='Hello from a learned skill.'
            return decision
    engine.model=Planner()
    await engine.run(state)
    assert state.status=='completed' and state.step==4
    assert state.active_skills==['greeting']
    assert SkillLoader(engine.loader.root,tmp_path/'learned').load('greeting').body==body
    assert (tmp_path/'workspace/hello.txt').read_text()=='Hello from a learned skill.'
    assert not (engine.loader.root/'greeting').exists()


async def test_skill_overlay_preserves_gates_macro_and_rejects_secrets(tmp_path):
    base=tmp_path/'base/example';base.mkdir(parents=True)
    (base/'SKILL.md').write_text('---\nname: example\ndescription: Test\ngates: [danger]\nversion: 1\n---\n# Goal\nTest\n')
    (base/'macro.yaml').write_text(yaml.safe_dump({'steps':[{'tool':'danger','assert':{'key':'ok'}}]}))
    loader=SkillLoader(base.parent,tmp_path/'learned')
    writer=SkillWriter(loader,Redactor(['secret-canary-value']))
    await writer.append_note('example','Check the result before continuing.')
    skill=loader.load('example')
    assert skill.metadata['gates']==['danger'] and skill.macro[0]['tool']=='danger'
    assert 'Check the result' in skill.body and 'Check the result' not in (base/'SKILL.md').read_text()
    with pytest.raises(ValueError,match='secret'):
        await writer.create('private','A secret-canary-value task','Do it')
    with pytest.raises(ValueError):await writer.create('../escape','Test','Do it')
    with pytest.raises(ValueError,match='already exists'):await writer.create('example','Test','Do it')
    with pytest.raises(PermissionError):await SkillWriter(loader,Redactor(),False).append_note('example','No write')


async def test_restored_skill_gates_and_disabled_learning(tmp_path):
    engine,state=runtime(tmp_path,skill_writes_enabled=False)
    assert 'create_skill' not in engine.registry.tools and 'append_skill_note' not in engine.registry.tools
    writer=SkillWriter(engine.loader,Redactor())
    await writer.create('gated','Test restored gate','# Goal\nTest')
    path=tmp_path/'learned/gated/SKILL.md'
    path.write_text(path.read_text().replace('gates: []','gates: [danger]'))
    state.active_skills=['gated']
    executed=[]
    async def danger():executed.append(True);return {}
    engine.registry.register('danger',danger)
    decisions=iter([Decision('Attempt gated tool',[ToolCall('danger')]),Decision('',done=True)])
    class Planner:
        async def decide(self,*args):return next(decisions)
    engine.model=Planner();await engine.run(state)
    assert not executed and 'danger' in engine.gates


async def test_handoff_pauses_then_reply_returns_to_model(tmp_path):
    from harness.handoff.channel import HumanChannel
    human=HumanChannel(tmp_path/'handoff.json')
    engine,state=runtime(tmp_path,human=human)
    class Planner:
        async def decide(self,context,tools):
            if context['history'] and context['history'][-1]['phase']=='execute':
                return Decision('You chose blue.',done=True)
            return Decision('Ask for the missing choice',[ToolCall('ask_human',{'kind':'choose','text':'Choose a color','options':['blue','green'],'timeout':5})])
    engine.model=Planner();task=asyncio.create_task(engine.run(state))
    for _ in range(100):
        await asyncio.sleep(.01)
        if human.pending():break
    assert engine.store.load(state.run_id).status=='waiting_human'
    assert human.reply(human.pending()[0]['id'],'blue')
    await task
    assert state.status=='completed' and state.handoffs==1 and state.answer=='You chose blue.'


async def test_notification_uses_configured_channel_without_a_handoff(tmp_path):
    from harness.handoff.channel import HumanChannel
    sent=[]
    class Transport:
        async def send(self,request):sent.append(request)
    human=HumanChannel(tmp_path/'handoff.json',Transport())
    engine,state=runtime(tmp_path,human=human)
    result=await engine.act(state,ToolCall('notify_human',{'text':'The local task is complete.'}),'Report the verified result')
    assert result.ok and sent[0]['kind']=='notice' and state.handoffs==0
    assert not human.pending()


async def test_extract_workbook_and_pdf_respects_workspace(tmp_path):
    from openpyxl import Workbook
    from pypdf import PdfWriter
    from pypdf.generic import DictionaryObject,NameObject,DecodedStreamObject
    from harness.tools.files import FileTools
    files=FileTools(tmp_path)
    workbook=Workbook();workbook.active.append(['Value',42]);workbook.save(tmp_path/'values.xlsx')
    assert 'Value\t42' in (await files.extract('values.xlsx'))['text']
    assert (await files.extract('values.xlsx',max_chars=5))['truncated']
    writer=PdfWriter();page=writer.add_blank_page(612,792)
    font=DictionaryObject({NameObject('/Type'):NameObject('/Font'),NameObject('/Subtype'):NameObject('/Type1'),NameObject('/BaseFont'):NameObject('/Helvetica')})
    page[NameObject('/Resources')]=DictionaryObject({NameObject('/Font'):DictionaryObject({NameObject('/F1'):writer._add_object(font)})})
    contents=DecodedStreamObject();contents.set_data(b'BT /F1 12 Tf 72 720 Td (The value is 42) Tj ET')
    page[NameObject('/Contents')]=writer._add_object(contents)
    writer.write(tmp_path/'values.pdf')
    assert 'The value is 42' in (await files.extract('values.pdf'))['text']
    with pytest.raises(PermissionError):await files.extract('../private.pdf')
