# Do You Know How to Train? Implementation Plan

Syntax Error 2026, Alum Track Dev I. Written Oct 23, 2026 for the team's coding agents.

## 0. How to use this document

Goal: build our own general-purpose computer-use agent harness, teach it jobs through skill files, and use it to book one Tatkal ticket (Roorkee to Haridwar) hands-free at 11:00 on Oct 25. Read sections 1 to 4 before writing code. Build in the order of section 9. Every component has a test in section 8 and is not done until that test passes. If this doc conflicts with the official problem statement, the statement wins; flag it to a human.

Why the order matters: the booking is a one-shot with two windows. Reliability, logging, handoff and rehearsal matter more than cleverness.

## 1. What we are optimizing for

1. Qualify: a correct Tatkal ticket, booked hands-free, with proof in the Drive folder.
2. Final round: live, unseen tasks across the whole device. The agent must be truly generic, not an IRCTC bot.
3. Tie-break: fewer human handoffs, then architecture and UX.

Required components: Hands, Eyes, Loop, Skills, Triggers, Human Handoff, Run Log. Bonus: self-improving skills, skills from a demo. Section 4 designs each, section 8 tests each.

## 2. Ground rules

1. The core is generic. No site names in harness code. All IRCTC knowledge lives in skills (enforced by lint L1).
2. One booking, from one team member's own IRCTC account. No borrowed or extra accounts. Rehearsals on the real site stop before payment.
3. The only human action in the live run is approving the final payment. Every other handoff costs points. The harness must still support handoff generically.
4. Code freeze is 09:00 on Oct 25. Tag the repo `freeze`, record a hash manifest, and disable skill self-editing for the live run. After freeze only the Drive folder changes.
5. Secrets (IRCTC password, UPI id, API keys) never go in the repo, logs, screenshots or the Drive folder.
6. Behave like a normal user on the site: real Chrome, own phone hotspot, human-scale pacing (at most about 2 requests per second), no fingerprint spoofing, no proxy rotation. IRCTC's terms restrict automated booking tools and the organizers sanctioned this one attempt, so keep it narrow. The team is responsible for the device and account (T&C 7).
7. Agents never run real-site login or booking flows without a human watching. Use the mock (section 7) for everything else.

## 3. Confirm with organizers now (assumption in brackets)

1. Do edits to skill files and config count as 'code' under the freeze? (Assume yes. Freeze everything.)
2. What does 'cheapest' mean? (Assume: lowest total fare including Tatkal charge, across all trains and classes, among options with confirmed seats. Waitlisted or RAC are skipped. Tie goes to earliest departure.)
3. Is one handoff acceptable for payment, where the agent submits the UPI request and the human approves it in the UPI app? Or do they expect a separate chat approval first? (Assume single handoff.)
4. Does the account need Aadhaar or OTP verification at booking time? If an OTP appears, may the agent read it from SMS or email? (Assume the account is pre-verified. Check today.)
5. What are the 'two windows'? (Assume two attempts, and a retry is allowed if the first fails.)
6. Which classes open at 11:00? (Assume non-AC such as SL and 2S. AC Tatkal usually opens at 10:00. Verify on the real site.)

## 4. Architecture

```
Triggers (chat | schedule | file/email event)
        |
   Run Manager  -- persists state after every step (resume after crash)
        |
   The Loop: plan -> act -> observe -> verify -> repeat
     |         |          |            |
   Model     Tools      Observers    Verifiers
   layer    (hands)     (eyes)     (skill checkpoints)
     |
   Skills (markdown folders)   Human Handoff (Telegram)   Run Log (JSONL + screenshots)
```

### 4.1 Build fresh, borrow selectively from Hermes

Hermes (Nous Research) is MIT licensed, so we can copy code. The problem requires our own harness, so:

- Write fresh: the loop, tool registry, run manager, run log, macro runner. They are small, and we must understand every line when debugging at 3 a.m.
- Borrow with attribution (keep their MIT notice in a NOTICE file): the skill file format and loader, the cron scheduler, the Telegram gateway code, and any browser or terminal tool code that is cleaner than ours.
- Do not vendor the whole repo. It carries many platforms and RL tooling we do not need, and unfamiliar code is the biggest bug risk.
- First task for the lead agent: spend at most 45 minutes reading the Hermes repo and write `docs/borrow-list.md` (file paths to lift and why).

### 4.2 Repo layout

```
harness/
  core/      loop.py run_manager.py context.py verify.py macro.py
  models/    adapter.py failover.py
  tools/     shell.py files.py browser.py desktop.py clock.py human.py secrets.py
  triggers/  chat.py schedule.py events.py
  handoff/   telegram.py
  log/       runlog.py redact.py replay.py
  skillrt/   loader.py recorder.py reflector.py
skills/      (data only: SKILL.md, macro.yaml per skill)
profile/     passenger.yaml (template committed, real file gitignored)
mock/        mock_irctc/  mock_tasks/
tests/       unit/ integration/ generality/ lint/
docs/        borrow-list.md irctc-recon.md runbook.md interfaces.md
```

Python 3.11+, asyncio, Playwright attached over CDP, mss for screenshots, pyautogui or OS-native calls for input behind one `desktop.py` interface. First question to the human: which OS is the booking laptop?

### 4.3 Tools: hands and eyes

All tools are generic. Every action tool auto-captures an after-screenshot and a state hash, and returns a structured result.

Hands:

- `shell(cmd, timeout, cwd)`, `file_read/write/edit/list`
- `browser_goto/click(ref)/type(ref,text)/press/select/scroll/wait_for(text|ref|url)/tabs/download`
- `desktop_click(x,y)/double_click/drag/scroll/type_text/hotkey/launch_app/focus_window`
- `clock_wait_until(timestamp)` with NTP offset correction
- `secret(name)`: inserts a secret into a field without echoing it
- `ask_human(...)`: see 4.7

Eyes:

- `screenshot(scope=screen|window|page)`
- `browser_snapshot()`: compact DOM and accessibility text with stable element refs, visible text, form fields, error banners
- `desktop_a11y_tree()` where the OS allows it (UI Automation, AX, AT-SPI)
- terminal output from `shell`

Browser design: attach to a real Chrome that the human launches with a remote-debugging port and a dedicated persistent profile. Why: normal fingerprint and cookies get past most bot checks without any evasion tricks, and the same code works for any site.

Prefer structure over pixels: DOM refs first, vision to confirm results and to handle captcha, canvas and non-web apps. Why: faster, cheaper and more reliable under load. Pixels are what make the agent general.

### 4.4 The loop

Each step:

1. Build context: system prompt, skill index, active skill bodies, goal, compact history, latest observation.
2. The model returns a one-sentence reason plus tool calls.
3. Execute and capture artifacts.
4. Verify: if the active skill step has a checkpoint (URL, text or element present, or a short vision check), evaluate it and log pass or fail.
5. Decide: continue, retry, run the skill's recovery rule, or hand off.

Guards:

- Max steps and max wall time per phase.
- Stuck detector: same state hash for 3 steps, or same action failing 3 times, triggers recovery, then handoff.
- Error classes: transient errors retry with backoff and jitter; model rate limits fail over to another model; session loss reruns the login skill; real ambiguity hands off.
- Context hygiene: keep the last 2 screenshots in full, replace older ones with one-line text summaries.

Tiered execution (our improvement over a plain LLM loop):

- Reflex: a skill may ship `macro.yaml`, a declarative list of tool calls with selectors, data bindings (from the profile) and one assertion per step. A generic macro runner replays it in milliseconds. It is data, not code, so 'new task = new skill' still holds.
- Reason: when an assertion fails or an unexpected screen appears, the loop drops to the LLM for that step, finishes it, then returns to the macro.
- Human: only when both fail, or a gate is hit.

Why: each LLM step costs seconds, and seconds add up in the 11:00 burst when IRCTC is slow. Macros give speed, the LLM gives resilience. Macros are compiled from successful run traces (section 6), so we do not hand-write selectors.

### 4.5 Skills

One folder per skill. `SKILL.md` has frontmatter (name, one-line description, when\_to\_use, requires, gates, version) and sections: Goal, Preconditions, Procedure (numbered, each step with a `Verify:` line), Screen landmarks (what each page looks like in words, plus DOM hints), Failure modes and recovery (table), Definition of done, Field notes (append-only, written by the reflector). Optional `macro.yaml` and annotated screenshots.

Loading: only name and description go in the prompt. The model calls `use_skill(name)` to load the body. Skills can call other skills. Check Hermes' skill format and stay compatible if it is sane.

IRCTC skills, kept small and composable: `irctc-login`, `read-captcha`, `irctc-search-train`, `irctc-rank-fares`, `irctc-book-tatkal`, `fill-passenger-from-profile`, `pay-handoff`, `capture-evidence`, `recover-irctc-errors`. Generic helpers: `web-form-fill`, `handoff-etiquette`, `save-proof-screenshot`.

### 4.6 Triggers

Chat command (Telegram and CLI), schedule (one-shot and cron, persistent job store, millisecond precision, survives restart), and event (file watcher, IMAP or Gmail poll for 'when an email arrives', webhook). Every trigger just creates a Run with goal text and inputs. Why one abstraction: the final round will likely test triggers.

### 4.7 Human handoff

`ask_human(kind, text, attachments, options, timeout, on_timeout)` with kinds `approve`, `choose`, `text`, `external_approval`. It sends a Telegram message with a screenshot, persists run state, suspends the loop, and resumes when the reply arrives. The channel is ours, not the screen. Each handoff increments a counter shown in the run summary.

Gates: a skill can list gated actions in frontmatter. The harness refuses to execute a gated tool call without a prior approval event.

Payment: the `pay-handoff` skill submits the UPI request, then calls `external_approval('Approve Rs X in your UPI app now')` and watches for the success page. Replying 'done' is the fallback. This is one handoff, the allowed one. Send a loud notification and keep the phone in hand at 11:00.

### 4.8 Run log and replay

`runs/<run_id>/` holds `run.jsonl`, `steps/0001_before.png`, `0001_after.png`, `summary.md`, and a generated `replay.html`. Each JSONL line has: step, timestamp (ms), phase, skill, tier (reflex, reason or human), reason, action (args redacted), result, verification (assertion and verdict), latency, tokens, model, handoff flag.

Redaction: secrets are never written; password fields are masked before screenshots; payment form fields are masked. Write the log directly into the Drive-synced folder from the start, so nothing needs editing after freeze.

`python -m harness.log.replay runs/<id>` builds an HTML timeline (screenshot, reason, action, verdict per step).

### 4.9 Model layer

Provider-agnostic adapter with tool calling and vision. Primary model plus a fallback on a different provider. Exponential backoff with jitter on 429 and 5xx. Per-phase model choice: a fast model for routine verification, the strongest model for recovery and captcha. Request timeouts shorter than the critical interval. Token and cost counters. Preflight sends a tiny call to check quota and keys. Why: the statement warns explicitly about rate limits.

### 4.10 State, secrets, config

Persist run state after every step (phase, step, skill stack, handoff count) so a crash resumes at the right step. Secrets come from the OS keychain or env vars. One YAML config holds times, paths, key names and the Telegram chat id. The passenger profile schema: name, age, gender, nationality, berth preference, mobile, ID details if the site requires them, payment method and UPI id. Preflight validates it.

## 5. IRCTC skill design

### 5.1 Timeline (IST, times configurable, clock NTP-corrected)

- 10:40 Run starts on the schedule trigger. Preflight, attach to Chrome, log in (read captcha, retry), verify the logged-in state. Check the session idle timeout during rehearsal and adjust the start time.
- 10:50 Search Roorkee (RK) to Haridwar Jn (HW) for tomorrow, quota Tatkal. Rank candidates by displayed fare. Verify station codes and how Tatkal fares display during recon. Hold the page.
- 10:59:50 Refresh results and arm.
- 11:00:00 Poll class tiles (at most 2 requests per second) until the cheapest candidate is bookable, then select it. If it shows waitlist or regret, move to the next candidate.
- Passenger page: macro fills from the profile, choose payment method, read the booking captcha, submit.
- Review page: assert train, class, date, quota, passenger and fare against the expected values, then run `pay-handoff`.
- After payment: wait for success, capture the PNR screenshot and e-ticket into the Drive folder, send a Telegram summary.

Why pre-stage: the only time-critical work at 11:00 is clicks and form fill.

### 5.2 Recovery rules (`recover-irctc-errors`)

| Symptom | Action |
| --- | --- |
| Service unavailable, 5xx, blank page | Wait 1 to 2 s, refresh or go back, retry the same step up to 5 times, then restart from the search page while keeping the login |
| Session expired | Run `irctc-login`, return to the last checkpoint |
| Wrong captcha | Refresh, re-read, up to 4 tries; switch to the strongest vision model; hand off only after that |
| Modal, ad overlay, confirm dialog | Dismiss per landmarks; never click Cancel or Back on a booking confirmation |
| No Tatkal availability yet | Keep polling past 11:00:05; if still nothing after N seconds, re-search |
| Wrong train, class or fare on review | Do not pay. Go back and fix. If it cannot be fixed, hand off |
| Payment gateway timeout | Re-initiate within the session; if the booking expired, restart from search |
| Access denied or bot-check page | Stop. Wait 30 to 60 s, retry once at human pace, hand off if it persists |
| Model 429 or timeout | Fail over to the fallback model |

## 6. Bonus features

### 6.1 Self-improving skills

After each run the reflector reads `run.jsonl` and the skill, then proposes edits to Field notes and recovery tables (new gotchas, better landmarks, timing). Proposals go to `skills_proposed/<skill>.patch.md`. A validation run on the mock applies the patch and reruns scenarios M1 to M3. Only if nothing regresses is it merged and committed. In the live window auto-merge is off. Demo it as: run 1 fails on a gotcha, skill is patched, run 2 passes with fewer steps.

### 6.2 Skills from a demo

Two modes. Told: the user describes the task in chat, the agent drafts `SKILL.md`, tries it in a sandbox and refines it. Shown: `recorder.py` captures screenshots, input events and DOM events while the human does the task once; an LLM turns that into `SKILL.md` and `macro.yaml`; validation is a replay; the agent asks only about ambiguous parts. The same compiler turns any successful run trace into a macro, which is also how the IRCTC macros get made.

## 7. Mock IRCTC (test double)

A small Flask or FastAPI app on localhost that mimics the flow shape, not IRCTC branding: login with a generated distorted captcha, station search, results with several trains and classes, fares, availability states (AVL, WL, REGRET, RAC), a Tatkal quota that unlocks at a configurable server time, passenger form, review page, booking captcha, payment page with 'UPI request sent' and a test endpoint to simulate approval, and a PNR ticket page.

Fault injection (seeded, reproducible): latency 1 to 8 s, 5xx rate, session expiry after N minutes, captcha failure rate, modal and ad popups, access-denied page, and layout variants that rename ids and classes. Variants force skills to use landmarks and text, not mock-specific selectors.

Also build a few mock non-IRCTC tasks (shop, inbox, form) for the generality suite. The mock is for deterministic regression and chaos testing. It does not replace real-site rehearsals.

## 8. Tests and benchmarks

### 8.1 Unit tests (U)

| ID | Test |
| --- | --- |
| U1 | `shell`: timeout kills the process tree, output truncates, exit codes captured |
| U2 | files: read, write, edit are atomic and respect the configured sandbox |
| U3 | browser tools on a mock page: click, type, wait\_for work; snapshot refs stay stable across re-render |
| U4 | desktop tools: open a native text editor, type, save; screenshot hash changes (per OS) |
| U5 | skill loader: parses frontmatter, builds index, rejects malformed files, loads bodies on demand |
| U6 | scheduler: fires within 100 ms of target over 20 trials; survives restart; NTP correction applied |
| U7 | run log: every step has before and after screenshots and a non-empty reason; valid JSONL; a canary secret never appears in any log file |
| U8 | handoff: message sent with screenshot, reply parsed, run resumes; timeout path works; duplicates suppressed |
| U9 | model adapter: 429 triggers backoff then failover within N seconds; malformed tool call is repaired or retried |
| U10 | loop guard: stuck detector triggers recovery, then handoff |
| U11 | macro runner: failed assertion falls back to LLM stub, then resumes the macro |
| U12 | run state: kill -9 mid-run, resume at the correct step |

### 8.2 Mock integration scenarios (M)

Run each 20 times with different seeds.

| ID | Fault | Pass criteria |
| --- | --- | --- |
| M1 | None (happy path) | Cheapest available train and class, correct passenger, exactly 1 handoff, PNR page captured |
| M2 | Latency 1 to 8 s | Same as M1 |
| M3 | 20% 5xx on search and booking | Same as M1 via retries |
| M4 | Session expires mid-flow | Re-login, resume, one booking |
| M5 | Captcha fails 40% | Recovers without handoff |
| M6 | Popups, ads, renamed ids and classes | Same as M1 |
| M7 | Fare trap: cheapest is waitlisted, cheapest available is not first, two equal fares | Picks per the cheapest rule in section 3 |
| M8 | Model 429 on 30% of calls plus a 60 s primary outage | Failover, same as M1 |
| M9 | Payment approval at 20 s, at 90 s, never | Books on approval; stops cleanly on never; no double booking |
| M10 | Process killed during the passenger form | Resume yields exactly one booking |
| M11 | Profile missing a field | Preflight fails before the run with a clear message |
| M12 | Access-denied page for 60 s | Backoff; request rate stays at or below 2 per second |
| M13 | Tatkal unlocks at mock 11:00:00 | No booking attempt before open; booking within the target time after open |

Thresholds: M1 20/20. M2 to M8, M12, M13 at least 18/20. M9 to M11 20/20 (they are safety tests). Across all scenarios: never more than one booking, never pay when the review page mismatches the profile, no handoff except payment.

### 8.3 Real-site rehearsals (R)

- R1 recon (a human, today): do the flow by hand once with screenshots. Record pages, class tiles, fare display, captcha types, popups, session timeouts, whether Roorkee to Haridwar shows Tatkal options at all, which classes open at 11:00, and any OTP or Aadhaar step. Write `docs/irctc-recon.md`. If the Tatkal list is tiny or empty, raise it with the organizers.
- R2: agent login-only runs, 3 times, spaced out, on the hotspot. Pass: logged in with no human.
- R3: timed dry run at 11:00 (Tatkal opens daily for the next day's journey) through to the review page. Never pay. Pass: reached review with the correct train, class and passenger. Record B1.
- R4: full live-conditions rehearsal on the last timed window before freeze (11:00 on Oct 24) with the near-final code: scheduled trigger, hotspot, screen recording, phone video, Drive logging, Telegram handoff, stopping before payment. Pass: every Drive artifact exists and `replay.html` opens.
- Limit real logins to about 5 in total to avoid locks or blocks.

### 8.4 Generality suite (G)

Each task is done by adding or changing only skill files, or nothing. Run it periodically with the IRCTC skills present, to catch overfitting.

| ID | Task |
| --- | --- |
| G1 | Shell and files: make a folder, write and run a script, report the output |
| G2 | Organize a sandbox folder by file type, with an undo log |
| G3 | Browser research: find a fact on a public or mock site, save a note |
| G4 | Non-browser desktop app: open a text editor or calculator, act by mouse and keyboard, verify by screenshot and saved file |
| G5 | Cross-app: read values from a PDF or spreadsheet, enter them in a web form |
| G6 | Schedule trigger: at hh:mm:ss, screenshot the desktop and send to Telegram |
| G7 | Event trigger: when a file lands or an email with subject X arrives, summarize and message |
| G8 | Handoff: ambiguous task, ask via Telegram, resume correctly |
| G9 | Skill from a told demo, then rerun: fewer steps the second time |
| G10 | Self-improvement: induced gotcha, skill patched, second run passes with fewer steps |

Target: G1 to G8 pass with at most one new skill file written by the agent itself. G9 and G10 are bonus.

### 8.5 Invariants and lints (L)

- L1: no 'irctc' or other site names anywhere under `harness/` (grep in CI).
- L2: adding a skill requires zero diff outside `skills/`, `profile/` and config.
- L3: secrets scan (canary plus regex) over the repo and all run logs.
- L4: at freeze, write `freeze_manifest.json` with file hashes. Include it in the Drive folder. At runtime log a warning if the tree hash differs.
- L5: request-rate limiter test (at most 2 per second against the site).

### 8.6 Benchmarks (B), reported in every run's `summary.md`

| ID | Metric | First-guess target |
| --- | --- | --- |
| B1 | Seconds from window open to review page | Mock no-latency: 15 s or less. Real site: p50 60 s or less. Recalibrate after R3 |
| B2 | Steps per run, and share of reflex steps in the burst | At least 70% reflex |
| B3 | Human handoffs | Exactly 1 |
| B4 | Injected faults recovered without handoff | At least 90% |
| B5 | Tokens and cost per run | Track, no hard target |
| B6 | LLM latency p50 and p95 per model | Use it to pick models per phase |

These targets are guesses. Treat them as a starting point and adjust after the first real-site rehearsal.

### 8.7 Go/no-go gate before freeze

- All U tests pass.
- M1 to M13 meet their thresholds.
- R3 reached the review page autonomously at least once.
- R4 done, with all Drive artifacts and a working `replay.html`.
- L1 to L5 pass; `freeze` tag and manifest created.
- Runbook printed.

## 9. Build plan and work split

Calendar anchors: Oct 24 11:00 is the last real timed rehearsal, so the near-final code must exist by then. Feature freeze about 6 hours before the code freeze. Code freeze Oct 25 09:00. Live run Oct 25 11:00.

Priorities:

- P0, working by Oct 24 11:00: loop, tools (shell, files, browser, screenshots), run log, scheduler, Telegram handoff, IRCTC skills through to the review page, first mock scenarios.
- P1, before feature freeze: macros and tiered execution, model failover, M1 to M13, desktop tools, G1 to G8, replay, evidence capture.
- P2, only if P0 and P1 are green: reflector, demo recorder, G9, G10, polish.

Parallel agents, coding against `docs/interfaces.md` that Agent A writes in the first hour (tool signature, observation schema, RunEvent schema, skill frontmatter schema, handoff API):

| Agent | Owns |
| --- | --- |
| A | core loop, context, run manager, model adapter and failover, macro runner |
| B | tools: browser (CDP), desktop, shell and files, clock, secrets |
| C | triggers, scheduler, Telegram handoff, run log, redaction, replay |
| D | mock IRCTC, fault injection, test scaffolding, lints, generality tasks |
| E | skills (IRCTC set and generic helpers), then reflector and recorder |
| Humans | recon R1, accounts, organizer questions, rehearsals, recordings, demo video |

Rules for every agent: small commits, tests with every change, no secrets, no real-site flows without a human present, and ask a human through the handoff channel when a decision is needed.

## 10. Run-day runbook and evidence

Oct 25, after freeze, no code edits:

- 09:30 Laptop plugged in, sleep disabled, notifications on. Own phone hotspot connected. UPI app ready on the phone. Telegram open. Chrome profile ready. Screen recorder running from start to finish. A second phone filming the untouched laptop. Drive folder open.
- 10:30 Preflight script: NTP drift under 50 ms, hotspot latency and bandwidth, both model APIs respond, Telegram works, profile valid, disk space, IRCTC reachable, account not locked.
- 10:40 Scheduled run starts. Nobody touches the keyboard or mouse.
- 11:00 onward Watch only through Telegram. Approve the UPI request when prompted. If it fails and a retry window exists, rerun per the organizers' rules.
- After: stop recordings and check the Drive folder.

Drive folder layout:

```
drive/
  run-log/    run.jsonl steps/ summary.md replay.html
  ticket/     pnr.png eticket.pdf
  recordings/ screen.mp4 phone-untouched.mp4
  skills/     skills as of freeze, freeze_manifest.json
  README.md   what is where, how to replay
```

Demo video (3 to 5 minutes): the problem, one architecture diagram, the loop live, a skill file explained, trigger and handoff demo, a non-IRCTC task done by adding only a skill, bonus features, benchmark results.

## 11. Top risks

1. Bot check or captcha breaks login: real Chrome profile, hotspot, human pacing, strongest vision model for captcha, limited rehearsals.
2. IRCTC slow or erroring at 11:00: pre-staging, macros, retries, the recovery table.
3. Account problems (OTP, Aadhaar, lock): verify the account today, rehearse sparingly.
4. Model rate limits: fallback provider, cheaper model for verification, preflight quota check.
5. Overfitting to IRCTC: lints L1 and L2, run the G suite regularly.
6. Time sink on the mock or bonuses: obey the P0, P1, P2 order.
7. Freeze ambiguity: ask organizers; treat everything as frozen.
8. Missed payment approval: phone in hand, loud alert, generous timeout.
9. Wrong ticket: ranking tested in M7, review-page assertion, fare comparison written to the log.
10. Forgotten recordings: they are in the runbook and tested in R4.
