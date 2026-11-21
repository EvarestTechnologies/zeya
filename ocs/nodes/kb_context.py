"""
Open Chat Studio Python node: knowledge-base context selector.

Reads participant saved language preference and computes current gestational
week from enrollment data.  Selects approved (or explicitly staged-eligible)
knowledge-base entries within the UTF-8 byte budget and writes three temp-state
keys for downstream nodes:

  kb_section   – bounded concatenation of selected entry texts (str)
  kb_ids       – stable IDs of selected entries (list[str])
  kb_available – True when at least one entry was selected (bool)

No approved content => empty section and kb_available=False; the pipeline
routes to a fixed health-worker referral before any LLM call.

Participant data keys read (set by the registration node):
  language_preference           'en' | 'sw'  — no silent default to either
  gestational_age_at_enrollment int          — weeks pregnant at enrollment
  enrolled_at                   str          — ISO-8601 UTC datetime of enrollment

Week computation mirrors registration.py:
  current_week = gestational_age_at_enrollment + (now - enrolled_at).days // 7

Unknown or uncomputable week => entries with any week bound are excluded;
general (unbounded) entries remain eligible.

The KB_JSON string is replaced by build_pipeline with the validated JSON
export of approved entries from docs/zeya-knowledge-base.md.
Until entries pass clinical and language review, KB_JSON is '[]'
and the node will always set kb_available=False.

Returns the original participant message unchanged.
"""


def main(input, **kwargs):
    import json

    # Approved knowledge-base entries injected by build_pipeline.
    # All public entries require review_status == 'approved'.
    # Pending entries are excluded at load time; this list is empty until
    # entries pass clinical and language review.
    # In synthetic staging, pending entries may carry eligible=True; the node
    # checks both review_status and eligible without relabelling pending content.
    KB_JSON = "[]"

    entries = json.loads(KB_JSON)

    # Read participant saved state; do not mutate it.
    participant = get_participant_data()

    # Language preference set by the registration node.
    # No silent default: an absent or unsupported value means no entries match.
    saved_language = participant.get("language_preference")

    # Compute current gestational week from enrollment data.
    # Mirrors registration.py: (now - enrolled_at).days // 7 + ga_at_enrollment.
    # On any parse or arithmetic error current_week stays None.
    # None → exclude all week-ranged entries (unknown week must not include
    # week-restricted content).
    current_week = None
    ga_raw = participant.get("gestational_age_at_enrollment")
    enrolled_at_str = participant.get("enrolled_at")
    if ga_raw is not None and enrolled_at_str is not None:
        try:
            ga = int(ga_raw)
            enrolled_dt = datetime.datetime.fromisoformat(enrolled_at_str)
            now_utc = datetime.datetime.now(datetime.timezone.utc)
            days_since = (now_utc - enrolled_dt).days
            if days_since >= 0:
                current_week = ga + (days_since // 7)
        except Exception:
            current_week = None

    # Select eligible entries: approved (or staged-eligible), matching language,
    # within week range.  Exact UTF-8 byte count with separator bytes included.
    max_context_bytes = 2000
    used_bytes = 0
    eligible_texts = []
    eligible_ids = []

    for entry in entries:
        # Eligibility: approved status or explicit staging flag (eligible=True).
        # Staging flag is added by render_kb_node(include_pending=True) without
        # changing review_status; never relabels pending content as approved.
        is_eligible = entry.get("review_status") == "approved" or entry.get("eligible") is True
        if not is_eligible:
            continue

        if entry.get("language") != saved_language:
            continue

        min_week = entry.get("min_week")
        max_week = entry.get("max_week")

        # Unknown week: exclude any entry that carries a week bound.
        if current_week is None:
            if min_week is not None or max_week is not None:
                continue
        else:
            if min_week is not None and current_week < min_week:
                continue
            if max_week is not None and current_week > max_week:
                continue

        text = entry.get("text", "")
        # Exact UTF-8 byte count; separator '\n\n' = 2 bytes per join.
        text_bytes = len(text.encode("utf-8"))
        sep_bytes = 2 if len(eligible_texts) > 0 else 0
        if used_bytes + sep_bytes + text_bytes > max_context_bytes:
            break

        eligible_texts.append(text)
        eligible_ids.append(entry.get("id", ""))
        used_bytes = used_bytes + sep_bytes + text_bytes

    kb_section = "\n\n".join(eligible_texts)
    kb_available = len(eligible_ids) > 0

    set_temp_state_key("kb_section", kb_section)
    set_temp_state_key("kb_ids", eligible_ids)
    set_temp_state_key("kb_available", kb_available)

    return input
