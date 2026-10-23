# Generic tools verification

Executed 2026-10-24 00:02 IST on Windows / Python 3.13. No live service, native desktop input, external message, login, booking or payment was performed.

Final command: `python -m pytest tests/unit/test_tools.py tests/unit/test_tools_browser.py -q --junitxml=test/tools-results.xml`

Result: **10 passed, 1 skipped**, 2.91 seconds. JUnit details in `tools-results.xml`.

Coverage: atomic file write/edit/read/list, rejected parent traversal, bounded shell output and nonzero status, timeout including child-process termination, offset-aware clock waits, concurrent sliding-window rate limiting, desktop disabled by default, secret direct insertion without a returned value, fill-error message excludes inserted secrets, installed tool schemas/status, actual headless Chromium DOM actions, semantic refs after DOM replacement, explicit label/text macro refs, disallowed host rejection, password screenshot masking verified by pixel color, typed-value exclusion from snapshot.

Skipped: filesystem symlink escape test requires Windows symlink privilege unavailable to this process. Parent traversal test passed; resolved-path implementation still rejects symlink escape, but that specific host check remains unverified.

Earlier runs during development:

- `python -m pytest tests/unit/test_tools.py -q`: 7 passed/1 skipped; after schema and registry-shell tests, 8 passed/1 skipped.
- Initial browser command failed because Chromium's headless-shell download had not completed. Browser installation subsequently completed with `python -m playwright install chromium`; tests use headless full Chromium (`channel='chromium'`).
- Next browser run failed at select-label lookup: an enclosing label incorrectly included option text. Fixed semantic label extraction to exclude child form controls.
- Browser-only rerun: 1 passed. Combined run: 9 passed/1 skipped (2.86 s); fill-error masking change rerun: 9 passed/1 skipped (3.48 s); after adding fill-error canary test, final command above: 10 passed/1 skipped (2.91 s).
- `python -m compileall -q harness/tools`: passed.

Limits: CDP attachment to operator Chrome, real-site DOM/captchas, NTP over the public network, native desktop accessibility and input, keychain provider and browser downloads have not been exercised. Shell commands are trusted and not OS sandboxed; only cwd and file tools are workspace confined. Desktop screenshots cannot guarantee generic automatic secret redaction and remain an explicitly enabled operator feature. Request pacing covers browser navigation and XHR/fetch, not image/style/script subresources. Artifact PNGs were temporary test output; tracked test results contain no real passenger or credential data.
