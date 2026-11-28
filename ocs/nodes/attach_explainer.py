"""
Open Chat Studio Python node: attach the danger-signs explainer clip.

Sits between the output guard and the danger-question line. When the approved
danger_signs answer card was sent and passed the guard, it downloads the clip from
a fixed public address and attaches it to the reply (issue #31, approved by Stella
Oiro on 28 November 2026). The clip is drawn from Mother and Child Health Handbook
page 14, with English and Kiswahili captions.

If the download fails, the card text is still sent and the turn is tagged
``explainer_clip:failed``. No model, no participant data, no credentials.

Limits: OCS caps a Python node download at 1 MB on some releases, so the clip is
kept under 1 MB (913,976 bytes). WhatsApp needs MP4 with H.264 video and AAC audio;
the clip carries a silent AAC track.
"""


def main(input, **kwargs):
    if get_temp_state_key("answer_route") != "CARD":
        return input
    if get_temp_state_key("guard_route") != "PASS":
        return input
    card = get_temp_state_key("matched_card") or ""
    if not card.startswith("danger_signs_"):
        return input

    url = "https://raw.githubusercontent.com/EvarestTechnologies/zeya/main/media/explainers/zeya_danger_signs.mp4"
    try:
        response = http.get(url, timeout=8)
    except Exception:
        add_message_tag("explainer_clip:failed")
        return input

    content = response.get("content")
    if not response.get("is_success") or not isinstance(content, bytes):
        add_message_tag("explainer_clip:failed")
        return input

    add_file_attachment("zeya_danger_signs.mp4", content, "video/mp4")
    add_message_tag("explainer_clip:danger_signs")
    return input
