"""
Danger sign detection service for maternal health emergencies.

Detects keywords and phrases that indicate obstetric danger signs requiring
immediate medical attention, per WHO and Kenya MOH guidelines.
"""

import logging
import re
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# Danger sign keyword patterns grouped by category.
# Each pattern is compiled as case-insensitive regex. These are verbatim copies of
# ocs/nodes/danger_gate.py, enforced by ocs/tests/test_danger_gate_parity.py, and
# were approved in docs/review/clinical-signoff.md (A1 to A12).
DANGER_SIGN_PATTERNS: dict[str, list[re.Pattern]] = {
    "bleeding": [
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
        re.compile(
            r"\b(losing|lost|passing|passed)\s+(some\s+|a\s+lot\s+of\s+)?blood\b",
            re.IGNORECASE,
        ),
        re.compile(r"tok(a|wa)\s+(na\s+)?damu\b", re.IGNORECASE),
        re.compile(r"\bdamu\s+(ina|ime)?(toka|vuja|tiririka)", re.IGNORECASE),
        re.compile(r"\bdamu\s+(kwenye|ukeni)\b", re.IGNORECASE),
    ],
    "headache_vision": [
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
            r"\bkichwa\b.{0,20}\b(kinauma|kinaniuma|kuuma)\b.{0,15}\b(sana|mno|vibaya)\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\b(naona|ninaona)\s+(giza|ukungu|nyota|vibaya)\b|\bsioni\s+vizuri\b",
            re.IGNORECASE,
        ),
        re.compile(r"\b(1[6-9]\d|2\d\d)\s*(/|over)\s*\d{2,3}\b", re.IGNORECASE),
        re.compile(r"\b\d{2,3}\s*(/|over)\s*(1[1-9]\d)\b", re.IGNORECASE),
    ],
    "pallor_anaemia": [
        re.compile(
            r"\b(look|looks|looking|am|is|'m|feel|become|became|becoming|turned|gone)\s+(very\s+|so\s+|really\s+)?pale\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\b(palms?|lips|eyes|nails|gums|tongue)\b.{0,20}\b(white|pale)\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\b(breathless|out\s+of\s+breath|short(ness)?\s+of\s+breath)\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\bdizz(y|iness)\b.{0,40}\b(heart|breath|pale|tired|all\s+the\s+time|always|every\s+day|keep)\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\b(heart|breath|pale|tired|always|keep)\b.{0,40}\bdizz(y|iness)\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\bheart\s+(is\s+)?(racing|pounding|beating\s+(very\s+)?fast)\b",
            re.IGNORECASE,
        ),
        re.compile(r"\bextremely\s+tired\b", re.IGNORECASE),
        re.compile(
            r"\b(hb|haemoglobin|hemoglobin|hgb)\b\D{0,15}\b[0-6](\.\d)?\b(?!\s*(/|over))",
            re.IGNORECASE,
        ),
        re.compile(r"\b\w*pauka\b", re.IGNORECASE),
        re.compile(
            r"\b(viganja|midomo|macho|kucha)\b.{0,25}\b(vyeupe|meupe|myeupe|nyeupe)\b",
            re.IGNORECASE,
        ),
        re.compile(r"\bnimekuwa\s+mweupe\b|\bmeupe\s+sana\b", re.IGNORECASE),
        re.compile(r"\bmweupe\b|\bweupe\b", re.IGNORECASE),
        re.compile(
            r"\bheart\b.{0,10}\b(races?|racing|pounds?|pounding)\b", re.IGNORECASE
        ),
        re.compile(
            r"\btired\b.{0,25}\b(just|even)\s+(walking|standing|getting\s+up)\b",
            re.IGNORECASE,
        ),
        re.compile(r"pumua\s+kwa\s+shida\b", re.IGNORECASE),
        re.compile(
            r"\bkizunguzungu\b.{0,40}\b(moyo|pumua|mweupe|nimechoka|kila\s+siku|kila\s+mara|sana)\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\bmoyo\b.{0,15}\b(unadunda|unapiga)\b.{0,15}\b(kasi|haraka)\b",
            re.IGNORECASE,
        ),
    ],
    "fever": [
        re.compile(r"\bhigh\s+fever\b", re.IGNORECASE),
        re.compile(r"\bsevere\s+fever\b", re.IGNORECASE),
        re.compile(r"\bchills\b", re.IGNORECASE),
        re.compile(r"\bhoma\s+kali\b", re.IGNORECASE),
        re.compile(r"\bbaridi\s+mwilini\b", re.IGNORECASE),
        re.compile(r"\bfever(ish)?\b", re.IGNORECASE),
        re.compile(r"\bshiver(s|ing)?\b", re.IGNORECASE),
        re.compile(
            r"\b(smell(y|s|ing)?|foul)\b.{0,20}\bdischarge\b|\bdischarge\b.{0,20}\b(smell|foul)",
            re.IGNORECASE,
        ),
        re.compile(
            r"\bpain\b.{0,30}\bpelvi(s|c)\b|\bpelvi(s|c)\b.{0,30}\bpain\b",
            re.IGNORECASE,
        ),
        re.compile(r"\bhoma\b", re.IGNORECASE),
        re.compile(
            r"\bjoto\s+(jingi|kali|sana)\b|\bmwili\b.{0,15}\bjoto\b", re.IGNORECASE
        ),
        re.compile(r"tetemeka\b", re.IGNORECASE),
        re.compile(r"\bhot\s+and\s+cold\b|\bshaking\b", re.IGNORECASE),
        re.compile(r"\btemperature\b\D{0,15}\b(3[89]|4[0-2])(\.\d)?\b", re.IGNORECASE),
        re.compile(
            r"\b(uchafu|ute|majimaji)\b.{0,25}\b(unanuka|unaonuka|harufu)\b|\bharufu\s+mbaya\b.{0,25}\b(uchafu|ute|ukeni)\b",
            re.IGNORECASE,
        ),
    ],
    "fetal_movement": [
        re.compile(r"\breduced\s+fetal\s+movement\b", re.IGNORECASE),
        re.compile(r"\bno\s+(fetal\s+)?movement\b", re.IGNORECASE),
        re.compile(
            r"\bbaby\s+(not\s+moving|stopped?\s+moving|isn'?t\s+moving)\b",
            re.IGNORECASE,
        ),
        re.compile(r"\bcan'?t\s+feel\s+(the\s+)?baby\b", re.IGNORECASE),
        re.compile(r"\bmtoto\s+ha(tembei|chezi)\b", re.IGNORECASE),
        re.compile(
            r"\bbaby\b.{0,20}\b(not|n'?t|has\s+not|stopped|no\s+longer)\b.{0,15}\b(mov|kick)",
            re.IGNORECASE,
        ),
        re.compile(
            r"\bbaby\b.{0,15}\bmov(ing|es)\s+(less|much\s+less|very\s+little)\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\b(haven'?t|have\s+not|not|can'?t|cannot|didn'?t)\s+(felt|feel)\s+(the\s+|my\s+)?baby\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\bmovements?\s+(have\s+|has\s+)?(reduced|decreased|stopped|slowed)\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\b(reduced|decreased|fewer|less)\s+(fetal\s+|baby'?s?\s+)?(movements?|kicks?)\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\bmtoto\b.{0,20}\b(hachezi|hajacheza|hatembei|hasogei|hajasogea|amepunguza|ameacha\s+kucheza)\b",
            re.IGNORECASE,
        ),
        re.compile(r"\bsi(m)?hisi\s+mtoto\b", re.IGNORECASE),
        re.compile(r"\bha(ja)?move\b", re.IGNORECASE),
        re.compile(
            r"\bbaby\b.{0,15}\b(hasn'?t|has\s+not|hadn'?t|not|didn'?t)\s+(kicked|moved)\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\b(don'?t|do\s+not|can'?t|cannot|no\s+longer)\s+feel\s+(the\s+|my\s+)?baby\b",
            re.IGNORECASE,
        ),
    ],
    "abdominal_pain": [
        re.compile(r"\bsevere\s+(abdominal\s+)?pain\b", re.IGNORECASE),
        re.compile(r"\bstomach\s+pain\b", re.IGNORECASE),
        re.compile(r"\bsharp\s+pain\b", re.IGNORECASE),
        re.compile(r"\btumbo\s+kuuma\s+sana\b", re.IGNORECASE),
        re.compile(
            r"\b(severe|bad|terrible|strong|sharp)\s+(abdominal|stomach|tummy|belly)\s+pain\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\b(stomach|tummy|belly|abdomen)\b.{0,25}\b(hurt(s|ing)?|pain(ful)?|aching)\b.{0,25}\b(so\s+much|a\s+lot|badly|can'?t)\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\b(pain|ache)\b.{0,15}\b(under|below)\s+(my\s+)?ribs?\b", re.IGNORECASE
        ),
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
    "water_breaking": [
        re.compile(r"\bwater\s+(break(ing|s)?|broke)\b", re.IGNORECASE),
        re.compile(r"\bfluid\s+(leaking|leakage|gushing)\b", re.IGNORECASE),
        re.compile(r"\bleaking\s+fluid\b", re.IGNORECASE),
        re.compile(r"\bmaji\s+ya(mekatika|kutoka)\b", re.IGNORECASE),
        re.compile(
            r"\bwaters?\s+(have\s+|has\s+)?(broke|broken|burst)\b", re.IGNORECASE
        ),
        re.compile(r"\bwater\b.{0,20}\bleak", re.IGNORECASE),
        re.compile(r"\bleak(ing|s)?\b.{0,25}\b(water|fluid)\b", re.IGNORECASE),
        re.compile(
            r"\bmaji\b.{0,15}\b(yametoka|yanatoka|yanavuja|yamevunjika|yamepasuka|yamekatika)\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\bchupa\b.{0,10}\b(imepasuka|imevunjika|imetoboka)\b", re.IGNORECASE
        ),
        re.compile(
            r"\b(wet|water|fluid|liquid)\b.{0,30}\b(running|gushing|dripping|pouring|trickling)\b.{0,20}\b(legs?|down)\b",
            re.IGNORECASE,
        ),
        re.compile(r"\bmaji\b.{0,10}\bya\w*toka\b", re.IGNORECASE),
    ],
    "convulsions": [
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
            r"\bjerking\b|\b(not|isn'?t)\s+(answering|responding|waking)\b|\bunresponsive\b",
            re.IGNORECASE,
        ),
        re.compile(r"poteza\s+fahamu\b|\bamezimia\b|\balizimia\b", re.IGNORECASE),
    ],
    "swelling": [
        re.compile(r"\bsevere\s+swelling\b", re.IGNORECASE),
        re.compile(r"\bswollen\s+(face|hands?|feet)\b", re.IGNORECASE),
        re.compile(r"\bkuvimba\s+sana\b", re.IGNORECASE),
        re.compile(
            r"\b(face|hands?|fingers|eyes)\b.{0,20}\b(swollen|swelling|puffy|swell(ed|ing)?)\b",
            re.IGNORECASE,
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
}

# General questions about danger signs.
INFO_QUESTION_PATTERNS: list[re.Pattern] = [
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
GENERAL_CONTEXT_PATTERNS: list[re.Pattern] = [
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
NOT_OBSTETRIC_BLOOD_PATTERNS: list[re.Pattern] = [
    re.compile(
        r"\b(gums?|teeth|tooth|brush\w*|nose|ufizi|fizi|meno|pua)\b", re.IGNORECASE
    ),
    re.compile(
        r"\b(foods?|eat|vyakula|chakula|kula)\b.{0,30}\b(blood|damu)\b|\b(add|adds|increase|build|give\w*)\s+(me\s+)?(more\s+)?blood\b|ongeza\s+damu",
        re.IGNORECASE,
    ),
]

# Signs that it is happening to her now.
HAPPENING_NOW_PATTERNS: list[re.Pattern] = [
    re.compile(
        r"\b(i'?m|i\s+am|i\s+have|i'?ve|i\s+had|i\s+feel|i\s+see|i\s+can'?t|i\s+haven'?t|i\s+look)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bmy\s+(face|hands?|waters?|vision|head|stomach|tummy|palms|lips|blood\s+pressure|bp|hb)\s+(is|are|has|have|was|were|broke|hurts?)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bmy\s+baby\s+(has|is|hasn'?t|isn'?t|stopped|won'?t|doesn'?t)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(nina|niko|natoka|naona|naumwa|nahisi|sihisi|simhisi|nimeona|nimeanza)\b",
        re.IGNORECASE,
    ),
    re.compile(r"\bnime\w+|\bnili\w+", re.IGNORECASE),
]

VAGINAL_WORDS = re.compile(
    r"\b(vagina\w*|ukeni|down\s+there|pad|chupi|toilet)\b", re.IGNORECASE
)

# Emergency response templates (without hardcoded facilities)
EMERGENCY_RESPONSE_HEADER_EN = (
    "URGENT: This sounds like it could be a danger sign that requires immediate "
    "medical attention. Please do the following right away:\n\n"
    "1. Go to your nearest health facility immediately or call emergency services.\n"
    "2. If you cannot travel, ask someone nearby to help you get to the hospital.\n"
    "3. Do NOT wait to see if symptoms improve on their own.\n\n"
)

EMERGENCY_RESPONSE_HEADER_SW = (
    "DHARURA: Hii inaweza kuwa dalili ya hatari inayohitaji matibabu ya haraka. "
    "Fanya yafuatayo sasa hivi:\n\n"
    "1. Nenda kituo cha afya kilicho karibu nawe mara moja, au piga simu ya dharura.\n"
    "2. Ikiwa huwezi kusafiri, mwombe mtu aliye karibu akusaidie kufika kituo cha afya.\n"
    "3. USISUBIRI kuona kama dalili zitapungua zenyewe.\n\n"
)

EMERGENCY_RESPONSE_FOOTER_EN = (
    "\n\nThis is educational information, not medical diagnosis. "
    "Always consult your healthcare provider for medical advice."
)

EMERGENCY_RESPONSE_FOOTER_SW = (
    "\n\nHii ni taarifa ya kielimu, si utambuzi wa ugonjwa. "
    "Kwa ushauri, wasiliana na muhudumu wa afya."
)

# Fallback emergency contacts (used only if database is unavailable)
FALLBACK_CONTACTS_EN = (
    "Nearest facilities in Migori County:\n"
    "- Migori County Referral Hospital: 0800 723 253\n"
    "- Ombo Mission Hospital\n"
    "- Isebania Sub-County Hospital"
)

FALLBACK_CONTACTS_SW = (
    "Hospitali za karibu katika Kaunti ya Migori:\n"
    "- Hospitali ya Rufaa ya Kaunti ya Migori: 0800 723 253\n"
    "- Hospitali ya Ombo Mission\n"
    "- Hospitali ya Isebania Sub-County"
)


class DangerSignResult:
    """Result of danger sign detection."""

    def __init__(
        self,
        detected: bool,
        categories: list[str],
        keywords: list[str],
        question: bool = False,
    ):
        self.detected = detected
        self.categories = categories
        self.keywords = keywords
        # True when a match is a general question or history, not happening now.
        self.question = question

    def __bool__(self) -> bool:
        return self.detected


def detect_danger_signs(message: str) -> DangerSignResult:
    """
    Scan a message for danger sign keywords.

    Returns a DangerSignResult with detection status, matched categories,
    the specific keywords found, and whether the match is a general question.
    """
    categories_found: list[str] = []
    keywords_found: list[str] = []
    for category, patterns in DANGER_SIGN_PATTERNS.items():
        for pattern in patterns:
            match = pattern.search(message)
            if match:
                if category not in categories_found:
                    categories_found.append(category)
                keywords_found.append(match.group())
                break

    if "bleeding" in categories_found:
        other_source = any(p.search(message) for p in NOT_OBSTETRIC_BLOOD_PATTERNS)
        if other_source and not VAGINAL_WORDS.search(message):
            index = categories_found.index("bleeding")
            categories_found.pop(index)
            keywords_found.pop(index)

    question = False
    if categories_found:
        asks = any(p.search(message) for p in INFO_QUESTION_PATTERNS)
        now = any(p.search(message) for p in HAPPENING_NOW_PATTERNS)
        general = any(p.search(message) for p in GENERAL_CONTEXT_PATTERNS)
        question = general or (asks and not now)

    detected = bool(categories_found) and not question

    return DangerSignResult(
        detected=detected,
        categories=categories_found,
        keywords=keywords_found,
        question=question,
    )


async def get_emergency_response(
    db: Optional[AsyncSession] = None,
    county: str = "Migori",
    language: str = "en",
) -> str:
    """
    Get the localized emergency response message with facility contacts.

    Args:
        db: Database session (optional). If None, uses fallback contacts.
        county: County name for facility lookup.
        language: Response language ("en" or "sw").

    Returns:
        Formatted emergency response message with facility contacts.
    """
    from app.services.health_facility_service import health_facility_service

    # Build header
    header = (
        EMERGENCY_RESPONSE_HEADER_SW
        if language == "sw"
        else EMERGENCY_RESPONSE_HEADER_EN
    )

    # Get facility contacts
    facilities_text = ""
    if db is not None:
        try:
            facilities = await health_facility_service.get_emergency_facilities(
                db, county=county, limit=5
            )
            if facilities:
                facilities_text = health_facility_service.format_emergency_message(
                    facilities, language=language
                )
            else:
                # No facilities found in database, use fallback
                logger.warning(
                    "No emergency facilities found for county: %s, using fallback",
                    county,
                )
                facilities_text = (
                    FALLBACK_CONTACTS_SW if language == "sw" else FALLBACK_CONTACTS_EN
                )
        except Exception as e:
            logger.error(
                "Failed to fetch emergency facilities: %s, using fallback", str(e)
            )
            facilities_text = (
                FALLBACK_CONTACTS_SW if language == "sw" else FALLBACK_CONTACTS_EN
            )
    else:
        # No database session provided, use fallback
        facilities_text = (
            FALLBACK_CONTACTS_SW if language == "sw" else FALLBACK_CONTACTS_EN
        )

    # Build footer
    footer = (
        EMERGENCY_RESPONSE_FOOTER_SW
        if language == "sw"
        else EMERGENCY_RESPONSE_FOOTER_EN
    )

    return header + facilities_text + footer


def get_emergency_response_sync(language: str = "en") -> str:
    """
    Get emergency response message without database access (fallback).

    DEPRECATED: Use get_emergency_response() instead with database session.
    This function is kept for backward compatibility only.
    """
    header = (
        EMERGENCY_RESPONSE_HEADER_SW
        if language == "sw"
        else EMERGENCY_RESPONSE_HEADER_EN
    )
    contacts = FALLBACK_CONTACTS_SW if language == "sw" else FALLBACK_CONTACTS_EN
    footer = (
        EMERGENCY_RESPONSE_FOOTER_SW
        if language == "sw"
        else EMERGENCY_RESPONSE_FOOTER_EN
    )
    return header + contacts + footer
