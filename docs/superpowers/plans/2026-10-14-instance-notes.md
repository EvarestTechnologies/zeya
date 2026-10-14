# openchatstudio.co.ke — instance notes (2026-10-14)

No secrets in this file.

- **OCS version:** none shown in the UI. It has the newer Integrations settings and team-migration features, so it is close to upstream `dimagi/open-chat-studio` (much newer than the 2026-04-30 Evarest fork).
- **Team:** `evarest`. Setup was done as `evarestke@gmail.com` (Super Admin). `stellaacharoiro@gmail.com` is still invited (since 2026-10-03), not active.
- **Providers:**
  - 1 = Evarest OpenAI (unverified)
  - 2 = Zeya Gemini (saved but **not working**: the server times out reaching Google, `DeadlineExceeded 504`, with a valid `AIza` key)
  - 3 = **Zeya OpenRouter** (verified)
- **Model:** 120 = `google/gemini-3.8-flash` (custom model on provider 3, $0.75 in / $3.75 out per 1M tokens). Chosen because the direct Gemini connection fails from this server, while OpenRouter connects over plain HTTPS.
- **Chatbot:** 20 = "Zeya". Pipeline 7. Version 2 published (pipeline from `main`, built with `--llm-provider-id 3 --llm-provider-model-id 120`).
- **Old chatbot 8**, "Zeya Antenatal Demo" (3 months old, someone else's rough demo), was left untouched.
- **Load result:** HTTP 200, no validation errors. The Python nodes, Static Router (temp state) and LLM node are all accepted by this instance.
- **Drift check:** OK. Every node, edge, code hash and prompt hash matches the repository.
- **Smoke test (web chat, unreleased version):** welcome ✅; `Ninatoka damu nyingi` gives the instant URGENT message ✅ (works before consent too); registration ✅; nutrition question gets a Gemini answer with 20-week context and local foods ✅. Cost $0.0037.
- **Still to do:**
  - Real facility numbers (the placeholders are visible in the emergency message).
  - Fix server egress to Google, or keep OpenRouter.
  - Gemini or OpenRouter billing and privacy settings before real participants.
  - WhatsApp channel (optional).
