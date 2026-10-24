---
name: irctc-book-ticket
description: Book one normal GENERAL-quota reserved ticket with reviewed fare, human payment and ticket delivery
when_to_use: Normal or non-Tatkal booking on the official railway site
requires: [irctc-login, irctc-search-train, fill-passenger-from-profile, pay-handoff, capture-evidence]
gates: []
version: 0.1.0
---
# Goal
Book one correct normal reserved ticket and deliver its actual document.

## Preconditions
Watching owner, authorized route/date or flexible date range, one passenger profile in ignored local storage, fare preference and configured browser. GENERAL is normal reserved quota, not an unreserved/UTS ticket. Ask for missing information; never invent passenger data.

## Procedure
1. Load irctc-login and verify authentication. A blocked service is a blocker. Switch providers only when the owner selects one, then use rail-book-ticket.
   Verify: Actual signed-in landmark; no simulator substituted.
2. Load irctc-search-train with requested route/date and GENERAL. Normal booking has no Tatkal opening-time wait. For flexible dates start on the next future day, inspect at most seven dates, and stop on an acceptable cheapest available option.
   Verify: Actual station selections, date and GENERAL quota match.
3. Compare displayed confirmed train/class options by total including mandatory charges. Skip WL/RAC unless authorized. Remove optional insurance/guarantees unless requested. State the scope compared rather than claiming a global minimum.
   Verify: Selected confirmed option is cheapest among those checked.
4. Load fill-passenger-from-profile. Verify passenger/contact, boarding point, route, date, train, class, quota and final total. Show nonprivate journey details and exact total with ask_human(kind=approve) before creating payment.
   Verify: Owner approves actual journey/total; denial or mismatch stops.
5. Load pay-handoff. Show the service's actual payment image when offered, then pause for owner payment. Never invent a QR or retry an unresolved payment.
   Verify: One transaction reference followed by actual service confirmation/PNR.
6. Load capture-evidence. Download the actual ticket or print the service's actual confirmed ticket page to PDF. Return its private session download link.
   Verify: Document exists and matches the booking; a receipt alone is not a ticket.

## Failure modes and recovery
Missing inputs, access denial, no seats or review mismatch stop before payment. Reconcile transaction/booked-ticket history before retrying uncertain payment. Local checks do not establish live readiness.

## Definition of done
Exactly one service-confirmed ticket paid by the owner and its actual downloadable document; otherwise report the last verified stage and blocker.
