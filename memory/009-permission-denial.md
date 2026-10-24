# Permission denial stops account retry loops

Implementation commit: `2da05cb928c1cca44d78085c67afcb263608a736`.

Changed files: harness/core/types.py, harness/core/loop.py, harness/models/adapter.py, tests/unit/test_core.py, test/20261024T195802639795Z/.

The reported live attempt had 66 tool actions, including 39 shell calls, and two rejected browser navigations. Browser hosts were still localhost-only. No credential values or raw task contents were copied into evidence. PermissionError now becomes a structured operator-configuration block. The loop stops the same action batch immediately, persists the reason, and makes no recovery model request or shell workaround. Ordinary transient exceptions remain recoverable. Generic model instructions reinforce browser-only account operations, transaction review, actual payment images and service-confirmed success. Human-handoff schema now exposes optional attachment paths.

Checks: `python scripts/test_project.py -q tests/unit/test_core.py tests/unit/test_model_vision.py tests/generality/test_general_agent.py`: 26 passed, 5.22 s. Timestamp, exact command and JUnit output are in the evidence directory. These are local tests with model fixtures, not real login or booking passes.

Remaining: configure the explicitly authorized live hosts locally, validate the live login with the watching owner, add regular-ticket instructions and deliver payment images/downloads in the GUI. No payment or real booking was attempted by this change.
