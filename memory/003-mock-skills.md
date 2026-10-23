# Mock flows and task skills

Commit: `cf04913` (`feat: add seeded booking lab and composable task skills`).

- `mock/mock_irctc/app.py`, `index.html`: localhost API/browser app with login, search, fare/availability traps, passenger validation, exact review digest, external test payment and MOCK ticket. Seeded latency/5xx/captcha/session/popups/open-window faults. Idempotency and one booking per app instance.
- `mock/mock_tasks/app.py`: unrelated shop/inbox/form fixtures used to test generic task access.
- `skills/*/SKILL.md`: fourteen procedural skills, with domain knowledge outside harness. `skills/mock-booking/macro.yaml` is a review-only local browser rehearsal with checkpoints.
- `profile/passenger.example.yaml`: fictional template; actual profile remains ignored.
- `tests/integration/test_mock_booking.py`: service-level seeded cases, review mismatch guards, payment approval/expiry and idempotency.
- `tests/integration/test_browser_workflow.py`: actual Chromium + generic engine + skill macro, then test-only transport approval, exact ticket and single handoff checks.
- `tests/generality/test_mock_tasks.py`: unrelated service fixture checks.
- `docs/mock-lab.md`, `docs/irctc-recon.md`: usage, API and honestly pending live reconnaissance.
- `test/mock-service-results.md`, `mock-browser-results.md`: commands/results/qualification limitations.

Verification: 134 service tests pass; real local browser end-to-end passes. Last combined run 159 pass/1 platform skip. Service fault coverage is not full autonomous M1-M13 qualification: virtual time, API drivers and lost-response simulations are explicitly distinguished from real latency/process-death/browser recovery. External providers, Telegram and live booking remain untested.
