---
name: save-proof-screenshot
description: Save a redacted proof screenshot
when_to_use: Save a redacted proof screenshot
requires: []
gates: []
version: 0.1.0
---

# Goal

Save a redacted proof screenshot.

## Preconditions

Verified result is visible.

## Procedure

1. Mask sensitive inputs and private payment fields.
   Verify: Confirm the observed page or tool result matches this step before continuing.
2. Capture a screenshot in the configured run directory.
   Verify: Confirm the observed page or tool result matches this step before continuing.
3. Verify the artifact exists and add it to replay with a reason.
   Verify: Confirm the observed page or tool result matches this step before continuing.

## Screen landmarks

Use visible labels, accessible names, headings and current DOM references; re-observe after navigation. Live landmarks remain unverified pending reconnaissance.

## Failure modes and recovery

Retry transient failures with bounded backoff; re-observe after state changes. Stop on review mismatch, uncertain payment, repeated access denial or missing inputs. Use an own-channel handoff for unresolved ambiguity.

## Definition of done

Nonempty screenshot referenced by a logged verification.

## Field notes

- Initial procedural draft. Local mock checks do not establish real-site reliability.
