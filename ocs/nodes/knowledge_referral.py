"""
Open Chat Studio Python node: fixed health-worker referral when no approved KB content.

Reached via the kb_router FALSE output when kb_available=False — i.e. the approved
knowledge base returned no entries eligible for this participant's language and
gestational week.  Returns a fixed, source-free referral to the participant's
healthcare provider WITHOUT calling any AI model.

No model, network, file I/O or credentials.
No participant data mutation; reads saved language preference only.
Non-sensitive route tag emitted for completed-observation evaluation (#28).

Language copies:
  English — suitable for review / production use.
  Swahili  — DRAFT, pending fluent-speaker and clinical review.  Not approved
              for public use; shown only while approved SW content is unavailable.
"""


def main(input, **kwargs):
    # Read the participant's saved language preference.
    # Set by the registration node; absent or unrecognised value → English default.
    data = get_participant_data() or {}
    lang = data.get("language_preference", "en")

    if lang == "sw":
        # Draft Swahili referral — pending fluent-speaker and clinical review.
        referral = "Sina taarifa iliyokaguliwa kujibu swali hilo. Tafadhali uliza mtoa huduma wako wa afya."
    else:
        # English referral — default for all non-Swahili or absent preferences.
        referral = "I do not have reviewed information to answer that question. Please ask your healthcare provider."

    set_temp_state_key("knowledge_referral_route", "REFERRAL")
    add_message_tag("route:knowledge_referral")
    return referral
