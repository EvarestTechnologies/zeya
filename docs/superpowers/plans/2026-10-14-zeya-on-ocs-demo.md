# Zeya on Open Chat Studio + Dimagi Demo Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Get Zeya running as a chatbot on `openchatstudio.co.ke` (team `evarest`), working end to end in OCS web chat and optionally on WhatsApp, then record a 4-minute demo video for Dimagi.

**Architecture:** The pipeline is already built and tested in the repository (`ocs/build_pipeline.py`, generated from `ocs/nodes/*.py`). This plan:
- merges that work,
- fixes the two things that would look wrong on camera (placeholder phone numbers, a test that breaks on newer OCS),
- configures the instance in the browser: Gemini provider, chatbot, pipeline loaded via the pipeline-data endpoint,
- verifies it with `check_drift` and a scripted smoke test,
- records the demo.

**Tech Stack:** Open Chat Studio (web UI + `/a/<team>/pipelines/data/<id>/` endpoint), Google Gemini, Python 3.11 tooling in `ocs/`, Claude in Chrome for browser steps, QuickTime/Loom for recording.

**Spec:** `docs/ocs-migration.md` (design) and the demo script in the conversation of 2026-10-14 (reproduced in Task 9).

**Who does what:** 🧑 = you (decisions, secrets, phone, recording). 🌐 = I drive your Chrome, **you must be logged in to OCS first**. 💻 = I do it in the terminal.

## Global Constraints

- Never commit to `main`; branch `fix/<slug>` or `docs/<slug>`; PR, review, then merge.
- Do not modify `/Users/stellaoiro/Evarest/open-chat-studio` or `/Users/stellaoiro/kintaraa`.
- Danger-sign patterns stay byte-identical to `backend/app/services/danger_signs.py` (`make test-ocs` enforces this).
- No LLM node on the EMERGENCY branch; never edit pipeline nodes by hand in the OCS UI. Only load the generated JSON.
- API keys are typed by you into OCS, never pasted into chat or committed.
- The demo claims only what works: no Dholuo, weekly messages, voice notes or results.
- Before every commit: `make test-ocs` and `make lint-ocs` pass.

## Review Focus

1. **A "safe" demo question that matches a danger pattern.** Asking "what helps stomach pain?" fires the emergency response, because the pattern is `\bstomach\s+pain\b`. Task 8's smoke list includes this case, and the demo script avoids such phrases on purpose.
2. **The instance runs an older or newer OCS than the repository's tests.** The `StaticRouterNode` temp-state source, `LLMResponseWithPrompt` params, or Gemini model names may differ. Task 4 records the version, and Task 6 checks `pipeline.errors == {}` after loading.
3. **Loading the pipeline is rejected.** CSRF, a validation error, or a pipeline id that doesn't belong to the team. Task 6 checks the response body, then re-reads the pipeline and runs `check_drift`.
4. **Registration state leaks between demo takes.** OCS remembers participant data per identifier, so a second take skips registration. Task 8 covers reset with a fresh web-chat participant for each take.
5. **WhatsApp replies outside the 24-hour window.** Only replies to an incoming message are free-form. Task 7 tests by sending from the phone first and never relies on bot-initiated messages.

---

### Task 1: Merge the OCS migration stack 🧑

**Files:** none (GitHub).

- [ ] **Step 1:** Re-review the fix commits `33af22f`, `fa0abb9`, `e4ff99e`, `3e4d191` and `f466b75` (PRs #5–#9).
- [ ] **Step 2:** Merge in order with merge commits. Either run the following yourself, or allow `gh pr merge` for me:

```bash
cd /Users/stellaoiro/Projects/zeya
for n in 2 3 4 5 6 7 8 9; do gh pr edit $n --base main; gh pr merge $n --merge; done
git checkout main && git pull
```

- [ ] **Step 3:** 💻 Verify on `main`. Expected: `283 passed, 1 xfailed` and `All checks passed!`.

```bash
make test-ocs PYTHON=<venv>/bin/python && make lint-ocs PYTHON=<venv>/bin/python
```

---

### Task 2: Make the tuple-unpacking test work on any OCS version 💻

Upstream OCS (`930956ce0`) now supports `a, b = …`. The current test asserts it fails, so it breaks against newer OCS. The nodes avoid tuple unpacking, so they work on both. The test should instead pin what we rely on: the nodes don't use it.

**Files:**
- Modify: `ocs/tests/test_node_sources.py` (replace `test_sandbox_rejects_tuple_unpacking_assignment`)

- [ ] **Step 1:** Create branch `fix/ocs-version-agnostic-tests` from `main`.
- [ ] **Step 2:** Replace the test with:

```python
@pytest.mark.parametrize("path", NODE_FILES, ids=lambda p: p.stem)
def test_nodes_avoid_tuple_unpacking_assignment(path):
    # OCS before 930956ce0 (2026) has no _unpack_sequence_, so "a, b = ..." fails at run time
    # inside a node. Avoiding it keeps the nodes working on old and new instances.
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.Assign):
            assert not any(isinstance(t, ast.Tuple | ast.List) for t in node.targets), (
                f"{path.name}:{node.lineno} uses tuple-unpacking assignment"
            )
```

- [ ] **Step 3:** Check that the new test fails on an offending node. Temporarily add `a, b = 1, 2` inside `main` in `ocs/nodes/emergency_response.py`, run `pytest ocs/tests/test_node_sources.py -q -c /dev/null --rootdir=.`, and expect FAIL `uses tuple-unpacking assignment`. Then revert the line.
- [ ] **Step 4:** Run both sandbox modes. Expected: all pass, 1 xfailed, in both runs.

```bash
make test-ocs PYTHON=<venv>/bin/python
OCS_SOURCE=<scratchpad>/ocs-upstream make test-ocs PYTHON=<venv>/bin/python
```

- [ ] **Step 5:** Commit `test(ocs): pin that nodes avoid tuple unpacking instead of pinning OCS behaviour`, then push and open a PR.

---

### Task 3: Real facility phone numbers 🧑 → 💻

**Blocks recording**, because the emergency message is on screen. Today four of the five numbers look fake.

**Files:**
- Modify: `backend/app/seeds/health_facilities.py` (`phone_number`, and `emergency_line` where known, for the 7 facilities)
- Modify: `ocs/nodes/emergency_response.py:43-49` (the `facilities` list)
- Modify: `ocs/tests/test_emergency_response_node.py` (remove the `@pytest.mark.xfail(...)` decorator)

- [ ] **Step 1 🧑:** Get verified numbers from Migori County Health or the facilities: Migori County Referral, Ombo Mission, Isebania, Awendo, Rongo (plus Macalder and Kehancha for the seed). Also confirm the facility levels (your proposal says Rongo is Level 4 and Migori County Referral is Level 5; the seed says 3 and 4).
- [ ] **Step 2 💻:** Create branch `fix/verified-facility-numbers`. Update the seed values to the verified numbers and levels.
- [ ] **Step 3 💻:** Run `make test-ocs`. Expected: `test_message_matches_zeya` FAILS, because the node no longer matches the seed. This shows the parity check works.
- [ ] **Step 4 💻:** Update the `facilities` list in `emergency_response.py` to the same top 5, in the same order, with the same strings.
- [ ] **Step 5 💻:** Remove the xfail decorator. Run `make test-ocs`. Expected: everything passes with **0 xfailed**. `test_facility_numbers_are_not_placeholders` now passes.
- [ ] **Step 6 💻:** Regenerate the pipeline (`python -m ocs.build_pipeline --write`). Remove the go-live blocker note at the top of `docs/ocs-migration.md`. Commit `fix: verified Migori facility contacts`, then open a PR and merge it after review.

> If verified numbers aren't available before recording: record anyway, but with on-screen text "Demo — facility contacts pending verification". Do **not** invent numbers.

---

### Task 4: Inspect the instance 🌐 (browser needed: log in to openchatstudio.co.ke first)

**Files:** none. Record the findings in `docs/superpowers/plans/2026-10-14-instance-notes.md` (no secrets).

- [ ] **Step 1:** Open the `evarest` team. Note the OCS version if the footer or admin page shows one.
- [ ] **Step 2:** Team settings → LLM Service Providers. Check whether a **Google Gemini** provider type is offered, and which Gemini models it lists.
- [ ] **Step 3:** Pipelines → New pipeline. Check that the node palette has **Python Node**, **Static Router** (with a "Temporary State" data source) and **LLM**.
- [ ] **Step 4:** Check the chatbot's channel options: **Web** (always) and **WhatsApp** (Meta Cloud API).
- [ ] **Step 5:** Decide the model. Use the newest stable Gemini Flash the provider lists (for example `gemini-3.5-flash`). Fall back to `gemini-3-flash-preview` as a custom model only if no Gemini 3 model is listed. Record the choice and the reason in the notes file. Since recruitment hasn't started, this isn't a mid-study change.

**Gate:** if the instance has no Google provider type, or no Static Router with temp state, stop and decide together. The options are asking the instance operator to upgrade, or accepting OpenAI for the demo only.

---

### Task 5: Add the Gemini provider 🧑🌐

- [ ] **Step 1 🧑:** Confirm the Gemini key is on a **paid** tier. Your proposal promises the data isn't used for model training, and as far as I know the free tier allows it. Check Google AI Studio → API keys → plan.
- [ ] **Step 2 🌐:** Open Team settings → LLM Service Providers → Add → Google Gemini. Name it "Zeya Gemini". 🧑 **You type the API key** into the field yourself.
- [ ] **Step 3 🌐:** If the chosen model isn't listed, add it as a custom model under the provider.
- [ ] **Step 4 🌐:** Read and record the provider id and the model id. They're in the URL or the LLM node's model dropdown value, and they're needed for Task 6.

---

### Task 6: Create the chatbot and load the pipeline 🌐💻

**Files:** generates `<scratchpad>/deploy.json` (not committed), plus `<scratchpad>/live.json`.

- [ ] **Step 1 🌐:** Chatbots → New → name "Zeya (demo)", pipeline type. Open its pipeline editor. Record the pipeline id from the URL, `/a/evarest/pipelines/<id>/…`.
- [ ] **Step 2 💻:** Build the deployable copy:

```bash
python -m ocs.build_pipeline --llm-provider-id <PROVIDER_ID> --llm-provider-model-id <MODEL_ID> > <scratchpad>/deploy.json
```

- [ ] **Step 3 🌐:** Load it from the logged-in page. I run this in the page with the javascript tool, with the JSON inlined from `deploy.json`:

```javascript
const csrf = document.cookie.split('; ').find(c => c.startsWith('csrftoken='))?.split('=')[1];
const res = await fetch('/a/evarest/pipelines/data/<PIPELINE_ID>/', {
  method: 'POST', headers: {'Content-Type': 'application/json', 'X-CSRFToken': csrf},
  body: JSON.stringify(DEPLOY_JSON),
});
const body = await res.json();
console.log(res.status, JSON.stringify(body.errors));
```

Expected: `200 {}`. Any entry in `errors` is a validation problem (Review Focus 2). Stop and fix it in the repo, never in the UI.

- [ ] **Step 4 🌐:** Reload the editor. Expected: 8 nodes with the danger gate first, and EMERGENCY going straight to `emergency_response` → End.
- [ ] **Step 5 🌐💻:** Save the live copy from `GET /a/evarest/pipelines/data/<PIPELINE_ID>/` to `<scratchpad>/live.json`, then run:

```bash
python -m ocs.check_drift <scratchpad>/live.json --llm-provider-id <PROVIDER_ID> --llm-provider-model-id <MODEL_ID>
```

Expected: `OK: live pipeline matches the repository`.

- [ ] **Step 6 🌐:** Publish a version of the chatbot, so the channels serve this pipeline.

---

### Task 7 (recommended): Connect WhatsApp 🧑🌐

A phone on camera is far more convincing than web chat. Nobody is enrolled, so moving the number off the old Zeya webhook affects nobody.

- [ ] **Step 1 🧑:** Get the Meta app credentials Zeya uses today (`WHATSAPP_PHONE_NUMBER_ID`, `WHATSAPP_ACCESS_TOKEN` in `backend/.env`). Use a permanent system-user token if the current one is temporary.
- [ ] **Step 2 🌐:** Team settings → Messaging providers → add a Meta Cloud API provider. 🧑 You paste the token. Then go to the chatbot → Channels → WhatsApp → select the provider and the number.
- [ ] **Step 3 🧑:** In Meta Developer Console, set the webhook callback URL and verify token to the values OCS shows, and subscribe to `messages`.
- [ ] **Step 4 🧑:** From your phone, send "Hi". Expected: the welcome and consent message comes back within a few seconds.

---

### Task 8: Smoke test before recording 🌐🧑

Use a **fresh participant** for each run: a new web-chat session or new identifier, or a second phone (Review Focus 4).

- [ ] **Step 1:** Run through the conversation below and tick each expected reply.

| Send | Expected |
|---|---|
| `Hi` | Welcome and consent message (English) |
| `yes` | "Thank you for consenting… What is your name?" |
| `Akinyi` | "Nice to meet you, Akinyi! How many weeks pregnant are you?…" |
| `20` | "You are registered! You are 20 weeks pregnant…" |
| `What should I eat this trimester?` | Gemini answer mentioning the second trimester, under 200 words |
| `Ninatoka damu nyingi` | **Immediate** `URGENT:` message with 5 facilities, no LLM text (the emergency message is in English because the language preference is `en`) |
| `my water broke` | `URGENT:` message |
| `what helps stomach pain?` | `URGENT:` message. This is correct (Review Focus 1), so **keep it out of the demo script** |
| `Asante, nitakula mboga` | Gemini answer in Swahili |

- [ ] **Step 1b 🌐:** For a Swahili take, open the participant in OCS (Participants → the participant → Data) and set `language_preference` to `"sw"`. That's participant data, not the pipeline, so it's allowed. Then `Ninatoka damu nyingi` returns the `DHARURA:` message and Gemini answers in Swahili. Registration has no language step, which is the same as Zeya today, so this is how the language gets set.
- [ ] **Step 2 🌐:** Open the session in OCS. Check that the emergency replies carry the tags `danger_sign:bleeding` and `danger_router:EMERGENCY`.
- [ ] **Step 3 🌐:** Open the trace or timing for the emergency turn. Expected: no LLM step listed.
- [ ] **Step 4:** Run `check_drift` again (Task 6 Step 5).

---

### Task 9: Prepare and record the demo 🧑 (I prepare materials 💻)

- [ ] **Step 1 💻:** Fix the pitch facts before they go on camera:
  - Don't use the "47% in Migori" figure (the source paper studied Kisumu).
  - Correct the budget: transport alone is KES 400 × 140 × 3 = 168,000, so the total and the per-participant cost change.
- [ ] **Step 2 💻:** Make 3 slides (problem, the ask, what funding unlocks) as a Slides artifact.
- [ ] **Step 3 🧑:** Record each section separately in QuickTime (File → New Screen Recording), with browser zoom at 125–150%:
  1. **Problem (30 s):**
     - 93% ANC attendance, but a maternal mortality ratio of 673 per 100,000.
     - The first delay is behind 58% of deaths.
  2. **The idea (20 s):**
     - AI answers questions.
     - Emergencies never go through the AI.
  3. **Pipeline in the OCS editor (40 s):** Start → danger gate → router → emergency or LLM. "OCS replaced about 1,500 lines of my code; I kept the safety logic."
  4. **Live chat (90 s):** registration → nutrition question → `Ninatoka damu nyingi` → `my water broke` → the tags in the OCS session view.
  5. **Why it's safe (40 s):**
     - Run `make test-ocs`.
     - The engine test: 16 emergency messages, 0 LLM calls.
     - Run `check_drift`.
  6. **What Zeya shows about OCS (30 s):**
     - There's no node locking, so I built a drift check.
     - The export's Trace ID is blank without a tracing provider.
     - Routers pass their own input on, not the user's message.
     - Offer to contribute a pre-generation safety hook upstream.
  7. **The ask (20 s):** the 140-woman RCT at Rongo and Migori County Referral, plus Dholuo support with validated danger signs and weekly gestational-age messages.
- [ ] **Step 4 🧑:** Cut the clips together, check that the Swahili message and the emergency reply are readable, and export as 1080p MP4.
- [ ] **Step 5 🧑:** Send it to your Dimagi contact with the PR link or repository, and the one-page brief (`ZEYA_GRANT_BRIEF.md`, rewritten around OCS).

---

## After the demo (not in this plan; needed before recruitment)

- An allowlist, so only imported intervention participants get the chatbot. Replace the in-chat consent step with an AI-disclosure notice.
- Dholuo danger patterns and replies, reviewed by a clinician and a native speaker. A "prolonged labour" category.
- Weekly gestational-age messages and reminders, using WhatsApp templates.
- Control-arm access after endline.
- Scheduled drift checks, and restricted OCS roles.
- Instance operator commitments (encryption, backups, data location).
