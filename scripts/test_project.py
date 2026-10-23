"""Record every verification run under test/ (including failing runs)."""
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys

root=Path(__file__).resolve().parents[1]
stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
target=root/'test'/stamp
target.mkdir(parents=True)
command=[sys.executable,'-m','pytest','--junitxml='+str(target/'junit.xml'),*sys.argv[1:]]
started=datetime.now(timezone.utc)
result=subprocess.run(command,cwd=root,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf-8',errors='replace')
(target/'output.txt').write_text(result.stdout,encoding='utf-8')
(target/'result.json').write_text(json.dumps({'command':command,'started':started.isoformat(),'finished':datetime.now(timezone.utc).isoformat(),'exit_code':result.returncode,'scope':'Local tests only; browser skips and real-service limitations appear in output.'},indent=2),encoding='utf-8')
print(result.stdout)
print('Saved results: '+str(target))
raise SystemExit(result.returncode)
