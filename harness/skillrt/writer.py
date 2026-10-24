"""Agent-authored skills and append-only lessons, kept in the local learned-skill store."""
from datetime import datetime, timezone
import os
import tempfile
import yaml


class SkillWriter:
    def __init__(self, loader, redactor, enabled=True):
        self.loader, self.redactor, self.enabled = loader, redactor, enabled

    def clean(self, text):
        if not self.enabled:
            raise PermissionError('Skill writing is disabled or the runtime is frozen')
        if not isinstance(text, str) or not text.strip() or len(text) > 80000:
            raise ValueError('Skill text must contain between 1 and 80000 characters')
        if self.redactor.redact(text) != text:
            raise ValueError('Skill text contains secret or private data; use environment references instead')
        return text.strip()

    def write(self, path, text):
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(prefix='.skill-', dir=path.parent)
        try:
            with os.fdopen(fd, 'w', encoding='utf-8', newline='') as stream:
                stream.write(text)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

    async def create(self, name: str, description: str, body: str):
        description, body = self.clean(description), self.clean(body)
        folder = self.loader.folder(name, writable=True)
        if any(item['name'] == name for item in self.loader.index()):
            raise ValueError('Skill already exists; append a field note instead')
        if body.startswith('---'):
            raise ValueError('Provide the Markdown body only; frontmatter is generated automatically')
        metadata = dict(name=name, description=description, version=1, requires=[], gates=[])
        text = '---\n' + yaml.safe_dump(metadata, sort_keys=False) + '---\n\n' + body + '\n'
        self.write(folder/'SKILL.md', text)
        return {'name': name, 'saved': True, 'validation': 'Format validated; task execution has not been tested'}

    async def append_note(self, name: str, note: str):
        note = self.clean(note)
        skill = self.loader.load(name)
        source = self.loader.folder(name)
        folder = self.loader.folder(name, writable=True)
        text = (source/'SKILL.md').read_text(encoding='utf-8-sig')
        if '\n## Field notes' not in text:
            text += '\n\n## Field notes\n'
        text += '\n- ' + datetime.now(timezone.utc).isoformat(timespec='seconds') + ': ' + note.replace('\n', '\n  ') + '\n'
        # Preserve the full base skill and its checkpointed macro when creating an overlay.
        if source != folder and (source/'macro.yaml').exists():
            self.write(folder/'macro.yaml', (source/'macro.yaml').read_text(encoding='utf-8'))
        self.write(folder/'SKILL.md', text)
        return {'name': skill.name, 'saved': True, 'validation': 'Field note saved; procedure and gates preserved'}
