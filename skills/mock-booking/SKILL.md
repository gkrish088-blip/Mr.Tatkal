---
name: mock-booking
description: Rehearse a fictional booking on localhost
when_to_use: Rehearse a fictional booking on localhost
requires: []
gates: []
version: 0.1.0
---

# Goal

Rehearse a fictional booking on localhost.

## Preconditions

Local Rail Lab running; fictional profile only. Not a live-service skill.

## Procedure

1. Open the localhost rail lab; log in as demo/demo with visible TRAIN challenge.
   Verify: Confirm the observed page or tool result matches this step before continuing.
2. Search RK to HW for the input date using TATKAL quota.
   Verify: Confirm the observed page or tool result matches this step before continuing.
3. Compare all results: exclude WL/RAC/REGRET, sort total fare then departure. Select Morning local, 2S, Rs 65 at 07:15.
   Verify: Confirm the observed page or tool result matches this step before continuing.
4. Fill the fictional input profile, continue to review and verify every field.
   Verify: Confirm the observed page or tool result matches this step before continuing.
5. Request the fictional payment once and use external_approval handoff.
   Verify: Confirm the observed page or tool result matches this step before continuing.
6. Wait for an external test driver to approve /api/test/approve/{reservation_id}; check payment status and capture PNR proof.
   Verify: Confirm the observed page or tool result matches this step before continuing.

## Screen landmarks

Use visible labels, accessible names, headings and current DOM references; re-observe after navigation. Live landmarks remain unverified pending reconnaissance.

## Failure modes and recovery

Retry transient failures with bounded backoff; re-observe after state changes. Stop on review mismatch, uncertain payment, repeated access denial or missing inputs. Use an own-channel handoff for unresolved ambiguity.

## Definition of done

One MOCK ticket, exact profile, cheapest confirmed fare, one external approval.

## Field notes

- Initial procedural draft. Local mock checks do not establish real-site reliability.
