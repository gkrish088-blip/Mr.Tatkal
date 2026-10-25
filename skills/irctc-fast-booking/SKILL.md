---
name: irctc-fast-booking
description: Fastest end-to-end IRCTC booking for one passenger, Roorkee to Haridwar by default, with human CAPTCHA/OTP and payment handoffs
when_to_use: Owner asks to book the cheapest Tatkal (or, before the window, cheapest regular) ticket quickly on the official IRCTC site
requires: [irctc-login, irctc-search-train, fill-passenger-from-profile, pay-handoff, capture-evidence]
gates: []
version: 0.1.0
---
# Goal
Book exactly one cheapest ticket as fast as possible, with the owner doing only CAPTCHA, OTP and the final payment.

## Preconditions
Watching owner. Secrets IRCTC_USERNAME and IRCTC_PASSWORD in the keychain (never in files or model text). Passenger in ignored profile/passenger.yaml. Browser allows www.irctc.co.in. Do not use a VPN.

## Procedure
1. Check the clock. Tatkal opens the day before travel at 10:00 (AC) and 11:00 (Sleeper/non-AC). If it is open, book Tatkal; otherwise GENERAL quota.
   Verify: Quota choice stated with the observed time.
2. Open https://www.irctc.co.in/nget/train-search once. Dismiss the language/beta banners (click English, close the banner). Do this BEFORE the window to save seconds.
   Verify: Search form visible.
3. Log in ahead of time: click Login, insert username and password through secret(name, ref). Hand off with ask_human so the owner solves the CAPTCHA and OTP in the visible browser.
   Verify: Logout/My Account landmark. Never submit more than twice.
4. Search RK (Roorkee) to HW (Haridwar), travel date, quota. Pick the cheapest available class/train from the listed fares; skip WL/RAC. Click the class card, confirm availability, then Book Now.
   Verify: Route, date, class and fare match.
5. Fill passenger from profile: name, age, gender, nationality, berth preference. Fill remaining required fields with defaults; turn off auto-upgrade and insurance. Use the profile, never invent identity data.
   Verify: Review page matches the profile.
6. Show the exact fare with ask_human(kind=approve). Continue to payment only on approval.
   Verify: Owner approved the real total.
7. Reach the payment page and hand off to the owner. Never enter payment details or pay.
   Verify: Owner reports payment done.
8. Capture the confirmed ticket page and PNR as proof; save run log and screenshots.
   Verify: PNR visible on the service's confirmation page.

## Speed tips
Pre-login before the window; keep the profile ready; reuse the persistent browser profile; click by screenshot coordinates when DOM refs time out; retry a failed click once, then re-observe.

## Failure modes and recovery
Edge/access error: stop and report, ask the owner to disconnect any VPN. Invalid element refs: re-snapshot. Timeouts after 11:00: wait briefly and retry once, never loop. Uncertain payment: check booked-ticket history before retrying.

## Definition of done
Service-confirmed ticket with PNR paid by the owner, plus saved proof; otherwise report the last verified stage and blocker.
