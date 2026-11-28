# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

Zeya is a WhatsApp antenatal education service for pregnant women in Kenya, in English and Kiswahili. It runs as a pipeline on Dimagi's Open Chat Studio (OCS), self-hosted by Evarest Technologies at openchatstudio.co.ke. Release 1 is used with **synthetic test participants only**. Real participants need ethics approval, a NACOSTI licence, ODPC registration and a DPIA first.

The live product is the OCS pipeline under `ocs/`. The FastAPI backend under `backend/` is the earlier version. It still calls Google Gemini, whose terms bar medical advice, so it must not serve participants (#30). Two of its modules are kept as parity sources for the pipeline (see "Parity with the legacy backend").

## Rules that apply to every change

1. **One clinical source.** Everything Zeya can send a participant traces to a page in the Kenya Ministry of Health documents: the MCH Handbook 2020 (HB), the national guidelines 2024 (NG24) and the Basic Obstetric Protocols 2026 (BOP).
   - **Clinical source of truth:** `docs/clinical/moh-knowledge-base.md`.
   - **Not runtime sources:** WHO material, and NG12 (superseded).
   - **Gaps:** go in `docs/clinical/gaps.md`. Never fill them from general knowledge.
2. **Nothing goes live without a tick** on the signed sheet `docs/review/clinical-signoff.md`. A comment, commit message or "owner approved" is not sign-off. Unapproved content stays `Review-state: pending`.
3. **No AI on the emergency, access or media paths.** Danger signs, non-testers and attachments get fixed replies.
4. **No drug names, doses or diagnoses** in anything sent to a participant.
5. **Kiswahili is always a draft** until a fluent speaker and the clinical reviewer approve it.
6. **Naming.** Zeya is a product. Do not use event or audience names in code, prompts, participant text, tests, file names, branch names, commits or docs you add. Use "release 1" and "synthetic test participants".
7. **Privacy.**
   - No real participant data in tests, fixtures or commits.
   - No API keys.
   - No phone numbers in prompts.
   - Never add a phone number to the emergency reply or the output guard until it is ticked in section D of the sign-off sheet.
8. **Do not deploy or change the live OCS instance** from this repository. Raymond publishes.

## Commands

```bash
make test-ocs        # OCS node, pipeline, parity and evaluation tests (pinned RestrictedPython sandbox)
make lint-ocs        # ruff check and format check for ocs/
make test-ocs-engine OCS_SOURCE=/path/to/open-chat-studio   # real OCS engine tests; needs the pinned checkout (9f5c254) and its test database

python -m ocs.build_pipeline --write               # regenerate ocs/pipeline/zeya_pipeline.json after any node, prompt, card or knowledge change
python -m ocs.build_pipeline --rules-only --write  # regenerate the rules-only pipeline (no AI node, #26)
python -m ocs.check_drift live.json --llm-provider-id <id> --llm-provider-model-id <id>
python -m ocs.check_drift live.json --rules-only     # when the rules-only version is live
python -m ocs.seed_participants --zeya-users users.csv --out ocs_participants.csv

python -m ocs.eval.score_gate                      # danger gate on the 310-message corpus
python -m ocs.eval.score_heldout --details         # danger gate on held-out sets B to E
```

The legacy backend still has `make up`, `make test` and the rest (see `make help`), but those are not the release path.

## Pipeline

Built by `ocs/build_pipeline.py` from the node sources in `ocs/nodes/`, the knowledge entries, the answer cards and the prompt.

```
start -> danger_gate -> danger_router
  EMERGENCY -> emergency_response -> end                        (fixed reply, no AI; default route)
  SAFE -> access_gate -> access_router
    NOT_TESTER -> danger_question_line -> end                   (fixed reply, no AI; default route)
    MEDIA      -> danger_question_line -> end                   (fixed reply, no AI)
    OK -> registration -> registration_router
      REPLY -> danger_question_line -> end                      (onboarding)
      REGISTERED -> kb_context -> kb_router
        FALSE -> knowledge_referral -> danger_question_line -> end
        TRUE  -> answer_match -> answer_router
          CARD   -> output_guard -> attach_explainer -> danger_question_line -> end
          ASK_AI -> llm_input -> prompt_budget -> budget_router
            OVER_BUDGET -> knowledge_referral -> ...
            VALID -> llm -> output_guard -> attach_explainer -> danger_question_line -> end
```

| Node | What it does |
|---|---|
| `danger_gate` | 152 signed-off patterns in 9 categories (bleeding, headache_vision, pallor_anaemia, fever, fetal_movement, abdominal_pain, water_breaking, convulsions, swelling). It also has a question and history check and typo tolerance. It sets `danger_route`, `danger_categories`, `danger_keywords` and `danger_question`. |
| `emergency_response` | Fixed reply listing 922, 999 or 112, and the four Migori County ambulance numbers. |
| `access_gate` | Only participants with `approved_tester: true` get through. Attachments get a fixed reply. |
| `registration` | Language choice, consent, name and weeks. It sets `language_preference` and the NG24 p107 week context. |
| `kb_context` | Approved Ministry entries for her language and week (`docs/zeya-knowledge-base.md`). |
| `answer_match` | Matches her question to an approved card in `docs/answer-cards.yaml` by word overlap. |
| `llm_input`, `prompt_budget` | Strip her name and phone numbers from her message, and cap the prompt at 4,000 bytes. Chat history is off (`history_type: none`). |
| `llm` | The AI model, temperature 0.3, no tools. Planned provider: Groq `openai/gpt-oss-120b` with zero data retention; the provider is set when the bot is published. Prompt: `ocs/prompts/system_prompt.txt` (120 words). |
| `output_guard` | Blocks drug names, doses, diagnoses, links and phone numbers (`docs/output-policy.json`). |
| `attach_explainer` | Sends `media/explainers/zeya_danger_signs.mp4` with the danger_signs card. It downloads the clip from `main`. |
| `danger_question_line` | Puts a fixed "go to a health facility now" line before the reply when `danger_question` is set. |

**OCS node limits:**
- Imports are limited to `json`, `re`, `datetime`, `time` and `random`, and they must sit inside `main`.
- HTTP downloads are capped at 1 MB on some releases.
- Static routers turn Python booleans into "TRUE" and "FALSE".
- The `abort_with_message` helper asks an AI to write its reply. Never use it on a safety path.

## Parity with the legacy backend

`ocs/nodes/danger_gate.py` and `backend/app/services/danger_signs.py` must hold the same patterns, rules and typo vocabulary. `ocs/tests/test_danger_gate_parity.py` enforces this, with one example per pattern in `ocs/tests/danger_corpus.py`. Change both files together, ideally by generating both from the reviewed draft `ocs/eval/proposed_danger_gate.py`.

The registration tests also read the welcome messages and week context from `backend/app/services/conversation_handler.py` and `ai_engine.py`, so change those together too.

## Evaluation

- **Test sets:**
  - Corpus: `ocs/tests/danger_eval_corpus.csv`, 310 messages.
  - Held-out sets: `ocs/eval/heldout.py`. Set B. Set C, which was used to choose the near-miss rules. Set D, untuned: the fair test overall. Set E, untuned, written for A15 and A16 (history versus now, typo misreads).
- **Results:** `docs/scores.md` and section 0 of `docs/review/danger-gate.md`.
- **Reporting:** always report held-out recall next to tuned recall.
- **New patterns:** write a new held-out set before tuning them, then score them on it.

## Key documents

- **Work order:** `docs/work-orders/2026-11-27-guideline-alignment.md`, with answers in `docs/work-orders/open-items-answers-2026-11-27.md`
- **Release 1 walkthrough and troubleshooting:** `docs/runbook-release-1.md`
- **Security checklist:** `docs/security-checklist.md`
- **Participant-facing documents:**
  - `docs/privacy-policy.md` (draft, pending legal review)
  - `docs/intended-use.md`
  - `docs/sources.md`
- **Research:** `docs/research/2026-11-27-content-source-and-policy.md`, covering the law, licences and the knowledge base check
