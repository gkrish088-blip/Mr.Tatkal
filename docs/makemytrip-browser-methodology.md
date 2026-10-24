# MakeMyTrip browser-control methodology and failure analysis

## Scope and conclusion

This document reconstructs the recorded MakeMyTrip attempts for the ticket task from the tracked test summaries, run action records, and browser-tool implementation. It explains what the agent actually did, what was done separately as a manual diagnostic, and which actions failed.

The project opened a visible installed Chrome window, but the automation did **not** consistently operate it the same way a person would. The recorded traces use the project’s browser tools; they do not show native desktop-control calls. Most actions were Playwright commands aimed at DOM-discovered elements. In the final login attempt, the stored phone number was inserted with a field fill; the action did not send individual keyboard events. The browser tool can issue mouse and keyboard events, but the last login did not use per-key typing. That is a real gap against a strict “control the mouse and keyboard like a human” requirement.

The evidence does **not** prove that this gap caused MakeMyTrip to withhold the OTP screen. The number-field fill and Continue click both returned successful tool results, but the page did not visibly advance. The service may not have accepted the request, the input event sequence may have mattered, or another site-side condition may have prevented the transition. No retained evidence identifies which one happened, and SMS delivery is unknown.

This is evidence about a failure in this run and harness. It does not establish that the booking task is inherently beyond an agent that uses a reliable, properly instrumented browser workflow.

## How the project controlled the browser

The live page used the project’s `BrowserTools` wrapper around Playwright:

| Operation | Actual browser operation | What that means for “like a human” |
| --- | --- | --- |
| Open the website | `launch(headless=False, channel="chrome")` created a persistent, visible Chrome context. `goto()` then navigated directly to the MakeMyTrip rail URL. | A real Chrome window was visible, but the agent did not type the address into Chrome’s address bar. |
| Read the page | `snapshot()` extracted visible DOM elements, labels, roles, bounds, page text and network diagnostics; `screenshot()` captured an image. | The model usually received structured DOM observations, not only a screenshot interpreted by sight. |
| Click a named element | `browser_click` refreshed the snapshot and resolved a generated element reference, then called Playwright `locator.click()`. | A browser click was generated, but the target was picked by its DOM reference. Stale or incorrect references caused failures. |
| Click by screen position | `browser_click_at` called `page.mouse.click(x, y)` after checking that the coordinates were in the viewport. | This is the clearest mouse-like path in the tool. It was used a small number of times, not as the primary interaction method. |
| Enter text | `browser_type` normally called Playwright `locator.fill(text)`. Only `sequential=true` used `press_sequentially()` with a 75 ms delay between characters. | The recorded public and login typing actions omitted `sequential`, so they used field fill, not visible per-key typing. |
| Press a key | `browser_press` called `page.keyboard.press(key)`. | Actual browser keyboard events were available. One attempt used an invalid key name; a later `Control+a` was accepted. |
| Scroll | `browser_scroll` moved the pointer and called `page.mouse.wheel(0, amount)`. Amounts are pixels. | Scroll calls of `3` or `5` moved only a few pixels, so they were not useful human-sized scrolls. |
| Insert the login number | The `secret` tool fetched a named value from local keychain storage, registered it for redaction, then called `browser.type()`. Its default is `sequential=False`. | The value stayed out of model output and tracked evidence, but this login entry was a direct field fill. The final run did not request sequential key events. |

Relevant implementation: [`browser.py`](../harness/tools/browser.py#L111) contains the host guard, Chrome launch, snapshots, clicks, typing, keypress and scroll behavior; [`secrets.py`](../harness/tools/secrets.py#L9) shows the private insertion default. The browser wrapper allows only explicitly configured hosts and aborts requests to other hosts. Its default limiter permits at most two navigations or application `xhr`/`fetch` requests per second; ordinary static assets are not paced by that limiter.

## Recorded sequence

Times below use India Standard Time when stated. Action counts are from the run records; they are **not** counts of MakeMyTrip HTTP requests.

### 1. First MakeMyTrip page load

At about 01:34 IST, the initial public-page probe launched headed installed Chrome and navigated to the rail landing page. The public page rendered and the search control was present. The probe also recorded blocked hosts, including MakeMyTrip application and asset hosts. A later dependency investigation explicitly identified `ground-auto-suggest.makemytrip.com`, `cdnjs.cloudflare.com`, and `railways.makemytrip.com` as required hosts that had been blocked by the browser allowlist.

That is a confirmed configuration problem for the early search attempts: allowing the main page alone did not allow all of the page’s required services. The later probe added the observed hosts. The first page-load record also lists other blocked hosts, but it does not establish that every one of those was needed for booking; some may be analytics or advertising.

Evidence: [MakeMyTrip page probe](../test/20261024T200422766861Z-live-makemytrip-page/result.json), [search/dependency diagnosis](../test/20261024T203131930068Z-live-search-diagnostics/result.json).

### 2. First autonomous public-search run

Run `81a3919d-fd3e-4da1-8c3a-6463963f8ba0` ran from about 01:39 to 01:41 IST. It recorded 23 tool actions and 23 model decisions. The trace shows this sequence at a high level:

1. Read system information and navigate to the rail page.
2. Try several DOM-reference clicks. The first timed out after 10 seconds while clicking a header link; the next four returned `Invalid element reference`.
3. Use one coordinate click at `(1108, 127)`, then another reference click and take a screenshot.
4. Fill a public search field, issue a 3-pixel scroll, click, fill another field and take more screenshots.
5. Try another click, request an unsupported `browser_triple_click` tool, then try another click that timed out on a read-only station input.
6. Fill a field again, take another screenshot, and stop the run for diagnosis.

The tracked action breakdown is: 10 `browser_click`, 1 `browser_click_at`, 5 screenshots, 3 text fills, 1 scroll, 1 navigation, 1 system-info read, and 1 unsupported triple-click request. Failed tool calls are included in those counts.

The input actions omitted `sequential=true`, so the text entries used `locator.fill()`. In the first run, typing also used the default private mode, which masked public autocomplete text from the agent’s observation. The trace shows tool-call errors, not a MakeMyTrip HTTP rejection.

### 3. Second autonomous public-search run

Run `88b260c4-e029-44a6-96d1-622c0e76d880` ran from about 01:43 to 01:45 IST. It recorded 22 tool actions and 21 model decisions. The trace shows:

1. Navigate to the rail page and take a screenshot.
2. Make four clicks with invalid element references.
3. Use a coordinate click at `(1108, 128)`, click a field and fill a public search value with `private=false`.
4. Scroll 3 pixels. Try `ctrl+a`, which failed because Playwright rejected the key name `ctrl`.
5. Click and fill again, take a screenshot, and try unsupported `browser_triple_click`.
6. Use another field fill and screenshot; later `Control+a` succeeded, followed by a short fill and another click.

Its tracked action breakdown is: 8 `browser_click`, 1 `browser_click_at`, 4 screenshots, 4 text fills, 1 scroll, 2 keypresses, 1 navigation, and 1 unsupported triple-click request. Failed tool calls are included in those counts.

This run improved visibility of public search text, but it still relied on `fill()` rather than per-key typing. The invalid references, unsupported triple-click tool, and invalid key name were agent/tool-contract errors. Both autonomous runs were stopped for diagnosis after repetitive work; they did not reach login.

The two run summaries together record **45 tool actions and 44 model decisions**. The project evidence does not support a claim that these were 45 or 50 HTTP requests to MakeMyTrip. They are browser/tool and model-decision counts.

### 4. Separate public-page diagnostic

After stopping those autonomous attempts, a separate diagnostic helper called the same `BrowserTools` methods directly. It selected public origin, destination and date fields and observed 28 cached train results. A candidate fare was shown, but the record explicitly marks it cached and says availability needed refreshing.

This was **not** the autonomous agent completing search. It was a separate operator diagnostic used to learn how the live page behaved. The diagnostic record says no credentials, passenger data or direct account APIs were used. The page itself still made its normal browser-mediated resource and application requests; the investigation did not save a complete count of those network requests.

Evidence: [public search diagnosis and cached result](../test/20261024T203131930068Z-live-search-diagnostics/result.json).

### 5. Large page context caused a model request failure

One listing snapshot contained 723 controls and the serialized context was about 179 KB. The following provider request returned HTTP 400. The retained evidence does not include the provider’s exact error body, so oversized or duplicated context is a plausible cause rather than a proven diagnosis.

After browser observations were compacted, a separate real provider request accepted a context with 72 current controls and 51,334 serialized bytes. It proposed a scroll tool, but that proposed action was not executed in that check. This recovered model-request acceptance; it did not complete the browser task.

Evidence: [compacted-context provider check](../test/20261024T203551592842Z-live-context-check/result.json), [browser-context implementation note](../memory/012-browser-context.md).

### 6. Fare and availability clicks did not open booking

Two direct public-page inspections clicked visible listing text:

- The displayed normal fare text was clicked. The browser action returned, but there was no refreshed availability panel or full fare.
- The displayed `Available 895` text was clicked. The browser action returned, but `has_book_now` remained false. The recorded failed-request list was empty.

These were not network errors. The observed click did not trigger the required booking transition. The evidence does not say whether the clicked text was outside the real button hit area, whether another parent control was required, or whether the listing was stale. The correct conclusion is that the panel did not open and current availability was not established.

Evidence: [fare-text click](../test/20261024T204403942218Z-live-fare-card/result.json), [availability-text click](../test/20261024T204505301985Z-live-availability-control/result.json).

### 7. Further scrolling and human handoff

Run `67362ac8-8450-4d92-8853-80c3305eed7d` issued 12 scroll calls, each with an amount of 3 or 5 pixels, and repeated a skill load. The page therefore barely moved. That run was cancelled; it did not discover a booking action.

A later run reached a human handoff for provider sign-in. Its recorded `ask_human` action timed out, so that run could not continue from the earlier request. Another short run failed after one tool action. These are execution/control-flow failures, not proof that MakeMyTrip rejected a login.

Evidence: [handoff attempt summary](../test/20261024T204829226391Z-live-handoff/result.json), [pixel-scroll implementation](../memory/012-browser-context.md).

### 8. Final MakeMyTrip login attempt

The login-only run used the visible Chrome session and a locally stored named secret. Its retained summary records 14 tool actions, one secret insertion and two successful clicks:

1. Navigate to the MakeMyTrip login page.
2. Take two snapshots, then click the mobile-number field once.
3. Insert the stored number once through the `secret` tool. The logged arguments include only the secret’s name and element reference; the actual number is excluded.
4. Take a snapshot and click `CONTINUE` once. Both browser actions returned success.
5. Take seven more snapshots. No further browser action was issued, and the run ended blocked.

The secret action omitted the optional `sequential` argument. Since the default is false, it used `locator.fill()` rather than key-by-key entry. The browser tool’s successful click result confirms that Playwright performed a click; it does **not** confirm that MakeMyTrip accepted an OTP request. The page did not show a verified OTP-entry screen, no OTP was entered, and delivery of an SMS was not confirmed. The agent’s repeated snapshots without a new action were wasted work after the page stopped changing.

Evidence: [redacted login-attempt summary](../test/20261024T222005295290Z-live-login-attempt/result.json), [private-input implementation and limits](../memory/013-private-login-entry.md).

## Which failures are established

| Step | What failed | Evidence-based conclusion |
| --- | --- | --- |
| Early page/search access | Required dependency hosts were blocked by the explicit browser allowlist. | Confirmed configuration blocker for early search interactions; the main public page could still render. |
| Search controls | Invalid element refs, a locator timeout, a click on a read-only field, unsupported `browser_triple_click`, and an invalid `ctrl` key name. | Confirmed agent/tool-use errors. They wasted attempts before login. |
| Scrolling | Values `3` and `5` were interpreted as pixels. | Confirmed ineffective scrolls due to wrong scale. |
| Model request | A request after a 723-control, roughly 179 KB observation returned HTTP 400. | Confirmed request failure; context size is a plausible cause, but the exact provider error is unknown. |
| Booking panel | Price and availability text clicks returned without a booking panel or `Book now` state. | Confirmed lack of UI transition, not an HTTP error. |
| Login | A field fill and one Continue click returned successfully, followed by repeated snapshots of the same login stage. | Confirmed no OTP screen was established. The cause and SMS delivery remain unknown. |

## About the “50 requests” count

The two recorded autonomous MakeMyTrip search runs contain 45 browser/tool actions and 44 model-decision events combined. There were additional diagnostic and follow-up runs, but the records do not contain a complete count of outbound website HTTP requests. The browser itself loaded page assets and sent the site’s normal application requests, paced by the project’s browser guard. The logs do not show the agent manually calling MakeMyTrip booking endpoints with `curl` or a direct HTTP client.

The earlier 66-action / 39-shell-call count belongs to the initial IRCTC/localhost permission investigation; it is not a count of MakeMyTrip requests. These separate counts should not be described as 50 MakeMyTrip API calls.

## What would meet a strict human-input requirement

Before claiming that this harness controls the site the way a person does, the live flow should use and record visible screenshots, screen-coordinate mouse actions, and actual keyboard events for text entry. In particular:

1. Use the headed Chrome window and make decisions from a fresh screenshot after each major screen change.
2. Use a visible coordinate click for custom controls when DOM references do not identify the clickable surface; verify the page changed afterward.
3. For public autocomplete and private login fields, use per-key entry (`sequential=true`) or an explicitly implemented desktop keyboard action. The final login did not do this.
4. After Continue, require visible evidence of the OTP form before treating the request as accepted or asking for a code.
5. On a no-change result, take at most one fresh observation, try one justified alternate target, then stop and report the exact state. Do not send repeated snapshots as if they advance the flow.
6. Keep the host allowlist explicit, but distinguish observed application dependencies from analytics hosts. Confirm the browser’s required requests are no longer blocked before judging a UI action.

These are next-run criteria, not claims that the live login, payment or ticket has since succeeded. No credential, OTP, passenger identity or secret value is included in this report.

## Evidence index

- [Public MakeMyTrip page load](../test/20261024T200422766861Z-live-makemytrip-page/result.json)
- [Two search runs, dependency diagnosis and cached results](../test/20261024T203131930068Z-live-search-diagnostics/result.json)
- [Reduced-context provider check](../test/20261024T203551592842Z-live-context-check/result.json)
- [Fare click result](../test/20261024T204403942218Z-live-fare-card/result.json)
- [Availability click result](../test/20261024T204505301985Z-live-availability-control/result.json)
- [Provider sign-in handoff result](../test/20261024T204829226391Z-live-handoff/result.json)
- [Final redacted login summary](../test/20261024T222005295290Z-live-login-attempt/result.json)
- [Browser-control implementation](../harness/tools/browser.py)
- [Secret insertion implementation](../harness/tools/secrets.py)
- [Documentation link and whitespace check](../test/20261024T223837Z-browser-methodology-docs/result.json)
