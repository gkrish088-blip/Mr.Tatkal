import re
from harness.core.verify import lookup
from harness.core.types import ToolCall


def bind(value, context):
    if isinstance(value, dict):
        return {key: bind(item, context) for key, item in value.items()}
    if isinstance(value, list):
        return [bind(item, context) for item in value]
    if not isinstance(value, str):
        return value
    match = re.fullmatch(r"\$\{([^}]+)\}", value)
    if match:
        return lookup(context, match[1])
    return re.sub(r"\$\{([^}]+)\}", lambda m: str(lookup(context, m[1])), value)


class MacroRunner:
    def __init__(self, engine):
        self.engine = engine

    async def run(self, state, skill):
        if state.pending_action:
            state.status = "needs_reconciliation"
            self.engine.store.save(state)
            return state
        for index in range(state.macro_index, len(skill.macro)):
            step = bind(skill.macro[index], {"inputs": state.inputs, "history": state.history})
            call_data = step.get("call", step)
            call = ToolCall(call_data.get("tool", call_data.get("name")), call_data.get("arguments", call_data.get("args", {})))
            result = await self.engine.act(state, call, step.get("reason", f"Execute skill step {index+1}"), "reflex", step.get("assert", step.get("verify")))
            if not result.ok:
                if state.status in {"blocked", "needs_reconciliation", "limit_reached", "rejected"}:
                    return state
                if not await self.engine.recover(state, skill):
                    return state
                # Recovery must establish this step's checkpoint before moving on.
                from harness.core.verify import verify
                observation = await self.engine.observe()
                if not verify(step.get("assert", step.get("verify")), observation):
                    state.status = "blocked"
                    self.engine.store.save(state)
                    return state
            state.macro_index = index + 1
            self.engine.store.save(state)
        state.status = "completed"
        self.engine.store.save(state)
        self.engine.log.summary(state)
        return state
