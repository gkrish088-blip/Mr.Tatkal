# Shared interfaces

Python 3.11+, async tools. Harness code is domain independent.

`ToolCall(name: str, arguments: dict)`; `ToolResult(ok: bool, data: dict, error: str | None, state_hash: str='')` in `harness/core/types.py`.
`ToolRegistry.register(name, async_callable, description='', parameters=None)` and `await execute(ToolCall)` returns ToolResult; `schemas()` returns OpenAI-compatible tool definitions. Callable accepts keyword arguments and returns dict or ToolResult. Registry catches errors. `registry.capture` optional async callable returning dict with screenshot/path/hash.

`SkillLoader(root).index()` returns list of metadata dicts; `.load(name)` returns Skill with `.name`, `.body`, `.metadata`, `.macro` (list of dicts). Malformed/path traversal rejected.

`RunStore(root).create(goal, inputs=None)` returns RunState; `.save(state)`; `.load(run_id)`. State fields run_id, goal, inputs, step, status, history, handoffs, pending_action. Atomic JSON persistence.

`RunLog(root, run_id, redactor=None).append(event: dict)` synchronous, redacted JSONL; `.summary(state)` writes summary and replay. Redactor `.redact(value)` recursively handles structures, `.register(secret)`.

`await model.decide(context: dict, tools: list)` returns Decision(reason: str, calls: list[ToolCall], done: bool=False). Context includes goal, inputs, history, observation, skills. Implement compatible HTTP model and stub in models.

Decision also carries `answer`, per-request `usage` and `model`. A nonempty final text without tool calls is a completed answer; legacy `DONE` remains accepted. Empty responses stop with an explicit blocked reason. Each model decision is logged as a `phase=plan` event, distinct from an executed tool action, so answers, model latency and tokens survive replay. RunState persists `answer`, `blocked_reason`, `messages` and `active_skills`; loading old states uses their defaults. The model request shares the run deadline. `/api/sessions/{id}/messages` queues a follow-up only after the previous turn ends and refuses uncertain pending actions.

`SkillLoader(root, learned_root=None)` merges bundled skills with local overlays. Agent-created skills and field notes use the learned store; notes preserve base macro and gates. `create_skill`, `append_skill_note` and `list_skills` are generic runtime tools. Skill writing is unavailable when disabled or a freeze manifest is configured. Format validation is explicitly separate from execution validation. `system_info` reports configured capabilities; `file_extract` reads PDF/XLSX data within the file workspace.

Tools owner provides `install_tools(registry, workspace: Path, browser=None, desktop=None)` in harness/tools/__init__.py. Browser class `BrowserTools` with `attach(cdp_url)`, `goto(url)`, `snapshot()`, `click(ref)`, `type(ref,text)`, `press(key)`, `select(ref,value)`, `scroll(amount)`, `wait_for(text=None,ref=None,url=None,timeout=...)`, `screenshot()`, `close()`. Register tools as browser_goto/browser_snapshot/browser_click/browser_type/browser_press/browser_select/browser_scroll/browser_wait_for/browser_screenshot. Browser security: default localhost allowlist, explicit live configuration required. Desktop optional and enabled explicitly.

Handoff `HumanChannel(store_path, transport=None)` async `ask(kind,text,options=None,timeout=300,**kwargs)` returns dict; `.reply(request_id,value)` returns bool, persists requests, suppress duplicates. Telegram adapter transport `.send(request)` async and polling reply interface. `Scheduler(path, clock=None)` `.add(goal, when, inputs=None, cron=None)` persistent jobs; async `.tick(dispatch)` dispatches due jobs; `.serve(dispatch)` loop. File event watcher emits run goals.

Mock owner builds FastAPI mock at mock/mock_irctc/app.py with create_app(seed=0, scenario='M1', **kwargs), UI with accessible labels, JSON endpoints for isolated scenario tests. Domain logic and ranking only mock/skills, never harness/. Own tests/integration and mock skills. Agents do not commit; primary agent integrates and commits with memory notes.

## Implemented macro and checkpoint contract

`macro.yaml` contains a `steps` list. Each step has `tool`, `arguments`, `reason`, and `assert`. Bindings `${inputs.key}` preserve type when the whole value is a binding; bindings embedded in text become strings. Assertions support `text` substring, `url` substring, or `key` dotted path with optional `equals`. Assertions inspect the tool result merged with the current observation. UI transitions receive up to two seconds for a checkpoint before recovery. Every reflex step must have a checkpoint (lint).

Element refs can be stable snapshot IDs, `label:Accessible label` or `text:Visible text`. `browser_assert_json(ref='css:pre', expected=...)` verifies a rendered JSON object against an expected subset without returning its private contents. Failed review checks stop a macro before later payment steps. The local full-ticket skill demonstrates this generic verifier; no domain rules are embedded in its implementation.

Pending actions persist only a name/fingerprint. Interrupted external effects require reconciliation. Macros save a cursor after verified completion; no automatic retry of an uncertain action. Approval denial/timeout is terminal. Desktop and browser observers are optional; a run without one explicitly records missing visual evidence and cannot satisfy screenshot acceptance. HTTP models receive at most the latest two existing screenshots, with older observations summarized in context.

Single-process state ownership is required. Runtime manifest checking is opt-in and refuses changed/missing listed files; the standalone freeze verifier additionally compares the tracked file set. NTP synchronization is opt-in before scheduler serve; local timing checks do not establish real-world time accuracy.

## GUI server

`python -m harness.web` starts the FastAPI control room on port 8787. `harness/web/settings.py` loads server-owned provider credentials from `.env` (deployment environment wins). `RunManager` queues existing RunStore states by run ID; `SessionStore` keeps metadata and trigger IDs in local SQLite. Only one task runs at a time and a process file lock protects DATA_DIR.

GUI sessions and schedules are REST resources under `/api/`. A signed HttpOnly operator cookie is required when GUI_PASSWORD is set; non-loopback binding requires a strong password. Writes require X-Agent-Request and matching Origin. No model-key editing endpoint exists. Artifact serving is confined to run screenshots/replay/summary/log and excludes private state JSON.

`Scheduler.add(..., timezone_name='UTC')` remains backward compatible; GUI cron jobs explicitly store an IANA timezone and compute subsequent runs in that timezone. API and scheduler mutations share a lock. A stable trigger ID deduplicates queued work across dispatch retries. Active tasks at restart become needs_reconciliation; queued tasks survive. A separate mock/gui_demo plugin supplies the isolated local test without placing booking logic in harness.

Managed BrowserTools.launch(profile_dir, headless) uses persistent Chromium storage. It closes only its owned context; CDP mode still disconnects from operator Chrome. Keyed private-field digests let masked form updates change state hashes without exposing field values. Native desktop control is optional and belongs to the server machine.
