---
name: mock-ticket
description: Complete one fictional localhost ticket with exact review verification and one external approval
requires: []
gates: []
version: 0.1.0
---
# Goal
Complete a fictional localhost booking entirely through tools and declarative skill steps.

## Preconditions
Local Rail Lab, fictional profile only. Inputs: url, date, name, age (string), age_number (integer matching age), gender, nationality, mobile. The human channel must be configured. No production channel auto-approves payment.

## Procedure
1. Follow the mock-booking macro to the review checkpoint.
   Verify: Review journey before payment is visible.
2. Verify exact profile, route, date, quota, cheapest confirmed train and total fare using browser_assert_json on the rendered review.
   Verify: matches=true. Stop on mismatch.
3. Submit the fictional request, ask one external_approval handoff, and check status.
   Verify: approval received and Ticket confirmed is visible.
4. Capture a masked PNR screenshot.
   Verify: PNR remains visible in the ticket page and screenshot artifact exists.

## Definition of done
One fictional ticket for the exact profile, cheapest confirmed fare and exactly one external approval. A denied or missing approval stops the macro.

## Field notes
No live service was tested. Test transports approve only isolated localhost fixtures.
