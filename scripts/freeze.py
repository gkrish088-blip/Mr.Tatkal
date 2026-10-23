"""Prepare or verify a tracked-file manifest; never freezes/tag the repo implicitly."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

def manifest(root):
    names=subprocess.check_output(['git','ls-files','-z'],cwd=root).decode().split('\0')
    return {name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in names if name and name!='freeze_manifest.json'}

def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--verify',action='store_true'); args=parser.parse_args()
    root=Path(__file__).resolve().parents[1]; path=root/'freeze_manifest.json'
    actual=manifest(root)
    if args.verify:
        expected=json.loads(path.read_text())
        raise SystemExit(0 if expected==actual else 'Freeze manifest differs from tracked files')
    if subprocess.check_output(['git','status','--porcelain'],cwd=root).strip():
        raise SystemExit('Commit all changes before preparing a freeze manifest')
    path.write_text(json.dumps(actual,indent=2),encoding='utf-8')
    print('Manifest prepared. Review, commit and tag freeze only after go/no-go checks.')

if __name__=='__main__': main()
