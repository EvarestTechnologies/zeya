# Study export privacy

This document describes the host-side PII scrubbing applied to Zeya transcript
exports (#55) and the diagnostic privacy applied to the participant seeding tool (#56).

## Transcript export scrubbing (#55)

### What is scrubbed

`conversations_export_ocs.csv` is produced by `python -m ocs.export_adapter`.
Two columns receive scrubbing before the row is written to the output file:

| Column | Scrubbing applied |
|--------|-------------------|
| `message_text` | Names, phones, emails, labelled IDs |
| `danger_keywords` | Names, phones, emails, labelled IDs |

All other columns (study\_id, study\_group, direction, gestational\_age, danger\_sign,
response\_time\_ms, timestamp) are not scrubbed — they carry analytical metadata, not
free-text participant input.

Outgoing AI-generated reply text in `message_text` is also scrubbed for the supported
identifier classes. PII that was already embedded in upstream provider calls before
export is not retroactively removed by this tool.

### Application order

Scrubbing passes run in this order: **emails → personal IDs → masked phones →
standard phones → names**.

Emails run first so that a numeric local part (e.g. `0712345678@example.test`) is
replaced by `[EMAIL]` rather than `[PHONE]@domain`. Personal IDs run before phones
so that a labelled numeric payload (e.g. `ID number 0700000001`) is replaced by
`[PERSONAL_ID]` rather than `[PHONE]`.

### Scrubbing rules

**Names** (`[NAME]`)

Exact literal name strings saved in the `Participant Name` OCS column or in
`Participant Data.name` are matched case-insensitively at whole-word Unicode
boundaries. Names are gathered across all rows for the same participant, so a later
row lacking name metadata does not lose a name established by an earlier row. Name
substitution is per-participant: names from one participant are never applied to
another participant's rows.

A name appearing inside brackets (e.g. `[Exampleperson]`) is matched and replaced;
the outer brackets are preserved, yielding `[[NAME]]`. The four reserved placeholder
tokens (`[NAME]`, `[PHONE]`, `[EMAIL]`, `[PERSONAL_ID]`) are protected from name
substitution by a structural segment-split strategy: the text is split around
existing placeholder tokens before name patterns are applied, and patterns run only
on the non-placeholder segments. This reserves no source characters or strings; a
participant whose saved name happens to be `S0`, `S1`, or any other token is handled
identically to any other name.

When two saved names have the same character length, they are ordered
lexicographically to give a deterministic result independent of `PYTHONHASHSEED`.

**Phones** (`[PHONE]`)

Recognised by structural prefix followed by decimal-digit groups with allowed
separators. Total decimal-digit count in the matched span must be **9–15** (using
`str.isdecimal()`, which covers ASCII, fullwidth U+FF10–U+FF19, and Arabic-Indic
U+0660–U+0669 digits).

Supported prefixes:

| Prefix form | Example |
|-------------|---------|
| `+` | `+254712345678` |
| `00` | `00254712345678` |
| Bare country code `254` | `254712345678` |
| ASCII Kenya local `07` / `01` | `0712345678` |
| Fullwidth Kenya local `０７` / `０１` | `０７１２３４５６７８` |
| Arabic-Indic Kenya local `٠٧` / `٠١` | `٠٧٠٠ ٠٠٠ ٠٠١` |

Allowed separators within a phone: space, NBSP (U+00A0), thin space (U+2009),
parentheses, ASCII hyphen (`-`), U+2010–U+2015, U+2212. Dot (`.`) is a separator
only when **immediately followed by a decimal digit** — this preserves dotted-phone
forms like `+254.700.000.001` while ensuring that a sentence period
(`Call 0712345678. 20 weeks.`) is not consumed as part of the phone.

An explicit masked-phone form `+CCC****NNNN` (upstream-redacted Kenya numbers where
`****` replaces masked digits) is handled as a separate bounded case.

Not matched: pregnancy week counts (no prefix), ordinary dates (digit count 8, no
symbol prefix), emergency helplines (3–4 digits, no prefix), BSUIDs (preceded by
`[A-Za-z.]`), overlong sequences (> 15 decimal digits).

**Emails** (`[EMAIL]`)

Standard address forms: `local@domain.tld` with plus/hyphen/subdomain variants,
case-insensitive, ASCII-only.

**Labelled personal IDs** (`[PERSONAL_ID]`)

Explicit label followed by payload only. The label **and** separator bytes are
preserved exactly; only the payload bytes are replaced. A word-boundary guard
prevents matching label suffixes inside other words (e.g. `valid: 12345678` is not
matched).

Supported labels (English and Swahili):

- `National ID`, `National ID number`, `ID number`, `ID:`, `ID=`, `ID#`, `ID ` (space)
- `kitambulisho`, `namba ya kitambulisho`
- `passport`, `passport number`, `passport no`

Label-payload separator: colon (`:`), equals (`=`), hash (`#`), whitespace, or the
English/Swahili connectors `is`/`ni`. Labels are matched case-insensitively.

Payload ranges:
- National ID: 6–10 ASCII decimal digits, not followed by another word char
- Passport: 6–12 ASCII alphanumeric characters containing at least one decimal digit,
  not followed by another alphanumeric char

Not matched: unlabelled bare numbers, clinical values, text discussing passports or
IDs without a digit payload, payloads with alphanumeric suffixes (`ID: 12345678a`).

### Source-file integrity and registry

Input CSV files (`--ocs-export`, `--zeya-users`) are never modified by the export
adapter. The `--study-id-registry` file is intentionally updated: newly allocated
study IDs are committed to the registry before any output is written (commit-before-
output invariant). If the registry commit fails, no output is produced and the
registry remains unchanged.

## Coverage limits

The following limitations are documented and finite:

- Phone body separators are the specific listed characters; other Unicode punctuation
  is not recognised as a separator.
- Emails in non-Latin scripts are not covered (explicitly permitted limitation).
- Personal-ID labels are Kenya-specific: English and Swahili only.
- The bare `254` country-code prefix may match a 9-digit number starting with `254`
  that is not a phone in some edge cases; the 9-digit minimum mitigates this.
- Saved names are matched as exact literals with whole-word boundaries. Multi-word
  names use `\s+` between words, so minor spacing variation (multiple spaces between
  words) is matched. Unicode script coverage depends on what was saved: a name stored
  in Latin script is matched in Latin text; a name stored in another script (Arabic,
  Cyrillic, etc.) is matched in text of the same script.
- Common-word name collisions (e.g. name `"May"` matching the modal verb `"may"`) are
  **not** prevented by whole-word boundaries. Boundaries only prevent matching within
  longer words (e.g. `"Maybe"`); standalone occurrences of the word are matched
  case-insensitively regardless of grammatical context. Operators should review
  exports when participants have common given names.
- Outgoing AI-generated text is scrubbed for the supported classes. PII already
  embedded in upstream provider calls before export is not retroactively removed.

## Seeding diagnostics (#56)

The participant seeding tool (`python -m ocs.seed_participants`) produces a CSV for
import into OCS. The seeding CSV is an **intentionally identifying** import file — it
must retain legitimate identifiers (WhatsApp phone as `identifier`), names, consent
status, language, group and registration fields. The seeding CSV is **not** an
anonymised export.

What **is** changed:

- **Stderr diagnostics are count-only** — the number of participants written and the
  number skipped are reported, without echoing phone numbers, names, or file paths.
- **Missing or malformed rows return controlled non-zero** — a missing required
  column, a missing value in a row, an invalid date, or an invalid gestational age
  causes `seed_main()` to return non-zero with a safe error message that does not
  echo the bad value. No partial output is produced.
- **Input encoding errors return controlled non-zero** — invalid UTF-8 causes a
  controlled error without traceback.
- **Library errors do not echo input values** — `zeya_user_to_participant()` raises
  `ValueError` with a safe message when date or gestational-age parsing fails.
- **Output errors return controlled non-zero** — an `OSError` opening the output file
  returns a safe error message without echoing the output path.

## Study ID stability

The `--study-id-registry` persistent registry path is not affected by scrubbing.
Study ID allocation and all existing #54 invariants (commit-before-output,
alias/hardlink protection, fail-closed on missing registry) are preserved.

## What this scrubbing is not

This is a host-side, deterministic, pattern-based scrubbing tool for research
transcript exports. It is not a universal anonymisation guarantee, is not clinically
validated, does not cover all languages or scripts, and does not apply to hosted API
responses, production deployments, or real-time messaging.
