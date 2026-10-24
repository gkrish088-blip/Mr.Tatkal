---
name: irctc-login
description: Verify railway login with private credential insertion and bounded retries
when_to_use: The watching owner requests live railway login
requires: [read-captcha]
gates: []
version: 0.2.0
---
# Goal
Verify a signed-in account without wasting requests or exposing credentials.

## Preconditions
Watching account owner and authorized login. Browser must allow official hosts. Credentials must be named environment/keychain secrets, such as IRCTC_USERNAME and IRCTC_PASSWORD. A passenger name is not an account username.

## Procedure
1. Check system_info once. If browser/host access is missing, stop with the configuration needed. Never use shell/curl, scripts, proxies or other accounts to work around restrictions.
   Verify: Browser enabled and www.irctc.co.in allowed.
2. Open https://www.irctc.co.in/nget/train-search once. Inspect the actual form. An edge error or access-denied page means stop before entering credentials.
   Verify: Actual login controls, not merely a successful navigation result.
3. Insert username/password through secret(name, ref) with current references. Never read credentials through shell/file tools or copy values into model text/logs.
   Verify: Both insertions return inserted=true without printing values.
4. Ask the watching owner to complete CAPTCHA/OTP directly in the visible browser and reply done through ask_human. Do not collect secrets in normal text handoffs. Submit once after verification is complete.
   Verify: My Account/Logout or another signed-in landmark appears and login dialog disappears. Search alone is not authentication proof.
5. Stop on rejected credentials/challenge. A second submission requires owner correction and explicit request; re-observe first.
   Verify: At most two submissions, no refresh loop or shell workaround.

## Failure modes and recovery
Missing secrets/configuration: request local setup and stop. Service error: report before credential submission. CAPTCHA/OTP: hand off once; never spend the run budget guessing.

## Definition of done
Observed signed-in landmark, or explicit statement that login was not verified.

## Field notes
The reported 66-action attempt had a localhost-only allowlist and repeated shell networking. Watching-human probes on 2026-10-25 IST received service edge errors in Chromium and installed Chrome before credentials were submitted. Local passes are not live login evidence.
