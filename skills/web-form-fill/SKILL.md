---
name: web-form-fill
description: Complete a labeled web form
when_to_use: Complete a labeled web form
requires: []
gates: []
version: 0.1.0
---

# Goal

Complete a labeled web form.

## Preconditions

Field values and success criterion supplied in run inputs.

## Procedure

1. Observe form labels and required fields.
   Verify: Confirm the observed page or tool result matches this step before continuing.
2. Fill controls using input values and submit once.
   Verify: Confirm the observed page or tool result matches this step before continuing.
3. Verify the success landmark and saved values.
   Verify: Confirm the observed page or tool result matches this step before continuing.

## Screen landmarks

Use visible labels, accessible names, headings and current DOM references; re-observe after navigation. Live landmarks remain unverified pending reconnaissance.

## Failure modes and recovery

Retry transient failures with bounded backoff; re-observe after state changes. Stop on review mismatch, uncertain payment, repeated access denial or missing inputs. Use an own-channel handoff for unresolved ambiguity.

## Definition of done

Requested values saved and success landmark visible.

## Field notes

- Initial procedural draft. Local mock checks do not establish real-site reliability.
