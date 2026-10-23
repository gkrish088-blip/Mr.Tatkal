# Local mock service checks

- Timestamp: 2026-10-24T00:01:19+05:30
- Command: `python -m pytest tests/integration/test_mock_booking.py tests/generality/test_mock_tasks.py -q`
- Result: **134 passed**, one upstream Starlette TestClient deprecation warning, 12.64 seconds initially; rerun after single-booking and repeat-approval guards: **134 passed in 11.07 seconds**.
- Coverage: 20-seed service fault matrix M1–M7; 20 seeds each for payment approval at 20s, 90s, never; idempotent lost-response replay; missing profile validation; virtual 60s access denial; closed/open booking window; mismatch blocks payment; non-bookable seats rejected; generic research/contact fixture.
- Limits: These are HTTP service-contract tests driven by a deterministic test client. Latency, payment timing, access denial and window opening use virtual time. They do not establish harness recovery, real timing, model failover (M8), OS crash recovery (M10), browser layout robustness (M6) or real-site readiness. Those require separate harness/browser/rehearsal checks. No real tickets, credentials, payments or messages were used.
