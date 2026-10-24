# Generality progress and real-provider verification

Implementation commit: `f71dd83d943fa899b495130d812f1daec79b2a07` (`fix: recognize progress across computer tools`). This documentation-only closure records the last implementation commit; no recursive note is required.

Changed files: harness/core/loop.py, harness/handoff/channel.py, harness/web/manager.py, tests/generality/test_general_agent.py, tests/web/test_conversation.py, new scripts/smoke_general_agent.py, docs/general-agent.md, test/general-agent-verification.md, screenshots and timestamped evidence. Includes the preceding implementation's memory/007-connected-triggers.md.

Real Haiku exposed a generic-progress bug: a static browser screenshot caused recovery during successful file/shell work. Stuck detection now compares repeated action/result/state combinations; unrelated successful actions no longer look stalled. Existing repeated-identical-action detection still passes. Cancelling a pending question cancels persisted requests and safely clears an ask_human intent. Uncertain computer actions retain needs_reconciliation.

Checks and evidence:

- Focused progress/core/conversation regression: 26 passed, 5.42 s, test/20261024T192819278344Z/.
- Initial real-model check retained as failed: test/20261024T192158894802Z-live-general/result.json. It passed a question and terminal task, then unnecessarily handed off while learning. Stopped without any real account operation.
- After the fix and server restart: `python scripts/smoke_general_agent.py --live-model` passed all four independent checks using real claude-haiku-4-5-20251001 and local tools. Evidence: test/20261024T192850405543Z-live-general/result.json. Question 0 steps; terminal follow-up 3 steps/stdout 42; new skill load/execute/field-note 6 steps/stdout 56; XLSX -> local browser form 5 steps and exact saved values independently confirmed. Temporary fictional web service was stopped by the script. Sessions and detailed redacted logs remain in ignored data/runs, keyed by IDs in the report.
- Final full regression: 205 passed, 1 skipped, 54.36 s, test/20261024T192944122701Z/. Skip is Windows symlink privilege; existing Starlette/httpx deprecation remains. JavaScript syntax, compileall and whitespace checks passed.
- Actual local form screenshot visually inspected with input fields masked. Updated GUI conversation screenshot also retained. GUI suite uses actual Chromium with local model fixtures; the four smoke checks above use a real paid provider.

The GUI was restarted on http://127.0.0.1:8787 with the final implementation; refresh the browser to load the new client. No real login, booking, payment, native-desktop input, Telegram or mailbox access was performed. Native-adapter and live-domain rehearsals, submission evidence, shown-demo recording, trace-to-macro compilation and automatic validated skill promotion remain the explicit limitations in docs/general-agent.md. No freeze tag/live schedule was created. A baseline test directory from the earlier conversation remains untracked and was left unchanged.
