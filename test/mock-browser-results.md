# Local browser integration check

- Timestamp: 2026-10-24, Asia/Calcutta
- Command: `python -m pytest tests/integration/test_browser_workflow.py -q`
- Final result: **1 passed in 5.95 seconds**.
- Actual headless Chromium ran the generic Engine and MacroRunner against a local
  FastAPI server using `skills/mock-booking/macro.yaml`. The macro reached review.
  The test checked every rendered profile/route/date/quota value, submitted one
  fictional payment, used one durable HumanChannel external-approval request with
  an isolated test transport, then verified one ticket, one booking, PNR, per-step
  before/after screenshots, nonempty reasons and generated replay HTML.
- Two initial failures uncovered a missing explicit accessible label on a select
  and short typed values corrupting screenshot UUIDs during redaction. The UI label
  and shared redactor were corrected; the complete browser test then passed.
- Limits: one deterministic local happy path. Test-only transport approved only a
  localhost fictional payment. Review-value comparisons and the final payment steps
  are test-driver checks after the skill macro; the shipped demo macro stops before
  payment. This is not an autonomous 20-seed M1–M13 qualification run. API tests use
  virtual latency/timing; actual M8 model outage, M10 OS kill, M12 paced autonomous
  recovery and R1–R4 live rehearsals remain separate checks. Browser artifacts are
  temporary test files; this report is the retained result.
