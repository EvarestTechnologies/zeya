# System prompt review — ZEYA #24

**Status: English draft for clinical and language review. Not approved for public deployment.**

The Swahili translation of the absent-source referral phrase and the response-language instruction below requires fluent-speaker review before use with Swahili-preference participants. No clinical sign-off is implied by this draft.

---

## Prompt text (English starter)

```
You are a maternal health education assistant for ZEYA, serving pregnant women in Kenya.

Answer using ONLY the knowledge entries supplied below. If a question is not covered by the supplied entries, reply: "I do not have reviewed information to answer that question. Please ask your healthcare provider." Do not diagnose conditions, prescribe treatments, state drug doses, or invent contact numbers.

{temp_state.kb_section}

{temp_state.llm_context}

Keep replies under 120 words. Respond in the participant's stored language. These rules are behavioural guidance; a separate output guard reviews the final reply before it is sent.
```

Word count (static template text, placeholders excluded): **90 words** (target ≤120).

---

## Scope and design decisions

### KB-only sourcing
The model is explicitly restricted to the content in `{temp_state.kb_section}`, which is populated each turn by the #22 KB context node with `include_pending=False` (approved entries only by default). If no relevant KB entry is selected, the node upstream sets `kb_available=False` and the parent pipeline routes to a fixed referral before the LLM is called, so the LLM rarely receives an empty section.

The absent-source fallback phrase ("I do not have reviewed information…") is included as a defence-in-depth instruction for cases where the KB section is present but does not answer the specific question asked.

### No diagnosis / prescription / dose / contacts
The prohibition is explicit in the system message. Enforcement at runtime is not guaranteed by the prompt alone — the #25 output guard applies conservative regex checks and blocks non-compliant output with a fixed referral. Claiming prompt-level clinical safety would be false; both layers are needed.

### Stored language
`{temp_state.llm_context}` already contains "User prefers Swahili. Respond in Swahili." when `language_preference == "sw"` (set by the registration node). The system prompt adds a general "respond in the participant's stored language" instruction as a belt-and-suspenders measure; the registration-node context remains the primary language signal.

**Pending review**: the phrase "participant's stored language" should be verified by a fluent Swahili speaker to ensure the model reliably switches. An alternative is to include the explicit Swahili instruction string in the prompt template directly; this is a decision for the language reviewer and parent.

### Output guard acknowledgement
"These rules are behavioural guidance; a separate output guard reviews the final reply before it is sent." — this sentence exists so reviewers, operators and evaluators understand the two-layer architecture. It is not visible to participants.

### 120-word response target
The existing pipeline used 200 words. 120 words is a tighter target for mobile readability; the output guard (#25) applies a deterministic safe-truncation treatment for responses that exceed this target.

---

## Privacy: LLM input sanitisation (llm_input.py)

The `llm_input.py` node sanitises the **current message only** before it reaches the model. It is **not** a universal PII filter.

### What is sanitised

| PII type | Coverage | Action | Placeholder |
|---|---|---|---|
| Participant name | Exact saved value in `participant_data.name`, whole-word, case-insensitive | Removed | `[name]` |
| Phone numbers | Generic `+CC` international (any `+` followed by 1–3 digit country code, then ≥6 digit positions with space/hyphen/paren separators); Kenya-local bare prefixes `254`, `07`, `01` without `+`; contiguous, spaced, hyphenated, fullwidth digits, zero-width insertions | Removed | `[phone]` |
| Email addresses | `local-part@domain.tld` pattern | Removed | `[email]` |

Fullwidth ASCII digits (U+FF10–U+FF19) are normalised to ASCII before matching. Zero-width characters (U+200B, U+200C, U+200D, U+FEFF, U+00AD) are stripped before matching.

**Pregnancy-week numbers, dates, and all other text are preserved.** The phone pattern requires at least 7 further digit positions after the prefix with only space/hyphen separators allowed; `"07 weeks"`, `"07/08/2025"`, and short codes do not match.

### Known limitations (explicit, not hidden)

- **Unknown names**: only the exact value stored in `participant_data.name` is matched. Names shared verbally but not registered, names corrected by an operator after registration, common words that happen to equal the saved name, and very short names (single characters) may cause under- or over-removal. This node makes no claim to remove all participant identifiers.
- **Phone coverage**: generic `+CC` branch covers any number starting with `+` followed by a recognisable digit run (≥6 positions after country code, ≥8 total digits). Kenya-local bare prefixes (`254`, `07`, `01`) are covered separately. Numbers written without any dialling prefix (e.g. a bare 7-digit local number) are not matched.
- **Email coverage**: basic RFC-5321 local-part pattern. Unusual quoted local parts are not covered.
- **Email policy**: the email pattern is included as a defensive measure. No claim is made that emails are routinely shared in this context; the limitation is acknowledged.
- **Historical turns**: this node sanitises only the current input string. It has no effect on prior messages already stored in LLM node history. See §History below.

---

## History privacy concern and builder requirement

**Risk:** The pipeline currently uses `history_type: "node"` with `max_history_length: 12` on the LLM node. Prior user messages are replayed verbatim to the model. Sanitising the current turn has no effect on those historical messages; if a participant included their name or phone in an earlier turn, that text flows to the model unsanitised.

**Required strategy:** Set `history_type: "none"` on the LLM node.

**Source evidence (OCS engine, HEAD 45aac42):**

| Behaviour | File | Lines |
|---|---|---|
| `PipelineChatHistoryTypes.NONE = "none"` defined | `apps/pipelines/models.py` | 831 |
| `history_is_disabled` returns True for NONE | `apps/pipelines/nodes/mixins.py` | 222–223 |
| `get_history()` returns `[]` when disabled | `apps/pipelines/nodes/mixins.py` | 240–241 |
| `build_history_middleware()` returns None | `apps/pipelines/nodes/mixins.py` | 266–267 |
| `save_history()` skips persistence | `apps/pipelines/nodes/mixins.py` | 295–296 |
| Field on `LLMResponseWithPrompt` | `apps/pipelines/nodes/nodes.py` | 369 |

This is a **parent-controlled pipeline parameter**. This worker does not edit the shared pipeline file or builder. The parent must change `"history_type": "node"` → `"history_type": "none"` and remove `"max_history_length": 12` from the LLM node config in the pipeline JSON. The requirement for real OCS engine integration tests proving no history turns are replayed is a separate parent deliverable.

**Tradeoff:** With no history the model does not remember previous questions within a session. For ZEYA's Q&A pattern this is acceptable because:
- Gestational-age and trimester guidance context is re-injected every turn via `{temp_state.llm_context}`
- KB entries relevant to the current question are re-selected every turn via `{temp_state.kb_section}`
- Each antenatal education question is typically self-contained

---

## What this draft does NOT cover

- Kiswahili translation of the absent-source referral phrase: **pending fluent-speaker review**
- Clinical validation of the KB entries themselves: **pending clinical review** (covered by #22)
- Coverage completeness: the five-entry starter KB covers general ANC purpose, records, food variety, food safety, and birth preparation only. Questions outside this scope will return the absent-source referral. This is by design; the original ~60-topic coverage requires the full KB to be authored and reviewed.
- The output guard allowlist for URLs/phone numbers: **covered in #25**
- Sanitisation of numbers written without any dialling prefix (bare local numbers with no country code or Kenya-local prefix): not matched; see limitations above
- Real history-integration proof: parent integrates `history_type=none` and executes OCS engine tests
