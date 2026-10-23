from pathlib import Path
from harness.skillrt.loader import SkillLoader

ROOT=Path(__file__).resolve().parents[2]


def test_harness_has_no_booking_domain_names():
    for path in (ROOT/'harness').rglob('*.py'):
        assert 'irctc' not in path.read_text(encoding='utf-8').lower(), str(path)


def test_all_skills_load_without_code_changes():
    loader=SkillLoader(ROOT/'skills')
    for metadata in loader.index():
        skill=loader.load(metadata['name'])
        assert skill.body and skill.metadata['version']
        for step in skill.macro:
            assert step.get('assert') or step.get('verify'), 'Every reflex action needs a checkpoint'


def test_no_accidental_real_provider_keys_in_python_sources():
    import re
    pattern=re.compile(r'\b(?:sk-proj-|ghp_)[A-Za-z0-9_-]{25,}')
    for folder in ('harness','mock','skills','profile'):
        for path in (ROOT/folder).rglob('*'):
            if path.is_file() and path.suffix in {'.py','.md','.yaml'} and path.name!='passenger.yaml':
                assert not pattern.search(path.read_text(encoding='utf-8')), str(path)
