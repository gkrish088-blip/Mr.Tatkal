# Local Rail Lab

Start `python -m uvicorn mock.mock_irctc.app:app --host 127.0.0.1 --port 8000`.
Open `http://127.0.0.1:8000`. Every account, payment, profile and PNR is fictional.
The built-in account is demo/demo; the visible demonstration challenge reads TRAIN.

The browser flow covers login, RK/HW/date/TATKAL search, six candidate train/class
fares, passenger form, exact review, external approval and ticket proof. The cheapest
two confirmed candidates cost Rs 65; Morning local wins the earlier-departure tie.
WL, RAC and REGRET candidates are excluded. Browser inputs use accessible labels;
scenario M6 changes field IDs and adds a dismissible modal.

`skills/mock-booking/macro.yaml` deliberately stops at the review checkpoint.
Its inputs are `url`, `date`, `name`, `age` (string), `gender`, `nationality`, `mobile`.
Review all values before requesting the fictional payment. The UI displays the
reservation ID; an external test driver approves with
`POST /api/test/approve/{reservation_id}`. Then click Check payment status.
No production handoff channel auto-approves anything.

`create_app(seed=0, scenario='M1', real_latency=False, open_at=0, clock=None,
payment_timeout=120)` builds isolated scenarios. M2 samples seeded 1–8s latency;
it advances a diagnostic virtual-latency counter unless `real_latency=True`.
M3 injects 20% 503 on search/passenger. M4 expires the session once on passenger
submission. M5 rejects 40% of login challenges. M6 changes layout IDs and shows
a modal. M7 uses the fare trap present in all scenarios. M9 uses payment deadlines.
M10 exercises idempotent passenger/payment calls after a lost response. M11 checks
the profile before starting. M12 denies requests until 60s have elapsed. M13 uses
the configured opening time; passenger submission is rejected before that instant.
M8 belongs to the model layer and is not simulated as a booking-server fault.

HTTP endpoints are `/api/login`, `/api/search`, `/api/passenger`,
`/api/review/{id}`, `/api/payment/{id}`, `/api/test/approve/{id}`,
`/api/ticket/{id}` and `/api/state`. Review requires an exact expected object and
SHA-256 digest. A review mismatch invalidates verification and blocks payment.
Passenger submissions require an idempotency key; conflicting reuse is rejected.
At most one booking can be confirmed in one application instance. State is
in-memory so each new instance starts a new isolated team rehearsal; this simulator
does not establish server persistence or real-service behavior.

`mock.mock_tasks.app:app` serves an unrelated library-fact/contact-form fixture.
Use it to exercise browser research and form filling with generic tools and skills.

Tests distinguish API contracts, actual headless Chromium, virtual-time faults,
test-only approval and unperformed live rehearsals. See `test/` for saved results.
