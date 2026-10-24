# Real-site reconnaissance: public pages observed; login/booking unverified

Completed booking tests use a fictional localhost simulator.
No real login, captcha, fare, account, availability, opening time, payment,
OTP requirement or Aadhaar behavior has been verified. Live skills are procedural
drafts and require a watching operator to conduct the R1–R4 checks in the supplied
plan. They must not be represented as booking-ready evidence.

Record date, operator, page landmarks, observed fare semantics, eligible classes,
session expiry, required verification, and the review-page dry-run timing here.
Use the team's own account and hotspot; stop rehearsals before payment. Organizer
clarifications about cheapest fare, two windows and freeze coverage remain open.

## Watching-human session on 2026-10-25 IST

The owner explicitly requested live login and a normal GENERAL-quota booking, later selected MakeMyTrip as an alternative, and confirmed they were watching. Their real credentials/passenger details are not recorded in this document or tracked evidence.

- The earlier run failed browser navigation because the host allowlist was localhost-only, then made repeated shell calls. The generic runtime now stops permission failures immediately, including in macros.
- One public-page probe in bundled Chromium and one in installed Chrome both returned the service edge error before a login form. No credentials were submitted. Reports: `test/20261024T195920781471Z-live-public-page/` and `test/20261024T200038929102Z-live-chrome-page/`. The owner independently reported the same error.
- The owner next requested BookMyTrain. Its public page failed to load (`test/20261024T200240763580Z-live-alternative-page/`), then the owner selected MakeMyTrip.
- MakeMyTrip's public search page loaded in ordinary installed Chrome with a provider-login dialog. Its API host `mapi.makemytrip.com` needed explicit browser configuration. Report: `test/20261024T200422766861Z-live-makemytrip-page/`. A console encoding error in the probe's diagnostic printing was corrected in the report; it was not a site navigation failure.
- A bounded real-model search exposed overly broad masking: public station queries were treated as secrets, hiding autocomplete suggestions. The run was stopped before any credentials or payment. Public typing is now explicitly supported while keeping private entry as default and forcing password masking.

Normal-ticket instructions now use supplied route/date and GENERAL quota rather than a Tatkal opening-time wait. Local GENERAL and TATKAL browser flows verify review, one fictional payment approval, a deliberately nonpayable service image and the actual simulator confirmation printed to PDF. None of those checks is a live-service booking pass.

The public MakeMyTrip listing was reached through actual station selection and returned 28 cached results. More required hosts were observed (`cdnjs.cloudflare.com` for listing assets and `railways.makemytrip.com` for application requests) and explicitly added to the ignored local configuration. The cached normal 2S lead on train #12054 was INR 75 base, 13:04 RK to 13:50 HW on 2026-10-26; mandatory fees/current availability are not verified. Clicking its price/availability text did not establish a refreshed booking panel, so this is not a completed ticket search/booking proof.

A real-model listing request failed HTTP 400 after a 723-control observation was duplicated in history/results. Viewport-only controls and compact history reduced a replayed public context to 51 KB / 72 controls; one real provider request accepted it (`test/20261024T203551592842Z-live-context-check/`). A later live model turn identified the candidate in three actions but ended with text announcing another action, so its completed turn status is not accepted as booking success. Browser scroll units are now explicitly pixels, with panel targeting and current viewport text to avoid tiny 3-5 pixel scroll loops.

The live GUI session `366f99e3-0799-4747-a26a-a775d1cf3253` then opened a visible provider-login page and persisted an actual operator handoff. The owner must complete their own MakeMyTrip phone/OTP login directly in the website and reply through the control room. No railway password was transferred to ordinary provider login. At this recorded stage there is no verified live login, payable payment QR, real payment or ticket.
