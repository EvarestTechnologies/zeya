# Zeya release 1 walkthrough runbook

For the person showing Zeya live on WhatsApp, with synthetic test participants only. Issue #34.

Every message and reply below was checked on 28 November 2026 by running it through the built pipeline's own nodes: danger gate, access gate, registration, knowledge, card matcher, output guard, clip and fixed lines. The model's answer was stubbed. The hosted bot has not been tested on a phone yet. Do the full rehearsal at the end before showing it to anyone.

---

## 1. Before the session

| Check | How | Who |
|---|---|---|
| PRs #62 and #63 merged; normal pipeline published as a new OCS version | OCS, Pipelines, Publish | Raymond |
| Live pipeline matches the repository | `python -m ocs.check_drift live.json --llm-provider-id <id> --llm-provider-model-id <id>` prints `OK` | Raymond |
| Rules-only version ready to publish | `ocs/pipeline/zeya_pipeline_rules_only.json` loaded as a draft (section 4) | Raymond |
| Test phones are approved testers | each test participant has `approved_tester: true` in OCS participant data. Without it, the phone gets the "being tested" reply | Raymond |
| One fresh tester for onboarding | a tester with only `approved_tester: true`, no other data | Raymond |
| One registered tester ("Akinyi") | Kiswahili, 28 weeks, registration complete | Raymond |
| One number that is **not** a tester | any phone not in OCS participants, or one without the flag | Stella |
| Danger-signs clip downloads | open `https://raw.githubusercontent.com/EvarestTechnologies/zeya/main/media/explainers/zeya_danger_signs.mp4` in a browser; a 47-second video plays | Stella |
| Backup recording of a full run | screen recording on the laptop and on a USB stick | Stella |
| Phone mirrored to the screen; OCS open in tabs | tabs in order: pipeline, session, trace, evaluations, versions, dashboard | Stella |

Use synthetic personas only. Never show a real phone number on screen.

---

## 2. The mother's side

Send each message exactly as written. "Starts with" means the reply begins with that text.

### Step 1. Onboarding (fresh tester)

| She sends | Zeya replies |
|---|---|
| `Habari` | "Please choose your language / Tafadhali chagua lugha yako: 1. English 2. Kiswahili" |
| `2` | Starts with "Karibu ZEYA! Niko hapa kukusaidia…", says the information is "kulingana na machapisho ya Wizara ya Afya ya Kenya", gives the privacy link, and asks for consent (NDIYO or HAPANA) |
| `NDIYO` | "Asante! Jina lako ni nani?" |
| `Akinyi` | "Nimefurahi kukutana nawe, Akinyi! Una wiki ngapi za ujauzito?…" |
| `28` | Starts with "Umesajiliwa! Una wiki 28 za ujauzito." and gives the expected date of birth |

**Say:** consent comes first, in her language. **Point at:** the participant data in OCS.

### Step 2. An approved answer card (registered tester)

| She sends | Zeya replies |
|---|---|
| `Nikule nini nikiwa na mimba?` | Starts with "Kula angalau makundi 5 kati ya makundi 10 ya vyakula kila siku…" and ends "Chanzo: Kitabu cha Afya ya Mama na Mtoto, Wizara ya Afya." |

**Say:** this answer is the Mother and Child Health Handbook's wording, approved by a clinical officer. The AI did not write it. **Point at:** the message tag for the card route.

### Step 3. A question no card covers

| She sends | Zeya replies |
|---|---|
| `Nifanye nini ili mtoto akue vizuri tumboni?` | The AI answers, using only the Ministry entries in Zeya, and ends with the source |

**Say:** the AI answers only from Ministry of Health entries, and a rule checks its answer before it is sent. **Point at:** the LLM node and the output guard in the trace.

If the AI provider is down, she gets the fixed reply in section 4 instead.

### Step 4. Danger signs, with the clip

| She sends | Zeya replies |
|---|---|
| `Dalili za hatari ni zipi?` | The danger-signs card ("Dalili za hatari wakati wa ujauzito: maumivu makali ya kichwa, kuonekana kupauka…"), **plus the 47-second clip** |

**Say:** the clip is drawn from page 14 of the handbook. It is sent by a fixed rule, not chosen by the AI.

### Step 5. An emergency

| She sends | Zeya replies |
|---|---|
| `Nina homa na kichwa kinauma sana` | Starts with "DHARURA: Hii inaweza kuwa dalili ya hatari…" and lists 922 (bila malipo), 999 au 112, and the four Migori County ambulance numbers |

**Say:** the emergency reply arrives at once, and no AI was involved. **Point at:** the trace (section 3, step 9).

### Step 6. A photo

| She sends | Zeya replies |
|---|---|
| any photo | "Kwa sasa ninaweza kusoma ujumbe wa maandishi pekee. Tafadhali andika swali lako kwa maneno." |

**Say:** the photo never reached the AI.

### Optional steps

| From | She sends | Zeya replies | What it shows |
|---|---|---|---|
| a number that is not a tester | `Habari` | "Zeya is being tested and is not open to the public yet…", in English then Kiswahili | only approved testers get through |
| a number that is not a tester | `Nina homa na kichwa kinauma sana` | the emergency reply, in English | emergencies are answered for everyone |
| registered tester | `Dalili za kutoka damu ni zipi?` | first "Kama hili linakutokea sasa, nenda kituo cha afya sasa hivi…" with the numbers, then the danger-signs card and the clip | a question about a danger sign still gets the "go now" line |

---

## 3. Under the hood

| # | Show | Say |
|---|---|---|
| 7 | The pipeline canvas | Every message passes rules first: danger gate, then access gate, then registration. The AI is one box near the end, with a rule check after it. |
| 8 | The session | Every reply carries a route tag: `route:access_ok`, the card route, `danger_sign:*`, `explainer_clip:danger_signs`, `danger_question_line`. |
| 9 | The trace for the step 5 emergency | The node path goes danger_gate, danger_router, emergency_response. **No model call.** |
| 10 | The scores (`docs/scores.md`) | See the note on honest numbers below. |
| 11 | Versions | The session runs a published, frozen version. We can roll back, or switch to the rules-only version, in one step. |
| 12 | Terminal: `python -m ocs.check_drift live.json …` | The live pipeline matches the reviewed code in the repository, node for node. |
| 13 | Team settings | Two-factor login for everyone. Study staff can read sessions but cannot change the bot. (Only after #29 is done.) |

**Honest numbers.** Show the untuned number next to the tuned one, never the tuned one alone.

| Test set | Emergencies caught | Notes |
|---|---|---|
| Held-out set D | 33 of 39 (85%) | written before the last changes, never tuned on |
| Corpus | 118 of 132 (89%) | partly seen while writing the rules |
| Set C | 37 of 39 (95%) | was used to choose rules, so not a fair test |

Routine messages wrongly sent to the emergency reply: 0 of 140 on the corpus.

---

## 4. If something goes wrong

| Problem | Do this |
|---|---|
| The AI provider fails or is slow | Publish the **rules-only** version: build `ocs/pipeline/zeya_pipeline_rules_only.json` (`python -m ocs.build_pipeline --rules-only --write`), load it, and publish. Questions with no card then get "Sina taarifa iliyokaguliwa ya kujibu swali hilo…" with the line about reaching a person. Cards, emergencies, the access gate and the clip still work, and there is no AI at all. Roll back to the normal version afterwards. Check it with `python -m ocs.check_drift live.json … --rules-only`. |
| A turn errors while the normal version is live | OCS sends its own generic English error message. Zeya cannot replace it yet, because OCS has no hook for a fixed Kiswahili reply (#26, needs an OCS change). Switch to the rules-only version. |
| Anything that must stop the bot at once | Turn off **Enabled** on the WhatsApp channel in OCS (optional static reply). Incoming messages are then not processed. |
| The clip does not arrive | The card text still goes, and the turn is tagged `explainer_clip:failed`. Check the raw GitHub link in section 1. |
| A tester gets "Zeya is being tested…" | Their participant data lacks `approved_tester: true`. Set it in OCS. |
| Wi-Fi fails | Play the backup recording. |

---

## 5. Lines for hard questions

- **"Is this live with mothers?"** Not yet, by design. Only synthetic test participants are used until ethics approval, a NACOSTI licence, ODPC registration and a DPIA are in place.
- **"Where does the content come from?"** It is based on the Ministry's Mother and Child Health Handbook and the national guidelines. A licensed clinical officer signs off every answer, and each answer names its source.
- **"Where does the data go?"** In this walkthrough, messages pass through Meta (WhatsApp) and Groq in the United States, and neither keeps them for training. For the trial, the model will run on our own server in Kenya.
- **"What if the AI is wrong?"** It never handles emergencies. Approved cards answer common questions. Its other answers are limited to Ministry content and checked by a rule before sending. Each change is scored before release, and the scores are published.
- **"How good is the emergency detection?"** 85% on messages it was never tuned on, with no false alarms on normal messages. Then name what it still misses, such as some short misspellings and new Sheng wording.

---

## 6. Rehearsal checklist

- [ ] Full run three times on venue-style Wi-Fi, with sections 2 and 3 in order
- [ ] Switch to the rules-only version once and back, timing how long it takes
- [ ] Confirm the clip plays on both test phones
- [ ] Backup recording on the laptop and on a USB stick
- [ ] The published version is the frozen version reviewed on 29 November 2026
