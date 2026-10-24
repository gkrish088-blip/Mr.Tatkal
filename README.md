# Do You Know How to Train?

A Python computer-use harness with skill files, a plan/act/observe/verify loop, optional browser and desktop tools, durable state, human handoff, schedule/event triggers and replayable run logs. The official problem PDF is authoritative; the supplied implementation guide drives the architecture.

## GUI control room

```powershell
python -m pip install -e ".[test]"
python -m playwright install chromium
python -m harness.web
```

Open **http://127.0.0.1:8787**, or start the server with `start-gui.cmd` on Windows. Run tasks, view local sessions/screenshots/replays, answer human handoffs, and create one-time or timezone-aware cron jobs directly in the GUI. **Run local test** exercises a complete fictional booking and GUI approval without an LLM key.

Add `ANTHROPIC_API_KEY` or `DEEPSEEK_API_KEY` to the ignored `.env`, choose `LLM_PROVIDER=claude` or `deepseek`, and restart. These are server-owned credentials; the GUI never asks users for API keys. Session metadata, browser cookies, runs and schedules stay under the ignored `data/` directory. The server includes a persistent managed Chromium browser and serializes tasks to avoid simultaneous control of one device.

The general agent answers questions, executes tools, reports results, and accepts follow-up messages in the same session. Try **List the skills you have**, then **Create a Python script that prints 6 * 7, run it, verify the output, and report it**. The runtime supplies its OS, Python path, workspace and enabled capabilities. Files and shell start in `data/workspace/`; `file_extract` reads PDFs and XLSX cells for cross-application tasks. Browser hosts are controlled by `BROWSER_ALLOWED_HOSTS` (explicit `*` permits any HTTP(S) host). Desktop control requires `DESKTOP_ENABLED=true`; browser and desktop evidence are combined when both are enabled.

Teach a reusable job by describing it and asking the agent to save a skill. `create_skill` saves validated Markdown under the ignored `data/skills/`, and `append_skill_note` records reusable lessons while preserving existing procedures and approval gates. Learned skills join the available index on subsequent model turns and restarts. A saved skill is not an execution pass: ask the agent to try it on a local fixture and verify the result. `SKILL_WRITES_ENABLED=false` or a configured `FREEZE_MANIFEST` disables these writing tools.

Docker deployment, login configuration, persistent volumes and full instructions: [docs/gui-server.md](docs/gui-server.md). A remote bind requires a strong `GUI_PASSWORD`. No production server has been deployed automatically.

## Setup on Windows

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[test,desktop]"
python -m playwright install chromium
python -m harness skills
python scripts/test_project.py -q
```

Python 3.11+ is required. The implementation was tested with Python 3.13 on Windows. Use a dedicated virtual environment for reproducible dependencies.

## Local mock and first run

```powershell
python -m uvicorn mock.mock_irctc.app:app --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000` to inspect the local test flow. Mock credentials are `demo` / `demo`, captcha `TRAIN`; these are fixtures. All approval and booking endpoints in the mock affect simulated tickets only.

Copy `config.example.yaml` to `config.local.yaml`. Configure model provider URLs, model names, API-key environment variable names, browser CDP and Telegram. Both a chat-completions-compatible API and a Messages-compatible API are supported, so the fallback can use a different provider. No provider or Telegram messages are contacted automatically by setup or tests.

For browser tasks, launch your installed Chrome with a dedicated profile and remote debugging enabled, then set `browser.cdp_url` to `http://127.0.0.1:9222`. Keep allowed hosts explicit. The default configuration allows localhost only. Do not attach your normal profile containing unrelated accounts.

```powershell
python -m harness --config config.local.yaml run "Complete the local mock to review" --skill mock-booking
python -m harness --config config.local.yaml run "Create a note in the workspace"
python -m harness --config config.local.yaml preflight
```

The mock skill documents its required inputs. A skill without a macro needs a configured model. Shell tools execute trusted commands with normal user permissions; the file-path sandbox does not isolate shell commands. Optional desktop actions require `desktop.enabled: true`; arbitrary desktop screenshots cannot guarantee automatic secret masking. Development tests never type into native applications.

## Triggers, handoff and replay

```powershell
python -m harness --config config.local.yaml schedule "Run the prepared skill" --at "2026-10-25T10:40:00+05:30" --skill mock-booking
python -m harness --config config.local.yaml serve
python -m harness --config config.local.yaml watch workspace/inbox "Summarize the new file"
python -m harness --config config.local.yaml resume RUN_ID --skill mock-booking
python -m harness --config config.local.yaml reply RUN_ID REQUEST_ID approve
python -m harness.log.replay runs/RUN_ID
```

One process owns the persisted stores and one computer task runs at a time. Schedule times require a timezone; cron expressions use UTC. Interrupted dispatches and pending actions stop for reconciliation rather than repeat a potentially irreversible action. Local handoff replies can be given from another terminal. Telegram adapters also support `/run` and `/reply`; live transport must be configured and exercised by the operator. The default CLI run wires Telegram replies for the active run.

`runs/<id>/` contains state, redacted JSONL, screenshots when a visual observer is configured, summary and offline replay. Place `runs` inside the intended Drive-synced folder before rehearsing. Secrets should be referenced by environment/keychain names and entered through the `secret` tool. Keep personal profiles in the ignored `profile/passenger.yaml`; pass a profile path instead of putting private data in a CLI JSON argument.

## Verification and current limits

Source tests are in `tests/`; timestamped output and JUnit evidence are in `test/`. The mock includes seeded faults and idempotent booking checks. These service simulations do not prove autonomous completion on the live website. The browser integration tests exercise actual local Chromium. External model calls, Telegram delivery, native desktop behavior, NTP accuracy and all real-site rehearsals remain operator checks unless separately recorded as passed.

Live-domain skills are rehearsal drafts: landmarks, fare interpretation, captcha handling and exact selectors must be validated on the real site with the account owner watching. Do not treat a passing mock or this scaffold as a qualified ticket booking. Preflight deliberately fails with the example configuration. See `docs/runbook.md` and `docs/irctc-recon.md` for remaining operational checks.

## Future agents and commits

Read `AGENTS.md`, `memory/README.md`, numbered memory notes and `docs/interfaces.md` before modifying the project. Keep domain knowledge in `skills/` or `mock/`, never `harness/`. Run `python scripts/test_project.py` after changes and record limitations honestly. After implementation commits, write a memory note mapping commit, files, behavior and evidence. Freeze is an explicit operator action after go/no-go checks; `scripts/freeze.py` prepares/verifies hashes but never silently tags the repository. Configure `freeze_manifest` to check frozen hashes before every run. Set `clock.ntp_server` to explicitly synchronize before serving schedules, or supply a measured `clock.offset_seconds`; no network-time query runs by default.
