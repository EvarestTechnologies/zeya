"""
Open Chat Studio Python node: emergency response for detected danger signs.

Runs on the EMERGENCY branch of the danger router. There is no LLM on this branch,
so the message never waits on model latency or availability.

The header and footer are the same as backend/app/services/danger_signs.py
get_emergency_response(). Zeya listed five Migori facilities between them. ZEYA is
open to women anywhere in Kenya, so this lists national emergency numbers instead
(methodological change 9). Each number must be confirmed by calling it before a
release; see docs/ocs-migration.md. The numbers below were verified by calling
(docs/review/clinical-signoff.md, section D, 27 and 28 November 2026). The four Migori
County ambulance dispatch numbers were confirmed by Stella Oiro on 28 November 2026. The Kiswahili text is
a DRAFT, pending fluent-speaker and clinical review (answers K1, 27 November 2026).

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
        "DHARURA: Hii inaweza kuwa dalili ya hatari inayohitaji matibabu ya haraka. "
        "Fanya yafuatayo sasa hivi:\n\n"
        "1. Nenda kituo cha afya kilicho karibu nawe mara moja, au piga simu ya dharura.\n"
        "2. Ikiwa huwezi kusafiri, mwombe mtu aliye karibu akusaidie kufika kituo cha afya.\n"
        "3. USISUBIRI kuona kama dalili zitapungua zenyewe.\n\n"
    )
    footer_en = (
        "\n\nThis is educational information, not medical diagnosis. "
        "Always consult your healthcare provider for medical advice."
    )
    footer_sw = "\n\nHii ni taarifa ya kielimu, si utambuzi wa ugonjwa. Kwa ushauri, wasiliana na muhudumu wa afya."

    numbers_en = (
        "Emergency numbers:\n"
        "- Ambulance: 922 (free)\n"
        "- Emergency services: 999 or 112\n"
        "- Migori County ambulance: 0740 587 479, 0740 588 519, 0740 588 853 or +254 724 024 296"
    )
    numbers_sw = (
        "Nambari za dharura:\n"
        "- Ambulensi: 922 (bila malipo)\n"
        "- Huduma za dharura: 999 au 112\n"
        "- Ambulensi ya Kaunti ya Migori: 0740 587 479, 0740 588 519, 0740 588 853 au +254 724 024 296"
    )

    language = (get_participant_data() or {}).get("language_preference")
    if language == "sw":
        return header_sw + numbers_sw + footer_sw
    return header_en + numbers_en + footer_en
