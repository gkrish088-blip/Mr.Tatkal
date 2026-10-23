---
name: pay-handoff
description: Request external human payment approval
when_to_use: Request external human payment approval
requires: []
gates:
- external_approval
version: 0.1.0
---

# Goal

Request external human payment approval.

## Preconditions

Review fields and total fare verified exactly; no earlier successful booking.

## Procedure

1. Submit the selected payment request once; persist its reference before waiting.
   Verify: Confirm the observed page or tool result matches this step before continuing.
2. Call ask_human with kind external_approval and the displayed amount; ask the owner to approve in their payment app.
   Verify: Confirm the observed page or tool result matches this step before continuing.
3. Observe the success page. On ambiguity or timeout, check booking status before any retry; never submit a second charge blindly.
   Verify: Confirm the observed page or tool result matches this step before continuing.

## Screen landmarks

Use visible labels, accessible names, headings and current DOM references; re-observe after navigation. Live landmarks remain unverified pending reconnaissance.

## Failure modes and recovery

Retry transient failures with bounded backoff; re-observe after state changes. Stop on review mismatch, uncertain payment, repeated access denial or missing inputs. Use an own-channel handoff for unresolved ambiguity.

## Definition of done

Confirmed success and exactly one external approval, or clean timeout without duplicate payment.

## Field notes

- Initial procedural draft. Local mock checks do not establish real-site reliability.
