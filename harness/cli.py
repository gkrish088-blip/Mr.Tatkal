"""Operator CLI. Local tools are opt-in; no external run starts on import."""
import argparse
import asyncio
import json
import os
from pathlib import Path
import yaml
from harness.core.types import ToolRegistry
from harness.core.run_manager import RunStore
from harness.core.loop import Engine
from harness.core.macro import MacroRunner
from harness.skillrt.loader import SkillLoader
from harness.log.runlog import RunLog
from harness.log.redact import Redactor
from harness.models.adapter import ModelConfig, HTTPModel
from harness.models.failover import FailoverModel
from harness.tools import install_tools


async def run_goal(config, goal, inputs=None, run_id=None, skill_name=None):
    if config.get('freeze_manifest'):
        from harness.integrity import verify_manifest
        verify_manifest(config['freeze_manifest'])
    runs = Path(config.get('runs', 'runs'))
    store = RunStore(runs)
    state = store.load(run_id) if run_id else store.create(goal, inputs)
    redactor = Redactor([v for k,v in os.environ.items() if any(word in k.upper() for word in ('SECRET','PASSWORD','API_KEY','TOKEN')) and v])
    log = RunLog(runs, state.run_id, redactor)
    registry = ToolRegistry()
    registry.redactor = redactor
    browser = None
    transport = None
    polling = None
    desktop = None
    model = None
    if config.get('models'):
        models = [HTTPModel(ModelConfig(**m)) for m in config['models']]
        model = FailoverModel(models[0], models[-1])
    if config.get('browser', {}).get('cdp_url'):
        from harness.tools.browser import BrowserTools
        bc = config['browser']
        browser = BrowserTools(allowed_hosts=bc.get('allowed_hosts'), artifact_dir=runs/state.run_id/'steps')
        await browser.attach(bc['cdp_url'])
    from harness.handoff.channel import HumanChannel
    if config.get('telegram', {}).get('enabled'):
        from harness.handoff.telegram import TelegramTransport
        tc = config['telegram']
        transport = TelegramTransport(os.environ[tc['token_env']], tc['chat_id'])
    human = HumanChannel(runs/state.run_id/'handoff.json', transport=transport)
    if transport:
        polling = asyncio.create_task(transport.serve(human))
    try:
        if config.get('desktop', {}).get('enabled'):
            from harness.tools.desktop import DesktopTools
            desktop = DesktopTools(enabled=True, artifact_dir=runs/state.run_id/'steps')
        install_tools(registry, Path(config.get('workspace','workspace')), browser=browser, desktop=desktop)
        if browser:
            async def capture():
                return {**await browser.snapshot(), **await browser.screenshot()}
            registry.capture = capture
        loader = SkillLoader(config.get('skills','skills'))
        engine = Engine(registry, store, log, loader, model, human,
                        config.get('max_steps',100), config.get('max_seconds',300))
        if state.pending_action:
            state.status = 'needs_reconciliation'
            store.save(state)
        elif skill_name:
            await engine.use_skill(skill_name)
            sk = loader.load(skill_name)
            if not sk.macro:
                if not model:
                    raise ValueError('This skill needs a configured model; it has no macro')
                await engine.run(state)
            else:
                await MacroRunner(engine).run(state, sk)
        elif model:
            await engine.run(state)
        else:
            raise ValueError('Configure a model or select a macro skill')
        log.summary(state)
        print(json.dumps({'run_id':state.run_id,'status':state.status,'steps':state.step}))
        return state
    finally:
        if polling:
            polling.cancel()
            await asyncio.gather(polling, return_exceptions=True)
        if transport: await transport.close()
        if browser: await browser.close()


def main():
    parser=argparse.ArgumentParser(description='Generic skill-driven computer agent')
    parser.add_argument('--config', default='config.example.yaml')
    sub=parser.add_subparsers(dest='command', required=True)
    sub.add_parser('skills')
    sub.add_parser('preflight')
    run=sub.add_parser('run'); run.add_argument('goal'); run.add_argument('--skill'); run.add_argument('--inputs', default='{}')
    resume=sub.add_parser('resume'); resume.add_argument('run_id'); resume.add_argument('--skill')
    add=sub.add_parser('schedule'); add.add_argument('goal'); add.add_argument('--at',required=True); add.add_argument('--skill'); add.add_argument('--cron')
    sub.add_parser('serve')
    watch=sub.add_parser('watch'); watch.add_argument('directory'); watch.add_argument('goal')
    reply=sub.add_parser('reply'); reply.add_argument('run_id'); reply.add_argument('request_id'); reply.add_argument('value')
    args=parser.parse_args()
    config=yaml.safe_load(Path(args.config).read_text(encoding='utf-8'))
    if args.command=='skills': print(json.dumps(SkillLoader(config.get('skills','skills')).index(),indent=2))
    elif args.command=='preflight':
        from harness.preflight import preflight
        result=preflight(config); print(json.dumps(result,indent=2)); raise SystemExit(0 if result['ok'] else 1)
    elif args.command=='run': asyncio.run(run_goal(config,args.goal,json.loads(args.inputs),skill_name=args.skill))
    elif args.command=='resume': asyncio.run(run_goal(config,'',run_id=args.run_id,skill_name=args.skill))
    elif args.command=='reply':
        from harness.handoff.channel import HumanChannel
        print(HumanChannel(Path(config.get('runs','runs'))/args.run_id/'handoff.json').reply(args.request_id,args.value))
    elif args.command=='watch':
        from harness.triggers.events import FileWatcher
        watcher=FileWatcher(args.directory,Path(config.get('runs','runs'))/'events.json',args.goal)
        async def dispatch_event(goal,inputs): await run_goal(config,goal,inputs)
        asyncio.run(watcher.serve(dispatch_event))
    else:
        from harness.triggers.schedule import Scheduler
        from harness.tools.clock import Clock
        clock=Clock(config.get('clock',{}).get('offset_seconds',0))
        if args.command=='serve' and config.get('clock',{}).get('ntp_server'):
            asyncio.run(clock.synchronize(config['clock']['ntp_server']))
        scheduler=Scheduler(config.get('schedule_store','runs/schedules.json'),clock=clock)
        if args.command=='schedule': print(scheduler.add(args.goal,args.at,{'skill':args.skill},args.cron))
        else:
            async def dispatch(goal,inputs):
                # Serialize computer tasks: concurrent runs must never fight over one device.
                await run_goal(config,goal,inputs,skill_name=inputs.get('skill'))
            asyncio.run(scheduler.serve(dispatch))


if __name__=='__main__': main()
