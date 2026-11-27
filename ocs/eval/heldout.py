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
    "Maji yamepasuka",
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
