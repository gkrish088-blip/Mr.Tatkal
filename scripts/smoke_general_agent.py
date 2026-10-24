"""Opt-in REAL model check through the GUI API; tasks use local files and a local browser fixture only."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
from urllib.parse import urlsplit

import httpx
from openpyxl import Workbook


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live-model',action='store_true',help='Explicitly permit real provider requests using server credentials')
    parser.add_argument('--url',default='http://127.0.0.1:8787')
    args=parser.parse_args()
    if not args.live_model:parser.error('Pass --live-model to permit paid model requests')
    if urlsplit(args.url).hostname not in {'127.0.0.1','localhost','::1'}:parser.error('This check only targets a local GUI server')
    root=Path(__file__).resolve().parents[1]
    started=datetime.now(timezone.utc)
    stamp=started.strftime('%Y%m%dT%H%M%S%fZ')
    output=root/'test'/(stamp+'-live-general');output.mkdir(parents=True)
    report={'command':[sys.executable,*sys.argv],'started':started.isoformat(),'checks':[],
            'scope':'REAL server-configured model; local workspace and fictional browser fixture. No live account login, booking, payment, native desktop input, Telegram or mailbox access.'}
    process=None
    try:
        with httpx.Client(base_url=args.url,headers={'X-Agent-Request':'1'},timeout=40) as api:
            access=api.get('/api/access').raise_for_status().json()
            if access['required']:
                from dotenv import load_dotenv
                load_dotenv(root/'.env')
                api.post('/api/login',json={'password':os.environ.get('GUI_PASSWORD','')}).raise_for_status()
            status=api.get('/api/status').raise_for_status().json()
            if status['active']:raise RuntimeError('An operator task is active; do not interrupt it')
            workspace=Path(status['capabilities']['workspace'])
            folder=workspace/'general-agent-smoke';folder.mkdir(parents=True,exist_ok=True)
            report['model']=status['providers'][status['default_provider']]['model']

            def run(name,goal,verify,run_id=None):
                print('Starting '+name,flush=True)
                endpoint=f'/api/sessions/{run_id}/messages' if run_id else '/api/sessions'
                payload={'value':goal} if run_id else {'goal':goal}
                row=api.post(endpoint,json=payload).raise_for_status().json();run_id=row['id']
                deadline=time.monotonic()+330
                stop_requested=False
                while time.monotonic()<deadline:
                    detail=api.get('/api/sessions/'+run_id).raise_for_status().json()
                    if detail['requests']:
                        api.post('/api/sessions/'+run_id+'/stop').raise_for_status()
                        stop_requested=True
                        break
                    if detail['status'] not in {'queued','running'}:break
                    time.sleep(.5)
                passed=detail['status']=='completed' and bool(verify(detail))
                if detail['status'] in {'queued','running'} and not stop_requested:
                    api.post('/api/sessions/'+run_id+'/stop').raise_for_status()
                record={'name':name,'run_id':run_id,'status':detail['status'],'steps':detail['step'],
                        'passed':passed,'answer':detail['answer'],'error':('Unexpected human handoff' if stop_requested else detail.get('error') or detail.get('blocked_reason')),
                        'model_tokens':sum(e.get('tokens',0) for e in detail['events'] if e.get('phase')=='plan')}
                report['checks'].append(record)
                (output/'result.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
                print(f'{name}: {detail["status"]}, verified={passed}, steps={detail["step"]}',flush=True)
                if not passed:raise RuntimeError(name+' did not meet its independent result checks')
                return run_id

            run_id=run('skill question','List the skills you have, grouped briefly by purpose. Answer directly; do not open websites.',
                       lambda d:bool(d['answer']) and any(s['name'] in d['answer'] for s in status['skills']))
            def has_stdout(detail,value):
                return any(e.get('phase')=='execute' and e['action']['name']=='shell' and e['result']['ok']
                           and e['result']['data'].get('stdout','').strip()==value for e in detail['events'])
            run('file and terminal follow-up',
                'Create general-agent-smoke/answer.py containing print(6 * 7), run it using the configured Python executable, then read the file back to verify it. Report its stdout and saved path. Use workspace file and shell tools only.',
                lambda d:(folder/'answer.py').exists() and has_stdout(d,'42') and '42' in d['answer'],run_id)
            skill='local-script-smoke-'+stamp.lower()
            run('learn and execute a skill',
                f'Learn a reusable skill named {skill} for creating a small Python script in the workspace, running it with the configured Python, and verifying stdout before reporting. Save it with create_skill and load it with use_skill. Execute it now to save general-agent-smoke/learned.py printing 7 * 8, run it and verify stdout. After verifying, append one reusable field note with append_skill_note. Keep the skill generic; do not record personal paths or credentials. Use local files and shell only.',
                lambda d:(folder/'learned.py').exists() and has_stdout(d,'56') and skill in d['active_skills']
                    and any(e.get('phase')=='execute' and e['action']['name']=='append_skill_note' and e['result']['ok'] for e in d['events']))

            with socket.socket() as sock:
                sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
            process=subprocess.Popen([sys.executable,'-m','uvicorn','mock.mock_tasks.app:app','--host','127.0.0.1','--port',str(port),'--log-level','error'],
                                     cwd=root,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,
                                     creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
            fixture=f'http://127.0.0.1:{port}'
            for _ in range(100):
                try:
                    if httpx.get(fixture,timeout=1).status_code==200:break
                except httpx.HTTPError:pass
                time.sleep(.1)
            workbook=Workbook();workbook.active.append(['Name','Message']);workbook.active.append(['Fictional Reader','Local cross-app value: 42.'])
            workbook.save(folder/'values.xlsx')
            run('spreadsheet to browser form',
                f'Read general-agent-smoke/values.xlsx with file_extract. Open {fixture}/ in the managed browser. Fill its contact form with the Name and Message values from row 2, click Save message, and use the browser to verify Message saved. This is an isolated fictional local fixture; use browser tools for form interaction and do not open any other site. Report the result.',
                lambda d:any(row=={'name':'Fictional Reader','message':'Local cross-app value: 42.'} for row in httpx.get(fixture+'/messages').raise_for_status().json())
                    and any(e.get('phase')=='execute' and e['action']['name']=='file_extract' and e['result']['ok'] for e in d['events'])
                    and any(e.get('phase')=='execute' and e['action']['name']=='browser_click' and e['result']['ok'] for e in d['events']))
            report['passed']=True
    except Exception as error:
        report['passed']=False;report['failure']=type(error).__name__+': '+str(error)
    finally:
        if process:
            process.terminate()
            try:process.wait(timeout=10)
            except subprocess.TimeoutExpired:process.kill();process.wait(timeout=5)
        report['finished']=datetime.now(timezone.utc).isoformat()
        (output/'result.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
        print('Evidence: '+str(output),flush=True)
    return 0 if report.get('passed') else 1


if __name__=='__main__':raise SystemExit(main())
