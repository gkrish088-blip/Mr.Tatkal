"""Durable request/reply handoff; no approval is inferred from a timeout."""
import asyncio
import json
import os
from pathlib import Path
import time
import uuid


def atomic_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + f".{uuid.uuid4().hex}.tmp")
    try:
        with temporary.open("w", encoding="utf-8") as stream:
            json.dump(data, stream, ensure_ascii=False)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


class HumanChannel:
    KINDS = {"approve", "choose", "text", "external_approval"}

    def __init__(self, store_path, transport=None):
        self.path = Path(store_path)
        self.transport = transport
        self._lock = asyncio.Lock()
        if not self.path.exists():
            atomic_json(self.path, {})

    def _read(self):
        return json.loads(self.path.read_text(encoding="utf-8"))

    def reply(self, request_id, value):
        requests = self._read()
        request = requests.get(request_id)
        if not request or request["status"] != "pending" or time.time() >= request["deadline"]:
            return False
        if request["kind"] in ("approve", "external_approval"):
            if str(value).strip().lower() not in {"yes", "approve", "approved", "done", "no", "deny", "denied"}:
                return False
        elif request["kind"] == "choose" and value not in request["options"]:
            return False
        request.update(status="replied", reply=value, replied_at=time.time())
        atomic_json(self.path, requests)
        return True

    async def ask(self, kind, text, options=None, timeout=300, **kwargs):
        if kind not in self.KINDS or timeout <= 0:
            raise ValueError("Invalid handoff kind or timeout")
        if kind == "choose" and not options:
            raise ValueError("Choice handoff requires options")
        request_id = kwargs.get("request_id") or uuid.uuid4().hex
        async with self._lock:
            requests = self._read()
            if request_id not in requests:
                requests[request_id] = dict(id=request_id, kind=kind, text=text, options=options or [],
                                            attachments=kwargs.get("attachments", []), status="pending",
                                            deadline=time.time() + timeout, created_at=time.time())
                atomic_json(self.path, requests)
            request = requests[request_id]
            if request["status"] == "pending" and not request.get("sent") and self.transport:
                await self.transport.send(request)
                requests = self._read()
                requests[request_id]["sent"] = True
                atomic_json(self.path, requests)
        while True:
            request = self._read()[request_id]
            if request["status"] != "pending":
                approved = request["kind"] in {"approve", "external_approval"} and str(request.get("reply", "")).strip().lower() in {"yes", "approve", "approved", "done"}
                return {"request_id": request_id, "status": request["status"], "value": request.get("reply"), "approved": approved}
            if time.time() >= request["deadline"]:
                requests = self._read()
                if requests[request_id]["status"] == "pending":
                    requests[request_id]["status"] = "timed_out"
                    atomic_json(self.path, requests)
                continue
            await asyncio.sleep(min(.05, max(0, request["deadline"] - time.time())))

    def pending(self):
        return [r for r in self._read().values() if r["status"] == "pending"]
