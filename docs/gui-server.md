# GUI and server deployment

The control room runs the existing general agent through a single serialized queue. No API key is requested in the GUI. One operator configures Claude or DeepSeek on the server in `.env`; all GUI users use those server credentials.

## Run locally

From the project folder:

```powershell
python -m pip install -e ".[test]"
python -m playwright install chromium
python -m harness.web
```

Then open **http://127.0.0.1:8787**. On Windows, `start-gui.cmd` starts the same server and uses `.venv` when available. The launcher creates `.env` from `.env.example` only if it does not already exist. A blank ignored `.env` has also been prepared in this checkout. No real key is included.

In `.env`, add one server key:

```dotenv
LLM_PROVIDER=claude
ANTHROPIC_API_KEY=your-server-key
```

Or:

```dotenv
LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=your-server-key
```

Restart after changing `.env`. Model IDs, endpoints, vision support, timeouts and local browser settings are server configuration. The defaults were checked against [Claude's model overview](https://platform.claude.com/docs/en/models/overview) and [DeepSeek's first-call documentation](https://api-docs.deepseek.com/). They remain editable as providers change or account access differs. Both keys enable a fallback to the other provider. Real connection checks send a small billable provider request; the GUI labels this explicitly.

The default server is localhost-only. It needs no login for local use. Set `GUI_PASSWORD` to enable the operator login on localhost as well. For a shared/remote server, a password of at least twelve characters is mandatory and startup refuses a non-loopback bind without it.

## Use the GUI

- **Run agent:** enter a general goal, select the configured provider, optionally select a skill and supply JSON inputs. The browser and files belong to the server's machine.
- **Run local test:** requires no model key. A per-run fictional booking service opens in the agent's managed Chromium. The task verifies the review, waits for **Approve test** in the GUI, then captures a fictional ticket. The approval affects only that isolated local test.
- **Live session:** inspect masked screenshots and the action timeline, answer handoff requests, stop a run or open the replay. Stop during an uncertain external action requires reconciliation; the GUI does not silently repeat it.
- **Sessions:** previous sessions and artifacts remain available after server/browser restarts. Eligible blocked/failed/cancelled sessions can resume; uncertain actions and interrupted live sessions cannot auto-resume.
- **Schedules:** choose a one-time datetime or a five-field cron expression plus an IANA timezone. `0 11 * * *` means daily at 11:00 in the selected timezone, not the server's timezone. For one ticket attempt, use a one-time schedule. Jobs can be paused, resumed and deleted. A running server is required. Overdue pending one-time jobs execute after restart; paused jobs do not. Uncertain dispatches stay stopped for inspection.
- **Settings:** view whether server keys are configured and optionally test their connection. Values of keys and `.env` contents are never served to the browser.

For ticket workflows, supply a private passenger-profile path through task inputs, select the appropriate prepared skill and rehearse while watching. Live website skills still need reconnaissance and the supervised acceptance checks in `runbook.md`. This GUI does not establish real booking readiness or auto-approve real payment.

## Local persistence

Everything under `DATA_DIR` stays on that server's disk:

- `sessions.sqlite3`: session metadata, queue status and trigger deduplication.
- `runs/<id>/`: run state, handoff requests, redacted logs, masked screenshots, summary and replay.
- `browser-profile/`: persistent agent browser cookies and local storage.
- `demo-browser-profile/`: separate fictional-test browser profile.
- `schedules.json`: one-time/cron jobs and their explicit timezone.
- `workspace/`: files created by the agent.
- `auth-secret` and `server.lock`: local operator-session signing secret and single-process ownership.

These directories and `.env` are ignored by Git. Back up them securely; browser profiles and private run inputs can contain sensitive account data. Session metadata survives restarts; work interrupted mid-action is marked for reconciliation. The file lock prevents two server processes from operating the same data directory. One active computer task runs at a time.

## Deploy as a server

Use a persistent host/VM or the provided Docker image. This Python/Playwright agent needs a running process and a writable browser profile; an ephemeral serverless web host is unsuitable. Docker packages the browser and uses a non-root account.

```bash
# Add a provider key and a >=12 character GUI_PASSWORD to .env first.
docker compose up --build -d
docker compose logs -f agent
```

The named `agent-data` volume retains sessions, browser state and jobs across container recreation. Compose exposes the port only on the host's loopback interface. For remote access, use an HTTPS reverse proxy, add its hostname to `ALLOWED_HOSTS`, and set `COOKIE_SECURE=true`. Uvicorn must trust forwarded headers only from the configured reverse proxy. Run **one worker/replica per DATA_DIR**; the active-process lock enforces this. Do not run the CLI scheduler against the GUI schedule file.

Set `BROWSER_ALLOWED_HOSTS` to every site and required dependency host the agent is allowed to use. Default access is localhost-only. Managed Chromium works on Linux/Windows. To attach an operator Chrome instead, use `BROWSER_MODE=cdp` and `CDP_URL`; native desktop tools remain optional and cannot control a laptop through a remote Linux container.

For managed installed Chrome, set `BROWSER_CHANNEL=chrome` and `BROWSER_HEADLESS=false`. This uses ordinary installed Chrome with the dedicated project profile; it does not change browser fingerprints or bypass service blocks. Restart after editing `.env`. Permission denials stop the run with a configuration reason, including within macros.

Browser observations include `network.blocked_hosts` and recent failed application request hosts/statuses; private URL paths and queries are omitted. Configure an observed required dependency explicitly rather than allowing all hosts. Use `browser_type(private=false)` for public search terms, and `sequential=true` for controls that require key events. Private entry remains the default and password fields always stay private. `browser_click` accepts observed refs, `label:` or `text:`; `browser_click_at` handles a visible custom control using current viewport coordinates.

Actionable DOM references cover the current viewport, with at most 200 controls; `elements_truncated` reports a dense view. Scroll and inspect again for offscreen controls. Stale references are removed, and duplicate controls keep their order across viewport changes. Model history keeps compact page landmarks and screenshot paths instead of duplicating every DOM node in each tool result/before/after observation. Full replay evidence remains in the run store.

Human handoffs display their run-owned image attachments in the GUI, so an actual service payment image can be scanned or opened at full size. `browser_capture_element` captures an observed image/canvas; `ask_human` accepts its path in `attachments`. A gateway must actually offer a QR; the agent must not manufacture one. Embedded cross-origin payment frames are not exposed by element capture and may require operator assistance.

`browser_download` saves actual service downloads under the run's `steps/downloads/`. `browser_print_pdf` prints the current observed page when the service offers a print view instead of a download. PDF files in that directory appear as download links in the session and are served as attachments with the same operator authentication as other artifacts. Raw state, unrelated files and PDF files outside that directory are not served. Ticket PDFs intentionally contain the booking's private details; keep DATA_DIR untracked.

No remote deployment has been performed by this implementation. Container build/start needs Docker and operator credentials; actual provider, Telegram and live-site behavior still require their own checks.

## Tests

```powershell
python scripts/test_project.py tests/web -q
python scripts/test_project.py -q
```

Web tests cover login/CSRF/host restrictions, server-key non-disclosure, persistent sessions, safe restart behavior, cron timezone recurrence, schedule controls, and actual Chromium GUI -> queue -> agent-browser -> fictional approval -> ticket -> replay. They also verify persistent browser cookies after closing and relaunching the browser. Reports and screenshots are retained under `test/`; local demo artifacts in `data/` are not committed.
