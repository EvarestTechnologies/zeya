"""
Open Chat Studio Python node: fixed reply in place of the AI answer (rules-only mode, #26).

Present only in the rules-only build (python -m ocs.build_pipeline --rules-only), which
has no LLM node. It takes the answer_router ASK_AI branch, so a question that no
reviewed answer card covers gets this fixed text instead of a model answer. The danger
gate, emergency response, registration, answer cards and knowledge referral are the
same as in the normal build.

An operator turns the mode on by making the published rules-only version the default
version in OCS, and off by making the normal version the default again. No WhatsApp
message can change it. See docs/ocs-migration.md, "Rules-only mode".

No model, network, file I/O or credentials.
No participant data mutation; reads saved language preference only.
Non-sensitive route tag so operators can count rules-only turns.

Language copies (suggested copy from #26):
  English — draft wording from the issue.
  Swahili — DRAFT, pending fluent-speaker review.
A preference that is neither "en" nor "sw" gets both, English first, because the
language is unknown. Today such a participant never gets here: kb_context finds no
entries for that language and sends the turn to knowledge_referral. Both copies are
kept so the reply stays safe if that changes.
"""


def main(input, **kwargs):
    data = get_participant_data() or {}
    lang = data.get("language_preference")

    english = (
        "Sorry, ZEYA couldn’t answer your question right now. Please try again later. "
        "For pregnancy concerns, contact your healthcare provider."
    )
    # Draft Swahili — pending fluent-speaker review.
    swahili = (
        "Samahani, ZEYA imeshindwa kujibu swali lako kwa sasa. Tafadhali jaribu tena baadaye. "
        "Kwa maswali kuhusu ujauzito, wasiliana na mtoa huduma wako wa afya."
    )

    if lang == "en":
        reply = english
    elif lang == "sw":
        reply = swahili
    else:
        reply = english + "\n\n" + swahili

    set_temp_state_key("rules_only_route", "RULES_ONLY")
    add_message_tag("route:rules_only")
    return reply
