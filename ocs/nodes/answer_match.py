"""
Open Chat Studio Python node: deterministic answer-card matcher.

Reads kb_ids and kb_available written by the #22 kb_context node.  Returns the
exact card answer text when a card is clearly matched, or routes to the LLM for
everything else.

Card data is injected at build time by render_answer_match() in
ocs/answer_cards.py, which replaces the ##CARDS_PLACEHOLDER## string literal
inside main() with a double-encoded JSON string of the baked data structure:

    {"cards": [...], "allow_pending": bool}

The runtime node unpacks this structure and independently re-checks
review_status so that eligibility cannot be bypassed in production:

    allow_pending == True  (exact bool, explicit staging): pending cards eligible.
    allow_pending == False (default / production): only approved cards eligible.

Pending review_status is never relabelled as approved.

Outputs (returned value):
    CARD route:   the exact card answer text (returned directly).
    ASK_AI route: the original user input (passed through to downstream LLM).

Outputs (temp state):
    answer_route:  "CARD" or "ASK_AI".
    matched_card:  stable card slug on CARD route; "" on ASK_AI.
    card_text:     answer text on CARD route (not set on ASK_AI).

Outputs (message tags — for completed-observation evaluator, see #28):
    CARD:   answer_route:CARD  +  answer_card:<stable-slug>
    ASK_AI: answer_route:ASK_AI  (all abstention paths)
    No user text, no PII in tags.  Card ID is validated as a safe slug before
    embedding so the tag cannot contain arbitrary content.

Matching algorithm:
    Pure-Python word overlap (Jaccard similarity) with light suffix stemming
    (strips -ing, -tion, -ed, -ly, -es, -s) and English stopword removal.
    "pregnancy" and "dur" (from "during") are treated as domain-agnostic
    function-words in maternal health (they appear in almost every question
    and add no topic discrimination) and are included in STOPWORDS.
    Scores each card as the maximum Jaccard score over all its trigger strings.
    Routes to CARD only when the best score > THRESHOLD (0.25, strict greater-
    than) AND the gap between first and second best is >= TIE_MARGIN (0.10).

Limitations (documented per contract):
    - No semantic understanding.  Near-synonyms without shared word stems
      (e.g. "clinic" vs "ANC") may miss without an explicit synonym trigger.
    - Typos in content words reduce overlap but do not change routing unless
      the score drops below threshold.
    - Very short inputs (<2 raw tokens) are caught by the trivial-input guard.
    - No Swahili or Sheng matching in v0; all starter cards are English-only
      pending Kiswahili translation review.
    - All five v0 cards are pending clinical review; the production build passes
      include_pending=False so the node bakes in an empty list and always routes
      ASK_AI until cards are explicitly approved.
    - += is disallowed in RestrictedPython; use explicit a = a + 1.
    - Known near-tie false positives are documented and tested in
      TestMatcherKnownFalsePositives / TestFormerFalsePositivesNowRegressions.
"""


def main(input, **kwargs):
    import json
    import re

    # ------------------------------------------------------------------
    # Card data injected by render_answer_match() in ocs/answer_cards.py.
    # Baked structure: {"cards": [...], "allow_pending": bool}.
    # review_status is independently re-checked below.
    # ------------------------------------------------------------------
    baked_json = "##CARDS_PLACEHOLDER##"
    baked = json.loads(baked_json)
    cards = baked["cards"]
    allow_pending = baked.get("allow_pending", False)

    # ------------------------------------------------------------------
    # Read KB context written by the #22 kb_context node.
    # ------------------------------------------------------------------
    kb_ids = get_temp_state_key("kb_ids") or []
    kb_available = get_temp_state_key("kb_available") or False

    if not kb_available or not kb_ids:
        set_temp_state_key("answer_route", "ASK_AI")
        set_temp_state_key("matched_card", "")
        add_message_tag("answer_route:ASK_AI")
        return input

    # ------------------------------------------------------------------
    # Participant language from registration data.
    # ------------------------------------------------------------------
    data = get_participant_data() or {}
    language = data.get("language_preference") or "en"

    # ------------------------------------------------------------------
    # Independent runtime eligibility:
    #   - kb_ref must be in selected KB IDs
    #   - language must match participant
    #   - review_status must be "approved", OR "pending" with allow_pending == True
    #     (exact bool True — not just truthy — only the production-baked bool passes)
    # ------------------------------------------------------------------
    eligible = []
    for c in cards:
        if c.get("kb_ref") not in kb_ids:
            continue
        if c.get("language") != language:
            continue
        status = c.get("review_status")
        if status == "approved":
            pass
        elif status == "pending" and allow_pending == True:  # noqa: E712 — strict bool check
            pass
        else:
            continue
        eligible.append(c)

    if not eligible:
        set_temp_state_key("answer_route", "ASK_AI")
        set_temp_state_key("matched_card", "")
        add_message_tag("answer_route:ASK_AI")
        return input

    # ------------------------------------------------------------------
    # Pure-Python word-overlap matcher
    # ------------------------------------------------------------------

    STOPWORDS = {
        "the",
        "and",
        "for",
        "are",
        "was",
        "you",
        "this",
        "that",
        "with",
        "have",
        "not",
        "can",
        "what",
        "why",
        "how",
        "should",
        "would",
        "could",
        "will",
        "when",
        "where",
        "who",
        "which",
        "from",
        "into",
        "out",
        "its",
        "your",
        "our",
        "their",
        "about",
        "also",
        "been",
        "does",
        "did",
        "get",
        "got",
        "had",
        "has",
        "her",
        "him",
        "his",
        "just",
        "let",
        "may",
        "more",
        "much",
        "must",
        "now",
        "one",
        "own",
        "she",
        "than",
        "then",
        "they",
        "too",
        "two",
        "use",
        "yet",
        # Domain-agnostic maternal-health function-words: appear in almost every
        # maternal question/trigger without discriminating between card topics.
        "pregnancy",  # universal context word; replaced by topic-specific vocabulary
        "dur",  # stem of "during" (preposition); adds no content information
    }

    def stem_word(word):
        # Light suffix stripping — preserves medical vocabulary roots.
        for suffix in ("ing", "tion", "ed", "ly", "es", "s"):
            if len(word) > len(suffix) + 2 and word.endswith(suffix):
                return word[: -len(suffix)]
        return word

    def topic_eligible(q_toks, card_anchors):
        """Return True if at least one stemmed anchor appears in q_toks.

        Each anchor string from card['topic_anchors'] is stemmed with the same
        stem_word function used on question tokens.  Generic words like 'safe',
        'pregnancy', or 'during' that are not in any card's anchor list cannot
        confer eligibility, regardless of their Jaccard score against triggers.
        An empty anchor list always returns False (absent topic abstains).
        """
        if not card_anchors:
            return False
        for anchor in card_anchors:
            if stem_word(anchor.lower()) in q_toks:
                return True
        return False

    def tokenize(text):
        raw = re.findall(r"[a-z]+", text.lower())
        tokens = set()
        for w in raw:
            if len(w) > 2:
                s = stem_word(w)
                if s not in STOPWORDS:
                    tokens.add(s)
        return tokens

    def jaccard_score(a_tokens, b_tokens):
        if not a_tokens or not b_tokens:
            return 0.0
        overlap = 0
        for x in a_tokens:
            if x in b_tokens:
                overlap = overlap + 1  # += disallowed in RestrictedPython
        union = len(a_tokens) + len(b_tokens) - overlap
        return overlap / union if union > 0 else 0.0

    # Threshold: strict greater-than (scores == THRESHOLD are rejected as
    # insufficiently confident, preventing borderline vocabulary-overlap matches
    # on domain-agnostic words like "safe" appearing in unrelated questions).
    THRESHOLD = 0.25
    TIE_MARGIN = 0.10

    # Guard on raw (pre-stopword) token count to catch truly empty/trivial inputs
    # without discarding short but specific questions like "Why should I go to ANC?"
    # (which produces only {"anc"} after stopword removal but is a clear question).
    raw_tokens = re.findall(r"[a-z]+", input.lower())
    if len(raw_tokens) < 2:
        set_temp_state_key("answer_route", "ASK_AI")
        set_temp_state_key("matched_card", "")
        add_message_tag("answer_route:ASK_AI")
        return input

    q_tokens = tokenize(input)
    if not q_tokens:
        set_temp_state_key("answer_route", "ASK_AI")
        set_temp_state_key("matched_card", "")
        add_message_tag("answer_route:ASK_AI")
        return input

    # Topic eligibility: at least one stemmed anchor from the card's topic_anchors
    # must appear in q_tokens before the card is scored.
    # This prevents generic words like "safe", "pregnancy", or "during" from
    # conferring eligibility solely through Jaccard overlap on trigger text.
    # A card with absent/unrecognised anchors abstains (topic_eligible returns False).
    topic_checked = []
    for card in eligible:
        if topic_eligible(q_tokens, card.get("topic_anchors", [])):
            topic_checked.append(card)

    if not topic_checked:
        set_temp_state_key("answer_route", "ASK_AI")
        set_temp_state_key("matched_card", "")
        add_message_tag("answer_route:ASK_AI")
        return input

    # Score each topic-eligible card as max Jaccard over all its triggers.
    best_score = 0.0
    best_card = None
    second_score = 0.0

    for card in topic_checked:
        card_best = 0.0
        for trigger in card.get("triggers", []):
            t_tokens = tokenize(trigger)
            s = jaccard_score(q_tokens, t_tokens)
            if s > card_best:
                card_best = s
        if card_best > best_score:
            second_score = best_score
            best_score = card_best
            best_card = card
        elif card_best > second_score:
            second_score = card_best

    # Low confidence — strict threshold: scores exactly at THRESHOLD are rejected.
    if best_score <= THRESHOLD or best_card is None:
        set_temp_state_key("answer_route", "ASK_AI")
        set_temp_state_key("matched_card", "")
        add_message_tag("answer_route:ASK_AI")
        return input

    # Ambiguous tie — no match.
    if best_score - second_score < TIE_MARGIN:
        set_temp_state_key("answer_route", "ASK_AI")
        set_temp_state_key("matched_card", "")
        add_message_tag("answer_route:ASK_AI")
        return input

    # Clear match — validate card ID is a safe slug before embedding in tag.
    # Defence-in-depth: validate_cards enforces the slug at load time;
    # this prevents any malformed ID from reaching the OCS message tag.
    card_id = best_card.get("id", "")
    if not re.match(r"^[a-z0-9_-]+$", card_id):
        # Slug check failed: fail closed, do not emit a potentially unsafe tag.
        set_temp_state_key("answer_route", "ASK_AI")
        set_temp_state_key("matched_card", "")
        add_message_tag("answer_route:ASK_AI")
        return input

    set_temp_state_key("answer_route", "CARD")
    set_temp_state_key("matched_card", card_id)
    set_temp_state_key("card_text", best_card["answer"])
    add_message_tag("answer_route:CARD")
    add_message_tag("answer_card:" + card_id)
    return best_card["answer"]
