# Runtime service test record

Executed on 2026-10-24 (Asia/Calcutta), Windows, Python 3.13.

Command: `python -m pytest tests/unit/test_services.py -q --junitxml=test/services-results.xml`

Initial result: 7 passed, 1 failed. Redaction treated the numeric `tokens` metric as a credential; corrected key matching and made summary counters robust to nonnumeric data.

Subsequent result: 8 passed. A later rerun exposed a timing-fixture issue: registering and fsyncing twenty jobs consumed the original 100 ms lead-in, so the first job was already due before the service started. The fixture now gives registration one second before the first deadline; the under-100-ms dispatch criterion is unchanged. Final JUnit details are in `services-results.xml`.

Coverage: structured/canary secret redaction, escaped offline HTML replay, partial JSONL tail recovery, durable handoff resume, duplicate/invalid/late reply rejection, timeout denial, choice handling, mocked Telegram delivery with image and unauthorized-chat filtering, scheduler restart/clock offset/UTC cron/uncertain dispatch, 20 actual wall-clock scheduler trials under 100 ms, persistent file/email/HMAC webhook event deduplication, CLI trigger parsing.

Limitations: Telegram HTTP calls were mocked; no external messages sent. IMAP uses TLS but no real mailbox was accessed. Scheduler timing is an observed local test, not a hard real-time guarantee. Scheduler dispatches and events persist intent before dispatch; a crash at that boundary is marked uncertain and requires explicit recovery or an idempotent run dispatcher. Shared stores assume one active process; they are not a multi-process database. Image masking happens in capture tools, not the JSON redactor. The service tests do not establish real-site or desktop rehearsal readiness.
