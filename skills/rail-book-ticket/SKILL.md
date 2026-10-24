---
name: rail-book-ticket
description: Book a normal train ticket through the owner-selected provider, including MakeMyTrip
when_to_use: The owner explicitly chooses an alternative railway booking website
requires: [pay-handoff, capture-evidence]
gates: []
version: 0.1.0
---
# Goal
Book one correct ticket through the selected provider's visible flow and deliver its actual document.

## Preconditions
Watching owner, selected provider, route/date or authorized flexible date range, passenger profile in ignored storage and fare preference. Browser hosts must include provider dependencies. Provider and railway accounts can differ. Never transfer a railway password to another site's ordinary login automatically.

## Procedure
1. Check system_info once and open the selected provider. For MakeMyTrip use https://www.makemytrip.com/railways/. Dismiss optional sign-in/advertising dialogs to search when allowed. Use current DOM references or browser_click_at for visible custom controls identified in the latest screenshot. Never bypass denied hosts through shell networking.
   Verify: Real search form, not an error page. Missing API/asset hosts need configuration.
2. Search authorized origin/destination, GENERAL quota and one person. Use browser_type(private=false) for public station searches and dates, then select the actual suggestion; keeping search words private hides the matching suggestion. Use private=true for passenger/credential fields. For flexible dates start on the next future day and inspect at most seven dates. Compare displayed confirmed train/class options by total payable fare; remove optional paid add-ons.
   Verify: Actual station suggestions selected, correct date/quota and confirmed seats; record options compared.
   MakeMyTrip may include nearby stations and longer-route alternatives: exclude those unless the owner authorizes them. For RK to HW, do not substitute Laksar or book a longer reservation merely because boarding/getting off is possible. Check filter state before clicking: unchecking General Quota removes the normal fares. Cached availability (including a timestamp of hours/days ago) is not current availability; refresh the actual chosen normal class before trusting it.
   If autocomplete does not update after fill, retry once with browser_type(private=false, sequential=true) to send real key events, then wait for the suggestion. Inspect observation.network.blocked_hosts and failed_requests to distinguish configuration denial from service errors. Report the missing provider dependency or HTTP status instead of repeating the search. Only observed e... refs, label: and text: references work with browser_click; use browser_click_at for a visible control without an accessible reference.
3. Choose the cheapest eligible option and fill the local profile. If provider login/OTP is required, ask the owner to complete it directly in the headed browser and reply done. Do not assume passenger contact is the provider account login. Insert named railway secrets only at an explicitly identified railway-authentication step authorized by the owner.
   Verify: Correct passenger/journey in review; provider login alone is not railway authentication or booking.
4. Show train/date/class/GENERAL and total including provider fees through ask_human(kind=approve). After approval load pay-handoff and attach the actual provider/gateway payment image. Disclose missing QR; never manufacture one or use a ticket QR as payment.
   Verify: One authorized payment request with amount and transaction reference.
5. Wait for owner payment, then inspect actual confirmation/PNR. A redirect to an unavailable railway service is a blocker. Reconcile pending payment through history before another attempt.
   Verify: Service confirms payment and ticket; owner reply alone is insufficient.
6. Load capture-evidence. Download the service ticket or browser_print_pdf on its actual confirmed ticket/print page. Return the private session download link. No external email/SMS/Telegram messages unless requested.
   Verify: Actual PDF exists under steps/downloads and agrees with booking.

## Failure modes and recovery
At most two owner-authorized login submissions. Stop on unexplained rejection, configuration denial, service error, review mismatch or uncertain payment. Hand off once for CAPTCHA/OTP; never guess. Keep secrets/passenger data out of notes and tracked evidence.

## Definition of done
One real confirmed ticket and actual document, or a precise last-verified-stage/blocker report. Simulator results are not live-provider passes.

## Field notes
Watching-human public diagnostics on 2026-10-25 IST verified the normal station autocomplete flow: type a public query, wait for its matching suggestion, select the full station name, and proceed through the auto-opening destination/date/class controls. Required observed hosts included ground-auto-suggest.makemytrip.com (station suggestions), cdnjs.cloudflare.com (listing assets) and railways.makemytrip.com (railway requests); configure exact needed hosts locally rather than allowing every host. The resulting RK-HW listing URL was observed through the normal UI and can be reused for that journey with its actual date; never invent a booking/payment endpoint. Public listing access and cached fare leads do not prove login, live availability or booking.
