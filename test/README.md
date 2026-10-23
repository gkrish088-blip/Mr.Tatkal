# Test evidence

Run `python scripts/test_project.py -q` to save timestamped command metadata, full pytest output and JUnit XML here, including failed checks. Source tests live in `tests/`; this folder contains their results.

Local API simulations are not browser qualification. Browser tests use real local Chromium against local pages. Native desktop actions and external model/Telegram/live booking checks require separate operator-controlled rehearsal. Skips are never passes. Generated runtime screenshots remain gitignored; retained evidence must contain no secrets.
