import asyncio
import hashlib
import json
import time
from dataclasses import asdict
from harness.core.context import build_context
from harness.core.types import ToolCall, ToolResult
from harness.core.verify import verify


class Engine:
    def __init__(self, registry, store, log, loader, model=None, human=None, max_steps=100, max_seconds=300, gates=None):
        self.registry, self.store, self.log, self.loader = registry, store, log, loader
        self.model, self.human = model, human
        self.max_steps, self.max_seconds = max_steps, max_seconds
        self.gates = set(gates or [])
        self.started = time.monotonic()
        self.active = []
        self.failures = {}
        registry.register("use_skill", self.use_skill, "Load a skill's full instructions", {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]})
        if human:
            registry.register("ask_human", self.ask_human, "Pause and ask the operator", {"type": "object", "properties": {"kind": {"type": "string"}, "text": {"type": "string"}}, "required": ["kind", "text"]})

    async def use_skill(self, name):
        skill = self.loader.load(name)
        self.active.append(skill)
        self.gates.update(skill.metadata.get("gates", []))
        return {"name": skill.name, "body": skill.body}

    async def ask_human(self, kind, text, **kwargs):
        return await self.human.ask(kind, text, **kwargs)

    async def observe(self):
        if self.registry.capture:
            return await self.registry.capture()
        return {"observer": "unconfigured", "screenshot": None}

    async def act(self, state, call, reason, tier="reason", assertion=None):
        if not reason.strip():
            raise ValueError("Every action needs a reason")
        if state.step >= self.max_steps or time.monotonic() - self.started > self.max_seconds:
            state.status = "limit_reached"
            self.store.save(state)
            return ToolResult(False, error="Run budget exhausted")
        before = await self.observe()
        if call.name in self.gates:
            # Approval is scoped to exact arguments, consumed once, and cannot be fabricated by a tool result.
            fingerprint = hashlib.sha256(json.dumps(asdict(call), sort_keys=True).encode()).hexdigest()
            if fingerprint not in state.approvals:
                if not self.human:
                    return ToolResult(False, error="Approval channel required for gated action")
                state.handoffs += 1
                state.status = "waiting_human"
                self.store.save(state)
                reply = await self.human.ask("approve", f"Approve action {call.name}?", options=["approve", "deny"], attachments=[before["screenshot"]] if before.get("screenshot") else [])
                if not reply.get("approved"):
                    state.status = "rejected"
                    self.store.save(state)
                    return ToolResult(False, error="Approval rejected or timed out")
                state.approvals.append(fingerprint)
            state.approvals.remove(fingerprint)
        redactor = getattr(self.log, "redactor", None)
        if call.name in {"browser_type", "desktop_type_text"} and redactor:
            redactor.register(call.arguments.get("text"))
        state.pending_action = {"name": call.name, "fingerprint": hashlib.sha256(json.dumps(asdict(call), sort_keys=True).encode()).hexdigest()}
        state.status = "acting"
        self.store.save(state)  # uncertain actions are NEVER replayed blindly after a crash
        started = time.monotonic()
        if call.name == "ask_human":
            state.handoffs += 1
        remaining = self.max_seconds - (time.monotonic() - self.started)
        try:
            result = await asyncio.wait_for(self.registry.execute(call), timeout=max(.001, remaining))
        except asyncio.TimeoutError:
            state.status = "needs_reconciliation"
            self.store.save(state)
            return ToolResult(False, error="Action deadline exceeded; reconcile observed state before retry")
        if call.name == "ask_human" and (result.data.get("status") == "timed_out" or (call.arguments.get("kind") in {"approve", "external_approval"} and not result.data.get("approved"))):
            result = ToolResult(False, result.data, "Human approval denied or timed out")
            state.status = "rejected"
        after = await self.observe()
        verdict = result.ok and verify(assertion, {**result.data, **after})
        checkpoint_deadline = min(time.monotonic() + 2, self.started + self.max_seconds)
        while result.ok and assertion and not verdict and time.monotonic() < checkpoint_deadline:
            await asyncio.sleep(.05)
            after = await self.observe()
            verdict = verify(assertion, {**result.data, **after})
        if not verdict and result.ok:
            result = ToolResult(False, result.data, "Checkpoint failed", result.state_hash)
        state.step += 1
        event = {"step": state.step, "timestamp": int(time.time()*1000), "phase": "execute", "skill": self.active[-1].name if self.active else None,
                 "tier": tier, "reason": reason, "action": asdict(call), "result": asdict(result),
                 "verification": {"assertion": assertion, "verdict": verdict}, "latency": time.monotonic()-started,
                 "handoff": call.name == "ask_human", "before": before, "after": after}
        # Persist only the same redacted content used by the log, never raw tool args.
        redactor = getattr(self.log, "redactor", None)
        safe = redactor.redact(event) if redactor else event
        self.log.append(safe)
        state.history.append(safe)
        state.pending_action = None
        state.status = "rejected" if state.status == "rejected" else "running"
        self.store.save(state)
        return result

    async def recover(self, state, skill=None):
        if not self.model:
            state.status = "blocked"
            self.store.save(state)
            return False
        decision = await self.model.decide(build_context(state, self.loader, self.active, await self.observe()), self.registry.schemas())
        for call in decision.calls:
            result = await self.act(state, call, decision.reason)
            if not result.ok:
                return False
        return bool(decision.calls)

    async def run(self, state):
        if state.pending_action:
            state.status = "needs_reconciliation"
            self.store.save(state)
            return state
        self.started = time.monotonic()
        recent = []
        recovered = False
        while state.step < self.max_steps and time.monotonic()-self.started < self.max_seconds:
            context = build_context(state, self.loader, self.active, await self.observe())
            decision = await self.model.decide(context, self.registry.schemas())
            if decision.done:
                state.status = "completed"
                break
            if not decision.calls:
                state.status = "blocked"
                break
            for call in decision.calls:
                result = await self.act(state, call, decision.reason)
                if state.status in {"rejected", "limit_reached", "needs_reconciliation"}:
                    break
                key = json.dumps(asdict(call), sort_keys=True)
                self.failures[key] = 0 if result.ok else self.failures.get(key, 0)+1
                observation = await self.observe()
                digest = observation.get("state_hash") or hashlib.sha256(json.dumps(result.data, sort_keys=True).encode()).hexdigest()
                recent.append(digest)
                stuck = (len(recent) >= 3 and len(set(recent[-3:])) == 1) or self.failures[key] >= 3
                if stuck:
                    if not recovered:
                        recovered = True
                        await self.recover(state)
                        recent.clear()
                    else:
                        if self.human:
                            await self.act(state, ToolCall("ask_human", {"kind": "text", "text": "Run is stuck. How should it recover?"}), "Request recovery guidance", "human")
                        state.status = "blocked"
                        break
            if state.status in {"blocked", "rejected", "limit_reached", "needs_reconciliation"}:
                break
        else:
            state.status = "limit_reached"
        self.store.save(state)
        self.log.summary(state)
        return state
