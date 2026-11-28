"""
Open Chat Studio Python node: access gate (issue #21).

Runs straight after the SAFE branch of the danger router, so the danger gate has
already answered any emergency, for everyone. Open Chat Studio removed its
participant allowlist on 17 September 2026 and WhatsApp channels answer anyone,
so this gate is the only thing between a stranger and the AI.

Routes (temp state ``access_route``, read by the access router):
    OK          participant data ``approved_tester`` is exactly True and the message
                has no attachment. The message continues to registration unchanged.
    NOT_TESTER  anyone else. Fixed reply that Zeya is in testing; no AI.
    MEDIA       an approved tester sent an image, voice note or file. Fixed reply
                asking her to type; no AI. The model reads text only, and the WhatsApp
                channel would otherwise pass the image to the model as a link.

The reply never repeats her message. With no saved language, the fixed reply is
given in English and Kiswahili. The replies were approved by Stella Oiro on
28 November 2026 (docs/review/clinical-signoff.md, item F). The Kiswahili stays
DRAFT until a fluent speaker reviews it.
"""


def main(input, **kwargs):
    not_tester_en = (
        "Zeya is being tested and is not open to the public yet. For pregnancy questions, "
        "please ask your health worker. In an emergency, call 922, free from any phone."
    )
    not_tester_sw = (
        "Zeya inafanyiwa majaribio na bado haijafunguliwa kwa umma. Kwa maswali ya ujauzito, "
        "tafadhali muulize muhudumu wa afya. Kwa dharura, piga 922 bila malipo."
    )
    media_en = "I can only read text messages for now. Please type your question in words."
    media_sw = "Kwa sasa ninaweza kusoma ujumbe wa maandishi pekee. Tafadhali andika swali lako kwa maneno."

    data = get_participant_data() or {}
    language = data.get("language_preference")

    def in_language(english, swahili):
        if language == "sw":
            return swahili
        if language == "en":
            return english
        return english + "\n\n" + swahili

    if data.get("approved_tester") is not True:
        set_temp_state_key("access_route", "NOT_TESTER")
        add_message_tag("route:access_not_tester")
        return in_language(not_tester_en, not_tester_sw)

    attachments = get_temp_state_key("attachments") or []
    if len(attachments) > 0:
        set_temp_state_key("access_route", "MEDIA")
        add_message_tag("route:access_media")
        return in_language(media_en, media_sw)

    set_temp_state_key("access_route", "OK")
    add_message_tag("route:access_ok")
    return input
