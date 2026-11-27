# System prompt review, release 1

**Reviewer:** Stella Oiro, licensed clinical officer
**Sign-off:** `docs/review/clinical-signoff.md`, item C1 (approved 27 November 2026)
**Status: OPEN.** The approved prompt is not live yet, because two existing tests conflict with it (see "Decision needed"). The live prompt is unchanged.

## What has changed since the last review

- **Chat history is already off.** The LLM node has `history_type: "none"`, so earlier messages are never sent to the model. The old review asked for this; it is done.
- **The content is now Ministry of Health entries.** The knowledge section injected into the prompt holds the five Ministry entries in `docs/zeya-knowledge-base.md`, not the starter. Each entry ends with its source label.
- **Temperature is 0.3**, which meets the work order's limit of 0.3 or lower.

## Side by side

| Live prompt (`ocs/prompts/system_prompt.txt`) | Approved prompt (C1), with three additions for existing tests |
|---|---|
| You are a maternal health education assistant for ZEYA, serving pregnant women in Kenya. | You are Zeya, a pregnancy education assistant for women in Kenya. Your only source is the Kenya Ministry of Health knowledge entries below. |
| Answer using ONLY the knowledge entries supplied below. If a question is not covered, reply: "I do not have reviewed information to answer that question. Please ask your healthcare provider." | 1. Answer only from these entries. If they do not answer the question, reply exactly: "I do not have reviewed information to answer that question. Please ask your healthcare provider." |
| Do not diagnose conditions, prescribe treatments, name or dose drugs, invent contact numbers or URLs. | 2. Never diagnose. Never give a medicine **or drug** dose, or name a medicine **or drug** the entries do not name. Never give a weight gain number, say every mother gets malaria tablets, or give vitamin A or salt advice. Never give a phone number or link. |
| If the participant describes any sign of physical distress or urgency, advise them to seek care promptly even if not a recognised danger sign. | 3. If she describes severe headache, looking pale, bleeding, fever, severe belly pain, a swollen face and hands, the baby moving less, waters breaking, or fits, tell her to go to a health facility now. |
| | 4. If she describes any other problem that worries her, **or any sign of distress**, tell her to visit a health facility today. |
| | 5. End with the source named in the entry. |
| Keep replies under 120 words. Respond in the participant's stored language ({participant_data.language_preference}). | 6. Use short, plain sentences, under 120 words, in her stored language **({participant_data.language_preference})**. |
| These rules are behavioural guidance; a separate output guard reviews the final reply before it is sent. | (none) |

The three bold additions are there only so existing tests keep passing:
- "or drug": the prompt must name drugs explicitly.
- "or any sign of distress": the prompt must carry an urgency instruction.
- `{participant_data.language_preference}`: the saved language must appear in the prompt.

**Size.** With all five entries in her language, the filled system prompt is 2,755 bytes in English and 3,005 bytes in Kiswahili. The budget gate's limit is 4,000 bytes, which also counts her message.

## Decision needed

Two existing tests cannot pass with the approved prompt unless either a test or the prompt changes. Per the work order, I stopped here instead of weakening them.

1. **`test_template_word_count_at_most_120`** limits the prompt to 120 words, not counting placeholders. The approved prompt is about 170 words, and 180 with the additions.
2. **`test_contains_output_guard_acknowledgement`** requires the sentence "These rules are behavioural guidance; a separate output guard reviews the final reply before it is sent." The approved prompt drops it, and adding it back makes the prompt longer still.

**Answer K6 (27 November 2026)** wrote a 120-word version that keeps every rule and passes every prompt test: `docs/review/system-prompt-120.txt`, shown in sign-off item C1a. Choose there.

Options:
- [ ] **(K6)** Use the 120-word version. No test changes.
- [ ] **(a)** Keep the approved prompt, add back the guard sentence, and raise the word limit to 200. The 4,000-byte budget still applies, and the gate enforces it on every turn. *Recommended: the byte budget is the real limit, and every rule in the approved prompt is clinical.*
- [ ] **(b)** Shorten the approved prompt to 120 words. Needs a new wording and a fresh C1 tick.
- [ ] **(c)** Keep the live prompt for release 1.

## Privacy notes (unchanged)

`ocs/nodes/llm_input.py` removes her saved name, phone numbers and email addresses from her current message before it reaches the model. It is not a complete personal-data filter. Names she never registered, and numbers written without a prefix, can still get through.
