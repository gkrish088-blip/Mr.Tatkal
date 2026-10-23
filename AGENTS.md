# Project instructions

Read `memory/README.md` and the latest implementation notes before changing code. The source PDF is authoritative; use the supplied implementation plan as the build guide. Keep harness domain independent; domain knowledge belongs in skills/mock only.

Every logical change needs appropriate tests. Save command, timestamp, result, and limitations under `test/`. Never label mocked or skipped checks as real-service passes. No live login, booking, payment, desktop control, or external messages during development unless explicitly requested with a watching human. Never store secrets or passenger information in tracked files.

Maintain small coherent Git commits. After each implementation commit, write `memory/<sequence>-<topic>.md` recording commit hash, changed files, behavior, checks, and remaining limitations, then include the note in the next commit. Final memory-only commit closes the last implementation commit. Do not recursively create notes for documentation-only closure commits.
