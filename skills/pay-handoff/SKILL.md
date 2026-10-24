---
name: pay-handoff
description: Show the actual service payment image and pause for owner payment after exact fare approval
when_to_use: Verified booking review is ready for human payment
requires: []
gates: [external_approval]
version: 0.2.0
---
# Goal
Owner completes one approved payment; independently verify the service result.

## Preconditions
Journey/passenger/contact and total verified; owner approved actual journey/fare before payment creation. No successful or unresolved earlier payment. Never request banking passwords, CVV, payment PINs or payment OTPs in chat.

## Procedure
1. Open the selected method once and preserve its displayed reference in private state. Check amount, merchant and expiry. Stop on a blocked gateway host; no shell workaround.
   Verify: Exactly one current payment request for the reviewed amount.
2. If the service offers a payment QR, locate its observed image/canvas with browser_snapshot and use browser_capture_element. For a new allowed tab, select it first. Pass its screenshot path in ask_human(kind=external_approval, text=amount/reference/expiry, attachments=[path]). A full page screenshot is also available. Never generate a QR from guessed data, reuse an expired code or substitute an e-ticket QR.
   Verify: Handoff shows the current service image and amount. Embedded-frame capture may require direct browser assistance; disclose hidden/missing codes.
3. Pause for owner scan/payment in their own app and reply done. If no QR is offered, explain and use only an owner-approved available method. Denial/timeout/ambiguity stops without another request.
   Verify: Owner reply prompts a service check; it is not proof of payment.
4. Inspect actual provider confirmation/transaction state and ticket PNR. Reconcile booked-ticket/transaction history before retrying. Report unresolved payment rather than charge again.
   Verify: Service confirms booking/payment, or run clearly reports its unresolved stage.

## Definition of done
One actual confirmed ticket/payment after owner action, or clean stop without duplicate charge. A fictional image is never payable or real-service evidence.
