# General agent runtime verification

Source: all four pages of the supplied problem PDF were read again, alongside the implementation plan. The PDF requires one generic computer harness, skill-based jobs, chat/schedule/event starts, handoff and replayable evidence. The adapters already existed; ordinary final answers, continued conversations, skill learning, restored skill gates, combined desktop/browser observations and model-decision evidence were missing or disconnected.

## Commands and results

- `python -m pip install -e ".[test]"`: successful; installed the newly declared openpyxl dependency. No model request was made by installation.
- `python scripts/test_project.py -q tests/generality/test_general_agent.py tests/unit/test_core.py tests/web/test_server.py tests/unit/test_model_vision.py`: 27 passed, 1 failed because openpyxl was not installed yet. Timestamp, command, output and JUnit: `test/20261024T191023632238Z/`.
- `python scripts/test_project.py -q tests/generality/test_general_agent.py tests/unit/test_core.py tests/web/test_conversation.py tests/web/test_gui.py`: 22 passed, 1 failed because the new API test fixture did not allow TestClient's testserver host. The fixture was corrected without weakening the production host check. Evidence: `test/20261024T191215259471Z/`.
- `python scripts/test_project.py -q`: **195 passed, 1 skipped**, 46.89 seconds. Evidence: `test/20261024T191349832518Z/`. The skip is Windows symlink privilege; the existing Starlette/httpx deprecation warning remains.
- `node --check harness/web/static/app.js` and `git diff --check`: passed.

New checks cover both model protocols for natural and empty answers; redacted answer persistence/replay/token accounting; bounded model deadlines; learned skills executed through real file tools; overlay gates/macros and frozen writes; restored skill gates; actual handoff pause/reply; actual PDF/XLSX extraction; combined observer data with test adapters; and API/Chromium conversation follow-ups, reload persistence and HTML escaping.

## Scope and limitations

The full automated suite uses local provider fixtures and simulated domain services. The GUI tests use actual Chromium, not a mocked browser. Combined native-desktop observation is adapter-tested; no native input was performed. No real login, booking, payment, Telegram or mailbox access occurred. Native-desktop rehearsal, live-domain qualification, external handoff delivery, recorder-based skill learning and automatic validated patch promotion remain separate operator work. Told-task skills and append-only field notes are supported; saving a skill is not represented as an execution pass.

The updated conversation screenshot was visually inspected and is retained as `test/general-agent-conversation.png`. It intentionally includes escaped script text from the XSS fixture.

## Connected event and operator channels

- `python scripts/test_project.py -q tests/web/test_event_sources.py tests/unit/test_services.py tests/web/test_server.py`: 23 passed, 7.35 s; `test/20261024T191836251307Z/`.
- `python scripts/test_project.py -q`: **202 passed, 1 skipped**, 56.50 s; `test/20261024T192224113047Z/`. This run includes the new event/notification tests. Skip/warning remain as above.
- After the final skill-dropdown/capability-display changes, `python scripts/test_project.py -q tests/web/test_gui.py tests/generality/test_general_agent.py`: 16 passed, 22.07 s; `test/20261024T192453636387Z/`.

These cover actual local file arrival/change/restart dispatch, source-namespaced queue inputs, signed webhook authentication/identity/replay/payload limits, concurrent event-state updates, read-only IMAP parsing and message-body delivery through a fake mailbox, and idle Telegram chat -> queue -> persisted handoff -> reply through one mocked HTTP transport. No real email or Telegram service was contacted. Learned skills appear in the GUI selector after a completed turn. Default configuration still enables no external messaging or mailbox sources.
