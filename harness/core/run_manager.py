import json
import os
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    with temporary.open("w", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


@dataclass
class RunState:
    run_id: str
    goal: str
    inputs: dict = field(default_factory=dict)
    step: int = 0
    status: str = "ready"
    history: list = field(default_factory=list)
    handoffs: int = 0
    pending_action: dict | None = None
    macro_index: int = 0
    approvals: list = field(default_factory=list)
    answer: str = ""
    blocked_reason: str = ""
    active_skills: list = field(default_factory=list)
    messages: list = field(default_factory=list)


class RunStore:
    def __init__(self, root):
        self.root = Path(root)

    def _path(self, run_id):
        if not run_id or any(c not in "0123456789abcdef-" for c in run_id):
            raise ValueError("Invalid run id")
        return self.root / run_id / "state.json"

    def create(self, goal, inputs=None):
        state = RunState(str(uuid.uuid4()), goal, inputs or {}, messages=[{"role": "user", "text": goal}])
        self.save(state)
        return state

    def save(self, state):
        atomic_json(self._path(state.run_id), asdict(state))

    def load(self, run_id):
        return RunState(**json.loads(self._path(run_id).read_text(encoding="utf-8")))
