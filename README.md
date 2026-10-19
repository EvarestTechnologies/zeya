# ZEYA

A pregnancy companion on WhatsApp for women in Kenya, built by
[Evarest Technologies](https://evarestke.com/zeya/) on
[Open Chat Studio](https://github.com/dimagi/open-chat-studio).

ZEYA answers questions about pregnancy in English and Kiswahili, using World Health
Organization and Kenya Ministry of Health guidelines, and fits each answer to the
woman's week of pregnancy. When a message describes a danger sign, she gets an
emergency message at once, before any AI runs.

**Status:** preparing for a randomised controlled trial in Migori County. Not yet open
to users.

## How it works

Every WhatsApp message goes through one Open Chat Studio pipeline:

```
WhatsApp message
   └─> danger-sign gate (Python node, 39 fixed rules for 8 danger signs, English and Kiswahili)
          ├─ danger sign ─> emergency message (no AI): 999 or 112, ambulance 922, Kenya Red Cross 1199
          └─ safe ─> registration (consent, name, weeks of pregnancy)
                        └─ registered ─> Gemini, with her week of pregnancy as context
```

The eight danger signs are bleeding, severe headache or blurred vision, fever,
reduced fetal movement, severe abdominal pain, water breaking, convulsions and
swelling.

Open Chat Studio provides the WhatsApp channel, sessions, history, participants and
the transcript export. The safety-critical and study-critical logic lives in this
repository.

## Safety by design

- **Danger signs never wait for AI.** The gate is fixed rules in code, and the
  emergency branch has no model call.
- **The pipeline is generated from this repository** (`ocs/build_pipeline.py`).
  Nobody edits the danger rules in the Open Chat Studio screen.
- **Tested under Open Chat Studio's sandbox rules.** `make test-ocs` runs 307 tests
  with a copy of Open Chat Studio's RestrictedPython sandbox, or with the real one
  when `OCS_SOURCE` points to a checkout.
- **Drift check.** `ocs/check_drift.py` compares the live pipeline with the
  repository before each release.
- **Every behaviour change is logged** for the study, with its reason, in
  [docs/ocs-migration.md](docs/ocs-migration.md).

## Research use

Anyone in Kenya can use ZEYA. Only women enrolled by the study team, imported with
`ocs/seed_participants.py`, are trial participants. Everyone else gets a general
welcome and never appears in the study export. `ocs/export_adapter.py` converts Open
Chat Studio transcripts into the study's columns, with study numbers instead of names
or phone numbers.

## Repository

```
ocs/                   The live system on Open Chat Studio
  nodes/               Python nodes: danger_gate, emergency_response, registration
  prompts/             The system prompt
  pipeline/            The generated pipeline (zeya_pipeline.json)
  build_pipeline.py    Builds the pipeline from the nodes and prompt
  check_drift.py       Compares a live pipeline with the repository
  export_adapter.py    Open Chat Studio export to the study's columns
  seed_participants.py Trial enrolment list to an Open Chat Studio import
  tests/, integration/ Unit, parity and engine tests
docs/
  ocs-migration.md     Design, decisions and the study's methodological changes
  privacy-policy.md    ZEYA privacy policy
  whatsapp-scale-up.md Meta verification, display name and message templates
website/zeya/          The evarestke.com/zeya page
backend/, frontend/    The original FastAPI and React app, kept for exporting
                       data collected before the move to Open Chat Studio
```

## Development

```bash
git clone https://github.com/EvarestTechnologies/zeya.git
cd zeya
python3 -m venv .venv && .venv/bin/pip install -r ocs/requirements-dev.txt
make test-ocs PYTHON=.venv/bin/python   # 307 tests
make lint-ocs PYTHON=.venv/bin/python
```

The engine suite runs the pipeline in a real Open Chat Studio checkout with a
database:

```bash
DATABASE_URL=... make test-ocs-engine OCS_SOURCE=/path/to/open-chat-studio
```

To deploy, build the pipeline with the instance's provider and model ids, load it,
run the drift check and publish a version. The steps are in
[docs/ocs-migration.md](docs/ocs-migration.md), under "Rollout":

```bash
python -m ocs.build_pipeline --llm-provider-id N --llm-provider-model-id M > deploy.json
python -m ocs.check_drift live.json --llm-provider-id N --llm-provider-model-id M
```

### The original app

`backend/` and `frontend/` are the FastAPI, PostgreSQL, Redis and React app that ran
ZEYA before Open Chat Studio. They stay available for exporting earlier data. See
[CLAUDE.md](CLAUDE.md) for its commands (`make up`, `make migrate`, `make test`).

## Privacy

See the [ZEYA privacy policy](docs/privacy-policy.md). Contact:
contact@evarestke.com.

## License

Copyright 2026 Evarest Technologies Ltd. Licensed under the
[Apache License, Version 2.0](LICENSE).
