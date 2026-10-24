from pathlib import Path
import re
from urllib.parse import unquote
from dotenv import dotenv_values
import keyring
root=Path(__file__).resolve().parents[2]
report=root/'docs/agent-task-failure-report.md'
content=report.read_text(encoding='utf-8')
links=re.findall(r'\]\(([^)]+)\)',content)
for link in links:
    if '://' not in link and not link.startswith('#'):
        target=(report.parent/unquote(link.split('#',1)[0])).resolve()
        assert target.is_file(), 'A report evidence link does not resolve'
reasons=re.findall(r'^### (\d+)\.',content,re.M)
assert reasons==[str(n) for n in range(1,13)], 'Expected twelve numbered reasons'
private_values=[v for k,v in dotenv_values(root/'.env').items() if v and len(v)>=10 and any(w in k.upper() for w in ('KEY','PASSWORD','TOKEN','SECRET'))]
phone=keyring.get_password('computer-harness','MMT_MOBILE')
if phone: private_values.append(phone)
assert all(value not in content for value in private_values), 'Report contains a configured private value'
assert 'unverified' in content and 'OTP delivery' in content
print(f'PASS: {len(reasons)} reasons; {len(links)} evidence links resolve; configured private values absent.')
