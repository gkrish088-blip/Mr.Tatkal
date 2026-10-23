# Self-hosted GUI, sessions and cron

Implementation commit: `e903ed1` (`feat: add self-hosted agent GUI with persistent sessions and timezone cron`).

User request: run and test the general agent from a GUI, schedule booking tasks, use a server-owned Claude/DeepSeek key in `.env` rather than per-user keys, prepare server deployment and persist sessions locally.

## Implementation map

- `harness/web/settings.py`: `.env` configuration, Claude Messages/DeepSeek chat providers, model IDs/URLs/vision, provider fallback, local paths, browser settings, timezone and non-loopback password requirement. `.env.example` is committed; an empty-key `.env` was created locally and is ignored. Keys never enter GUI forms or API responses.
- `harness/web/app.py`: FastAPI GUI/API, signed HttpOnly operator login, CSRF/Origin/Host checks, one-process data lock, session APIs, model connection check, restricted artifacts, timezone-aware schedule CRUD, background dispatch and isolated demo mount. Default localhost port 8787.
- `harness/web/manager.py`: one serialized agent queue, local session metadata, existing core run invocation by ID, cancellation/resume/handoff integration, persistent queued-task recovery, uncertain active-task reconciliation and trigger deduplication.
- `harness/web/store.py`: local SQLite session/queue metadata with unique trigger IDs; runs/checkpoints/logs remain in existing RunStore/RunLog files.
- `harness/web/static/index.html`, `style.css`, `app.js`: responsive control room, general task composer, provider/skill selection, JSON inputs, local test, live screenshot/timeline, GUI human approval, session history, replay, stop/resume, one-time/cron controls and server status. No credential editor or browser-local key storage.
- `harness/web/__main__.py`: `python -m harness.web` launcher, optional host/port/env arguments, first-use `.env` creation without overwriting existing files. `start-gui.cmd` is the Windows launcher. `pyproject.toml` exposes `train-gui`, packages static files and adds dotenv/tzdata dependencies.
- `harness/tools/browser.py`: managed persistent Chromium profile launch/owned-context cleanup, preserving the existing CDP path. Keyed private-form digests change state hashes even when screenshots are masked, without exposing private values. `tests/unit/test_tools_browser.py` adds the corresponding regression check.
- `harness/cli.py`: existing `run_goal` accepts managed-browser configuration; browser startup failure cleans up. Existing CLI behavior remains available.
- `harness/triggers/schedule.py`: optional stored IANA timezone, backward-compatible UTC default; cron recurrence uses each job's timezone.
- `mock/gui_demo.py`: per-session fictional booking plugin. GUI **Run local test** uses the full mock-ticket skill with no model key. Only this plugin translates GUI approval into the isolated fictional payment; production handoff never auto-approves anything.
- `.gitignore`, `.dockerignore`: exclude `.env`, runtime data, private profiles, browser cookies, workspaces and caches; keep `.env.example`.
- `Dockerfile`, `compose.yaml`: persistent Playwright-capable Python server, non-root container account, local healthcheck, named data volume, one worker and loopback host port. Remote binding requires GUI_PASSWORD.
- `README.md`, `docs/gui-server.md`, `docs/interfaces.md`: startup, server-owned keys, cron semantics, local persistence, login, deployment and remaining live-service limits.

## Verification

- `tests/web/test_server.py`: authentication/CSRF/Host validation, provider-key non-disclosure, local persistence/restart, scheduled dispatch deduplication, timezone cron recurrence, pause/resume/delete, serialized queue/cancel and uncertain-action safety.
- `tests/web/test_gui.py`: actual Chromium GUI -> queue -> agent Chromium -> fictional approval -> ticket/replay; actual general engine with a test-only Claude HTTP fixture writes a file from a GUI task; reload restores history; browser cookies persist; mobile layout and uncaught JavaScript checks.
- Final full suite: **181 passed, 1 skipped**, 40.37 s, `test/20261023T214135078991Z/`. Skip is Windows symlink privilege. Existing Starlette/httpx deprecation warning retained.
- `test/gui-server-verification.md`, `test/gui-overview.png`, `test/gui-mobile.png`: verification scope, honest intermediate failures/fixes, and visually inspected desktop/mobile screenshots.
- Compileall, JavaScript syntax, editable install, whitespace and Compose structure checks passed. Docker is unavailable, so image build/start is unverified. No real LLM, booking, payment, Telegram or remote deployment occurred.

## Continuation

Run `python -m harness.web` (or Windows launcher), open http://127.0.0.1:8787. Add ANTHROPIC_API_KEY or DEEPSEEK_API_KEY and choose LLM_PROVIDER in ignored `.env`, then restart. A local test works before adding a key. Use DATA_DIR backups or a persistent deployment volume; one process owns a data directory. Tasks control the machine hosting the server, not a remote visitor's laptop. Existing live reconnaissance/rehearsal gates still apply. This documentation-only closure commit needs no recursive note.
