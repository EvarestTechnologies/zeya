"""
Open Chat Studio Python node: emergency response for detected danger signs.

Runs on the EMERGENCY branch of the danger router. There is no LLM on this branch,
so the message never waits on model latency or availability.

The header and footer are the same as backend/app/services/danger_signs.py
get_emergency_response(). Zeya listed five Migori facilities between them. ZEYA is
open to women anywhere in Kenya, so this lists national emergency numbers instead
(methodological change 9). Each number must be confirmed by calling it before a
release; see docs/ocs-migration.md.

Language comes from participant data ``language_preference``; anything other than
"sw" gets English, as in Zeya.
"""


def main(input: str, **kwargs) -> str:
    header_en = (
        "URGENT: This sounds like it could be a danger sign that requires immediate "
        "medical attention. Please do the following right away:\n\n"
        "1. Go to your nearest health facility immediately or call emergency services.\n"
        "2. If you cannot travel, ask someone nearby to help you get to the hospital.\n"
        "3. Do NOT wait to see if symptoms improve on their own.\n\n"
    )
    header_sw = (
        "DHARURA: Hii inaonekana kama dalili ya hatari inayohitaji matibabu ya haraka. "
        "Tafadhali fanya yafuatayo mara moja:\n\n"
        "1. Nenda hospitali iliyo karibu nawe mara moja au piga simu ya dharura.\n"
        "2. Ikiwa huwezi kusafiri, mwombe mtu aliye karibu akusaidie kwenda hospitalini.\n"
        "3. USISUBIRI kuona kama dalili zitaboreshwa zenyewe.\n\n"
    )
    footer_en = (
        "\n\nThis is educational information, not medical diagnosis. "
        "Always consult your healthcare provider for medical advice."
    )
    footer_sw = (
        "\n\nHii ni taarifa ya kielimu, si utambuzi wa kimatibabu. "
        "Daima wasiliana na mtoa huduma wako wa afya kwa ushauri wa kimatibabu."
    )

    numbers_en = (
        "Emergency numbers (anywhere in Kenya):\n"
        "- Emergency services: 999 or 112\n"
        "- National ambulance: 922\n"
        "- Kenya Red Cross: 1199"
    )
    numbers_sw = (
        "Nambari za dharura (popote nchini Kenya):\n"
        "- Huduma za dharura: 999 au 112\n"
        "- Ambulensi ya kitaifa: 922\n"
        "- Shirika la Msalaba Mwekundu Kenya: 1199"
    )

    language = (get_participant_data() or {}).get("language_preference")
    if language == "sw":
        return header_sw + numbers_sw + footer_sw
    return header_en + numbers_en + footer_en
