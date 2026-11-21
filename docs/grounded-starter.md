# Zeya grounded-starter integration

This document covers the full pipeline graph introduced in the grounded-starter integration, which connects the four component ports (KB context, answer cards, LLM input, output guard) into a single Zeya pipeline.

## Pipeline graph

```
start
  → danger_gate
    → danger_router
        EMERGENCY → emergency_response → end
        SAFE      → registration
                    → registration_router
                        REPLY      → end
                        REGISTERED → kb_context
                                      → kb_router
                                          FALSE → knowledge_referral → end
                                          TRUE  → answer_match
                                                  → answer_router
                                                      CARD   → output_guard → end
                                                      ASK_AI → llm_input
                                                               → prompt_budget
                                                                 → budget_router
                                                                     OVER_BUDGET → knowledge_referral → end
                                                                     VALID       → llm → output_guard → end
```

## Default build semantics (all content pending)

All five KB entries and answer cards are pending clinical and language review. The default approved-only build produces:

- `kb_context` bakes `KB_JSON = '[]'`
- At runtime: `kb_available = False`
- `kb_router` routes FALSE → `knowledge_referral` → end for every registered participant
- **No model is called** until entries pass review

The fixed referral messages are:

- **English:** "I do not have reviewed information to answer that question. Please ask your healthcare provider."
- **Swahili (DRAFT — pending fluent-speaker and clinical review):** "Sina taarifa iliyokaguliwa kujibu swali hilo. Tafadhali uliza mtoa huduma wako wa afya."

## Routing contracts

### kb_router

- Reads `temp_state.kb_available` (Python bool set by `kb_context`)
- OCS StaticRouter stringifies Python bools to `"TRUE"` / `"FALSE"`
- Keywords: `["FALSE", "TRUE"]`, default index 0
- **Default is FALSE (fail-closed):** missing or empty `kb_available` → referral, no model call

### answer_router

- Reads `temp_state.answer_route` (string `"CARD"` or `"ASK_AI"` set by `answer_match`)
- Keywords: `["CARD", "ASK_AI"]`, default index 1
- **Default is ASK_AI:** unknown `answer_route` falls to the LLM rather than returning an empty or wrong card

### budget_router (prompt-budget gate)

The `prompt_budget` CodeNode runs after `llm_input` on the ASK_AI path.  It measures the
**total UTF-8 bytes** that the LLM would receive in this turn and sets `budget_route` before
any model call is attempted.

**Budget definition (hard cap: 4000 bytes):**

| Component | Source |
|---|---|
| System prompt template text | `ocs/prompts/system_prompt.txt` (baked in at build time) |
| `{temp_state.kb_section}` | Substituted once with the KB entries selected by `kb_context` |
| `{temp_state.llm_context}` | Substituted once with the registration context block |
| `{participant_data.language_preference}` | Substituted once with the stored language code |
| Sanitised participant question | `input` arg to the node (output of `llm_input`) |

**One-pass substitution:** a single `re.sub` callback replaces all `{source.key}` tokens.
Text introduced by substituted values (e.g. KB content that contains `{…}` patterns) is
never re-interpreted.  This matches the actual OCS LLM node rendering behaviour.

**Routing:**
- `temp_state.budget_route = "VALID"` → total bytes ≤ 4000 → continues to `llm`
- `temp_state.budget_route = "OVER_BUDGET"` → total bytes > 4000, OR any required state
  is missing/invalid → routes to `knowledge_referral` (fixed reply, no model call)

**Fail-closed conditions (all route OVER_BUDGET):**
- `kb_section` absent from `temp_state` or not a string
- `llm_context` absent from `temp_state` or not a string
- `language_preference` absent or empty in `participant_data`
- Sanitised question is blank (empty string or whitespace only)
- Any over-budget payload regardless of which component contributes

**budget_router config:**
- Reads `temp_state.budget_route`
- Keywords: `["OVER_BUDGET", "VALID"]`, default index 0
- **Default is OVER_BUDGET (fail-closed):** any unexpected value routes to referral

**The direct `llm_input → llm` edge must NOT exist.**  `test_grounded_pipeline.py`
enforces this as a hard assertion.

**Node source is generated at build time** by `ocs/prompt_budget.render_prompt_budget_node()`.
The system prompt template is baked in as a Python string literal so the byte measurement
is always consistent with the LLM node's actual prompt.  Calling this function also validates
the template at build time, raising `ValueError` if it contains unsupported placeholders.

## Staging flag

Pending content can be included for synthetic testing without changing `review_status`:

```bash
# Build with pending content eligible (staging only):
python -m ocs.build_pipeline --write --include-pending

# Check drift against a staging deployment:
python -m ocs.check_drift live.json --llm-provider-id 7 --llm-provider-model-id 31 --include-pending
```

The staging flag adds an explicit `eligible=True` runtime flag to pending entries in the baked JSON. The runtime node (`kb_context`, `answer_match`) checks both `review_status` and `eligible` without relabelling pending content as approved.

A staging deployment must not be accepted by the default (approved-only) drift check; `test_staging_pipeline_drifts_from_default_check` enforces this.

## LLM node configuration (#24 Phase A)

```
temperature:    0.3   (conservative, KB-grounded responses)
history_type:   none  (historical messages carry PII; disabling is the only
                       supported way to prevent prior turns reaching the model)
prompt:         SYSTEM_PROMPT_FILE verbatim (OCS substitutes placeholders at runtime)
```

The system prompt template embeds `{temp_state.kb_section}` (KB content) and `{temp_state.llm_context}` (language/week context). These are OCS template variables substituted by the engine — not Python f-strings.

## Output guard (#25)

The `output_guard` node applies to both CARD-routed answers and AI-generated responses:

- Blocks drug names, dose patterns, diagnoses, invented contacts
- Finite phone allow-list (review-pending)
- Finite URL allow-list (review-pending)
- Returns a fixed referral on blocked output; tags `route:guard_blocked`

## UTF-8 budget

The KB context budget is enforced by exact UTF-8 byte count in `kb_context`, with `max_context_bytes=2000` by default. Separately, the mandatory `prompt_budget` node limits the complete rendered system prompt plus sanitised current human input to 4000 UTF-8 bytes. This is a byte cap, not a tokenizer-based token count or a model-provider token guarantee. Actual captured system/human messages were checked against the recorded byte count in the pinned OCS engine, including EN/SW 4000-byte admission, 4001-byte refusal, and multibyte input.

## Owned paths

| Path | Owner |
|------|-------|
| `ocs/build_pipeline.py` | Integration writer |
| `ocs/check_drift.py` | Integration writer |
| `ocs/nodes/knowledge_referral.py` | Integration writer |
| `ocs/tests/test_grounded_pipeline.py` | Integration writer |
| `ocs/tests/test_pipeline_structure.py` | Integration writer (new-graph assertions) |
| `ocs/tests/test_check_drift.py` | Integration writer (staging tests) |
| `ocs/integration/test_grounded_engine.py` | Integration writer |
| `docs/grounded-starter.md` | Integration writer |
| `ocs/integration/test_grounded_privacy_engine.py` | Privacy verifier (do not edit) |
| Component modules (`knowledge.py`, `answer_cards.py`, etc.) | Component workers (do not edit) |

## Executed verification and release boundary

The final local candidate passed 1263 unit/sandbox tests and all 121 real-engine integration tests against OCS commit `9f5c25476555ff74a167c6a14832ce798832847a`. The integration suite includes 62 grounded-graph cases, 38 emergency/onboarding cases, 9 privacy cases and 12 completed-evaluation cases. These are observed results for this candidate, not promised counts for later revisions. OCS lint and format checks passed.

The graph tests exercise default approved-only referral and explicit synthetic staging CARD/ASK_AI paths, exact bilingual guard fallbacks, seeded-history exclusion, sanitised captured input, saved language/week context, prompt-byte boundaries and staging/default drift. Model responses are supplied by a captured FakeLlm; no real provider call, clinician approval or handset delivery is established by these tests. The isolated test database/container was removed and independently checked absent.

From the repository root, use `make test-ocs PYTHON=/path/to/venv/bin/python` and `make lint-ocs PYTHON=/path/to/venv/bin/python`. Set `OCS_SOURCE=/path/to/pinned/open-chat-studio` for the pinned sandbox probe. `make test-ocs-engine OCS_SOURCE=/path/to/pinned/open-chat-studio` additionally requires a prepared isolated OCS test database and supported test settings; never point it at a production database. `ZEYA_G2_EVIDENCE_DIR` can select an isolated artifact directory; otherwise the tests allocate a temporary directory.

All real content remains pending. Five starter topics do not complete the original approximately 60-card ambition. Clinical and fluent-language review, verified contact approval, expanded content and held-out evaluation, hosted deployment/drift checks, messaging-template approval and handset tests remain separate release work. Merging this source does not publish a bot version or change WhatsApp.
