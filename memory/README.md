# Agent memory

Start with `docs/interfaces.md`, `README.md`, and the numbered notes here. Notes map each implementation commit to changed files, behavior, verification and limitations. The final documentation commit records the preceding implementation commit; memory-only closure commits do not need another note.

Initial workspace: only the original PDF and implementation-plan Markdown, no code and no Git repository. Windows, PowerShell, Python 3.13 available. Official PDF read in full (four pages). Required: generic computer agent, skill learning, chat/schedule/event triggers, own handoff channel, screenshots/reasons/replay; single cheapest Tatkal booking and human payment approval. Freeze and real rehearsal require operator preparation.

## Implementation index

- [001: Foundation](001-foundation.md): initial architecture and shared interfaces.
- [002: Runtime](002-runtime.md): tools, triggers, handoff and execution runtime.
- [003: Mock skills](003-mock-skills.md): fictional workflows and skill-based tests.
- [004: Verification hardening](004-verification-hardening.md): full-run checks, vision and recovery boundaries.
- [005: GUI server](005-gui-server.md): persistent GUI sessions, server-owned credentials and timezone scheduling.
- [006: General agent](006-general-agent.md), implementation `e27f803`: natural answers, follow-up conversations, skill learning, document extraction, capabilities and model-decision evidence.
- [007: Connected triggers](007-connected-triggers.md), implementation `0fdca9f`: file/email/webhook/Telegram sources connected to the serialized queue, shared handoff transport and notifications.
- [008: Progress and real-provider verification](008-generality-progress-verification.md), implementation `f71dd83`: generic progress detection and handoff cancellation fixes, plus the final real-Haiku and regression evidence. This is the latest implementation handover; its memory-only closure was committed as `4b37e62`.

Notes record the state at their own commit. An older note's remaining-work list may have been resolved by a later note; use note 008 and the current [coverage document](../docs/general-agent.md) for the latest limitations.

## Current handover

The general agent now answers questions and retains conversations instead of marking ordinary final text blocked. It can discover/load skills, learn a told task, append reusable lessons, use files/terminal/browser tools, and extract PDF/XLSX data. Loaded skill gates survive a resumed turn. Model responses, token usage, failure reasons and screenshots are available in logs/replay. Different successful file/terminal actions count as progress even when the browser screen stays unchanged.

GUI, schedules and configured event/chat sources use the same persistent serialized run queue. Optional file, read-only IMAP, signed webhook and Telegram sources are wired into the server. The GUI is an operator handoff channel; optional Telegram handles idle /run commands, replies and notifications through one transport. Learned skills are local overlays under ignored data/skills and preserve bundled gates/macros. Freeze configuration disables the skill-writing tools.

The ignored local .env was changed from Sonnet to `CLAUDE_MODEL=claude-haiku-4-5-20251001`; the tracked settings default and .env.example now use that model too. No credential values are recorded in memory. At the last runtime check the GUI was idle on http://127.0.0.1:8787, desktop control was disabled, and Telegram was disabled. This is a recorded session state, not a guarantee that a process is still running; check it before restarting or submitting work. Start with `python -m harness.web` and reload the browser after client updates.

Latest verification: **205 passed, 1 skipped** (Windows symlink privilege), plus **four independently checked real-Haiku tasks**: skill listing, a verified file/terminal follow-up, learning/executing a new skill with a field note, and XLSX values entered into a fictional local browser form. The automated suite's model/email/Telegram fixtures remain distinct from those real-Haiku checks. The earlier failed real run that exposed the progress bug is retained.

See [verification commands and scope](../test/general-agent-verification.md), [final suite record](../test/20261024T192944122701Z/result.json), and [successful real-provider record](../test/20261024T192850405543Z-live-general/result.json). Repeat paid local checks only intentionally with `python scripts/smoke_general_agent.py --live-model`. An older baseline result under test/20261024T185033561096Z remains untracked from the earlier session and was left unchanged.

Native-app control and live-domain rehearsals, external mailbox/Telegram delivery, real booking/payment, submission recordings/proof and qualification remain unverified operator work. Shown-demo recording, trace-to-macro compilation and automatic regression-validated skill promotion remain unimplemented bonuses. No freeze tag or live booking schedule was created. Continue to follow AGENTS.md's watching-human and secret-handling restrictions.
