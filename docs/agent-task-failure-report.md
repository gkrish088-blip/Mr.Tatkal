# Why the agent did not complete the ticket-booking task

## Scope and outcome

This report covers the recorded attempts on 25 October 2026 IST to book one normal, GENERAL-quota ticket from Roorkee (RK) to Haridwar (HW), first through IRCTC and then through the owner-selected MakeMyTrip alternative.

**The task was not completed.** Public train results were reached, but authenticated login, refreshed availability, the final payable fare, payment and a confirmed ticket were not established. No real payment QR or ticket was produced.

The reasons below distinguish observed failures from suspected causes. They contain no account credentials, phone numbers, OTPs or passenger details.

## Confirmed failures and contributing factors

### 1. The browser initially permitted only localhost

The original configuration allowed local test pages but blocked navigation to the real booking site. The agent therefore could not reach the login form through its browser tools.

The recorded original attempt contained **66 tool actions, including 39 shell calls**, and two denied browser navigations. These are tool-action counts, not a verified count of API requests.

**Change made:** explicit site hosts were configured locally, and permission failures now stop the run with a configuration reason. This prevents a denied browser action from turning into repeated shell workarounds.

Evidence: [permission-denial investigation and checks](../memory/009-permission-denial.md).

### 2. The agent continued ineffective work instead of reporting the blocker

After navigation was denied, the agent tried shell/curl workarounds. In later attempts it repeatedly requested screenshots or snapshots despite already having an observation. The final phone-login attempt stopped after 14 tool actions without reaching an OTP verification screen.

The repetition consumed steps and model requests without completing the next required action. Stopping a loop limits the waste; it does not make the login succeed.

**Status:** permission-denial handling was fixed and tool guidance improved. Reliable execution throughout the live booking flow remains unverified.

Evidence: [original loop investigation](../memory/009-permission-denial.md), [recorded search attempts](../test/20261024T203131930068Z-live-search-diagnostics/result.json), [last phone-login attempt](../test/20261024T222005295290Z-live-login-attempt/result.json).

### 3. IRCTC returned an error before displaying a login form

Both bundled Chromium and installed Chrome received an edge error page stating that an error occurred while processing the request. The owner reported the same result in their usual browser.

**Effect:** the supplied railway credentials could not be tested against an actual login form. This does not establish that the credentials were wrong. The exact cause of the service error was not established.

BookMyTrain also failed to load when requested as an alternative. The owner then selected MakeMyTrip.

Evidence: [Chromium public-page probe](../test/20261024T195920781471Z-live-public-page/result.json), [installed-Chrome probe](../test/20261024T200038929102Z-live-chrome-page/result.json), [BookMyTrain probe](../test/20261024T200240763580Z-live-alternative-page/result.json).

### 4. Required MakeMyTrip dependencies were blocked

Allowing the main website alone was insufficient. Its station suggestions, listing assets and railway requests used additional hosts. Observed blocked dependencies included:

- `ground-auto-suggest.makemytrip.com`
- `cdnjs.cloudflare.com`
- `railways.makemytrip.com`

This let parts of the page appear while required interactions failed. Initially, the agent was not shown a useful explanation of these blocked requests.

**Change made:** observed required hosts were added explicitly to the ignored local configuration. Browser observations now expose blocked hosts and failed request status codes without private URL paths or queries.

A further script host referenced by the provider login page was allowed later. Its effect on login was **not verified**, so it cannot be presented as the proven cause of the OTP failure.

Evidence: [dependency investigation](../test/20261024T203131930068Z-live-search-diagnostics/result.json), [latest login handover](../memory/013-private-login-entry.md).

### 5. Privacy masking hid public station-search terms

The browser treated every typed value as private. After entering a station name, that word was also removed from observed suggestions. This made the agent's own search harder to interpret.

**Change made:** public search fields can use `private=false`; personal and credential entry stays private by default. This was tested locally and used during the public search investigation.

Evidence: [normal-booking implementation notes](../memory/011-normal-booking.md).

### 6. The tool contract and live controls did not match the agent's assumptions

The live pages used custom controls, read-only display fields and autocomplete inputs. Some actions used invalid references or unsupported tool names. A successful text fill or click did not necessarily trigger the expected application transition.

In particular, clicking the observed normal fare's price or availability text did **not** establish a refreshed availability or booking panel. Those clicks must not be counted as successful selection of a bookable ticket.

**Changes made:** clearer reference descriptions, coordinate clicks, read-only markers, additional observed controls, and optional key-event entry. Private named-secret insertion also supports key events. These improvements have local coverage; the complete live interaction sequence remains unverified.

Evidence: [search action records](../test/20261024T203131930068Z-live-search-diagnostics/result.json), [price-text inspection](../test/20261024T204403942218Z-live-fare-card/result.json), [availability-text inspection](../test/20261024T204505301985Z-live-availability-control/result.json), [private-input checks](../memory/013-private-login-entry.md).

### 7. Large, duplicated observations contributed to a failed model request

A live listing produced an observation with **723 controls, approximately 179 KB**. Page data was repeated in history, tool results and before/after observations. The next provider request returned HTTP 400.

Excessive context was a plausible contributor, but the precise provider rejection reason was not established from a retained error body.

**Change made:** current controls are limited to the viewport, with a 200-control cap, and historical observations are compacted. A subsequent real provider request accepted a public context containing 72 controls and 51,334 serialized bytes. That acceptance proves the reduced request worked; it does not prove booking success.

Evidence: [context investigation](../memory/012-browser-context.md), [real provider context check](../test/20261024T203551592842Z-live-context-check/result.json).

### 8. Scroll commands used the wrong scale

The agent issued scroll amounts such as 3 and 5 while the tool interpreted the amount as pixels. The page barely moved, leaving the agent repeatedly looking for the same train. Pointer position also matters on pages with nested scroll panels.

**Change made:** tool descriptions now specify pixel units, scrolling can target a panel, and observations include current viewport text. Real local-browser tests cover nested-panel scrolling.

Evidence: [browser-context and scrolling notes](../memory/012-browser-context.md).

### 9. A completed model turn was mistaken for progress toward task completion

One live turn ended with text saying that the agent needed to click the normal fare card. No further tool call accompanied that statement, and the turn received a completed status.

**Effect:** a completed conversational turn did not mean the requested booking work had been completed. Announcing a next action is not evidence that it happened.

**Status:** this remains a limitation of interpreting the run status. Booking success must be independently established from the service's confirmation and actual ticket/PNR.

Evidence: [live-turn limitations](../test/20261024T204829226391Z-live-handoff/result.json).

### 10. A human handoff expired before the next instruction was relayed

The provider-login handoff expired before the owner's response could be delivered to that request. A fresh login-only session was then started.

**Effect:** the previous waiting run could not continue through its expired request. This was a separate interruption; it does not explain why the website later failed to show an OTP screen.

Evidence: [handoff sequence](../memory/012-browser-context.md).

### 11. The final MakeMyTrip login did not reach OTP verification

The final recorded login attempt inserted the owner's number through named secret storage and clicked Continue **once**. The page remained at the phone-entry form. No OTP verification screen was established and no OTP was entered.

**Unresolved:** whether the website accepted an OTP request, whether an SMS arrived, and why the UI did not advance. A successful browser click alone proves none of these. The owner was asked whether a login OTP arrived; no delivery confirmation is recorded.

The private key-event option and additional script-host configuration were added afterward, but a successful live login using those changes was not demonstrated. Another code must not be requested automatically while delivery remains uncertain.

Evidence: [final login-attempt record](../test/20261024T222005295290Z-live-login-attempt/result.json), [latest implementation limitations](../memory/013-private-login-entry.md).

### 12. The normal-ticket path had no successful live rehearsal

The initial booking instructions were an unverified Tatkal-oriented draft. Normal GENERAL-quota and selected-provider workflows were added during this work, along with image handoff and PDF delivery support.

However, the live flow never established authenticated access, refreshed normal availability and the full payable amount. Passing the local simulator did not supply those missing live checks.

Evidence: [normal-ticket work](../memory/011-normal-booking.md), [live reconnaissance](irctc-recon.md).

## Why no payment QR or ticket was delivered

The run did not reach a verified payment stage. There was no confirmed service payment request from which to obtain an actual payable QR. No payment and confirmed reservation/PNR were established, so there was no real ticket to download.

Image handoff and PDF delivery passed local tests, but they were not exercised successfully against a real booking. Producing an invented QR or a fabricated ticket would not complete the task.

## What was verified

- The public MakeMyTrip search reached 28 cached results after station selection and dependency configuration.
- A cached normal 2S fare lead was observed; current availability and the final payable fare were not established.
- The full local suite passed **218 tests, with 1 skipped**. The subsequent focused private-input checks passed **16 tests, with 1 skipped**. The skip concerned Windows symlink privileges.
- Those local checks cover simulator bookings, browser behavior, image handoffs and document delivery. They are not live login, payment or ticket passes.

Evidence: [full-suite output](../test/20261024T204150145712Z/output.txt), [focused-check output](../test/20261024T221825501606Z/output.txt).

## What the evidence does not establish

- That the railway password was invalid: it was not submitted to an available official login form.
- That the API key was missing or invalid: real model requests succeeded during the investigation.
- That a particular model is inherently unable to do the task, or that changing models alone would solve it.
- The exact cause of the official site's edge error or MakeMyTrip's missing OTP transition.
- That an OTP was delivered or that any real reservation, payment or ticket exists.

## Remaining work before claiming success

1. Resolve the provider login transition and confirm OTP delivery with the watching owner before any resend.
2. Verify an actual authenticated account state.
3. Refresh the selected normal class, confirm the exact route/date and availability, and verify the full payable fare and passenger review.
4. Obtain the owner's approval of that review, create one payment request, and show the actual gateway QR if offered.
5. After the owner pays, independently verify service confirmation and the ticket/PNR, then deliver the actual ticket document.
