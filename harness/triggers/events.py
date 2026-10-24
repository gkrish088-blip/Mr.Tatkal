"""Persistent file, email and authenticated webhook event adapters."""
import asyncio
import hashlib
import hmac
import json
from pathlib import Path
from harness.handoff.channel import atomic_json


class EventTrigger:
    def __init__(self, state_path):
        self.path = Path(state_path)
        self.lock = asyncio.Lock()
        if not self.path.exists():
            atomic_json(self.path, {})

    async def emit(self, event_id, goal, inputs, dispatch):
        async with self.lock:
            return await self._emit(event_id, goal, inputs, dispatch)

    async def _emit(self, event_id, goal, inputs, dispatch):
        seen = json.loads(self.path.read_text(encoding="utf-8"))
        if event_id in seen:
            return False
        # Persist intent first. On a crash an operator can inspect the uncertain event;
        # silently repeating side effects is never safe.
        seen[event_id] = "dispatching"
        atomic_json(self.path, seen)
        await dispatch(goal, {**inputs, "trigger_id": event_id, "trigger": "event"})
        seen[event_id] = "done"
        atomic_json(self.path, seen)
        return True


class FileWatcher(EventTrigger):
    def __init__(self, directory, state_path, goal, pattern="*"):
        super().__init__(state_path)
        self.directory, self.goal, self.pattern = Path(directory).resolve(), goal, pattern

    async def poll_once(self, dispatch):
        count = 0
        for path in sorted(self.directory.glob(self.pattern)):
            if not path.is_file() or not path.resolve().is_relative_to(self.directory) or path.resolve() == self.path.resolve():
                continue
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            count += await self.emit(f"file:{path.resolve()}:{digest}", self.goal,
                                     {"path": str(path.resolve()), "sha256": digest}, dispatch)
        return count

    async def serve(self, dispatch, interval=1, stop=None):
        while stop is None or not stop.is_set():
            await self.poll_once(dispatch)
            await asyncio.sleep(interval)


class EmailTrigger(EventTrigger):
    async def process(self, messages, subject, goal, dispatch):
        count = 0
        for message in messages:
            if message.get("subject") == subject and message.get("id"):
                count += await self.emit("email:" + str(message["id"]), goal, {"message": message}, dispatch)
        return count

    async def poll_imap(self, host, username, password, subject, goal, dispatch, mailbox="INBOX"):
        """Read-only IMAP over TLS; credentials remain in memory."""
        def fetch():
            import imaplib
            from email.parser import BytesParser
            from email.policy import default
            from email.header import decode_header, make_header
            with imaplib.IMAP4_SSL(host) as connection:
                connection.login(username, password)
                connection.select(mailbox, readonly=True)
                status, result = connection.uid("search", None, "ALL")
                if status != "OK":
                    raise RuntimeError("Mail search failed")
                messages = []
                for uid in result[0].split()[-100:]:
                    status, payload = connection.uid("fetch", uid, "(BODY.PEEK[])")
                    if status != "OK":
                        continue
                    raw = next((part[1] for part in payload if isinstance(part, tuple)), b"")
                    parsed = BytesParser(policy=default).parsebytes(raw)
                    body = parsed.get_body(preferencelist=('plain',)) if parsed.is_multipart() else parsed
                    text = body.get_content() if body and body.get_content_maintype() == 'text' else ''
                    messages.append({"id": f"{host}:{mailbox}:{uid.decode()}",
                                     "subject": str(make_header(decode_header(parsed.get("Subject", "")))),
                                     "from": str(parsed.get("From", "")), "text": text[:50000]})
                return messages
        return await self.process(await asyncio.to_thread(fetch), subject, goal, dispatch)


class WebhookTrigger(EventTrigger):
    def __init__(self, state_path, secret, bind_event_id=False):
        super().__init__(state_path)
        if not secret:
            raise ValueError("Webhook signing secret is required")
        self.secret = secret.encode()
        self.bind_event_id = bind_event_id

    async def receive(self, body, signature, event_id, goal, dispatch):
        signed = event_id.encode()+b'.'+body if self.bind_event_id else body
        expected = hmac.new(self.secret, signed, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, signature.removeprefix("sha256=")):
            raise PermissionError("Invalid webhook signature")
        if not event_id:
            raise ValueError("Webhook event id is required")
        payload = json.loads(body)
        if not isinstance(payload, dict):
            raise ValueError('Webhook body must be a JSON object')
        return await self.emit("webhook:" + event_id, goal, payload, dispatch)
