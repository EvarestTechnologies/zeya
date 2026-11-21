"""
OCS Python Evaluator: card-accuracy, wrong-card and no-card negative reporting.
Completed-observation mode; generation must be disabled.

Evidence source
---------------
observation.output_tags — tags emitted by issue-23 (answer_match CodeNode)
via add_message_tag during the original completed pipeline turn.

Tag contract (issue-23 integration, coordinated by parent):
  answer_route:CARD       — answer_match selected a card
  answer_card:<slug>      — which card was selected (stable slug)
  answer_route:ASK_AI     — no card; defer to AI generation
  guard_blocked           — output guard blocked; card selection and final
                            delivery are DIFFERENT; reported separately

Tag provenance: add_message_tag → output_message_tags → ChatMessage.tags →
observation.output_tags.  NOT from session_state (which may use temp_state).
answer_match CodeNode writes tags (not persistent session_state) to avoid
the temp_state vs session_state boundary issue.

Row types and denominators
--------------------------
Expected card rows (expected_card_id non-empty):
  card_match=True,  wrong_card=False, no_card_missed=False → Correct match
  card_match=False, wrong_card=True,  no_card_missed=False → Wrong card returned
  card_match=False, wrong_card=False, no_card_missed=True  → Card missed (ASK_AI)

No-card negative rows (expected_card_id==''):
  no_card_correct=True,  spurious_card=False → Correct non-match
  no_card_correct=False, spurious_card=True  → Spurious card returned

Fail-closed errors (see _SHARED_VALIDATION_BODY for shared errors):
  expected_card_id_missing     — context key absent ('' is valid; absent is not)
  answer_route_tag_missing     — no answer_route:* tag (issue-23 not deployed)
  answer_route_tag_ambiguous   — multiple answer_route:* tags
"""

from ocs.evaluations.observation import build_evaluator_code

_CARD_SPECIFIC_BODY = """\
    # ----------------------------------------------------------------
    # Card accuracy from observation.output_tags
    # ----------------------------------------------------------------

    # expected_card_id: '' is valid (no-card negative); absent key is error
    if not isinstance(context, dict) or "expected_card_id" not in context:
        return {
            "error": "expected_card_id_missing",
            "note": (
                "context.expected_card_id key must be explicitly present. "
                "Use '' for no-card-negative rows; a missing key is an error."
            ),
        }
    expected_card = context["expected_card_id"]
    if not isinstance(expected_card, str):
        return {"error": "expected_card_id_invalid_type"}

    # -- Read answer route and card from output_tags (issue-23 CodeNode) --
    answer_route_tags = [
        t for t in output_tags
        if isinstance(t, str) and t.startswith("answer_route:")
    ]
    answer_card_tags = [
        t for t in output_tags
        if isinstance(t, str) and t.startswith("answer_card:")
    ]
    guard_blocked = any(t in ("route:guard_blocked", "guard_blocked") for t in output_tags)

    # -- Require exactly one answer_route tag (issue-23 must be deployed) --
    if not answer_route_tags:
        return {
            "error": "answer_route_tag_missing",
            "note": (
                "No answer_route:* tag in observation.output_tags. "
                "Requires issue-23 (answer_match CodeNode) to be deployed and emitting tags. "
                "Tags are written via add_message_tag in the answer_match CodeNode."
            ),
        }
    if len(answer_route_tags) > 1:
        return {"error": "answer_route_tag_ambiguous", "tags": answer_route_tags}

    actual_route = answer_route_tags[0][len("answer_route:"):]
    actual_card = answer_card_tags[0][len("answer_card:"):] if answer_card_tags else ""
    if actual_route not in ("CARD", "ASK_AI"):
        return {"error": "answer_route_tag_unknown"}
    if len(answer_card_tags) > 1:
        return {"error": "answer_card_tag_ambiguous"}
    if actual_route == "CARD" and not actual_card:
        return {"error": "answer_card_tag_missing"}
    if actual_route == "ASK_AI" and answer_card_tags:
        return {"error": "answer_card_tag_inconsistent"}

    # -- No-card negative rows (expected_card_id == '') --
    if not expected_card:
        no_card_correct = actual_route != "CARD"
        spurious_card = actual_route == "CARD"
        return {
            "expected_no_card": True,
            "no_card_correct": no_card_correct,
            "spurious_card": spurious_card,
            "guard_blocked": guard_blocked,
            "actual_route": actual_route,
            "actual_card": actual_card,
        }

    # -- Card rows (expected_card_id non-empty) --
    if actual_route == "CARD":
        card_match = actual_card == expected_card
        wrong_card = not card_match
        no_card_missed = False
    else:
        card_match = False
        wrong_card = False
        no_card_missed = True

    return {
        "expected_no_card": False,
        "card_match": card_match,
        "wrong_card": wrong_card,
        "no_card_missed": no_card_missed,
        "guard_blocked": guard_blocked,
        "actual_route": actual_route,
        "actual_card": actual_card,
        "expected_card": expected_card,
    }\
"""

CARD_ACCURACY_CODE = build_evaluator_code(_CARD_SPECIFIC_BODY)
