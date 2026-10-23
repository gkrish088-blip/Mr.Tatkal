"""Append-only, fsynced JSONL and derived human-readable artifacts."""
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import os
import statistics
from .redact import Redactor


class RunLog:
    def __init__(self, root, run_id, redactor=None):
        root = Path(root).resolve()
        self.path = (root / run_id).resolve()
        if not self.path.is_relative_to(root) or self.path == root:
            raise ValueError("Invalid run id")
        self.path.mkdir(parents=True, exist_ok=True)
        (self.path / "steps").mkdir(exist_ok=True)
        self.redactor = redactor or Redactor()

    def append(self, event):
        if not isinstance(event, dict):
            raise TypeError("Event must be a dictionary")
        if not str(event.get("reason", "")).strip():
            raise ValueError("Every event requires a reason")
        event = {"timestamp": datetime.now(timezone.utc).isoformat(timespec="milliseconds"), **event}
        with (self.path / "run.jsonl").open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(self.redactor.redact(event), ensure_ascii=False, default=str) + "\n")
            stream.flush()
            os.fsync(stream.fileno())

    def summary(self, state):
        from .replay import build_replay, read_events
        data = asdict(state) if is_dataclass(state) else dict(state)
        events = read_events(self.path)
        reflex = sum(e.get("tier") == "reflex" for e in events)
        latencies = sorted(float(e.get("latency", 0)) for e in events)
        total_tokens = sum(e.get("tokens", 0) if isinstance(e.get("tokens", 0), (int, float))
                           else e["tokens"].get("total_tokens", 0) if isinstance(e.get("tokens"), dict) else 0
                           for e in events)
        p95 = latencies[min(len(latencies) - 1, int(len(latencies) * .95))] if latencies else 0
        text = (f"# Run {data.get('run_id', self.path.name)}\n\n"
                f"Status: {data.get('status', 'unknown')}\n\n"
                f"Goal: {data.get('goal', '')}\n\n"
                f"Steps: {data.get('step', len(events))}\n\n"
                f"Reflex share: {reflex / max(1, len(events)):.1%}\n\n"
                f"Human handoffs: {data.get('handoffs', 0)}\n\n"
                f"Tokens: {total_tokens}\n\n"
                f"Latency p50/p95: {statistics.median(latencies) if latencies else 0:.3f}/{p95:.3f} s\n\n"
                "Window-to-review and fault-recovery metrics require scenario timestamps; do not infer live performance from mock runs.\n")
        (self.path / "summary.md").write_text(self.redactor.redact(text), encoding="utf-8")
        build_replay(self.path)
        return self.path / "summary.md"
