---
name: irctc-search-train
description: Find next-day Tatkal options for RK to HW
when_to_use: Find next-day Tatkal options for RK to HW
requires:
- irctc-rank-fares
gates: []
version: 0.1.0
---

# Goal

Find next-day Tatkal options for RK to HW.

## Preconditions

Account signed in; confirmed journey date is provided.

## Procedure

1. Set origin RK, destination HW, journey date from inputs, and Tatkal quota.
   Verify: Confirm the observed page or tool result matches this step before continuing.
2. Read all train/class options with total displayed fares and availability.
   Verify: Confirm the observed page or tool result matches this step before continuing.
3. Use irctc-rank-fares and wait for the configured opening time before booking.
   Verify: Confirm the observed page or tool result matches this step before continuing.

## Screen landmarks

Use visible labels, accessible names, headings and current DOM references; re-observe after navigation. Live landmarks remain unverified pending reconnaissance.

## Failure modes and recovery

Retry transient failures with bounded backoff; re-observe after state changes. Stop on review mismatch, uncertain payment, repeated access denial or missing inputs. Use an own-channel handoff for unresolved ambiguity.

## Definition of done

Route, date and quota match inputs on results page.

## Field notes

- Initial procedural draft. Local mock checks do not establish real-site reliability.
