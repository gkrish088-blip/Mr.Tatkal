# General agent setup and requirement coverage

The four-page source PDF requires one generic harness for terminal, files, browser and native apps; tasks taught as skill files; plan/act/observe/verify; chat, schedule and event starts; an operator handoff channel; and reasons/screenshots/replay. Domain workflows stay in skills and mock services.

## Implemented runtime

- Ordinary questions get final text answers, which persist in the GUI conversation, summary and replay. Follow-up messages retain the transcript and loaded skills. Empty model responses and failures get explanations. A pending uncertain external action cannot be automatically repeated by follow-up or resume.
- The model sees skill metadata, OS/Python/workspace information and enabled tool names. It can inspect/load skills, use terminal/file/browser/desktop tools, extract PDF/XLSX data, ask the operator for a choice or approval, and report its verified result. Tool success alone is not a complete goal-verification claim; prompts and skills require checking the resulting state.
- `create_skill` learns a told task into local data/skills. `append_skill_note` records lessons in local overlays and preserves a bundled skill's gates and macro. These tools disappear when skill writes are disabled or a freeze manifest is configured. Skills are format-checked on save; execution checks must still be run explicitly.
- Schedules, incoming GUI chat, optional file/mail/webhook events and optional Telegram chat all feed the serialized persistent queue. Operator handoffs work through the GUI; Telegram can additionally carry requests, screenshot notifications and replies.
- Model decisions and executed actions are separate log phases. Answers, token counts, model IDs, latencies, screenshot evidence and failure explanations survive replay. Loaded skills are restored before a resumed model turn so gates are restored too.

## Computer access

The GUI server owns the computer adapters. Workspace tools are confined to `data/workspace`; shell commands run with the server account's ordinary OS permissions. Put test documents in this workspace before asking the agent to read them.

The managed browser persists cookies in data/browser-profile. Default hosts are localhost only. Set `BROWSER_ALLOWED_HOSTS` to the domains needed for a task, or explicitly use `*` for unrestricted HTTP(S) host access. These settings do not authorize unattended real-account login or booking rehearsals during development.

Set `DESKTOP_ENABLED=true` only when ready to permit the server to control its native desktop and the optional desktop dependencies are installed. With both adapters enabled, observations contain the native desktop screenshot, browser screenshot and DOM structure. Native screenshot masking is not automatic; operator preparation still matters. No native input is performed by the automated development suite.

## Event source configuration

Copy the desired entries from config.triggers.example.json into an ignored file such as data/triggers.json and set `TRIGGERS_FILE=./data/triggers.json`. The example is an array of independent sources; remove entries you do not intend to enable. Restart the server after configuration changes. Source IDs must be unique lowercase names. Optional `provider` and `skill` fields select a model/skill; otherwise the default provider and general loop are used. Goals are configured on the server, and incoming content is supplied as untrusted event inputs.

File sources watch a directory inside the workspace. The default directory is inbox; text files can be read by the same confined file tools. Changed contents get a new event ID. Email sources poll IMAP over TLS with read-only selection and BODY.PEEK; usernames/passwords are resolved from the named environment variables. They inspect the latest 100 messages, including matching existing messages at first enablement, and supply subject/from/plain message text (bounded to 50000 characters). Attachments are not imported. No mail provider is contacted unless that source is explicitly configured.

Webhook sources expose `POST /hooks/<source-id>` with a JSON object body. Supply X-Event-ID and X-Signature. The signature is the hex HMAC-SHA256 of `event_id + "." + raw_body`, using the configured server-side signing-secret environment variable. Both body and event identity are authenticated. The endpoint uses signature authentication and does not require the operator cookie or browser request header. Payloads over 1 MB are refused. A repeated event ID does not enqueue a second task.

Trigger intent and source IDs persist under data/trigger-state. A dispatch interrupted after intent remains uncertain and is suppressed; inspect it before an operator retry. Polling failures appear by exception type in `/api/status` without echoing credential-bearing errors. File/event dispatches and schedule dispatches are deduplicated in the session store as well.

## Optional Telegram channel

Set TELEGRAM_ENABLED=true, TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in the ignored .env only when external messaging is intended. One server-owned transport polls updates, accepts `/run <goal>` from the configured chat, and routes `/reply <request-id> <answer>` to persisted handoff requests. It keeps its update offset on disk and shares the transport with active tasks instead of creating competing pollers. `notify_human` sends a result/current screenshot without creating an approval handoff. These features are tested with fake HTTP transports during development, not a real chat.

## Remaining operator and bonus work

Local regression passes do not qualify a live booking. Real-site landmarks, account readiness, model quota/failover under real conditions, external handoff delivery, native-app rehearsal, time synchronization, Drive placement, recordings and ticket proof remain operator checks. The source PDF's live attempt and hands-free submission evidence have not been performed.

Shown-demo recording, compiling successful traces into macros, and automatically promoting/refining skills after regression validation are bonus features from the plan and remain unimplemented. Told-task learning and append-only field notes are supported. No freeze tag, live schedule, real login, booking or payment is created automatically by these changes.

## Verification evidence

The final automated regression is 205 passed and one Windows symlink-privilege skip. Four separate real-Haiku checks passed through the running GUI API: answering a skill question, a verified file/terminal follow-up, teaching/loading/executing a new skill with a reusable field note, and extracting spreadsheet values into a fictional browser form with independently checked stored results. An earlier real test exposed and led to fixing a static-browser false stuck detection; its failed evidence is retained. See test/general-agent-verification.md and the timestamped records it links for commands, UTC timestamps, results and exact scope.

To repeat the paid provider checks on an idle local server, run `python scripts/smoke_general_agent.py --live-model`. It creates only local test files/learned skills and a temporary fictional web service, and does not drive native apps or real accounts. Reload the GUI after a server update to load the latest conversation client.
