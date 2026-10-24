import asyncio
import hashlib
import json
import time
from dataclasses import asdict
from harness.core.context import build_context
from harness.core.types import ToolCall, ToolResult
from harness.core.verify import verify


class Engine:
    def __init__(self, registry, store, log, loader, model=None, human=None, max_steps=100, max_seconds=300, gates=None, skill_writes_enabled=True):
        self.registry, self.store, self.log, self.loader = registry, store, log, loader
        self.model, self.human = model, human
        self.max_steps, self.max_seconds = max_steps, max_seconds
        self.gates = set(gates or [])
        self.started = time.monotonic()
        self.active = []
        self.failures = {}
        from harness.skillrt.writer import SkillWriter
        writer = SkillWriter(loader, log.redactor, skill_writes_enabled)
        registry.register('list_skills', self.list_skills, 'List available task skills and descriptions')
        if skill_writes_enabled:
            registry.register('create_skill', writer.create, 'Learn a reusable task from user instructions. Save Markdown with numbered steps, verification, and definition of done. Never save private data.')
            registry.register('append_skill_note', writer.append_note, 'Append a reusable lesson to a skill after observing a verified outcome; preserve its gates and procedure')
        registry.register("use_skill", self.use_skill, "Load a skill's full instructions", {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]})
        if human:
            registry.register("ask_human", self.ask_human, "Pause and ask the operator through the handoff channel", {"type": "object", "properties": {"kind": {"type": "string", "enum": ["text", "choose", "approve", "external_approval"]}, "text": {"type": "string"}, "options": {"type": "array", "items": {"type": "string"}}, "attachments": {"type": "array", "items": {"type": "string"}}, "timeout": {"type": "number"}}, "required": ["kind", "text"]})
            if getattr(human, 'transport', None):
                registry.register('notify_human', self.notify_human, 'Send a result and current screenshot through the configured operator channel without requesting a reply')

    async def list_skills(self):
        return {'skills': self.loader.index()}

    async def use_skill(self, name):
        skill = self.loader.load(name)
        self.active = [s for s in self.active if s.name != name] + [skill]
        self.gates.update(skill.metadata.get("gates", []))
        return {"name": skill.name, "body": skill.body}

    async def ask_human(self, kind, text, **kwargs):
        if 'attachments' not in kwargs:
            observation = await self.observe()
            kwargs['attachments'] = [observation['screenshot']] if observation.get('screenshot') else []
        return await self.human.ask(kind, text, **kwargs)

    async def notify_human(self, text: str):
        import uuid
        observation = await self.observe()
        await self.human.transport.send({'id': uuid.uuid4().hex, 'kind': 'notice', 'text': text,
                                        'attachments': [observation['screenshot']] if observation.get('screenshot') else []})
        return {'sent': True}

    async def decide(self, state):
        observation = await self.observe()
        context = build_context(state, self.loader, self.active, observation)
        context['capabilities'] = {**getattr(self.registry, 'capabilities', {}), 'tools': list(self.registry.tools)}
        remaining = self.max_seconds - (time.monotonic() - self.started)
        decision = await asyncio.wait_for(self.model.decide(context, self.registry.schemas()), timeout=max(.001, remaining))
        usage = decision.usage
        event = {'step': state.step, 'timestamp': int(time.time()*1000), 'phase': 'plan',
                 'reason': decision.reason or 'The model returned no text or tool action.', 'tier': 'reason',
                 'action': {'name': 'model_decision', 'arguments': {}},
                 'result': {'ok': bool(decision.calls or decision.done), 'data': {'answer': decision.answer}, 'error': None},
                 'verification': {'assertion': None, 'verdict': bool(decision.calls or decision.done)},
                 'model': decision.model, 'tokens': usage.get('input_tokens', 0)+usage.get('output_tokens', 0),
                 'usage': usage, 'latency': usage.get('latency', 0), 'before': observation, 'after': observation}
        safe = self.log.redactor.redact(event)
        self.log.append(safe)
        state.history.append(safe)
        self.store.save(state)
        return decision

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
        if call.name in {"browser_type", "desktop_type_text"} and redactor and call.arguments.get('private', True):
            redactor.register(call.arguments.get("text"))
        state.pending_action = {"name": call.name, "fingerprint": hashlib.sha256(json.dumps(asdict(call), sort_keys=True).encode()).hexdigest()}
        state.status = "waiting_human" if call.name == 'ask_human' else "acting"
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
        if call.name == 'browser_type' and result.data.get('private') and redactor:
            redactor.register(call.arguments.get('text'))
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
        state.active_skills = [s.name for s in self.active]
        state.status = "rejected" if state.status == "rejected" else "running"
        if result.data.get('requires_operator'):
            state.status = 'blocked'
            state.blocked_reason = self.log.redactor.redact(
                'Operator configuration required. ' + (result.error or 'Tool permission denied.') +
                ' Update the configuration and restart; do not bypass this restriction with another tool.')
        self.store.save(state)
        return result

    async def recover(self, state, skill=None):
        if not self.model:
            state.status = "blocked"
            self.store.save(state)
            return False
        decision = await self.decide(state)
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
        state.answer = ''
        state.blocked_reason = ''
        for name in state.active_skills:
            if name not in [s.name for s in self.active]:
                await self.use_skill(name)
        recent = []
        recovered = False
        while state.step < self.max_steps and time.monotonic()-self.started < self.max_seconds:
            decision = await self.decide(state)
            if decision.done:
                state.answer = self.log.redactor.redact(decision.answer or (decision.reason if decision.reason.strip() != 'DONE' else 'Task completed.'))
                state.messages.append({'role': 'assistant', 'text': state.answer})
                state.status = "completed"
                break
            if not decision.calls:
                state.blocked_reason = 'The model returned an empty response without a tool action. Retry or provide more detail.'
                state.status = "blocked"
                break
            for call in decision.calls:
                result = await self.act(state, call, decision.reason)
                if state.status in {"blocked", "rejected", "limit_reached", "needs_reconciliation"}:
                    break
                key = json.dumps(asdict(call), sort_keys=True)
                self.failures[key] = 0 if result.ok else self.failures.get(key, 0)+1
                observation = await self.observe()
                # A static browser does not imply a stalled filesystem or terminal task.
                # Detect repeated identical action/result/state, not unrelated successful work.
                digest = hashlib.sha256(json.dumps({'action': asdict(call), 'result': asdict(result),
                                                     'state_hash': observation.get('state_hash')},
                                                    sort_keys=True, default=str).encode()).hexdigest()
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
                        state.blocked_reason = 'Repeated actions made no progress after recovery. Review the last tool results and provide guidance.'
                        break
            if state.status in {"blocked", "rejected", "limit_reached", "needs_reconciliation"}:
                break
        else:
            state.status = "limit_reached"
        self.store.save(state)
        self.log.summary(state)
        return state
