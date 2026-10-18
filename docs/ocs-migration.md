# Migrating Zeya onto Open Chat Studio

Status: implemented, not deployed · Target: `https://openchatstudio.co.ke/` (team `evarest`) ·
OCS reference commit `7df40d8a4`

> **Go-live check:** before each release, someone calls each emergency number in the
> message (999, 112, 922, 1199) and records the date and result under
> [Emergency numbers](#emergency-numbers). 922 (the SHA national ambulance line) was
> launched in August 2026 and was found in only one source when it was added.

## Summary

OCS takes over the WhatsApp channel, sessions and history, LLM calls, participants and
admin. Zeya keeps, **in this repository**, the safety-critical and study-critical code:
the danger-sign gate, the emergency message with national emergency numbers, the
registration flow, and the export adapter. These are written as OCS Python-node
sources under `ocs/nodes/`, tested here against the real OCS sandbox and engine, and
assembled into `ocs/pipeline/zeya_pipeline.json` by `ocs/build_pipeline.py`.

```
Start → danger_gate (Python) → danger_router (Static Router on temp_state.danger_route)
          ├─ output_0 EMERGENCY (default) → emergency_response (Python, no LLM) → End
          └─ output_1 SAFE → registration (Python) → registration_router (Static Router on temp_state.registration_route)
                                ├─ output_0 REPLY (default) → End
                                └─ output_1 REGISTERED → llm (LLM, Gemini) → End
```

**Why not `CodeNode → BooleanNode`, as first sketched.** `BooleanNode` is
`@deprecated_node` (`can_add=False`), so it cannot be added in the UI. Also, every OCS
router passes its *input* downstream (`from_router_output(..., state["last_node_input"])`).
So if the gate returned the category, the LLM would receive `"none"` instead of the
user's message. Instead, the gate returns the message unchanged and writes
`danger_route` to temp state. A `StaticRouterNode` routes on that value.

## What moves, what stays

| Zeya today | After migration |
|---|---|
| `whatsapp.py`, `webhook.py` | OCS WhatsApp channel (participant identifier = Meta `wa_id` = Zeya `whatsapp_id`) |
| `conversation_handler.py` orchestration | the pipeline above |
| `conversation_handler.py` registration steps | `ocs/nodes/registration.py` |
| `ai_engine.py` | OCS LLM node. Prompt copied verbatim to `ocs/prompts/system_prompt.txt`; `_build_context` ported into the registration node |
| Redis history (6 turns, 24 h) | OCS node history, `max_history_length` 12 messages |
| `user_service.py`, `users.py` | OCS participants + participant data (same field names as the `users` columns) |
| `analytics_service.py`, React dashboard | OCS dashboard; `ocs/export_adapter.py` reproduces the analysis CSV |
| `danger_signs.py` | `ocs/nodes/danger_gate.py`, **patterns unchanged** |
| `health_facility_service.py` + table | static table built into `ocs/nodes/emergency_response.py`, checked against `app/seeds/health_facilities.py` |
| Zeya Postgres (existing transcripts) | **stays**, read-only, until the study closes |

## The danger-sign gate (the four hard rules)

1. **Deterministic regex.** `danger_gate.py` contains the same 39 patterns as
   `danger_signs.py`, in the same order, with the same flags. It uses the same
   first-match-per-category loop. No LLM node is before the router.
2. **Runs before the LLM.** It is the only node after Start, and the LLM can only be
   reached through the router's `SAFE` handle. Every message is gated, including
   registration messages. `EMERGENCY` is the router's default route, so a missing or
   unexpected value goes to the emergency message, not the LLM. If the gate raises,
   OCS stops the pipeline (`CodeNodeRunError`) and no LLM node runs.
3. **Not editable by non-engineers.** OCS has no per-node lock. Pipeline edit rights
   come from the *Chatbot Admin* group (`pipelines: ALL`, `apps/teams/backends.py`).
   Study staff get *Chat Viewer* + *Annotation Reviewer* only. Engineers deploy the
   generated JSON and never edit nodes in the UI. `python -m ocs.check_drift live.json`
   compares the live pipeline with the repository: node set, edges, all Python code,
   router settings, prompt and model parameters. It exits 1 on any difference. Run it
   after every deploy and on a schedule. This is an operational control, not a
   technical lock, and remains a residual risk.
4. **Version-controlled with tests.** The node source is a normal `.py` file. The
   parity tests compare each pattern's string and flags with the original. They also
   prove each of the 39 patterns individually and assert identical categories and
   keywords for every test message, both languages, the negatives and the edge cases.

### What changed to fit the Python-node constraint (structure only)

OCS runs node code with `exec(code, globals, locals)`. Module-level names land in
`locals`, so `main` cannot see them (verified in both the pinned and real sandbox).

- `import re` and the pattern table moved **inside** `main`.
- The table is a list of `(category, [patterns])` pairs instead of a `dict`, in the
  same order.
- `DangerSignResult` became temp-state values: `danger_route`, `danger_categories`,
  `danger_keywords`.
- The pattern block was generated mechanically from the original source lines, not
  retyped.

**No pattern string, flag or match rule changed.**

Also found: the sandbox has no `_unpack_sequence_`, so `a, b = ...` fails at run time
inside a node. `for a, b in ...` works. The nodes avoid it, and a test pins the
constraint.

### Gaps in the existing patterns (not changed; needs clinical review)

Porting verbatim keeps these existing misses. The tests record them as edge cases:

- `blurred?` matches "blurre"/"blurred", not "blur" or "blurry".
- `\bconvulsion\b` and `\bseizure\b` miss the plurals "convulsions" and "seizures".
- `stopped?` and `passed?` miss "stop moving" and "pass out".

Fixing them changes matching behaviour. It should be a separate, clinically reviewed
change made to `danger_signs.py` and the node together. The parity tests enforce that
both change together.

### No LLM on the emergency path

`emergency_response` is a Python node with no LLM. The structural tests read the
generated pipeline as a graph. They assert that no LLM-type node is reachable from
`EMERGENCY` and that, with the `SAFE` edge removed, no LLM node is reachable from Start.
The engine test runs all 8 categories × {en, sw} through OCS's real `PipelineGraph` with
a recording fake LLM and asserts zero LLM calls.

## Emergency numbers

ZEYA is open to women anywhere in Kenya, and the trial runs in Migori County. Zeya's
message listed five Migori facilities, four of them with placeholder numbers, and a
verified per-county list was not obtainable. The OCS message keeps Zeya's header and
footer and lists national numbers instead (methodological change 9):

| Number | Service | Source when added (2026-10-18) |
|---|---|---|
| 999, 112 | Emergency services | [Standard](https://standardmedia.co.ke/ureport/story/2001257538/emergency-lines-for-kenya), [HapaKenya](https://hapakenya.com/2026/03/09/how-to-contact-emergency-services-in-nairobi-nationwide), [Jambo Nairobi](https://jambonairobi.co.ke/directory/services/emergency/) |
| 922 | National ambulance (SHA 922 Lifeline) | [Dawan Africa](https://www.dawan.africa/news/president-ruto-launches-922-lifeline-to-cut-emergency-response-times-nationwide), one source only |
| 1199 | Kenya Red Cross toll-free line | the same three directories as 999 |

These are directories and news reports, not official pages. One source also lists 1199
as a mental-health line.

**Call log** (fill in before each release):

| Date | Number | Answered? | Sends ambulances or dispatches help? | Checked by |
|---|---|---|---|---|
| | 999 | | | |
| | 112 | | | |
| | 922 | | | |
| | 1199 | | | |

The numbers are written into the node, so the emergency path has no runtime
dependency (database, HTTP, participant-data lookup) that could fail, and any change
goes through code review. Nearest-facility lists per county can be added later on top
of these numbers.

## LLM provider

**Decision: add a Google Gemini provider on the instance, using the existing Zeya
key, and keep `gemini-3-flash-preview`. Do not switch to "Evarest OpenAI".**

- The config default became `gemini-3-flash-preview` in commit `70212c9` (2026-02-09).
  The README still says `gemini-2.0-flash-exp`. That date is when the default changed,
  not proof of what production ran: deployments read `GEMINI_MODEL` from their own
  `.env`. **Check production before relying on it:** `SELECT ai_model_used,
  min(created_at), max(created_at), count(*) FROM conversations WHERE
  message_direction = 'outgoing' GROUP BY 1 ORDER BY 2`. A local development database
  holds only test rows (all `gemini-3-flash-preview`, 2026-02-09), so it cannot confirm
  this.
- Switching provider partway through the study changes model family, Swahili quality,
  length and tone. That is a much larger methodological change than staying on Gemini.
- OCS lists `gemini-2.5-*` for the `google` provider, not `gemini-3-flash-preview`.
  Add it as a custom model. If that is impossible, use `gemini-2.5-flash` and record a
  model change point.
- **Temperature is pinned to 1.0.** Zeya called Gemini with no generation config, so it
  used the model default (1.0 for Gemini 3). OCS would otherwise default to 0.7.
  Confirm the default for the exact model at deploy time.

## Methodological changes (for the study log, with go-live date)

1. **No AI follow-up after an emergency message.** Zeya sends the template and then a
   second Gemini reply. The no-LLM emergency path removes the second reply, and those
   turns no longer enter LLM history.
2. **Danger signs are checked during registration.** Previously those messages skipped
   detection.
3. **Prompt assembly.** The system prompt, gestational-age guidance and Swahili context
   line are verbatim. History is sent as chat turns instead of an inline "Recent
   conversation history" block. It is still capped at 6 turns, with no 24-hour expiry.
   The "ALERT: Danger sign keywords detected" context line is gone, because it was only
   used for the removed follow-up.
4. **Declined consent.** Zeya deactivated the user and ignored them afterwards. Now
   `consent_declined` is recorded and the next message gets the consent question again,
   with the same wording as before. It is cleared if they later say YES.
5. **People who never consented are left out of the export.** Zeya's export kept their
   logged messages, such as consent-step replies from people who then declined. The
   adapter drops every row for participants whose latest data lacks
   `consent_given: true`.
6. **`response_time_ms` is measured differently.** Zeya timed from webhook processing
   to after both WhatsApp sends, so it included WhatsApp API latency and, on danger
   turns, the follow-up Gemini call. OCS-era values are the gap between the stored
   human and AI message timestamps, so the two eras are not directly comparable.
7. **Messages with no text.** Zeya ignored them (`if not message.text: return`). In
   OCS they reach the pipeline: an empty message at the name step asks for the name
   again, and voice notes may be transcribed by OCS and then gated like any text.
   Check the channel's media settings at deploy time.
8. **Save-contact tip in the welcome.** WhatsApp shows the bot's number, not "Zeya",
   until Meta approves a display name. The welcome adds one paragraph before the
   consent question: *Tip: save this number in your contacts as "Zeya" so you can find
   me easily.* (Swahili: *Kidokezo: hifadhi nambari hii kwenye anwani zako kama "Zeya"
   ili unipate kwa urahisi.*). The rest of the welcome is unchanged.
9. **National emergency numbers instead of Migori facilities.** The emergency message
   keeps Zeya's header and footer but lists 999 or 112, 922 and 1199 instead of five
   Migori facilities. See [Emergency numbers](#emergency-numbers).
10. **The prompt says "Kenya", not "rural Kenya".** Both occurrences changed, because
    ZEYA is open to women anywhere in Kenya. The rest of the prompt is verbatim.
11. **Only trial participants are exported.** Anyone in Kenya can use ZEYA.
    `seed_participants.py` marks people imported from the trial's enrolment list with
    `study_participant: true`, and the export adapter keeps only those. Someone who
    starts using ZEYA on her own is never in the study export, even if she consents.

## Study data continuity

- **Existing transcripts are not migrated.** The Zeya database and
  `/api/v1/analytics/export/*` stay running, read-only, until the study closes.
- **New transcripts:** `ocs/export_adapter.py` converts the OCS export to Zeya's exact
  9 columns and value formats:
  - Danger flags and keywords go on the outgoing row only, from gate tags. Keywords are
    in Zeya's category order; the tag holds the category because OCS exports tags
    alphabetically. Whitespace inside a keyword is collapsed and the tag is capped at
    100 characters (the OCS tag limit).
  - `gestational_age` is the age at message time.
  - `response_time_ms` is the AI time minus the human time (see change 6). Each reply is
    paired with the human message just before it in the same session. The export's
    `Trace ID` is not used, because OCS leaves it blank unless an external tracing
    provider is configured.
  - It drops what Zeya never logged: the first-contact turn, and registration replies.
    Registration answers are kept.
  - It drops participants who never consented (see change 5).
  - `study_id` uses Zeya's `STUDY_####` numbering, linked by `whatsapp_id`. OCS-only
    participants sort after every Zeya UUID, so existing IDs are unchanged. As in Zeya,
    numbering is over the unfiltered set.
- `ocs/seed_participants.py` imports existing users into OCS participant data, so they
  skip registration. It leaves out consented users whom an admin deactivated and lists
  them for a study-team decision. OCS exposes `participant.name` as `name`, so
  registration tracks the name step with `name_collected`.
- **WhatsApp identity (OCS ADR-0043).** Meta now sends a business-scoped user ID
  (BSUID, e.g. `KE.1123493676705328`), and OCS keys new WhatsApp participants by it,
  not by phone. The phone is kept on `participant.remote_id`, which the export does not
  include. What this means for Zeya:
  - Imported participants keep the phone as identifier. OCS finds them by an exact
    match against Meta's `wa_id` (digits only), so the seed writes digits only.
  - **Import before any seeded user messages the OCS number.** Otherwise OCS creates
    a BSUID participant first. The oldest matching participant wins, so the imported
    one, with consent and gestational age, would be ignored and she would register again.
  - The export adapter links only phone identifiers to Zeya users. BSUID participants
    are new to the study and get new `STUDY_####` ids.

## Testing

| Suite | Command | What it proves |
|---|---|---|
| Unit (pinned sandbox) | `make test-ocs` | parity, per-pattern, bilingual routing, registration, emergency text, graph structure, export, drift, seeding |
| Unit (real OCS sandbox) | `OCS_SOURCE=<checkout> make test-ocs` | the same, run in OCS's `RestrictedPythonExecutionMixin` |
| Engine | `DATABASE_URL=… make test-ocs-engine OCS_SOURCE=<checkout>` | pipeline validates; 16 danger messages → emergency with 0 LLM calls; SAFE → exactly one LLM call with the Zeya prompt and context; drift check passes on what OCS stores |

At the time of writing: 298 passed, in
both sandbox modes; 26 passed in the engine suite against a throwaway
`pgvector/pgvector:pg16` database. Install with `pip install -r ocs/requirements-dev.txt`.

## Rollout

1. Call the emergency numbers and fill in the call log (check above).
2. On the instance: add the Gemini provider and the `gemini-3-flash-preview` custom
   model. Create the chatbot and pipeline. Restrict roles as in rule 3.
3. Build with the instance's ids:
   `python -m ocs.build_pipeline --llm-provider-id N --llm-provider-model-id M > deploy.json`.
   Load it into the pipeline (`POST /a/evarest/pipelines/data/<id>/`). Publish a version.
4. Import `seed_participants.py` output **before step 5** (see WhatsApp identity
   above). Test on the web channel with the corpus in
   `ocs/tests/danger_corpus.py`. Run
   `python -m ocs.check_drift live.json --llm-provider-id N --llm-provider-model-id M`.
   The expected ids are required, so a model switched in the UI shows up as drift.
5. Move the WhatsApp number to OCS and switch Zeya's webhook off at the same time.
   Record the date in the study log with the methodological changes above. Keep the
   Zeya backend up for export only.

### WhatsApp findings (2026-10-16, openchatstudio.co.ke)

- Meta's +1 555 test numbers cannot be added as an OCS channel.
  `WhatsappChannelForm.clean_number` requires `phonenumbers.is_valid_number`, and 555
  is not a valid US area code. Use a real number.
- The webhook URL that the channel dialog shows uses `localhost:8000` because the
  instance's site domain is not set. The real one is
  `https://openchatstudio.co.ke/channels/whatsapp/meta/incoming_message`.
- WhatsApp location messages reach the pipeline as empty text, so nearest-facility
  lookup cannot use a shared location.
- First test: OCS generated all 9 replies, but 2 registration replies (the welcome and
  the name question) did not arrive on the phone. Not yet explained. Check Meta's
  delivery status before recruitment, because a lost welcome means no consent question.
