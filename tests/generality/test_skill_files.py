"""A new task executes by adding only a skill, using the same core and tools."""
import sys
import os
import yaml
from harness.core.loop import Engine
from harness.core.macro import MacroRunner
from harness.core.run_manager import RunStore
from harness.core.types import ToolRegistry
from harness.log.runlog import RunLog
from harness.skillrt.loader import SkillLoader
from harness.tools import install_tools


async def test_new_skill_writes_runs_and_verifies_script(tmp_path):
    folder=tmp_path/'skills'/'local-script'
    folder.mkdir(parents=True)
    (folder/'SKILL.md').write_text('---\nname: local-script\ndescription: Create and run a script\nversion: 1\n---\n# Goal\nWrite a script and verify its output.\n',encoding='utf-8')
    (folder/'macro.yaml').write_text(yaml.safe_dump({'steps':[
        {'tool':'file_write','arguments':{'path':'task/hello.py','text':'print(6 * 7)\n'},'reason':'Create the requested script','assert':{'key':'path','equals':'task/hello.py'}},
        {'tool':'shell','arguments':{'cmd':f'"{sys.executable}" task/hello.py'},'reason':'Run the created script','assert':{'key':'stdout','equals':'42'+os.linesep}},
        {'tool':'file_read','arguments':{'path':'task/hello.py'},'reason':'Verify saved script contents','assert':{'text':'print(6 * 7)'}}
    ]}),encoding='utf-8')
    registry=ToolRegistry();install_tools(registry,tmp_path/'workspace')
    store=RunStore(tmp_path/'runs');state=store.create('Run a local script')
    loader=SkillLoader(tmp_path/'skills')
    eng=Engine(registry,store,RunLog(tmp_path/'runs',state.run_id),loader)
    assert (await MacroRunner(eng).run(state,loader.load('local-script'))).status=='completed'
    assert state.step==3
    assert (tmp_path/'workspace/task/hello.py').read_text()=='print(6 * 7)\n'
