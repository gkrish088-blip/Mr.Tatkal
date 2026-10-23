import asyncio
from datetime import datetime, timezone
import hashlib
import hmac
import json
import time

import httpx
import pytest

from harness.handoff.channel import HumanChannel
from harness.handoff.telegram import TelegramTransport
from harness.log import Redactor, RunLog
from harness.log.replay import build_replay, read_events
from harness.triggers.schedule import Scheduler
from harness.triggers.events import FileWatcher, EmailTrigger, WebhookTrigger
from harness.triggers.chat import command


def test_log_redaction_and_escaped_replay(tmp_path):
    secret = "canary-only-in-memory-0193"
    log = RunLog(tmp_path, "example", Redactor([secret]))
    with pytest.raises(ValueError):
        log.append({"reason": ""})
    log.append({"step": 1, "reason": "<script>alert(1)</script> " + secret,
                "action": {"password": "not-registered", "value": secret, secret: "key canary"},
                "tokens": 20, "latency": .01, "tier": "reflex"})
    log.summary({"run_id": "example", "status": "done", "goal": secret, "step": 1, "handoffs": 1})
    for path in log.path.iterdir():
        if path.is_file():
            assert secret not in path.read_text(encoding="utf-8")
            assert "not-registered" not in path.read_text(encoding="utf-8")
    assert "<script>" not in (log.path / "replay.html").read_text()
    assert "&lt;script&gt;" in (log.path / "replay.html").read_text()
    assert read_events(log.path)[0]["action"]["password"] == "[REDACTED]"
    with pytest.raises(ValueError):
        RunLog(tmp_path, "../escape")


def test_replay_ignores_partial_tail_and_external_image(tmp_path):
    (tmp_path / "run.jsonl").write_text(json.dumps({"reason": "safe", "after": "https://evil.test/a.png"}) + '\n{"partial":')
    assert len(read_events(tmp_path)) == 1
    html = build_replay(tmp_path).read_text()
    assert "<img" not in html


@pytest.mark.asyncio
async def test_handoff_resume_duplicate_reply_and_timeout(tmp_path):
    sent = []
    class Transport:
        async def send(self, request):
            sent.append(request.copy())
    channel = HumanChannel(tmp_path / "requests.json", Transport())
    pending = asyncio.create_task(channel.ask("approve", "Proceed?", timeout=1, request_id="same", attachments=["masked.png"]))
    await asyncio.sleep(.01)
    restarted = HumanChannel(channel.path)
    assert restarted.reply("same", "maybe") is False
    assert restarted.reply("same", "yes") is True
    assert restarted.reply("same", "yes") is False
    result = await pending
    assert result["approved"] and len(sent) == 1
    assert sent[0]["attachments"] == ["masked.png"]
    assert (await channel.ask("approve", "Proceed?", request_id="same"))["approved"]
    assert len(sent) == 1
    result = await channel.ask("external_approval", "Wait for device", timeout=.01)
    assert result["status"] == "timed_out" and not result["approved"]
    assert not channel.reply(result["request_id"], "done")


@pytest.mark.asyncio
async def test_handoff_rejection_choice(tmp_path):
    channel = HumanChannel(tmp_path / "requests.json")
    task = asyncio.create_task(channel.ask("choose", "Which?", options=["A", "B"], request_id="choice"))
    await asyncio.sleep(.01)
    assert not channel.reply("choice", "C")
    assert channel.reply("choice", "B")
    assert (await task)["value"] == "B"


@pytest.mark.asyncio
async def test_telegram_filters_chat_and_sends_picture(tmp_path):
    calls = []
    def handler(request):
        calls.append(request.url.path)
        if request.url.path.endswith("getUpdates"):
            return httpx.Response(200, json={"ok": True, "result": [
                {"update_id": 1, "message": {"chat": {"id": "unauthorized"}, "text": "/reply req yes"}},
                {"update_id": 2, "message": {"chat": {"id": "123"}, "text": "/reply req no"}}]})
        return httpx.Response(200, json={"ok": True})
    channel = HumanChannel(tmp_path / "requests.json")
    task = asyncio.create_task(channel.ask("approve", "Proceed", request_id="req"))
    await asyncio.sleep(.01)
    picture = tmp_path / "masked.png"
    picture.write_bytes(b"test image")
    transport = TelegramTransport("fake-test-token", "123", httpx.AsyncClient(transport=httpx.MockTransport(handler)))
    await transport.send({"id": "req", "kind": "approve", "text": "Proceed", "attachments": [str(picture)]})
    await transport.poll_once(channel)
    assert not (await task)["approved"]
    assert transport.offset == 3
    assert any(p.endswith("sendPhoto") for p in calls)
    await transport.close()


@pytest.mark.asyncio
async def test_schedule_restart_offset_cron_and_uncertain_dispatch(tmp_path):
    now = [1000.]
    scheduler = Scheduler(tmp_path / "jobs.json", clock=lambda: now[0] + .5)
    job = scheduler.add("scheduled", 1001)
    calls = []
    async def dispatch(goal, inputs):
        calls.append((goal, inputs))
    assert not await scheduler.tick(dispatch)
    now[0] = 1000.5
    scheduler = Scheduler(scheduler.path, clock=lambda: now[0] + .5)
    assert await scheduler.tick(dispatch) == [job]
    assert not await scheduler.tick(dispatch)
    assert len(calls) == 1 and calls[0][1]["trigger_id"].startswith(job)
    with pytest.raises(ValueError):
        scheduler.add("bad", "2026-10-25T11:00:00")
    cron_job = scheduler.add("cron", 1001, cron="* * * * *")
    await scheduler.tick(dispatch)
    assert scheduler.jobs()[cron_job]["when"] > scheduler.now()
    failed = scheduler.add("uncertain", 1001)
    async def crash(goal, inputs):
        raise RuntimeError("crash after intent")
    with pytest.raises(RuntimeError):
        await scheduler.tick(crash)
    assert scheduler.jobs()[failed]["status"] == "dispatching"
    scheduler.recover(failed, retry=False)
    assert scheduler.jobs()[failed]["status"] == "done"


@pytest.mark.asyncio
async def test_scheduler_twenty_real_clock_trials_under_100ms(tmp_path):
    scheduler = Scheduler(tmp_path / "jobs.json")
    observed = []
    stop = asyncio.Event()
    async def dispatch(goal, inputs):
        observed.append(time.time() - inputs["due"])
        if len(observed) == 20:
            stop.set()
    # Leave room to fsync twenty registrations before evaluating firing latency.
    start = time.time() + 1
    for i in range(20):
        due = start + i * .06
        scheduler.add("timing", due, {"due": due})
    await asyncio.wait_for(scheduler.serve(dispatch, stop), timeout=5)
    assert len(observed) == 20
    assert min(observed) >= 0
    assert max(observed) < .1, observed


@pytest.mark.asyncio
async def test_file_email_webhook_and_chat_events(tmp_path):
    calls = []
    async def dispatch(goal, inputs):
        calls.append((goal, inputs))
    watched = tmp_path / "inbox"
    watched.mkdir()
    watcher = FileWatcher(watched, tmp_path / "seen.json", "Summarize")
    (watched / "note.txt").write_text("one")
    assert await watcher.poll_once(dispatch) == 1
    assert await FileWatcher(watched, watcher.path, "Summarize").poll_once(dispatch) == 0
    (watched / "note.txt").write_text("two")
    assert await watcher.poll_once(dispatch) == 1
    mail = EmailTrigger(tmp_path / "mail.json")
    messages = [{"id": "1", "subject": "invoice"}, {"id": "2", "subject": "other"}]
    assert await mail.process(messages, "invoice", "Record", dispatch) == 1
    assert await mail.process(messages, "invoice", "Record", dispatch) == 0
    webhook = WebhookTrigger(tmp_path / "webhook.json", "fake-test-secret")
    body = b'{"item":1}'
    signature = hmac.new(b"fake-test-secret", body, hashlib.sha256).hexdigest()
    with pytest.raises(PermissionError):
        await webhook.receive(body, "invalid", "1", "Record", dispatch)
    assert await webhook.receive(body, signature, "1", "Record", dispatch)
    assert not await webhook.receive(body, signature, "1", "Record", dispatch)
    await command("/run Make a note", dispatch)
    assert calls[-1][0] == "Make a note"
