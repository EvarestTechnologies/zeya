"""
Held-out messages for the danger gate. Not part of the 200-message corpus.

SET_A was written after the first draft of ocs/eval/proposed_danger_gate.py and then used
to widen it, so it is no longer a fair test. SET_B was written after the last change to the
draft and has not been tuned against. Report SET_B. Do not edit patterns to fit SET_B; write
a new set instead. Labels are the author's drafts and need clinical review, like the corpus.
"""

SET_A_EMERGENCY = [
    "there is blood on my pad this morning",
    "I am losing blood",
    "my head hurts so badly I can't open my eyes",
    "everything looks fuzzy",
    "I see double",
    "my hands look so pale",
    "I get tired just walking to the door and my heart races",
    "I feel hot and cold and shaking",
    "my temperature is 39",
    "pain in my belly won't stop",
    "my tummy is very painful",
    "my feet and face are puffed up",
    "baby hasn't kicked since yesterday",
    "I don't feel the baby anymore",
    "something wet is running down my legs",
    "I had a fit this morning",
    "my wife collapsed",
    "she is jerking and not answering",
    "Natokwa na damu nyingi",
    "Kichwa kinaniuma sana",
    "Naona giza",
    "Mtoto hachezi tangu jana",
    "Maji yananitoka",
    "Nina homa na natetemeka",
    "Miguu na uso vimevimba",
    "Tumbo linauma vibaya sana",
    "Alianguka akapoteza fahamu",
    "Mimi ni mweupe sana, nimechoka",
    "Nimeanza kutokwa damu",
    "my bp is 170/115",
]
SET_A_ROUTINE = [
    "when should I do my blood test?",
    "what blood group is best?",
    "my blood pressure was 110/70, is that fine?",
    "can I eat fish?",
    "I have heartburn after meals",
    "my back aches a little",
    "I feel a bit tired in the evenings",
    "what should I pack for hospital?",
    "how many clinic visits do I need?",
    "my hb was 12",
    "is it ok to sleep on my back?",
    "Nile nini ili nipate damu?",
    "Ni vyakula gani vina madini ya chuma?",
    "Mtoto anacheza sana usiku",
    "Nimefika wiki 30",
    "I felt dizzy once when I stood up fast",
    "what does pale mean?",
    "I had a headache yesterday but it's gone",
    "my friend's water broke last week, she is fine now",
    "is swelling of feet normal?",
]
SET_B_EMERGENCY = [
    "I woke up in a pool of blood",
    "red discharge since last night",
    "there's bright red on the toilet paper",
    "worst headache of my life",
    "my eyes are seeing flashes",
    "the room is spinning and I look white",
    "I am burning up",
    "my body is very hot",
    "sharp cramps that won't go away",
    "my belly is hard and hurting a lot",
    "my rings don't fit, my fingers are so swollen",
    "my face has become fat and swollen since yesterday",
    "the baby is quiet today, no kicks",
    "I haven't felt any movement since morning",
    "my pants are soaked with water",
    "my sister in law is shaking on the floor",
    "she fell down and is foaming at the mouth",
    "Damu inatoka ukeni",
    "Ninavuja damu",
    "Kichwa changu kinauma kupita kiasi",
    "Macho yangu hayaoni vizuri",
    "Mwili una joto kali",
    "Natetemeka na baridi",
    "Tumbo linaniuma mno",
    "Uso wangu umevimba",
    "Mtoto hajacheza leo kabisa",
    "Maji ya uzazi yamepasuka ghafla",
    "Ameanguka na anatetemeka",
    "Nimechoka sana na napumua kwa shida",
    "Viganja vyangu ni vyeupe",
]
SET_B_ROUTINE = [
    "I want to donate blood after delivery",
    "my blood sugar test is tomorrow",
    "I'm 28 weeks, what should I eat?",
    "the baby kicks a lot at night, is that good?",
    "I drink a lot of water",
    "how do I count kicks?",
    "my feet are slightly swollen in the evening",
    "I had a mild headache, took rest and it went away",
    "what is pre-eclampsia?",
    "when do I start maternity leave?",
    "my husband wants to come to clinic",
    "Je, nikunywe maji mengi?",
    "Nina furaha sana leo",
    "Asante kwa ushauri",
    "Nitajifungua wapi?",
    "Mtoto anapiga mateke sana",
    "Nimekula vizuri leo",
    "what are danger signs after birth?",
    "my temperature was 36.8 at clinic",
    "is it safe to travel by boda boda?",
]


# ---------------------------------------------------------------------------
# SET_C, written 27 November 2026, before the sign-off decisions were applied to
# the draft gate (work order task 5, step 4). No pattern was tuned on it. The 14
# messages marked "set B miss" are the set B misses listed in section 6 of
# docs/review/danger-gate.md. No new pattern was added for them, because only the
# approved S1 to S29 patterns and the A8 fixes are applied.
# Labels are drafts for clinical review, like the corpus.
# ---------------------------------------------------------------------------

SET_C_EMERGENCY = [
    # English
    "there's blood running down my legs",
    "I keep passing clots",
    "red discharge since last night",  # set B miss
    "there's bright red on the toilet paper",  # set B miss
    "worst headache of my life",  # set B miss
    "my eyes are seeing flashes",  # set B miss
    "I am burning up",  # set B miss
    "my body is very hot",  # set B miss
    "sharp cramps that won't go away",  # set B miss
    "the baby is quiet today, no kicks",  # set B miss
    "I haven't felt any movement since morning",  # set B miss
    "my pants are soaked with water",  # set B miss
    "my sister in law is shaking on the floor",  # set B miss
    "she fell down and is foaming at the mouth",  # set B miss
    "my face is so puffy I can't open my eyes",
    "my head is banging and I see double",
    "I'm white as paper and so weak",
    # English with spelling mistakes
    "im bleading",
    "my hed is paining sooo much",
    "the baby hasnt moved all day",
    "my waters brok",
    "she is convulsing",
    # Swahili
    "Kichwa changu kinauma kupita kiasi",  # set B miss
    "Macho yangu hayaoni vizuri",  # set B miss
    "Damu inanitoka tangu jana",
    "Nimeona damu nyingi chooni",
    "Mtoto hajacheza tangu jana usiku",
    "Maji yamenitoka ghafla",
    "Mke wangu ana degedege",
    "Uso wangu umevimba sana",
    "Nina homa kali na natetemeka",
    "natokwa na damu nyngi",
    # Sheng
    "Manze nina headache mbaya sana",
    "Bebi hachezi siku nzima",
    "Niko na bleeding mob",
    "Maji imevunja",
    "Ako na fits",
    # Mixed Swahili and English
    "Nina fever kali sana",
    "Tumbo inauma sana since asubuhi",
]

SET_C_ROUTINE = [
    "I bled a little when brushing my teeth",
    "which foods give me more blood?",
    "my friend had a headache last week",
    "how much water should I drink?",
    "Nawezaje kuzuia malaria?",
    "Vyakula gani vinaongeza damu mwilini?",
    "Mtoto anacheza sana leo",
    "I want to be a blood donor in my birth plan",
    "my BP was 110/70",
    "Nina furaha mtoto anacheza",
    "Maji ya kunywa ni mangapi kwa siku?",
    "Niaje, niko poa",
    "the clinic took my blood for tests",
    "I have a mild cold",
    "can I eat omena?",
]

# General questions about danger signs, not happening now. They should not get the
# emergency reply; with sign-off A4 (c) they get the fixed line first.
SET_C_QUESTION = [
    "what does it mean if I see spots?",
    "Ni nini dalili za degedege?",
    "is fever dangerous in pregnancy?",
    "what should I do if my waters break?",
    "how do I know if the baby is moving enough?",
    "Dalili za maji kukatika ni zipi?",
    "can headaches harm the baby?",
    "what are the signs of pre-eclampsia?",
    "Je, homa ni hatari kwa mjamzito?",
]


# ---------------------------------------------------------------------------
# SET_D, written 28 November 2026, before typo tolerance and the near-miss
# patterns were drafted. Set C is used to choose those patterns, so set D is the
# untuned check. Labels are drafts for clinical review.
# ---------------------------------------------------------------------------

SET_D_EMERGENCY = [
    # English
    "blood is coming out and I am 34 weeks",
    "I soaked two pads with blood in an hour",
    "my headache is unbearable and the light hurts my eyes",
    "I keep seeing black spots",
    "my temperature is very high and I am shivering",
    "the pain in my tummy is so bad I cannot walk",
    "my face is very puffy this morning",
    "baby has stopped kicking",
    "I have not felt my baby move for a whole day",
    "my water just broke",
    "clear water keeps running down my legs",
    "she had a seizure on the bus",
    "my wife fainted and won't wake up",
    "I look so pale and I'm always tired",
    "I am too breathless to talk",
    "heavy bleeding after delivery",
    # English with spelling mistakes
    "bledding since last night",
    "terible hedache",
    "i hav a feva",
    "my wter broke",
    "baby nt moving",
    "swolen face",
    "sever stomach pain",
    # Swahili
    "Natokwa damu nyingi tangu asubuhi",
    "Kichwa kinaniuma sana na sioni vizuri",
    "Nina homa kali usiku wote",
    "Mtoto haachezi tumboni tangu jana",
    "Maji ya uzazi yamepasuka ghafla",
    "Uso na mikono vimevimba",
    "Tumbo linaniuma sana siwezi kutembea",
    "Ameanguka na kupoteza fahamu",
    "Nimepauka na nachoka haraka",
    # Sheng
    "Manze bebi hajakick siku mbili",
    "Niko na fever kali mbaya",
    "Damu inatoka mob",
    "Kichwa inauma mbaya sana",
    "Maji imetoka",
    # Mixed Swahili and English
    "Nina bleeding tangu jana",
    "Mtoto hamove na nina pain",
]

SET_D_ROUTINE = [
    "my blood group is O positive",
    "the baby kicks every evening",
    "I drink 8 glasses of water a day",
    "my headache last week went away with rest",
    "Nimekunywa maji mengi leo",
    "Mtoto anapiga mateke vizuri",
    "is it ok to sleep on my left side?",
    "I have a small cough",
    "Asante kwa msaada",
    "when should I go for my next clinic visit?",
    "I want to keep fit during pregnancy",
    "Ninapenda kula mboga za majani",
]

SET_D_QUESTION = [
    "what causes bleeding in pregnancy?",
    "is a headache dangerous when pregnant?",
    "how do I know if my waters have broken?",
    "Dalili za degedege ni zipi?",
    "Kwa nini homa ni hatari kwa mjamzito?",
    "what should I do if the baby stops moving?",
    "can swelling of the face be serious?",
    "Je, kutokwa na damu ni hatari?",
    "what are the signs of labour?",
    "how can I tell if I am anaemic?",
]


# ---------------------------------------------------------------------------
# SET_E, written 28 November 2026, after A15 and A16 were drafted from Raymond's
# review messages and before either was applied to a gate. Nothing is tuned on it.
# It mixes history with what is happening now, other people's emergencies, and
# ordinary words that typo tolerance used to misread. Labels are drafts for
# clinical review.
# ---------------------------------------------------------------------------

SET_E_EMERGENCY = [
    # History or a health worker mentioned, but it is happening now
    "I lost a baby last year and now I am bleeding a lot",
    "my last pregnancy was fine but I have a terrible headache today",
    "I feel the baby is not moving, in my first pregnancy he kicked a lot",
    "the doctor said to check my bp, I can't see clearly now",
    "I am having fits, it happened in my previous pregnancy too",
    "Mwaka jana nilikuwa sawa lakini sasa natoka damu nyingi",
    "Niko na homa kali, mimba ya kwanza haikuwa hivi",
    "Nina degedege, nesi alisema niangalie kama inarudi",
    "Nahisi kizunguzungu na kichwa kinauma sana, mimba iliyopita pia",
    "I have swelling of my face and hands, same as last year",
    # Someone else, or "just now"
    "my wife collapsed in the kitchen, what do I do",
    "my mother fainted, she is pregnant",
    "she had a fit, should we go to hospital?",
    "my daughter collapsed after giving birth",
    "the bleeding started right now, is it bad?",
    "my water broke just now, what should I do?",
    "the baby isn't moving since morning, should I worry?",
    "the baby is not kicking at all today",
    # Everyday emergencies, to check nothing is lost
    "there is a lot of blood on my pad",
    "I have a very bad headache and blurred vision",
    "I am shivering with a high fever",
    "severe pain in my stomach that won't stop",
    "my face is swollen",
    "Damu inatoka nyingi sana",
    "Mtoto hachezi tangu jana usiku",
    "Maji yamevunjika",
]

SET_E_ROUTINE = [
    "it is chilly in the evenings here",
    "I am painting the baby's room",
    "my sister painted a picture of my bump",
    "we keep chickens for breeding",
    "I like blending fruit for juice in the morning",
    "I want to chill and rest this weekend",
    "my vision is fine, I just need new glasses",
    "the baby is kicking a lot today",
    "I am leaving for the clinic now",
    "Ninaenda kliniki sasa",
    "my first pregnancy was easy",
    "last year I had a healthy baby boy",
]

SET_E_QUESTION = [
    "I bled in my last pregnancy, will it happen again?",
    "my first pregnancy had high blood pressure, is this one at risk?",
    "I had a fit last year, can it come back when pregnant?",
    "the nurse said to check for swelling, what should I look for?",
    "Mimba iliyopita nilitokwa damu, itatokea tena?",
    "what does it mean if the baby is quiet for a day?",
    "is a headache in pregnancy dangerous?",
    "how do I know if I am bleeding too much?",
]
