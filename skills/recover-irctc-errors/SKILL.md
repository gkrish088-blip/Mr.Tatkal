---
name: recover-irctc-errors
description: Recover bounded transient booking errors
when_to_use: Recover bounded transient booking errors
requires:
- irctc-login
gates: []
version: 0.1.0
---

# Goal

Recover bounded transient booking errors.

## Preconditions

Known error or unexpected page encountered.

## Procedure

1. For 5xx retry up to five times with backoff; for session expiry rerun login then resume checkpoint.
   Verify: Confirm the observed page or tool result matches this step before continuing.
2. For access denied wait 30 to 60 seconds, retry once, then hand off; never evade blocks.
   Verify: Confirm the observed page or tool result matches this step before continuing.
3. For review mismatch stop payment and repair; for ambiguous payment inspect status before retry.
   Verify: Confirm the observed page or tool result matches this step before continuing.
4. If repeated recovery fails, ask_human with screenshot and persist state.
   Verify: Confirm the observed page or tool result matches this step before continuing.

## Screen landmarks

Use visible labels, accessible names, headings and current DOM references; re-observe after navigation. Live landmarks remain unverified pending reconnaissance.

## Failure modes and recovery

Retry transient failures with bounded backoff; re-observe after state changes. Stop on review mismatch, uncertain payment, repeated access denial or missing inputs. Use an own-channel handoff for unresolved ambiguity.

## Definition of done

Verified checkpoint restored or run safely suspended.

## Field notes

- Initial procedural draft. Local mock checks do not establish real-site reliability.
