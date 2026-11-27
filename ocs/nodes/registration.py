"""
Open Chat Studio Python node: study registration and LLM context.

Runs on the SAFE branch, after the danger gate, so registration messages are
also checked for danger signs.

Ports ConversationHandler._handle_registration (consent -> name -> gestational
age) and AIEngine._build_context from the Zeya backend, using participant data in
place of the User table. Reply wording is unchanged for trial participants.

Anyone in Kenya can use ZEYA. Only participants imported from the trial's enrolment
list have ``study_participant`` and get Zeya's study welcome and consent wording.
Everyone else is asked to consent to using ZEYA and having messages stored.

Language onboarding (Zeya #27): a participant without a valid stored/imported
language preference (``language_preference`` not "en"/"sw") is first shown a fixed,
deterministic bilingual choice -- no model call, and the triggering message's content
is discarded, same as the old single-language first contact. Once they reply with a
valid choice (case-insensitive, whitespace-stripped "1"/"English" or
"2"/"Kiswahili"/"Swahili"), the preference is persisted and the appropriate
language's welcome/consent (or, for a partially registered participant recovering a
missing/invalid preference, whatever prompt they were already waiting on) is sent as
a separate turn. The choice reply itself never grants consent or gets misread as a
pending name/weeks answer. An invalid/empty reply repeats the same choice without
advancing registration. A participant with an already-valid preference (explicit or
imported) bypasses the choice entirely, and a fully registered participant is never
sent back through it.

The Swahili wording below is a draft translation for fluent-speaker review. It is not
clinically approved, and this change does not claim fluent-speaker or clinical sign-off.

Outputs (temp state):
    registration_route: "REPLY" (return this node's text to the user) or
        "REGISTERED" (continue to the LLM with the user's message).
    llm_context: context block for the LLM system prompt (REGISTERED only).

Registration replies are tagged "registration", and the first-contact turn also
"registration:first_contact". Zeya never logged its registration replies or the
first message, so ocs/export_adapter.py uses these tags to leave them out.
"""


def main(input: str, **kwargs) -> str:
    welcome_en = (
        "Welcome to the Antenatal Education Chatbot! I am here to help you with "
        "information about your pregnancy journey.\n\n"
        "This is a research study chatbot that provides educational information about "
        "maternal health based on Kenya Ministry of Health materials.\n\n"
        "Important: This is educational information, not medical diagnosis. Always "
        "consult your healthcare provider for medical advice.\n\n"
        'Tip: save this number in your contacts as "Zeya" so you can find me easily.\n\n'
        "Do you consent to participate in this study and receive antenatal education "
        "messages? Please reply YES or NO."
    )
    welcome_sw = (
        "Karibu kwenye Chatbot ya Elimu ya Ujauzito! Niko hapa kukusaidia na "
        "habari kuhusu safari yako ya ujauzito.\n\n"
        "Hii ni chatbot ya utafiti inayotoa habari za kielimu kuhusu afya ya mama "
        "kulingana na machapisho ya Wizara ya Afya ya Kenya.\n\n"
        "Muhimu: Hii ni habari ya kielimu, si utambuzi wa kimatibabu. Daima "
        "wasiliana na mtoa huduma wako wa afya kwa ushauri wa kimatibabu.\n\n"
        'Kidokezo: hifadhi nambari hii kwenye anwani zako kama "Zeya" ili unipate kwa urahisi.\n\n'
        "Je, unakubali kushiriki katika utafiti huu na kupokea ujumbe wa elimu ya "
        "ujauzito? Tafadhali jibu NDIYO au HAPANA."
    )
    public_welcome_en = (
        "Welcome to ZEYA! I am here to help you with information about your pregnancy journey.\n\n"
        "I share educational information about maternal health based on Kenya Ministry "
        "of Health materials.\n\n"
        "Important: This is educational information, not medical diagnosis. Always consult your "
        "healthcare provider for medical advice.\n\n"
        "Your messages are stored securely so that ZEYA can reply to you. "
        "Privacy policy: https://evarestke.com/zeya/\n\n"
        'Tip: save this number in your contacts as "Zeya" so you can find me easily.\n\n'
        "Do you agree to use ZEYA and to have your messages stored? Please reply YES or NO."
    )
    public_welcome_sw = (
        "Karibu ZEYA! Niko hapa kukusaidia na habari kuhusu safari yako ya ujauzito.\n\n"
        "Ninatoa habari za kielimu kuhusu afya ya mama kulingana na machapisho ya "
        "Wizara ya Afya ya Kenya.\n\n"
        "Muhimu: Hii ni habari ya kielimu, si utambuzi wa kimatibabu. Daima wasiliana na "
        "mtoa huduma wako wa afya kwa ushauri wa kimatibabu.\n\n"
        "Ujumbe wako huhifadhiwa kwa usalama ili ZEYA iweze kukujibu. "
        "Sera ya faragha: https://evarestke.com/zeya/\n\n"
        'Kidokezo: hifadhi nambari hii kwenye anwani zako kama "Zeya" ili unipate kwa urahisi.\n\n'
        "Je, unakubali kutumia ZEYA na ujumbe wako kuhifadhiwa? Tafadhali jibu NDIYO au HAPANA."
    )
    # Week context for the AI, not a message to the participant. The topics are the
    # NG24 p107 ANC teaching topics (National Guidelines on Quality Obstetrics and
    # Perinatal Care, 2024), keyed by week. Approved in sign-off C3, 27 November 2026.
    gestational_guidance = [
        (1, 12, "First contact: history, examination and the ANC profile"),
        (13, 20, "Why ANC matters, iron and folic acid, self care"),
        (21, 26, "Danger signs in pregnancy, why to give birth in a health facility"),
        (27, 30, "Birth plan, danger signs, exclusive breastfeeding"),
        (31, 34, "Newborn care, breastfeeding position and attachment, family planning after birth"),
        (35, 36, "Kangaroo mother care, keeping the newborn warm, cord care"),
        (37, 42, "Signs of labour, newborn care recap"),
    ]

    language_choice_msg = "Please choose your language / Tafadhali chagua lugha yako:\n1. English\n2. Kiswahili"

    def parse_language_choice(raw):
        choice = (raw or "").strip().lower()
        if choice in ("1", "english"):
            return "en"
        if choice in ("2", "kiswahili", "swahili"):
            return "sw"
        return None

    consented_msg = {
        ("en", True): "Thank you for consenting to participate! What is your name?",
        ("en", False): "Thank you! What is your name?",
        ("sw", True): "Asante kwa kukubali kushiriki katika utafiti! Jina lako ni nani?",
        ("sw", False): "Asante! Jina lako ni nani?",
    }
    declined_msg = {
        "en": "Thank you for your response. You can message us anytime if you change your mind. Take care, Mama!",
        "sw": "Asante kwa jibu lako. Unaweza kutuma ujumbe wakati wowote ukibadilisha mawazo. Jihadhari, Mama!",
    }
    consent_retry_msg = {
        ("en", True): "Please reply YES or NO to consent to participate in the study.",
        ("en", False): "Please reply YES to start using ZEYA, or NO if you do not want to.",
        ("sw", True): "Tafadhali jibu NDIYO au HAPANA kukubali kushiriki katika utafiti.",
        ("sw", False): "Tafadhali jibu NDIYO kuanza kutumia ZEYA, au HAPANA kama hutaki.",
    }
    name_prompt_msg = {
        "en": "What is your name?",
        "sw": "Jina lako ni nani?",
    }
    name_greeting = {
        "en": "Nice to meet you, ",
        "sw": "Nimefurahi kukutana nawe, ",
    }
    weeks_prompt_tail = {
        "en": "How many weeks pregnant are you? Please reply with a number (for example: 20).",
        "sw": "Una wiki ngapi za ujauzito? Tafadhali jibu kwa nambari (kwa mfano: 20).",
    }
    ga_retry_msg = {
        "en": "Please enter a valid number of weeks (between 1 and 42). For example: 20",
        "sw": "Tafadhali ingiza idadi sahihi ya wiki (kati ya 1 na 42). Kwa mfano: 20",
    }
    fallback_completion_msg = {
        "en": "Just type your question and I will do my best to help you, Mama!",
        "sw": "Andika swali lako tu nami nitafanya niwezalo kukusaidia, Mama!",
    }

    data = get_participant_data() or {}
    now = datetime.datetime.now(datetime.timezone.utc)
    text = input or ""
    text_lower = text.strip().lower()
    is_study = data.get("study_participant") is True

    def reply(message):
        set_temp_state_key("registration_route", "REPLY")
        add_message_tag("registration")
        return message

    if data.get("registration_complete"):
        gestational_age = None
        if data.get("gestational_age_at_enrollment") is not None:
            enrolled_at = datetime.datetime.fromisoformat(data["enrolled_at"])
            weeks_since_enrollment = (now - enrolled_at).days // 7
            gestational_age = data["gestational_age_at_enrollment"] + weeks_since_enrollment

        parts = []
        if gestational_age is not None:
            parts.append("User's current gestational age: " + str(gestational_age) + " weeks.")
            for guidance in gestational_guidance:
                if guidance[0] <= gestational_age <= guidance[1]:
                    parts.append("Trimester guidance: " + guidance[2])
                    break
        if data.get("language_preference") == "sw":
            parts.append("User prefers Swahili. Respond in Swahili.")

        set_temp_state_key("llm_context", "\n".join(parts) if parts else "No additional context available.")
        set_temp_state_key("registration_route", "REGISTERED")
        return input

    def welcome_for(language):
        if is_study:
            return welcome_sw if language == "sw" else welcome_en
        return public_welcome_sw if language == "sw" else public_welcome_en

    def pending_prompt(language):
        # Resume wherever this (now-relanguaged) participant was already waiting, without
        # consuming the language-choice reply as the answer to that step.
        if not data.get("consent_given"):
            return consent_retry_msg[(language, is_study)]
        if not data.get("name_collected"):
            return name_prompt_msg[language]
        if data.get("gestational_age_at_enrollment") is None:
            return weeks_prompt_tail[language]
        set_participant_data_key("registration_complete", True)
        return fallback_completion_msg[language]

    stored_language = data.get("language_preference")
    has_valid_language = stored_language in ("en", "sw")

    if data.get("language_choice_pending") and has_valid_language:
        # A stale pending flag (e.g. an invalid stored preference later corrected by an
        # operator/re-import) must not override the now-valid preference and swallow the
        # real reply underneath it. Clear the stale flag and fall through to normal
        # processing of this message against the valid preference.
        set_participant_data_key("language_choice_pending", False)

    if data.get("language_choice_pending") and not has_valid_language:
        selected = parse_language_choice(text)
        if selected is None:
            return reply(language_choice_msg)
        set_participant_data_key("language_preference", selected)
        set_participant_data_key("language_choice_pending", False)
        if not data.get("welcome_sent"):
            set_participant_data_key("welcome_sent", True)
            set_participant_data_key("enrolled_at", now.isoformat())
            set_participant_data_key("consent_given", False)
            set_participant_data_key("registration_complete", False)
            set_participant_data_key("study_group", data.get("study_group") or "intervention")
            return reply(welcome_for(selected))
        return reply(pending_prompt(selected))

    if not has_valid_language:
        # New participant with no explicit/saved preference, or a stored value that is
        # neither "en" nor "sw" (invalid imported data, or a partial registration missing
        # it). Either way: show the choice, do not touch any other registration progress.
        set_participant_data_key("language_choice_pending", True)
        message = reply(language_choice_msg)
        if not data.get("welcome_sent"):
            add_message_tag("registration:first_contact")
        return message

    language = stored_language

    if not data.get("welcome_sent"):
        # First contact: enrol and send the consent request. Zeya ignored the content
        # of this first message; here that already happened in the language-choice step,
        # or the preference was imported/pre-set and this message is the first one seen.
        set_participant_data_key("welcome_sent", True)
        set_participant_data_key("enrolled_at", now.isoformat())
        set_participant_data_key("consent_given", False)
        set_participant_data_key("registration_complete", False)
        set_participant_data_key("study_group", data.get("study_group") or "intervention")
        message = reply(welcome_for(language))
        add_message_tag("registration:first_contact")
        return message

    if not data.get("consent_given"):
        if text_lower in ("yes", "ndiyo", "ndio"):
            set_participant_data_key("consent_given", True)
            set_participant_data_key("consent_given_at", now.isoformat())
            set_participant_data_key("consent_declined", False)
            return reply(consented_msg[(language, is_study)])
        if text_lower in ("no", "hapana"):
            # Zeya deactivated the user here. We record the decision instead, so a later
            # YES re-enrols them, as the reply promises.
            set_participant_data_key("consent_declined", True)
            return reply(declined_msg[language])
        return reply(consent_retry_msg[(language, is_study)])

    # OCS merges participant.name into participant data as "name", so a name may already
    # be present (e.g. from the channel). Track this step separately.
    if not data.get("name_collected"):
        name = text.strip()
        if not name:
            # A message with no text (photo, voice note). Zeya ignored these; ask again.
            return reply(name_prompt_msg[language])
        set_participant_data_key("name", name)
        set_participant_data_key("name_collected", True)
        return reply(name_greeting[language] + name + "! " + weeks_prompt_tail[language])

    if data.get("gestational_age_at_enrollment") is None:
        weeks = None
        try:
            weeks = int(text_lower.strip().split()[0])
        except (ValueError, IndexError):
            weeks = None
        if weeks is None or weeks < 1 or weeks > 42:
            return reply(ga_retry_msg[language])

        expected_delivery_date = now.date() + datetime.timedelta(weeks=40 - weeks)
        set_participant_data_key("gestational_age_at_enrollment", weeks)
        set_participant_data_key("expected_delivery_date", expected_delivery_date.isoformat())
        set_participant_data_key("registration_complete", True)
        if language == "sw":
            return reply(
                "Umesajiliwa! Una wiki " + str(weeks) + " za ujauzito. "
                "Tarehe yako inayotarajiwa ya kujifungua ni takriban "
                + expected_delivery_date.strftime("%B %d, %Y")
                + ".\n\n"
                "Sasa unaweza kuniuliza swali lolote kuhusu ujauzito wako. Ninaweza kusaidia na:\n"
                "- Lishe na mlo\n"
                "- Dalili za hatari za kuangalia\n"
                "- Maandalizi ya kujifungua\n"
                "- Usumbufu wa kawaida\n"
                "- Miadi ya ANC\n"
                "- Huduma ya mtoto mchanga\n\n" + fallback_completion_msg["sw"]
            )
        return reply(
            "You are registered! You are " + str(weeks) + " weeks pregnant. "
            "Your expected delivery date is approximately " + expected_delivery_date.strftime("%B %d, %Y") + ".\n\n"
            "You can now ask me any questions about your pregnancy. "
            "I can help with:\n"
            "- Nutrition and diet\n"
            "- Danger signs to watch for\n"
            "- Birth preparedness\n"
            "- Common discomforts\n"
            "- ANC appointments\n"
            "- Newborn care\n\n" + fallback_completion_msg["en"]
        )

    # Consent, name and gestational age are all set but registration_complete is not
    # (for example, data imported by hand). Finish registration.
    set_participant_data_key("registration_complete", True)
    return reply(fallback_completion_msg[language])
