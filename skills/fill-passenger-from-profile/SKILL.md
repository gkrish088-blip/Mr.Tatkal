---
name: fill-passenger-from-profile
description: Fill passenger details from a local profile
when_to_use: Fill passenger details from a local profile
requires: []
gates: []
version: 0.1.0
---

# Goal

Fill passenger details from a local profile.

## Preconditions

Profile validated before opening time; private values never included in prompts or screenshots.

## Procedure

1. Read locally validated fields and fill the corresponding labeled controls.
   Verify: Confirm the observed page or tool result matches this step before continuing.
2. Choose berth and payment preferences from the profile.
   Verify: Confirm the observed page or tool result matches this step before continuing.
3. Read back nonsecret review values and compare exactly to the profile.
   Verify: Confirm the observed page or tool result matches this step before continuing.

## Screen landmarks

Use visible labels, accessible names, headings and current DOM references; re-observe after navigation. Live landmarks remain unverified pending reconnaissance.

## Failure modes and recovery

Retry transient failures with bounded backoff; re-observe after state changes. Stop on review mismatch, uncertain payment, repeated access denial or missing inputs. Use an own-channel handoff for unresolved ambiguity.

## Definition of done

Passenger values match the local profile; mismatch blocks payment.

## Field notes

- Initial procedural draft. Local mock checks do not establish real-site reliability.
