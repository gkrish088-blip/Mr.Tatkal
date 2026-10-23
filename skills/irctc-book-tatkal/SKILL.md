---
name: irctc-book-tatkal
description: Execute and verify the one-booking workflow
when_to_use: Execute and verify the one-booking workflow
requires:
- irctc-login
- irctc-search-train
- fill-passenger-from-profile
- pay-handoff
- capture-evidence
gates: []
version: 0.1.0
---

# Goal

Execute and verify the one-booking workflow.

## Preconditions

Watching operator, complete profile, configured opening time, own account, rehearsal completed.

## Procedure

1. Run irctc-login then irctc-search-train.
   Verify: Confirm the observed page or tool result matches this step before continuing.
2. Wait until the configured opening time; use at most two requests per second.
   Verify: Confirm the observed page or tool result matches this step before continuing.
3. Select the cheapest confirmed candidate; run fill-passenger-from-profile.
   Verify: Confirm the observed page or tool result matches this step before continuing.
4. Verify exact route, date, quota, passenger, class, train and total fare on review. Stop on mismatch.
   Verify: Confirm the observed page or tool result matches this step before continuing.
5. Run pay-handoff exactly once, then capture-evidence after confirmed success.
   Verify: Confirm the observed page or tool result matches this step before continuing.

## Screen landmarks

Use visible labels, accessible names, headings and current DOM references; re-observe after navigation. Live landmarks remain unverified pending reconnaissance.

## Failure modes and recovery

Retry transient failures with bounded backoff; re-observe after state changes. Stop on review mismatch, uncertain payment, repeated access denial or missing inputs. Use an own-channel handoff for unresolved ambiguity.

## Definition of done

Exactly one correct ticket with PNR evidence and one payment handoff.

## Field notes

- Initial procedural draft. Local mock checks do not establish real-site reliability.
