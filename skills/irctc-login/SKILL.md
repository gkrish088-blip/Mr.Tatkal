---
name: irctc-login
description: Sign in using the team account
when_to_use: Sign in using the team account
requires:
- read-captcha
gates: []
version: 0.1.0
---

# Goal

Sign in using the team account.

## Preconditions

Use only a watching operator and the team member?s own preverified account.

## Procedure

1. Open the official website and find the sign-in form by visible labels.
   Verify: Confirm the observed page or tool result matches this step before continuing.
2. Insert username and password from secret storage without exposing them to logs.
   Verify: Confirm the observed page or tool result matches this step before continuing.
3. Use read-captcha; submit and verify a logged-in account landmark.
   Verify: Confirm the observed page or tool result matches this step before continuing.

## Screen landmarks

Use visible labels, accessible names, headings and current DOM references; re-observe after navigation. Live landmarks remain unverified pending reconnaissance.

## Failure modes and recovery

Retry transient failures with bounded backoff; re-observe after state changes. Stop on review mismatch, uncertain payment, repeated access denial or missing inputs. Use an own-channel handoff for unresolved ambiguity.

## Definition of done

Logged-in account landmark is visible.

## Field notes

- Initial procedural draft. Local mock checks do not establish real-site reliability.
