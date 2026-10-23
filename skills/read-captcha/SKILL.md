---
name: read-captcha
description: Read a visible challenge with vision
when_to_use: Read a visible challenge with vision
requires: []
gates: []
version: 0.1.0
---

# Goal

Read a visible challenge with vision.

## Preconditions

A visible challenge is on screen; use the strongest available vision model.

## Procedure

1. Observe the current challenge image; do not reuse an older answer.
   Verify: Confirm the observed page or tool result matches this step before continuing.
2. Read the challenge and fill the labeled response field.
   Verify: Confirm the observed page or tool result matches this step before continuing.
3. If rejected, refresh and retry at most four times; then hand off.
   Verify: Confirm the observed page or tool result matches this step before continuing.

## Screen landmarks

Use visible labels, accessible names, headings and current DOM references; re-observe after navigation. Live landmarks remain unverified pending reconnaissance.

## Failure modes and recovery

Retry transient failures with bounded backoff; re-observe after state changes. Stop on review mismatch, uncertain payment, repeated access denial or missing inputs. Use an own-channel handoff for unresolved ambiguity.

## Definition of done

The challenge is accepted by the current page.

## Field notes

- Initial procedural draft. Local mock checks do not establish real-site reliability.
