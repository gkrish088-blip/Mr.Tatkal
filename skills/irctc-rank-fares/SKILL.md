---
name: irctc-rank-fares
description: Rank confirmed seats by total fare then departure
when_to_use: Rank confirmed seats by total fare then departure
requires: []
gates: []
version: 0.1.0
---

# Goal

Rank confirmed seats by total fare then departure.

## Preconditions

All candidate train/class fares have been observed.

## Procedure

1. Exclude waitlisted, RAC, REGRET and unavailable candidates.
   Verify: Confirm the observed page or tool result matches this step before continuing.
2. Sort remaining options by total fare including Tatkal charges, then earliest departure.
   Verify: Confirm the observed page or tool result matches this step before continuing.
3. Save the candidates and observed fare evidence; choose the first available candidate.
   Verify: Confirm the observed page or tool result matches this step before continuing.

## Screen landmarks

Use visible labels, accessible names, headings and current DOM references; re-observe after navigation. Live landmarks remain unverified pending reconnaissance.

## Failure modes and recovery

Retry transient failures with bounded backoff; re-observe after state changes. Stop on review mismatch, uncertain payment, repeated access denial or missing inputs. Use an own-channel handoff for unresolved ambiguity.

## Definition of done

Chosen fare is minimum among confirmed candidates; ties use earliest departure.

## Field notes

- Initial procedural draft. Local mock checks do not establish real-site reliability.
