"""
Host-side PII scrubbing for Zeya transcript exports (#55).

Replaces four classes of personal identifiers with fixed placeholders:
  [NAME]        -- participant name from Participant Name column / data.name field
  [PHONE]       -- Kenya-local and international phone numbers
  [EMAIL]       -- email addresses
  [PERSONAL_ID] -- labelled national-ID and passport numbers only

Design constraints
------------------
- Deterministic and idempotent; no model/NER/fuzzy matching.
- Application order: emails -> personal IDs -> masked phones -> standard phones -> names.
  Emails run first so that a numeric local part (e.g. 0712345678@example.test) is
  consumed as [EMAIL] rather than [PHONE]@example.test.  IDs run before phones so
  that a numeric payload under an explicit label (e.g. ID number 0700000001) is
  replaced by [PERSONAL_ID] rather than [PHONE].
- Names: exact saved literals, case-insensitive, whole-word Unicode boundaries,
  gathered per participant across all rows.  Later rows lacking name metadata still
  use names gathered from earlier rows for the same participant.  No cross-participant
  substitution.  Longer names are matched first; among equal-length names the tie is
  broken lexicographically for PYTHONHASHSEED-independent ordering.  Multi-word names
  use ``\\s+`` between words, so minor whitespace variation (multiple spaces) is
  matched.  Reserved placeholder tokens ([NAME], [PHONE], [EMAIL], [PERSONAL_ID]) are
  protected from name substitution by a structural segment-split strategy: the text is
  split around existing placeholder tokens before name patterns run, and patterns are
  applied only to non-placeholder segments.  Newly inserted [NAME] tokens from each
  pass are also split out before subsequent patterns run.  This reserves no source
  characters or strings; a participant named 'S0' or 'S1' is handled identically to
  any other name, and literal NUL bytes or other unusual input bytes are preserved.
  A name appearing inside non-placeholder brackets (e.g. [Exampleperson]) IS
  replaced; outer brackets are preserved (yielding [[NAME]]).
- Phones: structural matching by recognized prefix followed by decimal-digit groups
  with allowed separators.  Total decimal-digit count in the matched span must be
  9-15 (using str.isdecimal(), which covers ASCII 0-9, fullwidth U+FF10-U+FF19, and
  Arabic-Indic U+0660-U+0669).  Supported prefixes: +, 00, bare 254 country code,
  ASCII Kenya-local 07/01, fullwidth ０７/０１ (U+FF10 U+FF17/U+FF11), Arabic-Indic
  ٠٧/٠١ (U+0660 U+0667/U+0661).  Allowed separators within a phone: space, NBSP
  (U+00A0), thin space (U+2009), parentheses, ASCII hyphen (-), U+2010-U+2015, U+2212.
  Dot (.) is a separator ONLY when immediately followed by a decimal digit; a trailing
  sentence period ('. ' or '. DIGIT_COUNT') is not consumed.  Leading guard
  (?<![\\w.]) prevents partial matches inside BSUIDs; trailing guard (?!\\w) prevents
  consuming into word suffixes.  Explicit masked-phone form +CCC****NNNN handled as a
  separate case.  Does NOT match: pregnancy week counts, ordinary dates (digit count
  <= 8, no symbol prefix), emergency helplines (3-4 digits, no prefix), BSUIDs
  (preceded by [A-Za-z.]), overlong sequences (> 15 decimal digits).
- Emails: standard address forms, case-insensitive, ASCII-only parts.
- Personal IDs: labelled explicit forms only.  The label and separator bytes are
  preserved exactly; only the payload bytes are replaced.  A word-boundary guard
  prevents matching label suffixes inside other words (e.g. 'valid:' does not trigger).

Personal-ID label variants (English and Swahili)
-------------------------------------------------
  national ID, national ID number, ID number, ID [with colon/hash/equals/space]
  kitambulisho, namba ya kitambulisho
  passport, passport number, passport no

  Label-payload separator: colon (:), equals (=), hash (#), whitespace, or the
  English/Swahili connectors 'is'/'ni'.  Labels are matched case-insensitively.
  Payload: national ID 6-10 ASCII decimal digits; passport 6-12 ASCII alphanumeric
  containing at least one decimal digit.  Payload is bounded by (?!\\w) to avoid
  partial matches within alphanumeric tokens (e.g. ID: 12345678a is not matched).

Coverage limits (documented per P11/P12)
-----------------------------------------
- Phone dot separator is conservative: dot is only recognised as an internal phone
  separator when immediately followed by a decimal digit.  A sentence period
  ('Call 0712345678. 20 weeks.') is therefore not consumed.  Supported dotted-phone
  form (+254.700.000.001) continues to work.
- Phone body separators are the specific listed characters; other Unicode punctuation
  is not recognised as a separator.
- Emails in non-Latin scripts are not covered (explicitly permitted limitation).
- Personal-ID labels are Kenya-specific: English and Swahili only.
- Bare 254 country-code prefix may match a 9-digit number starting with 254 that is
  not a phone in edge cases; the 9-digit minimum mitigates this.
- Saved names are matched as exact literals with whole-word boundaries and ``\\s+``
  between words (supporting minor spacing variation).  Unicode script coverage
  depends on what was saved: a name stored in Latin script is matched in Latin text;
  a name stored in another script (Arabic, Cyrillic, etc.) is matched in text of the
  same script.
- Common-word name collisions (e.g. name 'May' matching the modal verb 'may') are
  NOT prevented by whole-word boundaries.  Boundaries only prevent matching within
  longer words (e.g. 'Maybe'); standalone occurrences of the word are matched
  case-insensitively regardless of grammatical context.  Operators should review
  exports when participants have common given names.
- Outgoing AI-generated text is scrubbed for the supported classes.  PII already
  embedded in upstream provider calls before export is not retroactively removed.
"""

import json
import re

# ---------------------------------------------------------------------------
# Placeholders
# ---------------------------------------------------------------------------

PH_NAME = "[NAME]"
PH_PHONE = "[PHONE]"
PH_EMAIL = "[EMAIL]"
PH_ID = "[PERSONAL_ID]"

# Pattern that matches all four reserved placeholder tokens exactly.
# Used to split text into protected placeholder segments and free segments so
# that name patterns are only applied to the free (non-placeholder) portions.
_ALL_PH_RE = re.compile(r"\[NAME\]|\[PHONE\]|\[EMAIL\]|\[PERSONAL_ID\]")


# ---------------------------------------------------------------------------
# Email patterns — run FIRST so numeric local parts are protected
# ---------------------------------------------------------------------------

_EMAIL_RE = re.compile(
    r"(?<!\w)"
    r"[a-zA-Z0-9._%+\-]+"
    r"@"
    r"[a-zA-Z0-9.\-]+"
    r"\.[a-zA-Z]{2,}"
    r"(?!\w)",
    re.UNICODE,
)


def _replace_emails(text: str) -> str:
    return _EMAIL_RE.sub(PH_EMAIL, text)


# ---------------------------------------------------------------------------
# Personal-ID patterns — run before phones so labelled numeric payloads get
# [PERSONAL_ID] rather than [PHONE]
# ---------------------------------------------------------------------------

# Supported separators between label and payload:
#   (a) optional whitespace + "is"/"ni" connector + whitespace
#   (b) optional whitespace + colon / equals / hash + optional whitespace
#   (c) plain whitespace
# National IDs and passports share the same (a)/(b)/(c) logic; passports
# accept all three to support "passport no is A1234567".
_NID_SEP_GROUP = r"(?P<nid_sep>\s*(?:is|ni)\s+|\s*[:#=#]\s*|\s+)"
_PP_SEP_GROUP = r"(?P<pp_sep>\s*(?:is|ni)\s+|\s*[:#=#]\s*|\s+)"

_PERSONAL_ID_RE = re.compile(
    r"(?i)"
    r"(?:"
    # ── National-ID forms ────────────────────────────────────────────────────
    # (?<!\w) prevents matching the label suffix inside a word (e.g. "valid").
    r"(?<!\w)(?P<nid_lbl>"
    r"national\s+id(?:\s+number)?"
    r"|id(?:\s+number)?"
    r"|kitambulisho"
    r"|namba\s+ya\s+kitambulisho"
    r")" + _NID_SEP_GROUP + r"(?P<nid>[0-9]{6,10})(?!\w)"
    r"|"
    # ── Passport forms ───────────────────────────────────────────────────────
    r"(?<!\w)(?P<pp_lbl>passport(?:\s+(?:number|no\.?))?)" + _PP_SEP_GROUP + r"(?P<pp>[A-Za-z0-9]{6,12})(?!\w)"
    r")",
    re.UNICODE,
)


def _replace_personal_ids(text: str) -> str:
    def _sub(m: re.Match) -> str:
        if m.group("nid") is not None:
            # Preserve label + separator bytes exactly; replace payload.
            return m.group("nid_lbl") + m.group("nid_sep") + PH_ID
        pp = m.group("pp")
        if pp is not None and any(ch.isdecimal() for ch in pp):
            return m.group("pp_lbl") + m.group("pp_sep") + PH_ID
        return m.group(0)

    return _PERSONAL_ID_RE.sub(_sub, text)


# ---------------------------------------------------------------------------
# Phone patterns
# ---------------------------------------------------------------------------

# Non-dot separator characters (always OK inside a phone number).
_NON_DOT_SEP_CHARS = r" \u00a0\u2009()\u2010-\u2015\u2212\-"
_NDS = rf"[{_NON_DOT_SEP_CHARS}]"

# Conservative separator: a non-dot char, OR a dot that is immediately
# followed by a decimal digit.  This prevents consuming '. 20' (sentence
# period + clinical number) while still supporting '+254.700.000.001'.
_SEP = rf"(?:{_NDS}|\.(?=\d))"

# Supported phone prefixes (in alternation order):
#   + or 00         international
#   254             bare Kenya country code
#   0[17]           ASCII Kenya local 07/01
#   \uff10[\uff17\uff11]   fullwidth ０７/０１
#   \u0660[\u0667\u0661]  Arabic-Indic ٠٧/٠١
_PREFIX = (
    r"(?:\+|00|254"
    r"|0[17]"
    r"|\uff10[\uff17\uff11]"
    r"|\u0660[\u0667\u0661]"
    r")"
)

# Main phone RE: PREFIX SEP* DIGITS (SEP+ DIGITS)*
# Digit count validated in _phone_sub (9-15 isdecimal() chars).
# (?<![\w.]) prevents matches inside BSUIDs like KE.07...
# (?!\w) prevents consuming into alphanumeric suffixes.
_PHONE_RE = re.compile(
    r"(?<![\w.])"
    + _PREFIX
    + _SEP
    + r"*\d+"  # first digit group (required)
    + r"(?:"
    + _SEP
    + r"+\d+)*"  # additional digit groups
    + r"(?!\w)",
    re.UNICODE,
)


def _phone_sub(m: re.Match) -> str:
    """Replace a phone match only when decimal-digit count is in [9, 15]."""
    matched = m.group(0)
    digit_count = sum(1 for c in matched if c.isdecimal())
    return PH_PHONE if 9 <= digit_count <= 15 else matched


# Masked-phone pattern: explicitly handles upstream-redacted numbers such as
# +254****0001 where asterisks replace digit groups.  Targeted Kenya form
# only; decimal-digit count is below 9 so the main pattern would not match.
_MASKED_PHONE_RE = re.compile(
    r"(?<![\w.])"
    r"\+\d{1,3}\*+\d{2,}"
    r"(?![\w*])",
    re.UNICODE,
)


def _replace_phones(text: str) -> str:
    # Masked phones first (targeted form, no digit-count filter).
    text = _MASKED_PHONE_RE.sub(PH_PHONE, text)
    # Standard phones with decimal-digit count validation.
    text = _PHONE_RE.sub(_phone_sub, text)
    return text


# ---------------------------------------------------------------------------
# Name patterns
# ---------------------------------------------------------------------------


def _build_name_pattern(name: str) -> re.Pattern | None:
    """Return a whole-word case-insensitive pattern for *name*, or None if empty."""
    name = name.strip()
    if not name:
        return None
    parts = name.split()
    escaped_parts = [re.escape(p) for p in parts]
    pattern = r"\s+".join(escaped_parts)
    return re.compile(r"(?<!\w)" + pattern + r"(?!\w)", re.IGNORECASE | re.UNICODE)


def _replace_names(text: str, names: frozenset[str]) -> str:
    """Replace saved participant names with [NAME], protecting placeholder tokens.

    Uses a structural segment-split strategy:

    1. Split the input text around existing placeholder tokens into a list of
       ``(is_placeholder: bool, text: str)`` segments.  Placeholder segments are
       never modified by name patterns.
    2. Apply each name pattern (longest-first, then lexicographic tie-break) only
       to non-placeholder segments.
    3. After each individual pattern application, re-split newly inserted ``[NAME]``
       tokens out as new protected placeholder segments, so that a later shorter
       saved name cannot match inside a just-inserted placeholder.
    4. Reassemble all segments in order.

    This approach reserves no source characters or strings.  A participant saved
    as 'S0', 'S1', etc. is handled exactly like any other name.  Literal NUL bytes
    or other unusual input bytes are preserved as-is.  A name appearing inside
    brackets (e.g. ``[Exampleperson]``) is replaced because ``[`` and ``]`` are not
    word characters; the outer brackets are preserved (yielding ``[[NAME]]``).
    """
    # Build all patterns sorted deterministically.
    patterns = []
    for name in sorted(names, key=lambda n: (-len(n), n)):
        pat = _build_name_pattern(name)
        if pat is not None:
            patterns.append(pat)
    if not patterns:
        return text

    def _split_on_placeholders(s: str) -> list[tuple[bool, str]]:
        """Split *s* into (is_placeholder, text) segment pairs."""
        parts = _ALL_PH_RE.split(s)
        tokens = _ALL_PH_RE.findall(s)
        segs: list[tuple[bool, str]] = []
        for i, part in enumerate(parts):
            segs.append((False, part))
            if i < len(tokens):
                segs.append((True, tokens[i]))
        return segs

    # Initialise: split existing placeholder tokens into protected segments.
    segments = _split_on_placeholders(text)

    for pat in patterns:
        new_segments: list[tuple[bool, str]] = []
        for is_ph, seg in segments:
            if is_ph:
                new_segments.append((True, seg))
            else:
                replaced = pat.sub(PH_NAME, seg)
                # Re-split any placeholder tokens inserted by this pass.
                for sub_is_ph_seg in _split_on_placeholders(replaced):
                    new_segments.append(sub_is_ph_seg)
        segments = new_segments

    return "".join(seg for _, seg in segments)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def scrub(text: str, participant_names: frozenset[str] = frozenset()) -> str:
    """Return *text* with supported PII spans replaced by fixed placeholders.

    Parameters
    ----------
    text:
        Free-text string to scrub (e.g. ``message_text`` or ``danger_keywords``).
    participant_names:
        Exact name strings known for this participant, gathered across all rows.
        Empty frozenset means no name substitution.

    Returns
    -------
    str
        A new string with matched spans replaced by ``[NAME]``, ``[PHONE]``,
        ``[EMAIL]`` or ``[PERSONAL_ID]``.  Non-matching bytes are preserved
        exactly.

    Notes
    -----
    Application order: emails -> personal IDs -> masked phones -> standard phones
    -> names.  See module docstring for coverage limits.
    """
    if not isinstance(text, str):
        return text
    text = _replace_emails(text)
    text = _replace_personal_ids(text)
    text = _replace_phones(text)
    text = _replace_names(text, participant_names)
    return text


def gather_participant_names(rows: list[dict]) -> dict[str, frozenset[str]]:
    """Return per-participant name sets gathered across *all* rows.

    Key: ``Participant Public ID`` string.
    Value: frozenset of non-empty name strings from both:
      - ``Participant Name`` column
      - ``data.name`` inside ``Participant Data`` JSON

    Names are gathered from ALL rows (before consent/filtering) so that a later
    row lacking name metadata does not lose a name established by an earlier row
    for the same participant.  Cross-participant names are never shared.

    Raises
    ------
    TypeError
        If ``data.name`` is present but is not a string (e.g. a nested dict).
        Callers should treat this as a fatal input error and return nonzero.
    """
    result: dict[str, set[str]] = {}
    for row in rows:
        pid = row.get("Participant Public ID", "")
        if not pid:
            continue
        names = result.setdefault(pid, set())
        pname = (row.get("Participant Name") or "").strip()
        if pname:
            names.add(pname)
        try:
            data = json.loads(row.get("Participant Data") or "")
            if isinstance(data, dict):
                raw_name = data.get("name")
                if raw_name is not None:
                    if not isinstance(raw_name, str):
                        # Unexpected type (e.g. nested dict) — fail without
                        # echoing the value.
                        raise TypeError("unexpected name type in participant data")
                    dname = raw_name.strip()
                    if dname:
                        names.add(dname)
        except json.JSONDecodeError:
            pass  # malformed JSON — partial name data is acceptable
        # TypeError from bad name type propagates to caller

    return {k: frozenset(v) for k, v in result.items()}
