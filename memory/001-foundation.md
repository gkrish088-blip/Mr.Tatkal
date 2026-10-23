# Foundation commit

Commit: `261d600` (`docs: preserve requirements and define implementation contracts`).

- Original PDF and guide preserved without edits.
- `docs/interfaces.md`: shared Python contracts for tools, loop, state, logs, handoff, scheduling, mock.
- `AGENTS.md`: future-agent rules for regression tests, memory after implementation commits, secret handling, live-service boundaries.
- `.gitignore`: excludes runtime state, personal profiles, credentials and temporary outputs.
- `memory/README.md`: navigation and authoritative requirements read from all four PDF pages.

Validation: file inventory and full PDF text extraction with pypdf. No existing code/tests were present. Next: generic harness and local service tests. No live account or booking used.
