---
name: handoff-etiquette
description: Ask a person a precise resumable question
when_to_use: Ask a person a precise resumable question
requires: []
gates: []
version: 0.1.0
---

# Goal

Ask a person a precise resumable question.

## Preconditions

Ambiguous choice or approval gate encountered.

## Procedure

1. Persist current state and capture a redacted screenshot.
   Verify: Confirm the observed page or tool result matches this step before continuing.
2. Ask through ask_human with concise context, options, timeout and explicit consequence.
   Verify: Confirm the observed page or tool result matches this step before continuing.
3. Resume only on a matching reply; timeout stops dependent actions.
   Verify: Confirm the observed page or tool result matches this step before continuing.

## Screen landmarks

Use visible labels, accessible names, headings and current DOM references; re-observe after navigation. Live landmarks remain unverified pending reconnaissance.

## Failure modes and recovery

Retry transient failures with bounded backoff; re-observe after state changes. Stop on review mismatch, uncertain payment, repeated access denial or missing inputs. Use an own-channel handoff for unresolved ambiguity.

## Definition of done

One correlated reply applied once or a recorded timeout.

## Field notes

- Initial procedural draft. Local mock checks do not establish real-site reliability.
