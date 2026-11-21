"""
ocs/answer_cards.py — answer-card loader, validator and node renderer for Zeya #23.

Public API
----------
validate_cards(cards)
    Raise ValueError if any card in the list is malformed.  Called automatically
    by load_answer_cards and render_answer_match.

load_answer_cards(path, include_pending=False)
    Read docs/answer-cards.yaml (JSON-subset YAML, stdlib parser) and return a
    validated list of card dicts.  Validates ALL cards before filtering so that
    a malformed pending card is caught even when include_pending=False.

render_answer_match(cards, include_pending=False)
    Generate the answer_match CodeNode source string with card data embedded.
    Raises ValueError when pending cards are supplied without include_pending=True,
    so raw pending cards cannot reach the production runtime by default.
    With include_pending=True (explicit synthetic-staging only) the flag is
    encoded in the baked data as allow_pending=True; pending review_status is
    never relabelled as approved.

Design notes
------------
Parsing: json.loads() on the raw file text.  The file must therefore be valid
JSON (which is also valid YAML, since JSON is a strict subset of YAML).  This is
an explicit, documented design choice per the execution contract to avoid adding
a third-party YAML dependency.

Baked data structure (injected into the CodeNode template):
    {"cards": [...], "allow_pending": bool}
The runtime node unpacks this and independently re-checks review_status so that
eligibility cannot be bypassed by calling render_answer_match with an unexpected
combination of arguments.
"""

import json
import pathlib
import re

_NODES_DIR = pathlib.Path(__file__).parent / "nodes"
_NODE_TEMPLATE_PATH = _NODES_DIR / "answer_match.py"

# The Python string literal token that render_answer_match replaces inside the template.
# Must match the string assignment in answer_match.py's main():
#   baked_json = "##CARDS_PLACEHOLDER##"
PLACEHOLDER_LITERAL = '"##CARDS_PLACEHOLDER##"'

# Supported values — unknown or malformed states must not become approved.
SUPPORTED_REVIEW_STATUSES: frozenset = frozenset({"pending", "approved"})
SUPPORTED_LANGUAGES: frozenset = frozenset({"en", "sw"})

_REQUIRED_KEYS: frozenset = frozenset(
    {"id", "review_status", "language", "kb_ref", "triggers", "answer", "topic_anchors"}
)

# Card IDs must be safe lowercase slugs so they can be embedded in OCS message tags
# without risk of PII or malformed content reaching the evaluator (#28 contract).
_SLUG_RE = re.compile(r"^[a-z0-9_-]+$")


def validate_cards(cards):
    """Validate a list of answer card dicts.

    Raises ValueError with a descriptive message on the first validation failure.
    Called automatically by load_answer_cards and render_answer_match.

    Rules enforced
    --------------
    - cards must be a list.
    - Each element must be a dict.
    - Each dict must contain all required keys: id, review_status, language,
      kb_ref, triggers, answer.
    - id: non-empty, non-whitespace-only string.
    - review_status: exactly one of SUPPORTED_REVIEW_STATUSES {"pending", "approved"}.
      Unknown or malformed values (e.g. "APPROVED", "approved_draft", "in_review")
      are rejected; they must not silently become approved.
    - language: exactly one of SUPPORTED_LANGUAGES {"en", "sw"}.
    - kb_ref: non-empty, non-whitespace-only string.
    - triggers: non-empty list; each element is a non-empty, non-whitespace-only string.
    - answer: non-empty string; at most 80 words (split by whitespace).
    - (id, language) pair: unique across all cards.
    """
    if not isinstance(cards, list):
        raise ValueError(f"Answer cards file must contain a JSON array at top level; got {type(cards).__name__!r}.")
    seen_id_lang: set = set()
    for idx, card in enumerate(cards):
        if not isinstance(card, dict):
            raise ValueError(f"Card at index {idx} must be a JSON object; got {type(card).__name__!r}.")
        missing = _REQUIRED_KEYS - card.keys()
        if missing:
            raise ValueError(f"Card at index {idx} missing required key(s): {sorted(missing)!r}.")
        cid = card["id"]
        if not isinstance(cid, str) or not cid.strip():
            raise ValueError(f"Card at index {idx}: 'id' must be a non-empty string; got {cid!r}.")
        if not _SLUG_RE.match(cid):
            raise ValueError(
                f"Card {cid!r}: 'id' must be a safe lowercase slug matching "
                f"^[a-z0-9_-]+$ (no uppercase, spaces or special characters). "
                "IDs are embedded in OCS message tags and must not contain "
                "arbitrary text that could carry PII."
            )
        status = card["review_status"]
        if not isinstance(status, str):
            raise ValueError(f"Card {cid!r}: 'review_status' must be a string; got {type(status).__name__!r}.")
        if status not in SUPPORTED_REVIEW_STATUSES:
            raise ValueError(
                f"Card {cid!r}: 'review_status' must be one of "
                f"{sorted(SUPPORTED_REVIEW_STATUSES)!r}; got {status!r}. "
                "Unknown or malformed review_status must not be treated as approved."
            )
        lang = card["language"]
        if not isinstance(lang, str):
            raise ValueError(f"Card {cid!r}: 'language' must be a string; got {type(lang).__name__!r}.")
        if lang not in SUPPORTED_LANGUAGES:
            raise ValueError(f"Card {cid!r}: 'language' must be one of {sorted(SUPPORTED_LANGUAGES)!r}; got {lang!r}.")
        kb_ref = card["kb_ref"]
        if not isinstance(kb_ref, str) or not kb_ref.strip():
            raise ValueError(f"Card {cid!r}: 'kb_ref' must be a non-empty string; got {kb_ref!r}.")
        triggers = card["triggers"]
        if not isinstance(triggers, list) or len(triggers) == 0:
            raise ValueError(
                f"Card {cid!r}: 'triggers' must be a non-empty list; "
                f"got {type(triggers).__name__!r} with length "
                f"{len(triggers) if isinstance(triggers, list) else 'N/A'}."
            )
        for tidx, trigger in enumerate(triggers):
            if not isinstance(trigger, str) or not trigger.strip():
                raise ValueError(f"Card {cid!r}: trigger at index {tidx} must be a non-empty string; got {trigger!r}.")
        answer = card["answer"]
        if not isinstance(answer, str) or not answer.strip():
            raise ValueError(f"Card {cid!r}: 'answer' must be a non-empty string.")
        word_count = len(answer.split())
        if word_count >= 80:
            raise ValueError(
                f"Card {cid!r}: 'answer' has {word_count} words; "
                "contract requires strictly fewer than 80 words (at most 79)."
            )
        id_lang_key = (cid, lang)
        if id_lang_key in seen_id_lang:
            raise ValueError(
                f"Duplicate (id, language) pair {id_lang_key!r}. Each (id, language) combination must be unique."
            )
        seen_id_lang.add(id_lang_key)
        topic_anchors = card["topic_anchors"]
        if not isinstance(topic_anchors, list) or len(topic_anchors) == 0:
            raise ValueError(
                f"Card {cid!r}: 'topic_anchors' must be a non-empty list of anchor strings. "
                "Absent anchors cause the card to abstain on every question. "
                "Define at least one topic-specific vocabulary word."
            )
        for aidx, anchor in enumerate(topic_anchors):
            if not isinstance(anchor, str) or not anchor.strip():
                raise ValueError(
                    f"Card {cid!r}: topic_anchor at index {aidx} must be a non-empty string; got {anchor!r}."
                )


def load_answer_cards(path, include_pending=False):
    """Load answer cards from a JSON-subset YAML file.

    Parameters
    ----------
    path : str or pathlib.Path
        Path to docs/answer-cards.yaml (or any JSON-subset YAML file following
        the same schema).  The file must contain a JSON array of card objects.
    include_pending : bool
        When False (default), only cards with ``review_status == "approved"``
        are returned after validation.  Pass True only for explicit synthetic
        test fixtures and staging; document every call site.

    Returns
    -------
    list[dict]
        Validated card dicts with keys: id, review_status, language, kb_ref,
        triggers, answer.  Any extra keys in the file are preserved.

    Notes
    -----
    Validation is performed on ALL cards before filtering.  A malformed pending
    card is therefore caught even when include_pending=False.
    """
    if not isinstance(include_pending, bool):
        raise TypeError("load_answer_cards: include_pending must be bool; pass True explicitly for staging")
    text = pathlib.Path(path).read_text(encoding="utf-8")
    cards = json.loads(text)
    validate_cards(cards)
    if not include_pending:
        cards = [c for c in cards if c.get("review_status") == "approved"]
    return cards


def render_answer_match(cards, include_pending=False):
    """Generate the answer_match CodeNode source with card data embedded.

    Reads ocs/nodes/answer_match.py as a template, validates the supplied
    cards, checks the pending-eligibility gate, then replaces the placeholder
    string literal with the double-encoded baked JSON so that
    ``json.loads(baked_json)`` inside the RestrictedPython sandbox recovers
    the original structure.

    Parameters
    ----------
    cards : list[dict]
        Validated card dicts (e.g. from load_answer_cards()).  May be empty.
    include_pending : bool
        When False (default / production path): raises ValueError if any card
        has review_status == "pending".  Production builds must only embed
        approved cards; pending cards must not reach the production runtime.
        When True (explicit synthetic-staging): pending cards are embedded with
        allow_pending=True in the baked data so the runtime node independently
        permits them.  Pending review_status is NEVER relabelled as approved.

    Returns
    -------
    str
        Complete Python source string for the OCS CodeNode.  The returned
        source passes the OCS CodeNode validator (single top-level main
        function, restricted imports only).

    Raises
    ------
    ValueError
        If any card is malformed (via validate_cards).
        If include_pending=False and any card has review_status == "pending".
        If the template does not contain the expected placeholder literal.
    """
    validate_cards(cards)

    if not isinstance(include_pending, bool):
        raise TypeError(
            f"render_answer_match: include_pending must be bool; "
            f"got {type(include_pending).__name__!r}. "
            "Pass include_pending=True explicitly for synthetic staging only."
        )

    if not include_pending:
        pending_ids = [c["id"] for c in cards if c.get("review_status") != "approved"]
        if pending_ids:
            raise ValueError(
                f"render_answer_match: {len(pending_ids)} pending card(s) supplied to "
                f"production render (include_pending=False). "
                f"Pending card IDs: {pending_ids!r}. "
                "Pass include_pending=True only for explicit synthetic staging; "
                "document every call site. "
                "Pending review_status is never relabelled as approved."
            )

    template = _NODE_TEMPLATE_PATH.read_text(encoding="utf-8")
    if PLACEHOLDER_LITERAL not in template:
        raise ValueError(
            f"Template {_NODE_TEMPLATE_PATH} does not contain the expected "
            f"placeholder literal {PLACEHOLDER_LITERAL!r}. "
            "Do not edit the placeholder manually."
        )

    # Baked data structure: {"cards": [...], "allow_pending": bool}.
    # The runtime node unpacks this and independently re-checks review_status
    # against allow_pending so eligibility cannot be bypassed in production.
    baked: dict = {"cards": cards, "allow_pending": include_pending}
    baked_json = json.dumps(baked, ensure_ascii=True)
    # Double-encode: produce a Python/JSON string literal whose value is the
    # inner JSON string.  json.dumps of a str produces a valid JSON string
    # (and therefore a valid Python string literal) with all special characters
    # escaped, so it is safe to drop directly into source code.
    replacement = json.dumps(baked_json)
    return template.replace(PLACEHOLDER_LITERAL, replacement)
