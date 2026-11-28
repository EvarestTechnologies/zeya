# Zeya security checklist

Issue #33, with the hardening items from #29. Each line has an owner. Tick a line only when it has been checked on the live system, not just planned.

**Owners:**
- **Raymond:** OCS team and server.
- **Stella:** legal, clinical and Meta.
- **Repo:** done in this repository, and verified by tests or review.

## Before release 1 (synthetic test participants)

### OCS team settings

| Check | Owner | Done |
|---|---|---|
| Two-factor login required for the whole team | Raymond | [ ] |
| Pipeline edit rights for two or three people only. Study staff get Chat Viewer and Annotation Reviewer only. | Raymond | [ ] |
| Remove the unverified Evarest OpenAI provider and the broken Zeya Gemini provider | Raymond | [ ] |
| Groq provider set up with zero data retention switched on in the Groq console, with a screenshot kept | Raymond | [ ] |
| Rotate any key or token that was ever shared in chat, email or a screenshot | Raymond | [ ] |
| Langfuse tracing off. Built-in tracing kept, with who can open traces limited. | Raymond | [ ] |
| Moderation auto-block off. It sends messages to an outside service and could block a mother describing an emergency. | Raymond | [ ] |
| Email notifications on for pipeline errors and provider refusals | Raymond | [ ] |
| Drift check run after every publish (`python -m ocs.check_drift …`), and `--rules-only` when that version is live | Raymond | [ ] |
| Each test participant has `approved_tester: true`; nobody else does | Raymond | [ ] |

### Server for openchatstudio.co.ke (#29)

OCS ships with unsafe defaults in `config/settings.py`. Check each one on the running server.

| Check | Owner | Done |
|---|---|---|
| Record the OCS version, the cloud, the country and who has SSH access (#46). The running image currently reports `OCS_VERSION=unknown`. | Raymond | [ ] |
| `DEBUG=False` | Raymond | [ ] |
| nginx drops unknown Host headers, because `ALLOWED_HOSTS` is `["*"]` in OCS | Raymond | [ ] |
| `RATE_LIMIT_ENFORCE=True` | Raymond | [ ] |
| `CRYPTOGRAPHY_SALT` set to a non-empty secret | Raymond | [ ] |
| Sentry unset, or set with `send_default_pii` off | Raymond | [ ] |
| Langfuse host unset, or sample rate 0 | Raymond | [ ] |
| Meta App Secret set on the WhatsApp provider, and a forged unsigned POST to the webhook is rejected | Raymond | [ ] |
| External port scan: only 443 open, plus 22 from a VPN. Postgres and Redis not reachable from outside, and Redis has a password. | Raymond | [ ] |
| Disk encryption on, TLS valid, OS patch schedule written down | Raymond | [ ] |
| Encrypted backups, with one restore actually tested | Raymond | [ ] |
| RestrictedPython 8.4 or later (CVE-2026-55830) | Raymond | [ ] |
| Know where WhatsApp voice notes and uploaded files are stored | Raymond | [ ] |
| Legacy FastAPI backend (`/api/v1/webhook`, Gemini) not running or reachable anywhere (#30) | Raymond | [ ] |

### Pipeline (verified in this repository)

| Check | Owner | Done |
|---|---|---|
| No AI on the emergency path: the emergency reply is fixed text, and the router defaults to EMERGENCY | Repo | [x] |
| Access gate: only `approved_tester: true` gets past; attachments get a fixed reply; the router defaults to NOT_TESTER (#21) | Repo | [x] |
| No name or phone number in the prompt: `llm_input` strips them from her message, and chat history is off | Repo | [x] |
| Output guard blocks drug names, doses, diagnoses, links and phone numbers. The allow-lists are empty on purpose. | Repo | [x] |
| The AI has no tools and no secrets in its prompt. Assume the prompt can leak. | Repo | [x] |
| A rules-only version with no AI node is ready to publish (#26) | Repo | [x] |
| A WhatsApp channel kill switch (the **Enabled** toggle) is documented in `docs/runbook-release-1.md` | Repo | [x] |
| A red-team pass with promptfoo on staging, in English, Kiswahili and Sheng (#32, #57) | Raymond | [ ] |

### Data

| Check | Owner | Done |
|---|---|---|
| Collect the minimum. Synthetic personas only in sessions, slides and recordings. | Stella | [ ] |
| Research exports only through the pseudonymised export adapter (`ocs/export_privacy.py`) | Raymond | [x] in code |
| Test deleting one participant, and record what else is removed. Langfuse traces are not removed by OCS. | Raymond | [ ] |

## Before any real participant

| Check | Owner | Done |
|---|---|---|
| ODPC registration (controller and processor), and notice to the Digital Health Agency within 7 days | Stella | [ ] |
| DPIA filed at least 60 days before the first enrolment | Stella | [ ] |
| Ethics approval, then a NACOSTI licence | Stella | [ ] |
| Licensed facility or county partner, and Digital Health Agency certification check | Stella | [ ] |
| Pharmacy and Poisons Board pre-submission query on the danger-sign function | Stella | [ ] |
| Written controller and processor agreement with Evarest; data processing agreement with Groq; transfer basis for Meta and Groq | Stella | [ ] |
| Meta business verification and display name | Stella | [ ] |
| Consent and under-18 route (#36) | Stella | [ ] |
| Retention schedule and a scheduled deletion job. OCS has no retention setting (#37). | Raymond | [ ] |
| Incident runbook: 72 hours to the ODPC, 48 hours to the Digital Health Agency, and who presses the kill switch (#38) | Stella | [ ] |
| A staffed human contact for Zeya, so the escalation line fully meets WhatsApp's policy (#39) | Stella | [ ] |
| Self-hosted model in Kenya, on a private network only, with an API key, hash-pinned weights and patching within days (#35) | Raymond | [ ] |

## Reporting a breach

1. Turn off **Enabled** on the WhatsApp channel.
2. Tell Stella and Raymond.
3. The controller notifies the ODPC within 72 hours (Data Protection Act s.43). A digital health solution also notifies the Digital Health Agency within 48 hours.

This is not legal advice. A Kenyan data protection lawyer must confirm the duties before real participants are enrolled.
