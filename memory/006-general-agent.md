# General agent answers, conversations and learning

Implementation commit: `e27f8031185259857950c11217af8ee9d03788b4` (`feat: complete general agent answers and skill learning`).

Read all four source-PDF pages and the supplied plan again. Required adapters mostly existed, but the user-visible general-agent loop discarded final text and called ordinary skill-listing questions blocked. The model already received the skill index; the earlier chat diagnosis overstated a discovery problem.

Changed files: core types/state/context/loop, model adapter, CLI, skill loader and new writer, generic tools/files/browser/observer, GUI settings/manager/store/app/static assets, pyproject, .env.example, README/interfaces and tests. Exact changed paths are in the commit. New learned skills and field-note overlays live in ignored data/skills and preserve bundled gates/macros. Frozen runtimes do not expose skill-writing tools. Final answers and follow-up messages persist; model decisions, usage and explanations now appear in redacted logs, summary and replay. PDF/XLSX extraction and system capabilities support general tasks. When desktop is explicitly enabled, browser structure and desktop screenshots are combined.

Verification: `test/general-agent-verification.md`; full suite `test/20261024T191349832518Z/`: 195 passed, 1 skipped (Windows symlink privilege), 46.89 s. Initial dependency and test-fixture failures are retained and explained. Actual Chromium tested two-turn answers/reload/escaping; local HTTP fixtures supplied model output. No live desktop input or real booking/payment/external messages occurred. GUI conversation screenshot inspected.

Remaining: wire optional trigger adapters/Telegram into the GUI server; run safe real-model local tasks after restarting it; native-desktop and live-domain rehearsals still require the operator. Told-task skills and append-only lessons exist; shown-demo recording and validated automatic patch promotion are bonus work and are not claimed implemented.
