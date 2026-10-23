---
name: community-research
description: Read a local public fact and save a note
when_to_use: Read a local public fact and save a note
requires: []
gates: []
version: 0.1.0
---

# Goal

Read a local public fact and save a note.

## Preconditions

Local generality fixture running; destination note path supplied.

## Procedure

1. Navigate to the community desk fixture.
   Verify: Confirm the observed page or tool result matches this step before continuing.
2. Read the library opening fact from the page.
   Verify: Confirm the observed page or tool result matches this step before continuing.
3. Write the opening fact to the supplied sandbox note and read it back.
   Verify: Confirm the observed page or tool result matches this step before continuing.

## Screen landmarks

Use visible labels, accessible names, headings and current DOM references; re-observe after navigation. Live landmarks remain unverified pending reconnaissance.

## Failure modes and recovery

Retry transient failures with bounded backoff; re-observe after state changes. Stop on review mismatch, uncertain payment, repeated access denial or missing inputs. Use an own-channel handoff for unresolved ambiguity.

## Definition of done

Saved note states that the library opens Tuesday at 09:30.

## Field notes

- Initial procedural draft. Local mock checks do not establish real-site reliability.
