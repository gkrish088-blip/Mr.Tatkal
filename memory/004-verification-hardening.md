# Integrated verification and hardening

Commit: `4db24da` (`fix: verify full skill runs, vision payloads and recovery boundaries`).

- `harness/models/adapter.py`: actual vision payloads (latest two screenshots) for chat and Messages protocols, configurable vision and image-size guard. `tests/unit/test_model_vision.py` verifies both request formats with fixture HTTP.
- `harness/core/context.py`: summarize older observations while keeping the latest two detailed events.
- `harness/core/loop.py`: approval reply normalization, terminal denial/timeout, bounded action deadlines preserving uncertain intent, checkpoint polling for asynchronous UI, correct nonvisual-result verification and stuck-state hashing.
- `harness/tools/browser.py`, `__init__.py`: generic private rendered-JSON review verifier exposed as `browser_assert_json`. `files.py`: portable slash-normalized relative paths, fixing a Windows checkpoint mismatch.
- `skills/mock-booking/macro.yaml`: every action now has an explicit checkpoint.
- `skills/mock-ticket/`: full local ticket macro, exact profile/route/date/quota/confirmed-fare verification before test payment, one own-channel external approval, final screenshot. Inputs require both string `age` and matching integer `age_number`.
- `tests/integration/test_browser_workflow.py`: full flow now belongs entirely to the skill, test retains independent ticket assertions; screenshot files are inside the run and replay must embed images.
- `tests/generality/test_skill_files.py`: new task runs with only a new skill; script, output and saved content verified. Windows shell newline expectations use platform line endings.
- `tests/unit/test_core.py`: actual subprocess termination persistence, deadline reconciliation and terminal approval denial.
- `harness/integrity.py`, `tests/unit/test_integrity.py`: opt-in manifest guard before a run; refuses changed/missing/out-of-root files.
- `harness/cli.py`, `config.example.yaml`: optional desktop, file watcher, corrected clock/NTP synchronization before schedule serving, and runtime integrity configuration.
- `tests/lint/test_invariants.py`: harness domain independence, valid skills with checkpointed macros and common accidental provider-key detection.
- `pyproject.toml`: package HTML assets. `docs/interfaces.md`, `borrow-list.md`, `mock-lab.md`, `runbook.md`, `README.md`: implemented contracts, sources, usage and explicit limits.
- `test/`: final report plus timestamped full and targeted runs, including failed intermediate checks and subsequent fixes.

Final result: **169 passed, 1 skipped** in `test/20261023T183902657928Z/`. One Starlette/httpx deprecation warning; skip is Windows symlink privilege. Compileall and editable package installation passed. Final local ticket screenshot visually inspected: PNR visible and private profile content masked. Example preflight correctly refuses readiness.

No real account/site, native application input, external model request, Telegram message, NTP query, real payment, freeze tag or screen/phone recording was performed. Full autonomous fault matrix/general device qualification and R1-R4 remain pending, documented in `test/final-verification.md`. P2 demo recorder/reflector are deliberately deferred under the guide's priority gate. Use `docs/runbook.md` for operational continuation. The following documentation-only closure commit records this note and needs no recursive note.
