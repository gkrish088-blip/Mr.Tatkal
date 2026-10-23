"""Explicit frozen-tree integrity guard. No write operations."""
import hashlib
import json
from pathlib import Path


def verify_manifest(filename):
    path=Path(filename).resolve()
    root=path.parent
    expected=json.loads(path.read_text(encoding='utf-8'))
    changed=[]
    for name,digest in expected.items():
        target=(root/name).resolve()
        if not target.is_relative_to(root) or not target.is_file() or hashlib.sha256(target.read_bytes()).hexdigest()!=digest:
            changed.append(name)
    if changed:
        raise ValueError('Frozen files differ: '+', '.join(changed))
    return True
