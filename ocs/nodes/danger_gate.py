"""
Open Chat Studio Python node: deterministic obstetric danger-sign gate.

Source of truth for the first node after Start in the Zeya pipeline. Do not edit
this node in the OCS UI; change this file, run ``make test-ocs`` and redeploy
(see docs/ocs-migration.md).

The patterns and context rules are verbatim copies of backend/app/services/danger_signs.py,
enforced by ocs/tests/test_danger_gate_parity.py. They were reviewed in
docs/review/danger-gate.md and approved in docs/review/clinical-signoff.md (A1 to A12).
They live inside ``main`` because OCS executes node code with separate locals, so
module-level names are not visible to ``main``.

Outputs (temp state):
    danger_route: "EMERGENCY" or "SAFE", read by the Static Router that follows.
    danger_categories: matched categories, in detection order.
    danger_keywords: the matched text, one per category.
    danger_question: True when a match is a general question or history, not
        something happening to her now. The route is then SAFE.
Returns the user's message unchanged so the SAFE branch receives it.
"""


def main(input: str, **kwargs) -> str:
    import re

    # Danger sign patterns grouped by category, case-insensitive.
    danger_sign_patterns = [
        (
            "bleeding",
            [
                re.compile(r"\b(heavy\s+)?bleeding\b", re.IGNORECASE),
                re.compile(r"\bexcessive\s+blood\b", re.IGNORECASE),
                re.compile(r"\bblood\s+(clots?|loss)\b", re.IGNORECASE),
                re.compile(r"\bkutoka\s+damu\b", re.IGNORECASE),
                re.compile(r"\bdamu\s+nyingi\b", re.IGNORECASE),
                re.compile(r"\bbleed(s|ing)?\b", re.IGNORECASE),
                re.compile(r"\bspotting\b", re.IGNORECASE),
                re.compile(
                    r"\bblood\b(?!\s*(pressure|test|tests|group|sugar|level|levels|count|type|donor|transfusion|bank))",
                    re.IGNORECASE,
                ),
                re.compile(r"(toka|tokwa\s+na|ona|vuja)\s+damu\b", re.IGNORECASE),
                re.compile(r"\b(losing|lost|passing|passed)\s+(some\s+|a\s+lot\s+of\s+)?blood\b", re.IGNORECASE),
                re.compile(r"tok(a|wa)\s+(na\s+)?damu\b", re.IGNORECASE),
                re.compile(r"\bdamu\s+(ina|ime)?(toka|vuja|tiririka)", re.IGNORECASE),
                re.compile(r"\bdamu\s+(kwenye|ukeni)\b", re.IGNORECASE),
            ],
        ),
        (
            "headache_vision",
            [
                re.compile(r"\bsevere\s+headache\b", re.IGNORECASE),
                re.compile(r"\bblurred?\s+vision\b", re.IGNORECASE),
                re.compile(r"\bvision\s+(is\s+)?blurred?\b", re.IGNORECASE),
                re.compile(r"\bseeing\s+(spots?|stars?)\b", re.IGNORECASE),
                re.compile(r"\bkichwa\s+kuuma\b", re.IGNORECASE),
                re.compile(r"\bmacho\s+kuona\s+vibaya\b", re.IGNORECASE),
                re.compile(
                    r"\b(severe|bad|terrible|serious|strong|pounding|throbbing|splitting)\s+(\w+\s+)?headache\b",
                    re.IGNORECASE,
                ),
                re.compile(r"\bhead\s+(is\s+)?(pounding|throbbing|splitting)\b", re.IGNORECASE),
                re.compile(r"\b(blurry|blurring|blurred)\b", re.IGNORECASE),
                re.compile(r"\bflash(es|ing)?\s+(of\s+)?lights?\b", re.IGNORECASE),
                re.compile(r"\bconfus(ed|ion)\b", re.IGNORECASE),
                re.compile(
                    r"\bkichwa\b.{0,20}\b(\w*uma|\w*umwa|maumivu)\b.{0,20}\b(sana|mno|kali)\b|\b(\w*uma|\w*umwa|maumivu)\b.{0,20}\bkichwa\b.{0,20}\b(sana|mno|kali)\b",
                    re.IGNORECASE,
                ),
                re.compile(r"\bmaumivu\s+makali\s+ya\s+kichwa\b", re.IGNORECASE),
                re.compile(r"\bukungu\b", re.IGNORECASE),
                re.compile(r"\bgiza\s+machoni\b", re.IGNORECASE),
                re.compile(r"changanyikiwa\b", re.IGNORECASE),
                re.compile(
                    r"\bhead\b.{0,25}\b(hurt(s|ing)?|pain(ful|s)?|ach(e|es|ing))\b.{0,25}\b(very|so|really|badly|terribl[ey]|a\s+lot|too\s+much|so\s+much|won'?t\s+stop|can'?t|unbearabl[ey])",
                    re.IGNORECASE,
                ),
                re.compile(
                    r"\b(very|so|really|badly|terribl[ey]|a\s+lot|too\s+much|so\s+much|won'?t\s+stop|can'?t|unbearabl[ey])\b.{0,15}\bhead\s*ache\b",
                    re.IGNORECASE,
                ),
                re.compile(
                    r"\b(fuzzy|hazy|double\s+vision|see(ing)?\s+double|can'?t\s+see\s+(well|properly|clearly))\b",
                    re.IGNORECASE,
                ),
                re.compile(
                    r"\bkichwa\b.{0,20}\b(kinauma|kinaniuma|kuuma)\b.{0,15}\b(sana|mno|vibaya)\b", re.IGNORECASE
                ),
                re.compile(r"\b(naona|ninaona)\s+(giza|ukungu|nyota|vibaya)\b|\bsioni\s+vizuri\b", re.IGNORECASE),
                re.compile(r"\b(1[6-9]\d|2\d\d)\s*(/|over)\s*\d{2,3}\b", re.IGNORECASE),
                re.compile(r"\b\d{2,3}\s*(/|over)\s*(1[1-9]\d)\b", re.IGNORECASE),
            ],
        ),
        (
            "pallor_anaemia",
            [
                re.compile(
                    r"\b(look|looks|looking|am|is|'m|feel|become|became|becoming|turned|gone)\s+(very\s+|so\s+|really\s+)?pale\b",
                    re.IGNORECASE,
                ),
                re.compile(r"\b(palms?|lips|eyes|nails|gums|tongue)\b.{0,20}\b(white|pale)\b", re.IGNORECASE),
                re.compile(r"\b(breathless|out\s+of\s+breath|short(ness)?\s+of\s+breath)\b", re.IGNORECASE),
                re.compile(
                    r"\bdizz(y|iness)\b.{0,40}\b(heart|breath|pale|tired|all\s+the\s+time|always|every\s+day|keep)\b",
                    re.IGNORECASE,
                ),
                re.compile(r"\b(heart|breath|pale|tired|always|keep)\b.{0,40}\bdizz(y|iness)\b", re.IGNORECASE),
                re.compile(r"\bheart\s+(is\s+)?(racing|pounding|beating\s+(very\s+)?fast)\b", re.IGNORECASE),
                re.compile(r"\bextremely\s+tired\b", re.IGNORECASE),
                re.compile(
                    r"\b(hb|haemoglobin|hemoglobin|hgb)\b\D{0,15}\b[0-6](\.\d)?\b(?!\s*(/|over))", re.IGNORECASE
                ),
                re.compile(r"\b\w*pauka\b", re.IGNORECASE),
                re.compile(r"\b(viganja|midomo|macho|kucha)\b.{0,25}\b(vyeupe|meupe|myeupe|nyeupe)\b", re.IGNORECASE),
                re.compile(r"\bnimekuwa\s+mweupe\b|\bmeupe\s+sana\b", re.IGNORECASE),
                re.compile(r"\bmweupe\b|\bweupe\b", re.IGNORECASE),
                re.compile(r"\bheart\b.{0,10}\b(races?|racing|pounds?|pounding)\b", re.IGNORECASE),
                re.compile(r"\btired\b.{0,25}\b(just|even)\s+(walking|standing|getting\s+up)\b", re.IGNORECASE),
                re.compile(r"pumua\s+kwa\s+shida\b", re.IGNORECASE),
                re.compile(
                    r"\bkizunguzungu\b.{0,40}\b(moyo|pumua|mweupe|nimechoka|kila\s+siku|kila\s+mara|sana)\b",
                    re.IGNORECASE,
                ),
                re.compile(r"\bmoyo\b.{0,15}\b(unadunda|unapiga)\b.{0,15}\b(kasi|haraka)\b", re.IGNORECASE),
            ],
        ),
        (
            "fever",
            [
                re.compile(r"\bhigh\s+fever\b", re.IGNORECASE),
                re.compile(r"\bsevere\s+fever\b", re.IGNORECASE),
                re.compile(r"\bchills\b", re.IGNORECASE),
                re.compile(r"\bhoma\s+kali\b", re.IGNORECASE),
                re.compile(r"\bbaridi\s+mwilini\b", re.IGNORECASE),
                re.compile(r"\bfever(ish)?\b", re.IGNORECASE),
                re.compile(r"\bshiver(s|ing)?\b", re.IGNORECASE),
                re.compile(
                    r"\b(smell(y|s|ing)?|foul)\b.{0,20}\bdischarge\b|\bdischarge\b.{0,20}\b(smell|foul)", re.IGNORECASE
                ),
                re.compile(r"\bpain\b.{0,30}\bpelvi(s|c)\b|\bpelvi(s|c)\b.{0,30}\bpain\b", re.IGNORECASE),
                re.compile(r"\bhoma\b", re.IGNORECASE),
                re.compile(r"\bjoto\s+(jingi|kali|sana)\b|\bmwili\b.{0,15}\bjoto\b", re.IGNORECASE),
                re.compile(r"tetemeka\b", re.IGNORECASE),
                re.compile(r"\bhot\s+and\s+cold\b|\bshaking\b", re.IGNORECASE),
                re.compile(r"\btemperature\b\D{0,15}\b(3[89]|4[0-2])(\.\d)?\b", re.IGNORECASE),
                re.compile(
                    r"\b(uchafu|ute|majimaji)\b.{0,25}\b(unanuka|unaonuka|harufu)\b|\bharufu\s+mbaya\b.{0,25}\b(uchafu|ute|ukeni)\b",
                    re.IGNORECASE,
                ),
            ],
        ),
        (
            "fetal_movement",
            [
                re.compile(r"\breduced\s+fetal\s+movement\b", re.IGNORECASE),
                re.compile(r"\bno\s+(fetal\s+)?movement\b", re.IGNORECASE),
                re.compile(r"\bbaby\s+(not\s+moving|stopped?\s+moving|isn'?t\s+moving)\b", re.IGNORECASE),
                re.compile(r"\bcan'?t\s+feel\s+(the\s+)?baby\b", re.IGNORECASE),
                re.compile(r"\bmtoto\s+ha(tembei|chezi)\b", re.IGNORECASE),
                re.compile(
                    r"\bbaby\b.{0,20}\b(not|n'?t|has\s+not|stopped|no\s+longer)\b.{0,15}\b(mov|kick)", re.IGNORECASE
                ),
                re.compile(r"\bbaby\b.{0,15}\bmov(ing|es)\s+(less|much\s+less|very\s+little)\b", re.IGNORECASE),
                re.compile(
                    r"\b(haven'?t|have\s+not|not|can'?t|cannot|didn'?t)\s+(felt|feel)\s+(the\s+|my\s+)?baby\b",
                    re.IGNORECASE,
                ),
                re.compile(r"\bmovements?\s+(have\s+|has\s+)?(reduced|decreased|stopped|slowed)\b", re.IGNORECASE),
                re.compile(
                    r"\b(reduced|decreased|fewer|less)\s+(fetal\s+|baby'?s?\s+)?(movements?|kicks?)\b", re.IGNORECASE
                ),
                re.compile(
                    r"\bmtoto\b.{0,20}\b(hachezi|hajacheza|hatembei|hasogei|hajasogea|amepunguza|ameacha\s+kucheza)\b",
                    re.IGNORECASE,
                ),
                re.compile(r"\bsi(m)?hisi\s+mtoto\b", re.IGNORECASE),
                re.compile(r"\bha(ja)?move\b", re.IGNORECASE),
                re.compile(
                    r"\bbaby\b.{0,15}\b(hasn'?t|has\s+not|hadn'?t|not|didn'?t)\s+(kicked|moved)\b", re.IGNORECASE
                ),
                re.compile(
                    r"\b(don'?t|do\s+not|can'?t|cannot|no\s+longer)\s+feel\s+(the\s+|my\s+)?baby\b", re.IGNORECASE
                ),
            ],
        ),
        (
            "abdominal_pain",
            [
                re.compile(r"\bsevere\s+(abdominal\s+)?pain\b", re.IGNORECASE),
                re.compile(r"\bstomach\s+pain\b", re.IGNORECASE),
                re.compile(r"\bsharp\s+pain\b", re.IGNORECASE),
                re.compile(r"\btumbo\s+kuuma\s+sana\b", re.IGNORECASE),
                re.compile(
                    r"\b(severe|bad|terrible|strong|sharp)\s+(abdominal|stomach|tummy|belly)\s+pain\b", re.IGNORECASE
                ),
                re.compile(
                    r"\b(stomach|tummy|belly|abdomen)\b.{0,25}\b(hurt(s|ing)?|pain(ful)?|aching)\b.{0,25}\b(so\s+much|a\s+lot|badly|can'?t)\b",
                    re.IGNORECASE,
                ),
                re.compile(r"\b(pain|ache)\b.{0,15}\b(under|below)\s+(my\s+)?ribs?\b", re.IGNORECASE),
                re.compile(
                    r"\btumbo\b.{0,20}\b(\w*uma|\w*umwa|maumivu)\b.{0,20}\b(sana|mno|kali)\b|\b(\w*uma|\w*umwa|maumivu)\b.{0,20}\btumbo\b.{0,20}\b(sana|mno|kali)\b",
                    re.IGNORECASE,
                ),
                re.compile(r"\bmaumivu\s+makali\s+ya\s+tumbo\b", re.IGNORECASE),
                re.compile(
                    r"\b(stomach|tummy|belly|abdomen|abdominal)\b.{0,25}\b(hurt(s|ing)?|pain(ful|s)?|ach(e|es|ing))\b.{0,25}\b(very|so|really|badly|terribl[ey]|a\s+lot|too\s+much|so\s+much|won'?t\s+stop|can'?t|unbearabl[ey])",
                    re.IGNORECASE,
                ),
                re.compile(
                    r"\b(very|so|really|badly|terribl[ey]|a\s+lot|too\s+much|so\s+much|won'?t\s+stop|can'?t|unbearabl[ey])\b.{0,15}\b(painful|sore)\b.{0,5}$|\b(stomach|tummy|belly)\s+is\s+(very|so|really|badly|terribl[ey]|a\s+lot|too\s+much|so\s+much|won'?t\s+stop|can'?t|unbearabl[ey])\s+painful\b",
                    re.IGNORECASE,
                ),
                re.compile(
                    r"\bpain\b.{0,20}\b(stomach|tummy|belly|abdomen)\b.{0,25}\b(very|so|really|badly|terribl[ey]|a\s+lot|too\s+much|so\s+much|won'?t\s+stop|can'?t|unbearabl[ey])",
                    re.IGNORECASE,
                ),
                re.compile(
                    r"\btumbo\b.{0,20}\b(\w*uma|\w*umwa|maumivu)\b.{0,20}\bvibaya\b|\b(\w*uma|\w*umwa|maumivu)\b.{0,20}\btumbo\b.{0,20}\bvibaya\b",
                    re.IGNORECASE,
                ),
                re.compile(r"\bmaumivu\b.{0,20}\bmbavu\b", re.IGNORECASE),
            ],
        ),
        (
            "water_breaking",
            [
                re.compile(r"\bwater\s+(break(ing|s)?|broke)\b", re.IGNORECASE),
                re.compile(r"\bfluid\s+(leaking|leakage|gushing)\b", re.IGNORECASE),
                re.compile(r"\bleaking\s+fluid\b", re.IGNORECASE),
                re.compile(r"\bmaji\s+ya(mekatika|kutoka)\b", re.IGNORECASE),
                re.compile(r"\bwaters?\s+(have\s+|has\s+)?(broke|broken|burst)\b", re.IGNORECASE),
                re.compile(r"\bwater\b.{0,20}\bleak", re.IGNORECASE),
                re.compile(r"\bleak(ing|s)?\b.{0,25}\b(water|fluid)\b", re.IGNORECASE),
                re.compile(
                    r"\bmaji\b.{0,15}\b(yametoka|yanatoka|yanavuja|yamevunjika|yamepasuka|yamekatika)\b", re.IGNORECASE
                ),
                re.compile(r"\bchupa\b.{0,10}\b(imepasuka|imevunjika|imetoboka)\b", re.IGNORECASE),
                re.compile(
                    r"\b(wet|water|fluid|liquid)\b.{0,30}\b(running|gushing|dripping|pouring|trickling)\b.{0,20}\b(legs?|down)\b",
                    re.IGNORECASE,
                ),
                re.compile(r"\bmaji\b.{0,10}\bya\w*toka\b", re.IGNORECASE),
            ],
        ),
        (
            "convulsions",
            [
                re.compile(r"\bconvulsion\b", re.IGNORECASE),
                re.compile(r"\bseizure\b", re.IGNORECASE),
                re.compile(r"\bloss\s+of\s+consciousness\b", re.IGNORECASE),
                re.compile(r"\bfaint(ed|ing)\b", re.IGNORECASE),
                re.compile(r"\bpassed?\s+out\b", re.IGNORECASE),
                re.compile(r"\bdegedege\b", re.IGNORECASE),
                re.compile(r"\bkupoteza\s+fahamu\b", re.IGNORECASE),
                re.compile(r"\bconvulsions\b", re.IGNORECASE),
                re.compile(r"\bseizures\b", re.IGNORECASE),
                re.compile(r"\b(had|having|have|has)\s+(a\s+)?fits?\b", re.IGNORECASE),
                re.compile(r"\bunconscious\b|\bblack(ed)?\s+out\b", re.IGNORECASE),
                re.compile(r"zirai\b", re.IGNORECASE),
                re.compile(r"anguka\b.{0,25}tetemeka\b", re.IGNORECASE),
                re.compile(r"\bcollaps(e|ed|es|ing)\b", re.IGNORECASE),
                re.compile(
                    r"\bjerking\b|\b(not|isn'?t)\s+(answering|responding|waking)\b|\bunresponsive\b", re.IGNORECASE
                ),
                re.compile(r"poteza\s+fahamu\b|\bamezimia\b|\balizimia\b", re.IGNORECASE),
            ],
        ),
        (
            "swelling",
            [
                re.compile(r"\bsevere\s+swelling\b", re.IGNORECASE),
                re.compile(r"\bswollen\s+(face|hands?|feet)\b", re.IGNORECASE),
                re.compile(r"\bkuvimba\s+sana\b", re.IGNORECASE),
                re.compile(
                    r"\b(face|hands?|fingers|eyes)\b.{0,20}\b(swollen|swelling|puffy|swell(ed|ing)?)\b", re.IGNORECASE
                ),
                re.compile(r"\b(puffy)\s+(face|hands?|fingers|eyes)\b", re.IGNORECASE),
                re.compile(r"\bswell(ed|ing)\s+up\b", re.IGNORECASE),
                re.compile(
                    r"\b(face|hands?|fingers|eyes)\b.{0,25}\b(puffed|puffy|bloated)\b|\b(puffed|swollen)\s+up\b",
                    re.IGNORECASE,
                ),
                re.compile(
                    r"\b(uso|mikono|vidole|macho)\b.{0,20}\b(umevimba|imevimba|vimevimba|yamevimba|kuvimba|umefura|imefura|vimefura|kufura)\b",
                    re.IGNORECASE,
                ),
            ],
        ),
    ]

    # General questions about danger signs.
    info_question = [
        re.compile(r"\b(what|which)\s+(are|is)\s+(the\s+)?(\w+\s+)?signs\b", re.IGNORECASE),
        re.compile(r"\bsigns\s+of\b", re.IGNORECASE),
        re.compile(r"\bis\s+(it\s+|\w+\s+){0,3}normal\b", re.IGNORECASE),
        re.compile(r"\bcan\s+(a|an)\s+\w+\s+harm\b", re.IGNORECASE),
        re.compile(r"\bhow\s+(can|do)\s+i\s+(avoid|prevent|know|stop)\b", re.IGNORECASE),
        re.compile(r"\bkuzui\w*|\bnawezaje\b", re.IGNORECASE),
        re.compile(r"^\s*je\b.*\?\s*$", re.IGNORECASE),
        re.compile(r"\b(what|how)\b.{0,30}\bif\b", re.IGNORECASE),
        re.compile(r"\bwhat\s+does\s+\w+\s+mean\b", re.IGNORECASE),
        re.compile(r"^\s*(will|would|can|could|should|does|do)\b.*\?\s*$", re.IGNORECASE),
        re.compile(r"\b(my|a)\s+(friend|sister|neighbou?r|cousin)\b", re.IGNORECASE),
        re.compile(r"\bdalili\s+za\b", re.IGNORECASE),
        re.compile(r"\bni\s+kawaida\b", re.IGNORECASE),
        re.compile(r"\binaweza\s+kumdhuru\b", re.IGNORECASE),
        re.compile(r"\bnifanye\s+nini\b.*\b\w+ki\w+\b", re.IGNORECASE),
    ]
    # Context that makes a match general rather than happening now (sign-off A8).
    general_context = [
        re.compile(
            r"\b(nurse|clinic|health\s+worker|doctor|nesi|daktari|wanaangalia|wanapima)\b.{0,40}\b(check|test|look|kama|if|whether)\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\b(first|last|previous|past)\s+pregnancy\b|\bmimba\s+(ya\s+kwanza|iliyopita)\b|\blast\s+year\b|\bmwaka\s+jana\b",
            re.IGNORECASE,
        ),
    ]
    # Blood that is not from the vagina; a bleeding match is dropped unless a vaginal word is present.
    not_obstetric_blood = [
        re.compile(r"\b(gums?|teeth|tooth|brush\w*|nose|ufizi|fizi|meno|pua)\b", re.IGNORECASE),
        re.compile(
            r"\b(foods?|eat|vyakula|chakula|kula)\b.{0,30}\b(blood|damu)\b|\b(add|adds|increase|build|give\w*)\s+(me\s+)?(more\s+)?blood\b|ongeza\s+damu",
            re.IGNORECASE,
        ),
    ]
    vaginal_words = re.compile(r"\b(vagina\w*|ukeni|down\s+there|pad|chupi|toilet)\b", re.IGNORECASE)
    # Signs that it is happening to her now.
    happening_now = [
        re.compile(
            r"\b(i'?m|i\s+am|i\s+have|i'?ve|i\s+had|i\s+feel|i\s+see|i\s+can'?t|i\s+haven'?t|i\s+look)\b", re.IGNORECASE
        ),
        re.compile(
            r"\bmy\s+(face|hands?|waters?|vision|head|stomach|tummy|palms|lips|blood\s+pressure|bp|hb)\s+(is|are|has|have|was|were|broke|hurts?)\b",
            re.IGNORECASE,
        ),
        re.compile(r"\bmy\s+baby\s+(has|is|hasn'?t|isn'?t|stopped|won'?t|doesn'?t)\b", re.IGNORECASE),
        re.compile(r"\b(nina|niko|natoka|naona|naumwa|nahisi|sihisi|simhisi|nimeona|nimeanza)\b", re.IGNORECASE),
        re.compile(r"\bnime\w+|\bnili\w+", re.IGNORECASE),
    ]

    categories_found = []
    keywords_found = []
    for category, patterns in danger_sign_patterns:
        for pattern in patterns:
            match = pattern.search(input)
            if match:
                if category not in categories_found:
                    categories_found.append(category)
                keywords_found.append(match.group())
                break

    if "bleeding" in categories_found:
        other_source = False
        for pattern in not_obstetric_blood:
            if pattern.search(input):
                other_source = True
                break
        if other_source and not vaginal_words.search(input):
            index = categories_found.index("bleeding")
            categories_found.pop(index)
            keywords_found.pop(index)

    question = False
    if categories_found:
        asks = False
        for pattern in info_question:
            if pattern.search(input):
                asks = True
                break
        now = False
        for pattern in happening_now:
            if pattern.search(input):
                now = True
                break
        general = False
        for pattern in general_context:
            if pattern.search(input):
                general = True
                break
        question = general or (asks and not now)

    set_temp_state_key("danger_route", "EMERGENCY" if categories_found and not question else "SAFE")
    set_temp_state_key("danger_categories", categories_found)
    set_temp_state_key("danger_keywords", keywords_found)
    set_temp_state_key("danger_question", question)

    # Tags make danger signs countable in OCS (session view, evaluations, exports)
    # without re-running the patterns.
    for category in categories_found:
        add_message_tag("danger_sign:" + category)
    for index in range(len(keywords_found)):
        keyword = " ".join(keywords_found[index].split())
        add_message_tag(("danger_keyword:" + categories_found[index] + ":" + keyword)[:100])
    if question:
        add_message_tag("danger_question")

    return input
