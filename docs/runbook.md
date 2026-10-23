# Rehearsal and run-day runbook

Status: local implementation only. No live booking, external handoff, quota check, hotspot measurement or real rehearsal has been completed by the coding agents.

1. Owner completes `irctc-recon.md`: confirm account/Aadhaar/OTP readiness, quota and route, actual classes/window, passenger fields, total fare interpretation and allowed attempts with organizers.
2. Configure both model providers using environment variables and test a tiny actual request. Confirm timeouts and fallback under an injected outage. Example preflight checks key presence only, not quota or reachability.
3. Configure Telegram, verify message, screenshot, reply, timeout, restart and chat allowlist with the correct phone. Never approve an unknown action.
4. Use dedicated Chrome profile, own hotspot, explicit host allowlist and normal pacing. Operator must watch every real-site rehearsal. Stop before payment. Run local tests first.
5. Record the timed rehearsal on screen and from another phone, save evidence to the chosen Drive folder from the start. Confirm replay images display on another machine. Keep private fields masked in exported artifacts.
6. Verify every U/M/G/L requirement in the guide and record unpassed items. API mock tests are not the required autonomous 20-seed browser acceptance suite. Native desktop and live-service checks need their own results. Do not mark go/no-go green merely because unit tests pass.
7. Before the actual freeze: commit all approved code/skills/config, run `python scripts/freeze.py`, inspect and commit the manifest, then tag `freeze`. Run `python scripts/freeze.py --verify`. Set `freeze_manifest` in the private configuration before freeze so each runtime launch refuses changed/missing manifest files. Disable any learning/self-editing for live mode. The explicit verification script additionally compares the tracked file set; runtime checks listed file hashes.
8. Schedule with explicit `+05:30` timestamp and verify the persisted job. Keep scheduler process running, sleep disabled, laptop plugged in, phone/payment app ready, both recordings active. Check clock offset using trusted time; scheduler precision tests are local and do not establish network time accuracy.
9. Watch without input during the live run; approve the final payment only. If an interrupted action needs reconciliation, inspect site state before any retry to avoid duplicate booking.
10. Save ticket proof, PNR screenshot, e-ticket, run log, replay, frozen skills/manifest and both recordings in the Drive folder. Never invent or edit evidence of success.

No freeze tag has been created automatically because live readiness is not yet established.
