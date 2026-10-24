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
