# Hermes review and borrowing decision

Reviewed the public [Hermes repository](https://github.com/NousResearch/hermes-agent) and its visible architecture on 2026-10-23. Candidate areas in the guide are the skill loader/format, cron scheduling, gateway and tool adapters. The repository advertises an MIT license; no source code has been copied or vendored into this project.

Decision: implement the small contracts locally using PyYAML, croniter, httpx and Playwright. This keeps state semantics, approval rules and error handling auditable without bringing in a second agent runtime. No copied code means no third-party source notice is needed at present. If a future change copies Hermes code, record exact upstream paths/revision and preserve its license in NOTICE before committing.

Compatibility is limited to Markdown skill files with YAML frontmatter; we do not claim complete Hermes runtime compatibility. The local additional metadata and declarative macro format are documented in `interfaces.md`.

Browser attachment follows the official [Playwright CDP documentation](https://playwright.dev/python/docs/api/class-browsertype#browser-type-connect-over-cdp). External APIs remain unverified until credentials and an operator-controlled rehearsal are available.
