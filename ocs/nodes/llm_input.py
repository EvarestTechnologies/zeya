"""
Open Chat Studio Python node: privacy-preserving LLM input.

Sanitizes the question before it reaches the language model by removing:
  - The exact saved participant name (whole-word, case-insensitive)
  - Phone numbers: any +CC international prefix, plus Kenya-local prefixes
    254 / 07 / 01 without +, contiguous or with space/hyphen/parenthesis
    separators, fullwidth digit encoding, or zero-width characters inserted
    between groups
  - Email addresses (RFC-5321 local-part @ domain pattern)

Ordinary text, pregnancy-week numbers, dates, and all other content are
preserved. Fullwidth ASCII digits (U+FF10–U+FF19) are normalised to ASCII
before matching; zero-width characters (U+200B/C/D, U+FEFF, U+00AD) are
stripped before matching and do not appear in the output.

LIMITATIONS — this is best-effort sanitization, not a universal PII filter:
  - Name: only the exact value stored in participant_data.name is matched.
    Names shared verbally but not registered, names corrected by an operator
    after registration, common words that happen to equal the saved name,
    and very short names may cause under- or over-removal.
  - Phone: the generic +CC branch covers any number starting with +.
    Kenya-local bare prefixes (254, 07, 01) are also covered.
    Numbers written without any country-code or local prefix are not matched.
  - Email: basic pattern; unusual local-part quoting not covered.
  - Historical turns already in LLM node context are not re-sanitized.
    See docs/review/system-prompt.md for the history_type=none requirement
    that eliminates that channel.

No temp-state keys are written. Participant data is read-only.
Allowed imports: re (stdlib, in OCS allowed set).
"""


def main(input: str, **kwargs) -> str:
    import re

    text = input or ""
    data = get_participant_data() or {}

    # --- 1. Normalise fullwidth ASCII digits (U+FF10–U+FF19 → 0–9) ---
    # Chain of .replace() calls avoids str.translate / str.maketrans.
    text = (
        text.replace("\uff10", "0")
        .replace("\uff11", "1")
        .replace("\uff12", "2")
        .replace("\uff13", "3")
        .replace("\uff14", "4")
        .replace("\uff15", "5")
        .replace("\uff16", "6")
        .replace("\uff17", "7")
        .replace("\uff18", "8")
        .replace("\uff19", "9")
    )

    # --- 2. Strip zero-width characters ---
    # U+200B zero-width space, U+200C ZWNJ, U+200D ZWJ,
    # U+FEFF BOM/ZWNBSP, U+00AD soft hyphen
    text = re.sub(r"[\u200b\u200c\u200d\ufeff\u00ad]", "", text)

    # --- 3. Name sanitisation ---
    # Removes exact saved name only (whole-word, case-insensitive).
    # Empty or missing name: skip entirely.
    name = (data.get("name") or "").strip()
    if name:
        text = re.sub(r"(?i)\b" + re.escape(name) + r"\b", "[name]", text)

    # --- 4. Phone sanitisation ---
    #
    # Two branches in one compiled pattern:
    #
    # Branch A — generic +CC international:
    #   (?<!\w)                not preceded by a word character
    #   \+\d{1,3}              + followed by 1-3 digit country code (greedy)
    #   (?:[\s\-\(\)]*\d){6,13} 6-13 more digit positions; zero-or-more
    #                          space/hyphen/paren separators allowed before
    #                          each digit to handle "+1 (202) 555-0100"
    #   (?!\d)                 not followed by a digit
    #
    # Branch B — Kenya local bare prefix (no +):
    #   (?<!\w)
    #   (?:254|07|01)          Kenya prefix without +
    #   (?:[\s\-]?\d){7,11}   7-11 more digit positions, one optional sep
    #   (?!\d)
    #
    # +254 is covered by Branch A (the \d{1,3} matches "254").
    #
    # Preservation guarantee (both branches):
    #   "+20 weeks"   → '+20' prefix; ' w' fails [\s\-\(\)]*\d → 0 reps < 6
    #   "+2024"       → greedy takes '+202'; '4' = 1 rep < 6 → no match
    #   "07 weeks"    → '07' prefix; ' w' fails [\s\-]?\d → no match
    #   "07/08/2025"  → '/' not in [\s\-]; no match
    #   "(Kisumu)"    → no matching prefix → no match
    #
    # Callback strips separators/+ then requires ≥8 total digits so short
    # sequences (PIN codes, etc.) are not affected.
    phone_re = re.compile(
        r"(?<!\w)"
        r"(?:"
        r"\+\d{1,3}(?:[\s\-\(\)]*\d){6,13}"
        r"|"
        r"(?:254|07|01)(?:[\s\-]?\d){7,11}"
        r")"
        r"(?!\d)"
    )

    def replace_phone(m):
        clean = re.sub(r"[\s\-+\(\)]", "", m.group())
        return "[phone]" if len(clean) >= 8 else m.group()

    text = phone_re.sub(replace_phone, text)

    # --- 5. Email sanitisation ---
    text = re.sub(
        r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}",
        "[email]",
        text,
    )

    return text
