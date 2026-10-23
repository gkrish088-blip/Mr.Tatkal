import hashlib
import json
import pytest
from harness.integrity import verify_manifest


def test_frozen_files_checked_before_launch(tmp_path):
    source=tmp_path/'source.py';source.write_text('original')
    manifest=tmp_path/'freeze_manifest.json'
    manifest.write_text(json.dumps({'source.py':hashlib.sha256(source.read_bytes()).hexdigest()}))
    assert verify_manifest(manifest)
    source.write_text('changed')
    with pytest.raises(ValueError,match='source.py'): verify_manifest(manifest)
    manifest.write_text(json.dumps({'../escape':'anything'}))
    with pytest.raises(ValueError): verify_manifest(manifest)
