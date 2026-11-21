"""Knowledge base loader for Zeya.

Exposes functions used by the build pipeline and node tests:

  load_knowledge(path, include_pending=False) -> list[dict]
      Parse ``docs/zeya-knowledge-base.md``-formatted Markdown and return a
      list of entry dicts.  By default only entries whose ``review_status``
      is exactly ``'approved'`` are returned; ``include_pending=True`` also
      returns entries with ``review_status == 'pending'``.  Missing or
      unrecognised review-state values are treated as pending (fail-closed).
      Approved entries are validated on load; malformed approvals raise
      ``ValueError``.  Duplicate (id, language) pairs always raise.

  render_kb_context(entries, max_context_bytes=2000) -> tuple[str, list[str]]
      Render a pre-filtered list of entry dicts into a bounded context string.
      Returns ``(section_text, selected_ids)``.  Entries are taken in list
      order until adding the next entry (plus the separator ``'\\n\\n'``) would
      exceed the UTF-8 byte budget.

  render_kb_node(entries, max_context_bytes=2000, include_pending=False) -> str
      Return executable Python node source with the candidate entry list
      injected into the ``KB_JSON`` and ``max_context_bytes`` placeholders of
      ``ocs/nodes/kb_context.py``.

      Runtime selection (language, gestational week, budget enforcement) is
      performed by the node's ``main()`` with real participant state.  This
      function does NOT pre-filter by language or week.

      ``include_pending=False`` (public default) includes only approved entries.
      ``include_pending=True`` (synthetic staging ONLY) also includes pending
      entries with an explicit ``eligible=True`` runtime flag without changing
      their ``review_status``.  Original input dicts are never mutated.

      ``max_context_bytes`` must be a positive ``int`` (not ``bool``).

Entry dict schema
-----------------
  id            str         Stable slug, e.g. ``'anc_purpose'``
  review_status str         ``'approved'`` | ``'pending'``
  language      str         Language code as parsed (supported: ``'en'``, ``'sw'``)
  text          str         Educational body text
  source_refs   list[str]   Source URLs or citation labels
  topics        list[str]   Topic tags
  min_week      int|None    Inclusive lower gestational-week bound (None = no limit)
  max_week      int|None    Inclusive upper gestational-week bound (None = no limit)
"""

import json
import re
from pathlib import Path

_NODES_DIR = Path(__file__).parent / "nodes"

# Valid gestational week range: 1–50 (generous upper bound to accommodate
# post-dates pregnancies without artificially restricting content).
_MIN_VALID_WEEK = 1
_MAX_VALID_WEEK = 50


def load_knowledge(path, include_pending=False):
    """Parse the Markdown knowledge base at *path* and return entry dicts.

    Parameters
    ----------
    path:
        Path-like object pointing at a knowledge-base Markdown file.
    include_pending:
        When ``False`` (default) only ``review_status == 'approved'`` entries
        are returned.  When ``True`` both approved and pending entries are
        returned.  Entries whose review state is missing or unrecognised are
        always treated as pending.

    Raises
    ------
    ValueError
        When a duplicate ``(id, language)`` pair is found across all entries,
        or when an approved entry fails integrity validation (empty body,
        missing source refs, unsupported language, malformed or out-of-bounds
        week metadata, inverted bounds).

    Returns
    -------
    list[dict]
        Entry dicts with the keys described in the module docstring.
        Internal ``_raw_*`` tracking fields are stripped before return.
    """
    text = Path(path).read_text(encoding="utf-8")
    entries = []
    seen_id_lang: set = set()

    sections = re.split(r"\n---\n", text)

    for section in sections:
        entry = _parse_section(section)
        if entry is None:
            continue

        # Duplicate (id, language) is invalid regardless of review status.
        key = (entry["id"], entry["language"])
        if key in seen_id_lang:
            raise ValueError(
                f"Duplicate id/language pair in knowledge base: id={entry['id']!r}, language={entry['language']!r}"
            )
        seen_id_lang.add(key)

        # Approved entries must pass full integrity validation before being trusted.
        if entry["review_status"] == "approved":
            _validate_approved_entry(entry)

        if not include_pending and entry["review_status"] != "approved":
            continue

        # Strip internal tracking fields before returning.
        public_entry = {k: v for k, v in entry.items() if not k.startswith("_raw_")}
        entries.append(public_entry)

    return entries


def _validate_approved_entry(entry):
    """Raise ``ValueError`` if an approved entry fails integrity checks."""
    entry_id = entry["id"]

    # Language must be a supported code; no silent relabelling.
    if entry["language"] not in ("en", "sw"):
        raise ValueError(
            f"Approved entry {entry_id!r} has unsupported language {entry['language']!r}; "
            "only 'en' and 'sw' are supported. "
            "Entries with other language codes must remain pending."
        )

    # Body text must be nonempty.
    if not entry.get("text", "").strip():
        raise ValueError(
            f"Approved entry {entry_id!r} has empty body text; source text is required for approved entries"
        )

    # At least one source reference is required.
    if not entry.get("source_refs"):
        raise ValueError(
            f"Approved entry {entry_id!r} has no source references; "
            "at least one source reference is required for approved entries"
        )

    # Week bounds: each nonempty raw value must be a valid gestational week.
    # Malformed values (text strings, negatives, decimals, zero, out-of-range)
    # are silently lost by _parse_week; _validate_approved_entry catches them here.
    raw_min = entry.get("_raw_min_week", "")
    raw_max = entry.get("_raw_max_week", "")
    if not _is_valid_week_raw(raw_min):
        raise ValueError(
            f"Approved entry {entry_id!r} has invalid Min-week: {raw_min!r}; "
            f"must be empty (unrestricted) or a positive integer {_MIN_VALID_WEEK}–{_MAX_VALID_WEEK}"
        )
    if not _is_valid_week_raw(raw_max):
        raise ValueError(
            f"Approved entry {entry_id!r} has invalid Max-week: {raw_max!r}; "
            f"must be empty (unrestricted) or a positive integer {_MIN_VALID_WEEK}–{_MAX_VALID_WEEK}"
        )

    # Sensible direction when both bounds are present.
    min_week = entry.get("min_week")
    max_week = entry.get("max_week")
    if min_week is not None and max_week is not None and min_week > max_week:
        raise ValueError(
            f"Approved entry {entry_id!r} has inverted week bounds: min_week={min_week} > max_week={max_week}"
        )


def _is_valid_week_raw(raw):
    """Return ``True`` if *raw* is empty (unrestricted) or a valid gestational week.

    Valid: empty string (unrestricted) or a digit-only string whose integer
    value falls within ``_MIN_VALID_WEEK``–``_MAX_VALID_WEEK`` inclusive.
    Invalid: text strings, negative numbers (not digit strings), decimals,
    zero, out-of-range integers.
    """
    raw = raw.strip() if raw else ""
    if not raw:
        return True
    if raw.isdigit():
        val = int(raw)
        return _MIN_VALID_WEEK <= val <= _MAX_VALID_WEEK
    return False


def _parse_section(section_text):
    """Parse one knowledge-base section.  Returns a dict or ``None``."""
    section_text = section_text.strip()
    if not section_text:
        return None

    lines = section_text.split("\n")

    # Locate the entry header line: ``## id — optional description``
    header_line = None
    header_index = 0
    for i, line in enumerate(lines):
        if line.startswith("## "):
            header_line = line[3:].strip()
            header_index = i
            break

    if header_line is None:
        return None

    # Extract stable ID: everything before ``—`` / ``–`` or end of line.
    entry_id = re.split(r"\s*[—–]\s*", header_line, maxsplit=1)[0].strip()
    if not re.match(r"^[a-z][a-z0-9_]*$", entry_id):
        return None

    # Lines after the header; skip leading blank lines before metadata.
    after_header = lines[header_index + 1 :]
    skip = 0
    while skip < len(after_header) and not after_header[skip].strip():
        skip += 1
    after_header = after_header[skip:]

    # Separate metadata lines from body: metadata is key-value pairs up to
    # the first blank line; body is everything after.
    meta_lines = []
    body_start = len(after_header)
    for i, line in enumerate(after_header):
        if not line.strip():
            body_start = i + 1
            break
        meta_lines.append(line)

    body_lines = after_header[body_start:]
    text = "\n".join(body_lines).strip()

    # Parse metadata key: value pairs.
    meta = {}
    for mline in meta_lines:
        if ":" in mline:
            key, _, val = mline.partition(":")
            meta[key.strip().lower().replace("-", "_")] = val.strip()

    # review_state → review_status (fail-closed: only exact 'approved' qualifies).
    review_raw = meta.get("review_state", "").lower().strip()
    review_status = "approved" if review_raw == "approved" else "pending"

    # language — keep raw parsed value; do NOT silently relabel unsupported codes.
    language = meta.get("language", "").lower().strip()

    # topics — comma-separated.
    topics_raw = meta.get("topics", "")
    topics = [t.strip() for t in topics_raw.split(",") if t.strip()]

    # source_refs — comma-separated URLs / citation labels.
    source_refs_raw = meta.get("source_refs", "")
    source_refs = [s.strip() for s in source_refs_raw.split(",") if s.strip()]

    # week bounds — parsed int or None.  Raw strings stored for validation.
    raw_min = meta.get("min_week", "")
    raw_max = meta.get("max_week", "")
    min_week = _parse_week(raw_min)
    max_week = _parse_week(raw_max)

    return {
        "id": entry_id,
        "review_status": review_status,
        "language": language,
        "text": text,
        "source_refs": source_refs,
        "topics": topics,
        "min_week": min_week,
        "max_week": max_week,
        # Internal tracking fields; stripped by load_knowledge before return.
        "_raw_min_week": raw_min,
        "_raw_max_week": raw_max,
    }


def _parse_week(raw):
    """Return ``int`` or ``None``.

    Returns ``None`` for empty input (unrestricted) AND for malformed values
    (non-digits, negatives, decimals).  Callers that need to distinguish
    "unrestricted" from "malformed" must check the raw string with
    ``_is_valid_week_raw``.
    """
    raw = raw.strip() if raw else ""
    if not raw:
        return None
    return int(raw) if raw.isdigit() else None


def render_kb_context(entries, max_context_bytes=2000):
    """Render *entries* into a bounded context string.

    Entries are taken in list order.  The first entry whose addition would
    exceed *max_context_bytes* stops selection; subsequent entries are skipped.
    The separator ``'\\n\\n'`` (2 UTF-8 bytes) between entries is counted
    toward the budget.

    Parameters
    ----------
    entries:
        Pre-filtered list of entry dicts.
    max_context_bytes:
        UTF-8 byte budget for the concatenated section text, including
        separator bytes.  Actual final prompt budget enforcement is handled
        centrally by the LLM-input node.

    Returns
    -------
    tuple[str, list[str]]
        ``(section_text, selected_ids)`` where *section_text* is the entries
        joined by ``'\\n\\n'`` and *selected_ids* is the list of their IDs in
        selection order.
    """
    selected_texts = []
    selected_ids = []
    used_bytes = 0

    for entry in entries:
        text = entry.get("text", "")
        entry_bytes = len(text.encode("utf-8"))
        sep_bytes = 2 if selected_texts else 0
        if used_bytes + sep_bytes + entry_bytes > max_context_bytes:
            break
        selected_texts.append(text)
        selected_ids.append(entry["id"])
        used_bytes += sep_bytes + entry_bytes

    section_text = "\n\n".join(selected_texts)
    return section_text, selected_ids


def render_kb_node(entries, max_context_bytes=2000, include_pending=False):
    """Return executable Python node source with candidate entries injected.

    Reads ``ocs/nodes/kb_context.py`` as the template and injects:

    1. The filtered candidate JSON into the ``KB_JSON = "[]"`` placeholder.
    2. The validated byte budget into the ``max_context_bytes = 2000``
       placeholder.

    Both placeholders must occur exactly once in the template.  Runtime
    selection (language, gestational week, budget enforcement) is performed
    by the node's ``main()`` with real participant state.  This function does
    NOT pre-filter by language or week — all approved (or staged) entries are
    passed so the node can select for the actual participant.

    Parameters
    ----------
    entries:
        Knowledge-base entry dicts (may include pending entries).
    max_context_bytes:
        Byte budget forwarded to the node.  Must be a positive ``int``
        (not ``bool``).
    include_pending:
        When ``True`` (synthetic staging ONLY), pending entries receive an
        explicit ``eligible=True`` runtime flag without changing their
        ``review_status``.  Original input dicts are never mutated.
        Default ``False`` (public default: approved entries only).

    Returns
    -------
    str
        Executable Python source string ready for ``NodeHarness`` or OCS
        deployment.

    Raises
    ------
    ValueError
        When ``max_context_bytes`` is a ``bool``, not an ``int``, or not
        positive.  Also when either placeholder is not found exactly once in
        the template.
    """
    # Validate max_context_bytes: must be int (not bool subtype), positive.
    if isinstance(max_context_bytes, bool) or not isinstance(max_context_bytes, int):
        raise ValueError(f"max_context_bytes must be a positive int (not bool), got {max_context_bytes!r}")
    if max_context_bytes <= 0:
        raise ValueError(f"max_context_bytes must be positive, got {max_context_bytes}")

    # Build eligible list: approved always; pending only with explicit include_pending=True.
    eligible = []
    for entry in entries:
        if entry.get("review_status") == "approved":
            eligible.append(entry)
        elif include_pending and entry.get("review_status") == "pending":
            # Add staging eligibility flag to a copy; never mutate the original.
            staging = dict(entry)
            staging["eligible"] = True
            eligible.append(staging)

    candidate_json = json.dumps(eligible)

    # Read template from kb_context.py.
    template = (_NODES_DIR / "kb_context.py").read_text(encoding="utf-8")

    # Inject KB_JSON placeholder (must occur exactly once).
    json_placeholder = 'KB_JSON = "[]"'
    if template.count(json_placeholder) != 1:
        raise ValueError(
            f"Expected exactly 1 occurrence of {json_placeholder!r} in kb_context.py template, "
            f"found {template.count(json_placeholder)}"
        )
    # repr() produces a syntactically valid Python string literal for any JSON
    # content, correctly escaping embedded quotes and backslashes.
    source = template.replace(json_placeholder, f"KB_JSON = {repr(candidate_json)}", 1)

    # Inject max_context_bytes placeholder (must occur exactly once).
    budget_placeholder = "max_context_bytes = 2000"
    if source.count(budget_placeholder) != 1:
        raise ValueError(
            f"Expected exactly 1 occurrence of {budget_placeholder!r} in kb_context.py template, "
            f"found {source.count(budget_placeholder)}"
        )
    source = source.replace(budget_placeholder, f"max_context_bytes = {max_context_bytes}", 1)

    return source
