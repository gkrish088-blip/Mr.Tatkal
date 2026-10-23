# Shared interfaces

Python 3.11+, async tools. Harness code is domain independent.

`ToolCall(name: str, arguments: dict)`; `ToolResult(ok: bool, data: dict, error: str | None, state_hash: str='')` in `harness/core/types.py`.
`ToolRegistry.register(name, async_callable, description='', parameters=None)` and `await execute(ToolCall)` returns ToolResult; `schemas()` returns OpenAI-compatible tool definitions. Callable accepts keyword arguments and returns dict or ToolResult. Registry catches errors. `registry.capture` optional async callable returning dict with screenshot/path/hash.

`SkillLoader(root).index()` returns list of metadata dicts; `.load(name)` returns Skill with `.name`, `.body`, `.metadata`, `.macro` (list of dicts). Malformed/path traversal rejected.

`RunStore(root).create(goal, inputs=None)` returns RunState; `.save(state)`; `.load(run_id)`. State fields run_id, goal, inputs, step, status, history, handoffs, pending_action. Atomic JSON persistence.

`RunLog(root, run_id, redactor=None).append(event: dict)` synchronous, redacted JSONL; `.summary(state)` writes summary and replay. Redactor `.redact(value)` recursively handles structures, `.register(secret)`.

`await model.decide(context: dict, tools: list)` returns Decision(reason: str, calls: list[ToolCall], done: bool=False). Context includes goal, inputs, history, observation, skills. Implement compatible HTTP model and stub in models.

Tools owner provides `install_tools(registry, workspace: Path, browser=None, desktop=None)` in harness/tools/__init__.py. Browser class `BrowserTools` with `attach(cdp_url)`, `goto(url)`, `snapshot()`, `click(ref)`, `type(ref,text)`, `press(key)`, `select(ref,value)`, `scroll(amount)`, `wait_for(text=None,ref=None,url=None,timeout=...)`, `screenshot()`, `close()`. Register tools as browser_goto/browser_snapshot/browser_click/browser_type/browser_press/browser_select/browser_scroll/browser_wait_for/browser_screenshot. Browser security: default localhost allowlist, explicit live configuration required. Desktop optional and enabled explicitly.

Handoff `HumanChannel(store_path, transport=None)` async `ask(kind,text,options=None,timeout=300,**kwargs)` returns dict; `.reply(request_id,value)` returns bool, persists requests, suppress duplicates. Telegram adapter transport `.send(request)` async and polling reply interface. `Scheduler(path, clock=None)` `.add(goal, when, inputs=None, cron=None)` persistent jobs; async `.tick(dispatch)` dispatches due jobs; `.serve(dispatch)` loop. File event watcher emits run goals.

Mock owner builds FastAPI mock at mock/mock_irctc/app.py with create_app(seed=0, scenario='M1', **kwargs), UI with accessible labels, JSON endpoints for isolated scenario tests. Domain logic and ranking only mock/skills, never harness/. Own tests/integration and mock skills. Agents do not commit; primary agent integrates and commits with memory notes.
