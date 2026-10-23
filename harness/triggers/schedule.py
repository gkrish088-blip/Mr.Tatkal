"""Persistent timezone-aware schedules with explicit uncertain-dispatch recovery."""
import asyncio
from datetime import datetime, timezone
import json
from pathlib import Path
import time
import uuid
from harness.handoff.channel import atomic_json


def timestamp(value):
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        value = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise ValueError("Schedule time must have an explicit timezone")
    return value.timestamp()


class Scheduler:
    def __init__(self, path, clock=None):
        self.path = Path(path)
        self.clock = clock or time.time
        self._lock = asyncio.Lock()
        if not self.path.exists():
            atomic_json(self.path, {})

    def now(self):
        source = self.clock() if callable(self.clock) else self.clock.now()
        return source.timestamp() if isinstance(source, datetime) else float(source)

    def jobs(self):
        return json.loads(self.path.read_text(encoding="utf-8"))

    def add(self, goal, when, inputs=None, cron=None):
        if not goal.strip():
            raise ValueError("A scheduled goal is required")
        when = timestamp(when)
        if cron:
            from croniter import croniter
            if not croniter.is_valid(cron):
                raise ValueError("Invalid cron expression")
        job_id = uuid.uuid4().hex
        jobs = self.jobs()
        jobs[job_id] = dict(id=job_id, goal=goal, when=when, inputs=inputs or {}, cron=cron,
                            status="pending", executions=0)
        atomic_json(self.path, jobs)
        return job_id

    def recover(self, job_id, *, retry=False):
        """Operator resolves dispatching jobs after a crash; retry needs idempotent dispatch."""
        jobs = self.jobs()
        job = jobs[job_id]
        if job["status"] != "dispatching":
            raise ValueError("Only an uncertain dispatch may be recovered")
        job["status"] = "pending" if retry else "done"
        atomic_json(self.path, jobs)

    async def tick(self, dispatch):
        async with self._lock:
            jobs = self.jobs()
            fired = []
            for job_id, job in jobs.items():
                if job["status"] != "pending" or job["when"] > self.now():
                    continue
                job["status"] = "dispatching"
                atomic_json(self.path, jobs)
                # A stable trigger id lets the run manager deduplicate after recovery.
                inputs = {**job["inputs"], "trigger_id": f"{job_id}:{job['executions']}", "trigger": "schedule"}
                try:
                    await dispatch(job["goal"], inputs)
                except Exception as error:
                    job["last_error"] = type(error).__name__
                    atomic_json(self.path, jobs)
                    raise
                job["executions"] += 1
                job["fired_at"] = self.now()
                if job["cron"]:
                    from croniter import croniter
                    # Evaluate in UTC; explicit UTC semantics avoid DST ambiguities.
                    job["when"] = croniter(job["cron"], datetime.fromtimestamp(max(self.now(), job["when"]), timezone.utc)).get_next(float)
                    job["status"] = "pending"
                else:
                    job["status"] = "done"
                atomic_json(self.path, jobs)
                fired.append(job_id)
            return fired

    async def serve(self, dispatch, stop=None):
        while stop is None or not stop.is_set():
            await self.tick(dispatch)
            future = [j["when"] for j in self.jobs().values() if j["status"] == "pending"]
            delay = min(.05, max(.001, min(future) - self.now())) if future else .05
            await asyncio.sleep(delay)
