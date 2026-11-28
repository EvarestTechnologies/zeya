"""
PROPOSAL ONLY. Not deployed, not used by the pipeline. For review in
docs/danger-gate-review.md before any change to ocs/nodes/danger_gate.py or
backend/app/services/danger_signs.py.

Same contract as ocs/nodes/danger_gate.py (same temp-state keys, same tags), with:
  * the 39 existing patterns kept, in order, at the start of each category;
  * new English and Swahili patterns for the phrasings in ocs/eval/corpus.py;
  * a ninth category, "pallor_anaemia" (handbook p14), with the anaemia symptoms of BOP p39;
  * severe booklet readings (BP 160/110 or above, haemoglobin below 7);
  * a question check: a match inside a general question about danger signs, with no
    sign that it is happening to the mother now, goes to SAFE and is tagged
    "danger_question" so the LLM can answer it. Any present-tense first-person
    symptom keeps the emergency route.
"""


def main(input: str, **kwargs) -> str:
    import re

    def rx(p):
        return re.compile(p, re.IGNORECASE)

    danger_sign_patterns = [
        (
            "bleeding",
            [
                rx(r"\b(heavy\s+)?bleeding\b"),
                rx(r"\bexcessive\s+blood\b"),
                rx(r"\bblood\s+(clots?|loss)\b"),
                rx(r"\bkutoka\s+damu\b"),
                rx(r"\bdamu\s+nyingi\b"),
                # proposed
                rx(r"\bbleed(s|ing)?\b"),
                rx(r"\bspotting\b"),
                rx(r"\bblood\b(?!\s*(pressure|test|tests|group|sugar|level|levels|count|type|donor|transfusion|bank))"),
                rx(r"(toka|tokwa\s+na|ona|vuja)\s+damu\b"),
                rx(r"\b(losing|lost|passing|passed)\s+(some\s+|a\s+lot\s+of\s+)?blood\b"),
                rx(r"tok(a|wa)\s+(na\s+)?damu\b"),
                rx(r"\bdamu\s+(ina|ime)?(toka|vuja|tiririka)"),
                rx(r"\bdamu\s+(kwenye|ukeni)\b"),
                # near miss, approved in sign-off A14
                rx(r"\b(passing|passed)\s+(blood\s+)?clots?\b"),
                rx(r"\b(red|bloody|bright\s+red)\b.{0,20}\b(discharge|toilet\s+paper|pad|underwear)\b"),
                rx(r"\bdamu\s+i?na\w*toka\b"),
            ],
        ),
        (
            "headache_vision",
            [
                rx(r"\bsevere\s+headache\b"),
                rx(r"\bblurred?\s+vision\b"),
                rx(r"\bvision\s+(is\s+)?blurred?\b"),
                rx(r"\bseeing\s+(spots?|stars?)\b"),
                rx(r"\bkichwa\s+kuuma\b"),
                rx(r"\bmacho\s+kuona\s+vibaya\b"),
                # proposed
                rx(r"\b(severe|bad|terrible|serious|strong|pounding|throbbing|splitting)\s+(\w+\s+)?headache\b"),
                rx(r"\bhead\s+(is\s+)?(pounding|throbbing|splitting)\b"),
                rx(r"\b(blurry|blurring|blurred)\b"),
                rx(r"\bflash(es|ing)?\s+(of\s+)?lights?\b"),
                rx(r"\bconfus(ed|ion)\b"),
                rx(
                    r"\bkichwa\b.{0,20}\b(\w*uma|\w*umwa|maumivu)\b.{0,20}\b(sana|mno|kali)\b|\b(\w*uma|\w*umwa|maumivu)\b.{0,20}\bkichwa\b.{0,20}\b(sana|mno|kali)\b"
                ),
                rx(r"\bmaumivu\s+makali\s+ya\s+kichwa\b"),
                rx(r"\bukungu\b"),
                rx(r"\bgiza\s+machoni\b"),
                rx(r"changanyikiwa\b"),
                rx(
                    r"\bhead\b.{0,25}\b(hurt(s|ing)?|pain(ful|s)?|ach(e|es|ing))\b.{0,25}\b(very|so|really|badly|terribl[ey]|a\s+lot|too\s+much|so\s+much|won'?t\s+stop|can'?t|unbearabl[ey])"
                ),
                rx(
                    r"\b(very|so|really|badly|terribl[ey]|a\s+lot|too\s+much|so\s+much|won'?t\s+stop|can'?t|unbearabl[ey])\b.{0,15}\bhead\s*ache\b"
                ),
                rx(r"\b(fuzzy|hazy|double\s+vision|see(ing)?\s+double|can'?t\s+see\s+(well|properly|clearly))\b"),
                rx(r"\bkichwa\b.{0,20}\b(kinauma|kinaniuma|kuuma)\b.{0,15}\b(sana|mno|vibaya)\b"),
                rx(r"\b(naona|ninaona)\s+(giza|ukungu|nyota|vibaya)\b|\bsioni\s+vizuri\b"),
                # blood pressure 160/110 or above (BOP p15)
                rx(r"\b(1[6-9]\d|2\d\d)\s*(/|over)\s*\d{2,3}\b"),
                rx(r"\b\d{2,3}\s*(/|over)\s*(1[1-9]\d)\b"),
                # near miss, approved in sign-off A14
                rx(r"\bworst\s+headache\b"),
                rx(r"\bheadache\b.{0,10}\b(mbaya|sana)\b"),
                rx(r"\b(seeing|see)\s+(black\s+)?(spots|flashes|flashing\s+lights)\b|\beyes\b.{0,15}\bflash(es|ing)\b"),
                rx(r"\bkichwa\b.{0,30}\bkupita\s+kiasi\b"),
                rx(r"\b(hayaoni|haoni)\s+vizuri\b"),
                # approved in sign-off A17
                rx(r"\bhead\s*ache\b.{0,20}\b(unbearable|won'?t\s+stop|too\s+much|is\s+(so|very|really)\s+bad)\b"),
            ],
        ),
        (
            "pallor_anaemia",
            [
                rx(
                    r"\b(look|looks|looking|am|is|'m|feel|become|became|becoming|turned|gone)\s+(very\s+|so\s+|really\s+)?pale\b"
                ),
                rx(r"\b(palms?|lips|eyes|nails|gums|tongue)\b.{0,20}\b(white|pale)\b"),
                rx(r"\b(breathless|out\s+of\s+breath|short(ness)?\s+of\s+breath)\b"),
                rx(r"\bdizz(y|iness)\b.{0,40}\b(heart|breath|pale|tired|all\s+the\s+time|always|every\s+day|keep)\b"),
                rx(r"\b(heart|breath|pale|tired|always|keep)\b.{0,40}\bdizz(y|iness)\b"),
                rx(r"\bheart\s+(is\s+)?(racing|pounding|beating\s+(very\s+)?fast)\b"),
                rx(r"\bextremely\s+tired\b"),
                rx(r"\b(hb|haemoglobin|hemoglobin|hgb)\b\D{0,15}\b[0-6](\.\d)?\b(?!\s*(/|over))"),
                rx(r"\b\w*pauka\b"),
                rx(r"\b(viganja|midomo|macho|kucha)\b.{0,25}\b(vyeupe|meupe|myeupe|nyeupe)\b"),
                rx(r"\bnimekuwa\s+mweupe\b|\bmeupe\s+sana\b"),
                rx(r"\bmweupe\b|\bweupe\b"),
                rx(r"\bheart\b.{0,10}\b(races?|racing|pounds?|pounding)\b"),
                rx(r"\btired\b.{0,25}\b(just|even)\s+(walking|standing|getting\s+up)\b"),
                rx(r"pumua\s+kwa\s+shida\b"),
                rx(r"\bkizunguzungu\b.{0,40}\b(moyo|pumua|mweupe|nimechoka|kila\s+siku|kila\s+mara|sana)\b"),
                rx(r"\bmoyo\b.{0,15}\b(unadunda|unapiga)\b.{0,15}\b(kasi|haraka)\b"),
                # near miss, approved in sign-off A14
                rx(r"\bwhite\s+as\s+(paper|chalk|a\s+sheet)\b"),
            ],
        ),
        (
            "fever",
            [
                rx(r"\bhigh\s+fever\b"),
                rx(r"\bsevere\s+fever\b"),
                rx(r"\bchills\b"),
                rx(r"\bhoma\s+kali\b"),
                rx(r"\bbaridi\s+mwilini\b"),
                # proposed
                rx(r"\bfever(ish)?\b"),
                rx(r"\bshiver(s|ing)?\b"),
                rx(r"\b(smell(y|s|ing)?|foul)\b.{0,20}\bdischarge\b|\bdischarge\b.{0,20}\b(smell|foul)"),
                rx(r"\bpain\b.{0,30}\bpelvi(s|c)\b|\bpelvi(s|c)\b.{0,30}\bpain\b"),
                rx(r"\bhoma\b"),
                rx(r"\bjoto\s+(jingi|kali|sana)\b|\bmwili\b.{0,15}\bjoto\b"),
                rx(r"tetemeka\b"),
                rx(r"\bhot\s+and\s+cold\b|\bshaking\b"),
                rx(r"\btemperature\b\D{0,15}\b(3[89]|4[0-2])(\.\d)?\b"),
                rx(
                    r"\b(uchafu|ute|majimaji)\b.{0,25}\b(unanuka|unaonuka|harufu)\b|\bharufu\s+mbaya\b.{0,25}\b(uchafu|ute|ukeni)\b"
                ),
                # near miss, approved in sign-off A14
                rx(r"\bburning\s+up\b"),
                # approved in sign-off A17
                rx(r"\b(feva|fiva)\b"),
                rx(r"\b(body|i\s+am|i'?m)\b.{0,10}\b(very|so)\s+hot\b"),
            ],
        ),
        (
            "fetal_movement",
            [
                rx(r"\breduced\s+fetal\s+movement\b"),
                rx(r"\bno\s+(fetal\s+)?movement\b"),
                rx(r"\bbaby\s+(not\s+moving|stopped?\s+moving|isn'?t\s+moving)\b"),
                rx(r"\bcan'?t\s+feel\s+(the\s+)?baby\b"),
                rx(r"\bmtoto\s+ha(tembei|chezi)\b"),
                # proposed
                rx(r"\bbaby\b.{0,20}\b(not|n'?t|has\s+not|stopped|no\s+longer)\b.{0,15}\b(mov|kick)"),
                rx(r"\bbaby\b.{0,15}\bmov(ing|es)\s+(less|much\s+less|very\s+little)\b"),
                rx(r"\b(haven'?t|have\s+not|not|can'?t|cannot|didn'?t)\s+(felt|feel)\s+(the\s+|my\s+)?baby\b"),
                rx(r"\bmovements?\s+(have\s+|has\s+)?(reduced|decreased|stopped|slowed)\b"),
                rx(r"\b(reduced|decreased|fewer|less)\s+(fetal\s+|baby'?s?\s+)?(movements?|kicks?)\b"),
                rx(r"\bmtoto\b.{0,20}\b(hachezi|hajacheza|hatembei|hasogei|hajasogea|amepunguza|ameacha\s+kucheza)\b"),
                rx(r"\bsi(m)?hisi\s+mtoto\b"),
                rx(r"\bha(ja)?move\b"),
                rx(r"\bbaby\b.{0,15}\b(hasn'?t|has\s+not|hadn'?t|not|didn'?t)\s+(kicked|moved)\b"),
                rx(r"\b(don'?t|do\s+not|can'?t|cannot|no\s+longer)\s+feel\s+(the\s+|my\s+)?baby\b"),
                # near miss, approved in sign-off A14
                rx(r"\b(haven'?t|have\s+not|not|didn'?t)\s+(felt|feel)\s+(any\s+)?(movement|movements|kicks?)\b"),
                rx(r"\bno\s+kicks?\b"),
                rx(r"\b(bebi|mtoi)\b.{0,20}\b(hachezi|hajacheza|hajamove|hamove)\b"),
                # approved in sign-off A17
                rx(r"\bha(ja)?kicki?\b"),
            ],
        ),
        (
            "abdominal_pain",
            [
                rx(r"\bsevere\s+(abdominal\s+)?pain\b"),
                rx(r"\bstomach\s+pain\b"),
                rx(r"\bsharp\s+pain\b"),
                rx(r"\btumbo\s+kuuma\s+sana\b"),
                # proposed
                rx(r"\b(severe|bad|terrible|strong|sharp)\s+(abdominal|stomach|tummy|belly)\s+pain\b"),
                rx(
                    r"\b(stomach|tummy|belly|abdomen)\b.{0,25}\b(hurt(s|ing)?|pain(ful)?|aching)\b.{0,25}\b(so\s+much|a\s+lot|badly|can'?t)\b"
                ),
                rx(r"\b(pain|ache)\b.{0,15}\b(under|below)\s+(my\s+)?ribs?\b"),
                rx(
                    r"\btumbo\b.{0,20}\b(\w*uma|\w*umwa|maumivu)\b.{0,20}\b(sana|mno|kali)\b|\b(\w*uma|\w*umwa|maumivu)\b.{0,20}\btumbo\b.{0,20}\b(sana|mno|kali)\b"
                ),
                rx(r"\bmaumivu\s+makali\s+ya\s+tumbo\b"),
                rx(
                    r"\b(stomach|tummy|belly|abdomen|abdominal)\b.{0,25}\b(hurt(s|ing)?|pain(ful|s)?|ach(e|es|ing))\b.{0,25}\b(very|so|really|badly|terribl[ey]|a\s+lot|too\s+much|so\s+much|won'?t\s+stop|can'?t|unbearabl[ey])"
                ),
                rx(
                    r"\b(very|so|really|badly|terribl[ey]|a\s+lot|too\s+much|so\s+much|won'?t\s+stop|can'?t|unbearabl[ey])\b.{0,15}\b(painful|sore)\b.{0,5}$|\b(stomach|tummy|belly)\s+is\s+(very|so|really|badly|terribl[ey]|a\s+lot|too\s+much|so\s+much|won'?t\s+stop|can'?t|unbearabl[ey])\s+painful\b"
                ),
                rx(
                    r"\bpain\b.{0,20}\b(stomach|tummy|belly|abdomen)\b.{0,25}\b(very|so|really|badly|terribl[ey]|a\s+lot|too\s+much|so\s+much|won'?t\s+stop|can'?t|unbearabl[ey])"
                ),
                rx(
                    r"\btumbo\b.{0,20}\b(\w*uma|\w*umwa|maumivu)\b.{0,20}\bvibaya\b|\b(\w*uma|\w*umwa|maumivu)\b.{0,20}\btumbo\b.{0,20}\bvibaya\b"
                ),
                rx(r"\bmaumivu\b.{0,20}\bmbavu\b"),
                # near miss, approved in sign-off A14
                rx(
                    r"\bcramps?\b.{0,25}\b(won'?t\s+(go|stop)|severe|sharp|bad|unbearable)\b|\b(severe|sharp|bad)\s+cramps?\b"
                ),
            ],
        ),
        (
            "water_breaking",
            [
                rx(r"\bwater\s+(break(ing|s)?|broke)\b"),
                rx(r"\bfluid\s+(leaking|leakage|gushing)\b"),
                rx(r"\bleaking\s+fluid\b"),
                rx(r"\bmaji\s+ya(mekatika|kutoka)\b"),
                # proposed
                rx(r"\bwaters?\s+(have\s+|has\s+)?(broke|broken|burst)\b"),
                rx(r"\bwater\b.{0,20}\bleak"),
                rx(r"\bleak(ing|s)?\b.{0,25}\b(water|fluid)\b"),
                rx(r"\bmaji\b.{0,15}\b(yametoka|yanatoka|yanavuja|yamevunjika|yamepasuka|yamekatika)\b"),
                rx(r"\bchupa\b.{0,10}\b(imepasuka|imevunjika|imetoboka)\b"),
                rx(
                    r"\b(wet|water|fluid|liquid)\b.{0,30}\b(running|gushing|dripping|pouring|trickling)\b.{0,20}\b(legs?|down)\b"
                ),
                rx(r"\bmaji\b.{0,10}\bya\w*toka\b"),
                # near miss, approved in sign-off A14
                rx(r"\bsoaked\b.{0,20}\b(water|fluid|wet)\b"),
                rx(r"\bmaji\b.{0,10}\b(imevunja|imevunjika|imepasuka)\b"),
                # approved in sign-off A17
                rx(r"\bwaters?\s+(just|has\s+just|have\s+just|already|suddenly)\s+(broke|broken|burst)\b"),
                rx(r"\b(wter|watr|wata|warer)\b.{0,15}\b(broke|broken|burst)\b"),
                rx(r"\bmaji\b.{0,10}\bimetoka\b"),
            ],
        ),
        (
            "convulsions",
            [
                rx(r"\bconvulsion\b"),
                rx(r"\bseizure\b"),
                rx(r"\bloss\s+of\s+consciousness\b"),
                rx(r"\bfaint(ed|ing)\b"),
                rx(r"\bpassed?\s+out\b"),
                rx(r"\bdegedege\b"),
                rx(r"\bkupoteza\s+fahamu\b"),
                # proposed
                rx(r"\bconvulsions\b"),
                rx(r"\bseizures\b"),
                rx(r"\b(had|having|have|has)\s+(a\s+)?fits?\b"),
                rx(r"\bunconscious\b|\bblack(ed)?\s+out\b"),
                rx(r"zirai\b"),
                rx(r"anguka\b.{0,25}tetemeka\b"),
                rx(r"\bcollaps(e|ed|es|ing)\b"),
                rx(r"\bjerking\b|\b(not|isn'?t)\s+(answering|responding|waking)\b|\bunresponsive\b"),
                rx(r"poteza\s+fahamu\b|\bamezimia\b|\balizimia\b"),
                # near miss, approved in sign-off A14
                rx(r"\bconvuls(ing|ed|es)\b"),
                rx(r"\b(ako|yuko|ana|niko|nina)\s+na\s+fits?\b"),
                rx(r"\bfoam(ing)?\s+at\s+the\s+mouth\b"),
            ],
        ),
        (
            "swelling",
            [
                rx(r"\bsevere\s+swelling\b"),
                rx(r"\bswollen\s+(face|hands?|feet)\b"),
                rx(r"\bkuvimba\s+sana\b"),
                # proposed
                rx(r"\b(face|hands?|fingers|eyes)\b.{0,20}\b(swollen|swelling|puffy|swell(ed|ing)?)\b"),
                rx(r"\b(puffy)\s+(face|hands?|fingers|eyes)\b"),
                rx(r"\bswell(ed|ing)\s+up\b"),
                rx(r"\b(face|hands?|fingers|eyes)\b.{0,25}\b(puffed|puffy|bloated)\b|\b(puffed|swollen)\s+up\b"),
                rx(
                    r"\b(uso|mikono|vidole|macho)\b.{0,20}\b(umevimba|imevimba|vimevimba|yamevimba|kuvimba|umefura|imefura|vimefura|kufura)\b"
                ),
                # approved in sign-off A17
                rx(r"\bswell(ing|ed)\s+(of|in|on)\s+(my\s+|the\s+)?(face|hands?|fingers|eyes)\b"),
            ],
        ),
    ]

    # General questions about danger signs (proposed).
    info_question = [
        rx(r"\b(what|which)\s+(are|is)\s+(the\s+)?(\w+\s+)?signs\b"),
        rx(r"\bsigns\s+of\b"),
        rx(r"\bis\s+(it\s+|\w+\s+){0,3}normal\b"),
        # near miss, approved in sign-off A14
        rx(r"\bis\s+(it\s+|\w+\s+){0,2}(dangerous|serious)\b"),
        # approved in sign-off A17
        rx(r"\bwhat\s+does\b.{0,40}\bmean\b"),
        rx(r"\bcan\s+(a|an)\s+\w+\s+harm\b"),
        rx(r"\bhow\s+(can|do)\s+i\s+(avoid|prevent|know|stop)\b"),
        rx(r"\bkuzui\w*|\bnawezaje\b"),
        rx(r"^\s*je\b.*\?\s*$"),
        rx(r"\b(what|how)\b.{0,30}\bif\b"),
        rx(r"\bwhat\s+does\s+\w+\s+mean\b"),
        rx(r"^\s*(will|would|can|could|should|does|do)\b.*\?\s*$"),
        rx(r"\b(my|a)\s+(friend|sister|neighbou?r|cousin)\b"),
        rx(r"\bdalili\s+za\b"),
        rx(r"\bni\s+kawaida\b"),
        rx(r"\binaweza\s+kumdhuru\b"),
        rx(r"\bnifanye\s+nini\b.*\b\w+ki\w+\b"),
    ]
    # Context that makes a match general rather than happening now (sign-off A8):
    # a question about what the clinic checks, a past pregnancy, or blood that is
    # not vaginal (gums, nose, foods that "add blood"). These override happening_now.
    general_context = [
        rx(
            r"\b(nurse|clinic|health\s+worker|doctor|nesi|daktari|wanaangalia|wanapima)\b.{0,40}\b(check|test|look|kama|if|whether)\b"
        ),
        rx(
            r"\b(first|last|previous|past)\s+pregnancy\b|\bmimba\s+(ya\s+kwanza|iliyopita)\b|\blast\s+year\b|\bmwaka\s+jana\b"
        ),
    ]
    # Blood that is not from the vagina. A bleeding match is dropped when one of
    # these is present and no vaginal word is.
    not_obstetric_blood = [
        rx(r"\b(gums?|teeth|tooth|brush\w*|nose|ufizi|fizi|meno|pua)\b"),
        rx(
            r"\b(foods?|eat|vyakula|chakula|kula)\b.{0,30}\b(blood|damu)\b|\b(add|adds|increase|build|give\w*)\s+(me\s+)?(more\s+)?blood\b|ongeza\s+damu"
        ),
    ]
    vaginal_words = rx(r"\b(vagina\w*|ukeni|down\s+there|pad|chupi|toilet)\b")
    # Signs that it is happening to her now: these keep the emergency route.
    happening_now = [
        # near miss, approved in sign-off A14: someone with her, happening now
        rx(r"\b(she|he|my\s+(wife|sister|mother|daughter|friend|neighbou?r|cousin)(\s+in\s+law)?)\s+is\b"),
        rx(r"\b(i'?m|i\s+am|i\s+have|i'?ve|i\s+had|i\s+feel|i\s+see|i\s+can'?t|i\s+haven'?t|i\s+look)\b"),
        rx(
            r"\bmy\s+(face|hands?|waters?|vision|head|stomach|tummy|palms|lips|blood\s+pressure|bp|hb)\s+(is|are|has|have|was|were|broke|hurts?)\b"
        ),
        rx(r"\bmy\s+baby\s+(has|is|hasn'?t|isn'?t|stopped|won'?t|doesn'?t)\b"),
        rx(r"\b(nina|niko|natoka|naona|naumwa|nahisi|sihisi|simhisi|nimeona|nimeanza)\b"),
        rx(r"\bnime\w+|\bnili\w+"),
        # approved in sign-off A15: someone else's emergency, "just now", and the baby now
        rx(
            r"\b(she|he|my\s+(wife|sister|mother|daughter|friend|neighbou?r|cousin)(\s+in\s+law)?)\s+(just\s+)?(fainted|collapsed|had\s+a\s+fit)\b"
        ),
        rx(r"\b(just|right)\s+now\b"),
        rx(r"\bthe\s+baby\s+(is|isn'?t)\b"),
    ]
    # Approved in sign-off A15: present-tense words that override general_context, so
    # history ("last year", "first pregnancy") cannot soften a message about now.
    # "I had" and "nili..." are left out on purpose, so history questions stay questions.
    present_now = rx(r"\b(i'?m|i\s+am|i\s+have|i\s+feel|i\s+can'?t|now|nina|niko|natoka|naona|nahisi|sasa|nimeanza)\b")

    # Typo tolerance (approved in sign-off A13). A word one letter away from a danger word of
    # six or more letters is read as that word, for pattern matching only. Shorter danger
    # words are left out because ordinary words sit one letter away from them
    # ("flood" and "blood", "later" and "water", "home" and "homa").
    typo_vocabulary = [
        "bleeding",
        "headache",
        "severe",
        "terrible",
        "blurred",
        "blurry",
        "vision",
        "flashes",
        "feverish",
        "chills",
        "shivering",
        "stomach",
        "abdominal",
        "swollen",
        "swelling",
        "moving",
        "movement",
        "movements",
        "kicking",
        "broken",
        "leaking",
        "convulsion",
        "convulsions",
        "seizure",
        "seizures",
        "fainted",
        "fainting",
        "unconscious",
        "breathless",
        "dizziness",
        "kinauma",
        "hachezi",
        "hajacheza",
        "degedege",
        "yamevunjika",
        "yamepasuka",
        "umevimba",
        "vimevimba",
        "linauma",
        "kutokwa",
    ]

    # Approved in sign-off A16: real words that typo tolerance would misread as danger
    # words ("chilly" as "chills"). They are never corrected.
    typo_exempt = [
        "chilly",
        "chill",
        "painted",
        "painting",
        "sainted",
        "fainter",
        "blending",
        "breeding",
        "flurry",
        "slurry",
        "burry",
        "burred",
    ]

    def one_edit(word, target):
        if word == target or abs(len(word) - len(target)) > 1:
            return False
        if len(word) == len(target):
            diffs = [i for i in range(len(word)) if word[i] != target[i]]
            if len(diffs) == 1:
                return True
            return (
                len(diffs) == 2
                and diffs[1] == diffs[0] + 1
                and word[diffs[0]] == target[diffs[1]]
                and word[diffs[1]] == target[diffs[0]]
            )
        short = word if len(word) < len(target) else target
        long = target if len(word) < len(target) else word
        for i in range(len(long)):
            if long[:i] + long[i + 1 :] == short:
                return True
        return False

    corrected_words = []
    for word in re.findall(r"[a-z']+|[^a-z']+", input.lower()):
        replacement = word
        if len(word) >= 5 and word not in typo_vocabulary and word not in typo_exempt:
            for target in typo_vocabulary:
                if one_edit(word, target):
                    replacement = target
                    break
        corrected_words.append(replacement)
    corrected = "".join(corrected_words)
    use_corrected = corrected != input.lower()

    categories_found = []
    keywords_found = []
    for category, patterns in danger_sign_patterns:
        for pattern in patterns:
            match = pattern.search(input)
            if not match and use_corrected:
                match = pattern.search(corrected)
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
        question = (general and not present_now.search(input)) or (asks and not now)

    route = "EMERGENCY" if categories_found and not question else "SAFE"
    set_temp_state_key("danger_route", route)
    set_temp_state_key("danger_categories", categories_found)
    set_temp_state_key("danger_keywords", keywords_found)
    set_temp_state_key("danger_question", question)

    for category in categories_found:
        add_message_tag("danger_sign:" + category)
    for index in range(len(keywords_found)):
        keyword = " ".join(keywords_found[index].split())
        add_message_tag(("danger_keyword:" + categories_found[index] + ":" + keyword)[:100])
    if question:
        add_message_tag("danger_question")

    return input
