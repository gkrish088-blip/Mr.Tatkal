---
name: irctc-search-train
description: Find confirmed options for the requested route, date and GENERAL or TATKAL quota
when_to_use: Normal reserved or explicitly requested Tatkal search
requires: [irctc-rank-fares]
gates: []
version: 0.2.0
---
# Goal
Compare actual train options matching the requested journey.

## Preconditions
Supplied origin, destination and date or approved flexible date range. GENERAL for normal reserved booking; TATKAL only on explicit request. RK to HW means Roorkee to Haridwar, not a default for unrelated journeys.

## Procedure
1. Set supplied stations/date/quota through visible controls, selecting actual autocomplete suggestions. Use browser_type(private=false) for these public search values, so matching suggestions stay visible; passenger/credential fields remain private. Ask for missing inputs.
   Verify: Selected station names/codes, date and quota match on results.
2. Inspect displayed availability/full fares for eligible trains/classes. Include mandatory charges; skip WL/RAC unless authorized.
   Verify: Train/class/date, confirmed availability and total observed.
3. Rank by total payable fare, then earliest departure on ties; respect class constraints. GENERAL proceeds to review now; only TATKAL uses its configured opening time.
   Verify: Cheapest among actual checked options; no unobserved fare/availability claims.

## Failure modes and recovery
Stop on configuration denial or missing inputs. No refresh loop or shell workaround. Check at most seven dates only with authorized date flexibility; report search scope.

## Definition of done
Observed route/date/quota, confirmed availability and total match the journey.

## Field notes
Live fare semantics/landmarks need watching-human verification; simulator totals are not real fares.
