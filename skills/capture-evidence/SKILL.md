---
name: capture-evidence
description: Save ticket proof and the replay
when_to_use: Save ticket proof and the replay
requires: []
gates: []
version: 0.1.0
---

# Goal

Save ticket proof and the replay.

## Preconditions

Confirmed booking success page visible.

## Procedure

1. Capture the PNR ticket screenshot and download the e-ticket into the configured evidence directory.
   Verify: Confirm the observed page or tool result matches this step before continuing.
2. Generate replay and summary, preserving every reason and verification.
   Verify: Confirm the observed page or tool result matches this step before continuing.
3. Check run log, ticket proof, both recordings, frozen skills and manifest are present.
   Verify: Confirm the observed page or tool result matches this step before continuing.

## Screen landmarks

Use visible labels, accessible names, headings and current DOM references; re-observe after navigation. Live landmarks remain unverified pending reconnaissance.

## Failure modes and recovery

Retry transient failures with bounded backoff; re-observe after state changes. Stop on review mismatch, uncertain payment, repeated access denial or missing inputs. Use an own-channel handoff for unresolved ambiguity.

## Definition of done

Evidence files exist and replay opens; never claim missing recordings exist.

## Field notes

- Initial procedural draft. Local mock checks do not establish real-site reliability.
