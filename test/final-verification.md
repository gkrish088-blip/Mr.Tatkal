# Final local verification

Final command: `python scripts/test_project.py -q`.

Result: **169 passed, 1 skipped, 1 dependency deprecation warning**, 22.99 seconds.

Authoritative output, per-test JUnit results and command timestamps: `20261023T183902657928Z/`. The skip is the Windows symlink-creation privilege check; it is not recorded as a pass. Starlette's TestClient currently emits a deprecation warning for its httpx transport; fixture behavior passed.

Other completed checks:

- `python -m compileall -q harness mock scripts`: passed.
- `python -m pip install -e . --no-deps`: editable package built and installed successfully. HTML package data is declared for the local app.
- `python -m harness skills`: skill discovery succeeds (fifteen skills after full-ticket addition).
- `python -m harness preflight`: intentionally fails on the unconfigured example (no model keys, CDP, Telegram or rehearsal evidence). No readiness claimed.
- Actual local Chromium: full ticket solely from declarative skill macro, exact review verifier, one isolated test-transport approval, one fictional PNR, before/after screenshots and replay images. Final captured screenshot visually inspected: PNR legible, profile/review contents masked.
- New-task generality: adding only a temporary skill writes and executes a Python script and verifies the saved file/output through the generic runtime.
- Recovery/privacy checks include killed child process state, action timeout, approval denial, repeated-state guard, failover fixtures, masked screenshots, secret-safe errors, redacted state/logs, runtime manifest changes and domain-independence lint.

Retained earlier failed runs show issues fixed during integration: missing Chromium installation, incomplete macro checkpoints, Windows path separators, and platform newline expectations. Corrected source checks pass in the final full run. Separate service/tool reports preserve their own initial failures and fixes.

## Not established by these results

No real website, external model API, live Telegram, keychain, NTP server or native desktop input was exercised. API seeded scenario tests use drivers/virtual time where documented; they do not meet the guide's full autonomous M1-M13 browser qualification. G1 has an engine-level skills-only test; the remaining whole-device G cases need broader acceptance runs. R1-R4 are pending. The freeze tag and real booking were not executed. Bonus demo recorder/reflector are deferred until P0/P1 go/no-go requirements are met.

Use `docs/runbook.md`, `docs/irctc-recon.md`, and `docs/mock-lab.md` to continue without confusing mock success with live readiness.
