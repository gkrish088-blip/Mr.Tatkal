# Transient navigation snapshot recovery

Implementation commit: `f11e2fb8341db20d703923f7d05ab5a25984a3ef`.

Changed files: `harness/tools/browser.py`, `tests/unit/test_tools_browser.py`, and the focused test record in `test/20261024T231432415612Z/`.

Browser snapshots now handle an HTML document whose body is temporarily unavailable, returning an empty observation with `body_missing=true`. The snapshot path retries once after the two observed navigation-race errors: a destroyed execution context and a missing `Node` passed to `createTreeWalker`. Other exceptions still propagate. This protects generic browser workflows from an immediate redirect/document-replacement race without retrying site actions.

Verification: `python scripts/test_project.py -q tests/unit/test_tools_browser.py` — **5 passed in 11.81 seconds**. Coverage removes the body to check the empty-state observation, then simulates a document-replacement error and verifies one successful retry. The full suite was not rerun.

The owner reported disconnecting a VPN and asked for another watched IRCTC booking attempt. A fresh public-page probe loaded `www.irctc.co.in/nget/train-search`, displayed the General quota and Search Trains controls, and recorded zero failed application requests. This is public access evidence only; it does not prove login or inventory. The exact command, outcomes and limitations are in `test/20261024T231532Z-irctc-vpn-off-retry/`.

Before this fix, two new agent sessions failed during initial navigation snapshots; neither submitted credentials. A third reached the booking page and opened the sign-in menu, but was cancelled after repeated invalid element references; it also did not enter credentials. The project browser is managed Playwright Chrome. The native Windows Computer Use helper could not initialize (`failed to write kernel assets`, OS error 3) after its retry/reset procedure.

The owner-supplied IRCTC credential values are stored in Windows Credential Manager under `IRCTC_USERNAME` and `IRCTC_PASSWORD`; their values are not tracked or copied into agent goals. Passenger details have not been written to a local or tracked profile. Full legal name and nationality are still needed before entering passenger details. No login, CAPTCHA/OTP, live availability, passenger review, fare approval, payment QR, payment, PNR, or ticket has been verified.

Next: restart the idle local server to load this code, then start a fresh watched `irctc-book-ticket` run. Use sequential secret entry and current screenshot-based mouse clicks for controls whose DOM labels are corrupted. Hand CAPTCHA/OTP to the owner. If a required passenger field is missing, ask the owner in the GUI. Pause for explicit approval at the exact fare review and never make the payment for the owner.
