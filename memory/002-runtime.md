# Generic runtime

Commit: `8855f41` (`feat: build resumable generic agent runtime and computer tools`).

- `harness/core/types.py`: typed calls/results/decisions, tool registry and signature-derived model schemas.
- `harness/core/loop.py`, `context.py`, `verify.py`: bounded plan/act/observe/verify loop, lazy skill loading, approval gates, redacted events, stuck recovery and handoff. Pending actions are fingerprints; crash/timeout requires reconciliation.
- `harness/core/run_manager.py`, `macro.py`: atomic JSON run state, declarative bound macro steps, checkpoint failure recovery and persisted cursor.
- `harness/models/adapter.py`, `failover.py`: HTTP chat/Messages adapters, request timeout, usage, bounded retries and fallback.
- `harness/tools/`: shell process-tree timeout/truncation, atomic sandboxed files, browser CDP/semantic refs/masked screenshots/request pacing, opt-in desktop, clock/NTP helpers, environment/keychain secrets.
- `harness/log/`: central redaction, fsynced JSONL, HTML replay and summaries. Short-value boundary redaction prevents corruption of artifact UUIDs.
- `harness/handoff/`: persistent requests/replies/timeouts, own Telegram channel, duplicate suppression and chat filtering.
- `harness/triggers/`: persistent schedules, UTC cron, file/email/HMAC webhook events, chat commands.
- `harness/cli.py`, `preflight.py`, `__main__.py`, `config.example.yaml`: runnable operator CLI and fail-closed readiness report.
- `scripts/test_project.py`, `scripts/freeze.py`: timestamped test evidence and explicit manifest generation/verification.
- `pyproject.toml`, `README.md`, `docs/runbook.md`, `docs/borrow-list.md`: dependencies, setup, workflow, external checks and no-vendoring decision.
- `tests/unit/`: six initial core, eight service, ten tools checks; one Windows symlink privilege skip.

Evidence: tools and service XML/reports under `test/`; combined run `test/20261023T183316076774Z/` passed 159, skipped 1 (includes uncommitted mock tests staged in the next implementation commit). Earlier run `test/20261023T183127525147Z/` recorded Chromium-not-yet-installed failure; retained for honest history. No live-site flow, native input, model provider call or external message executed.

Remaining: model image payload support and regression hardening; local mock/skill commit follows. External credentials, actual CDP, Telegram, native desktop, network clock and live qualification require operator preparation. Bonus recorder/reflector intentionally deferred behind P0/P1 acceptance gates.
