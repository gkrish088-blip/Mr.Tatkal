# GUI server verification

Final command: `python scripts/test_project.py -q`.

Result: **181 passed, 1 skipped**, 40.37 seconds. Authoritative timestamps, console output and per-test JUnit records are in `20261023T214135078991Z/`. The skip remains the Windows symlink-creation privilege check. The existing Starlette/httpx TestClient deprecation warning does not affect results.

New tests in `tests/web/` verify:

- Real Chromium GUI -> server -> queued generic harness -> managed browser -> fictional booking -> GUI approval -> one ticket -> screenshots/replay.
- General agent initiated through the actual GUI, using a test-only Claude HTTP endpoint and a server-side key, writes a real workspace file; session is restored after page reload. No live provider call is used for this test.
- Session history and queued tasks survive server restarts; interrupted actions are marked for reconciliation.
- Real browser cookies survive closing and relaunching the persistent browser profile.
- Tasks execute serially; cancelled queued tasks are not executed.
- One-time schedules and cron jobs persist; pause/resume/delete work through both API and GUI. Due jobs queue once; daily 11:00 recurrence retains Asia/Kolkata timezone.
- Login cookie, cross-origin/CSRF restrictions, host validation, refusal of unauthenticated API access, private artifact restrictions and provider-key non-disclosure.
- Responsive 390px GUI has no horizontal page overflow; JavaScript emits no uncaught page errors. Desktop overview, completed ticket and mobile screenshots were generated, with overview/mobile copies retained in this folder.
- Masked form updates still change private keyed browser state hashes, so general form filling is not mistaken for a stuck screen.

Other checks passed: Python compileall, JavaScript syntax (`node --check`), editable package installation, Git whitespace check, and Compose YAML/persistent-volume structure validation. `.env` and local `data/` were verified ignored by Git.

Earlier run evidence is retained: `20261023T213650033634Z/` records a GUI test selector failure fixed by explicit accessible navigation labels; `20261023T214053530406Z/` records a test assertion that ran before async session hydration completed, fixed by waiting for the visible completed state. Both flows pass in the final full run.

## Limits

Neither real Claude nor DeepSeek credentials were supplied, so actual provider reachability/quota was not tested. The GUI exposes an explicit small-request connection check for the operator after adding a key to `.env`. No real booking, payment or external message was performed. Docker is unavailable on this machine: Dockerfile/Compose were prepared and structurally checked, but no image was built or container started. No remote server was deployed. Existing live-site reconnaissance and rehearsal requirements still apply.
