import re
from dataclasses import dataclass, field
from pathlib import Path
import yaml


@dataclass
class Skill:
    name: str
    body: str
    metadata: dict
    macro: list = field(default_factory=list)


class SkillLoader:
    def __init__(self, root):
        self.root = Path(root).resolve()

    def load(self, name):
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", name):
            raise ValueError("Invalid skill name")
        folder = (self.root / name).resolve()
        if not folder.is_relative_to(self.root):
            raise ValueError("Skill escapes root")
        text = (folder / "SKILL.md").read_text(encoding="utf-8-sig")
        parts = text.split("---", 2)
        if len(parts) != 3 or parts[0].strip():
            raise ValueError(f"{name}: missing frontmatter")
        metadata = yaml.safe_load(parts[1])
        if not isinstance(metadata, dict) or metadata.get("name") != name or not metadata.get("description"):
            raise ValueError(f"{name}: name and description required")
        for key in ("requires", "gates"):
            if key in metadata and not isinstance(metadata[key], list):
                raise ValueError(f"{name}: {key} must be a list")
        macro_file = folder / "macro.yaml"
        macro = yaml.safe_load(macro_file.read_text(encoding="utf-8")) if macro_file.exists() else []
        if isinstance(macro, dict):
            macro = macro.get("steps", [])
        if not isinstance(macro, list):
            raise ValueError("Macro must contain steps")
        return Skill(name, parts[2].strip(), metadata, macro or [])

    def index(self):
        if not self.root.exists():
            return []
        return [{"name": skill.name, "description": skill.metadata["description"]}
                for skill in (self.load(p.parent.name) for p in sorted(self.root.glob("*/SKILL.md")))]
