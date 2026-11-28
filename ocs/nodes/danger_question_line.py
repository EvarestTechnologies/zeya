"""
Open Chat Studio Python node: fixed line before answers to danger-sign questions.

Sits in front of End on every SAFE path (registration reply, fixed referral and
output guard). When the danger gate set ``danger_question`` (a match that is a
general question or history, not happening now), the participant first receives a
fixed line telling her to go to a health facility now if it is happening to her,
with the verified emergency numbers, and then the normal reply.

Approved in docs/review/clinical-signoff.md, A4 (c) and A9 ("go now").
The numbers are the verified numbers in ocs/nodes/emergency_response.py; a test
keeps them in step. No model, network, file I/O or credentials.

Language copies:
  English, approved.
  Swahili, DRAFT, pending fluent-speaker and clinical review.
"""


def main(input, **kwargs):
    if get_temp_state_key("danger_question") is not True:
        return input

    data = get_participant_data() or {}
    if data.get("language_preference") == "sw":
        line = (
            "Kama hili linakutokea sasa, nenda kituo cha afya sasa hivi. "
            "Nambari za dharura: ambulensi 922 (bila malipo), 999 au 112, "
            "ambulensi ya Kaunti ya Migori 0740 587 479, 0740 588 519, 0740 588 853 au +254 724 024 296."
        )
    else:
        line = (
            "If this is happening to you now, go to a health facility now. "
            "Emergency numbers: ambulance 922 (free), 999 or 112, "
            "Migori County ambulance 0740 587 479, 0740 588 519, 0740 588 853 or +254 724 024 296."
        )

    add_message_tag("danger_question_line")
    return line + "\n\n" + input
