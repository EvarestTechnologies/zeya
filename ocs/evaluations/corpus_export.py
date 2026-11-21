"""
Export the Zeya danger-sign corpus as an OCS Evaluation Dataset CSV.

The CSV column layout matches what the OCS Dataset CSV upload expects (documented
in apps/evaluations/tests/test_dataset_csv_upload.py at OCS commit
9f5c25476555ff74a167c6a14832ce798832847a):

    input  → EvaluationMessage.input.content   (user message text)
    output → EvaluationMessage.output.content  (expected/ground-truth; empty here)
    expected_route    → context field: "EMERGENCY" or "SAFE"
    expected_category → context field: danger category name or "" for SAFE rows
    source            → context field: which corpus list this row came from

Rows are authored test fixtures, not clinical ground truth.  Labels reflect
what the deterministic danger_gate node is expected to produce; they are not
clinically validated recall claims.

Usage::

    from ocs.evaluations.corpus_export import build_danger_rows, write_evaluation_csv
    rows = build_danger_rows()
    with open("zeya_eval_dataset.csv", "w", newline="", encoding="utf-8") as f:
        write_evaluation_csv(rows, f)
"""

import csv
from dataclasses import dataclass
from typing import IO

# Columns that the OCS CSV upload will map:
#   "input"  → message input content
#   "output" → ground-truth output (empty; we use context fields for expected labels)
# Extra columns become EvaluationMessage.context fields, available to evaluators
# as `context["expected_route"]`, `context["expected_category"]`, etc.
CORPUS_CSV_COLUMNS = [
    "input",
    "output",
    "expected_route",
    "expected_category",
    "source",
]


@dataclass(frozen=True)
class CorpusRow:
    """One evaluation dataset row derived from the danger corpus.

    ``source`` distinguishes authored test fixtures from any future clinical
    held-out labels; it is never omitted.
    """

    input: str  # user message text
    output: str  # ground-truth output (empty: not available here)
    expected_route: str  # "EMERGENCY" or "SAFE"
    expected_category: str  # danger category name, or "" for SAFE rows
    source: str  # e.g. "danger_corpus.PATTERN_EXAMPLES"


def build_danger_rows() -> list[CorpusRow]:
    """Build evaluation dataset rows from the available danger corpus.

    Sources used:
      - ``PATTERN_EXAMPLES``: one message per pattern per category → EMERGENCY
      - ``NEGATIVE_MESSAGES``: non-danger messages → SAFE

    Sources NOT used (unavailable at #28 scope):
      - Issue-20 310-row clinical branch (held-out; not in this worktree)
      - BILINGUAL_EXAMPLES / EDGE_CASE_MESSAGES (not labelled with categories)

    Returns rows in corpus-list order, deduplicating by input message text.
    """
    # Avoid circular imports; keep at function scope per OCS node convention.
    from ocs.tests.danger_corpus import NEGATIVE_MESSAGES, PATTERN_EXAMPLES  # noqa: PLC0415

    seen: set[str] = set()
    rows: list[CorpusRow] = []

    for category, _pattern_idx, message in PATTERN_EXAMPLES:
        if message in seen:
            continue
        seen.add(message)
        rows.append(
            CorpusRow(
                input=message,
                output="",
                expected_route="EMERGENCY",
                expected_category=category,
                source="danger_corpus.PATTERN_EXAMPLES",
            )
        )

    for message in NEGATIVE_MESSAGES:
        if message in seen:
            continue
        seen.add(message)
        rows.append(
            CorpusRow(
                input=message,
                output="",
                expected_route="SAFE",
                expected_category="",
                source="danger_corpus.NEGATIVE_MESSAGES",
            )
        )

    return rows


def write_evaluation_csv(rows: list[CorpusRow], dest: IO[str]) -> None:
    """Write *rows* to *dest* as an OCS-compatible evaluation dataset CSV.

    The column order follows ``CORPUS_CSV_COLUMNS``.  The caller is responsible
    for opening/closing *dest*; this function only writes.
    """
    writer = csv.DictWriter(dest, fieldnames=CORPUS_CSV_COLUMNS)
    writer.writeheader()
    for row in rows:
        writer.writerow(
            {
                "input": row.input,
                "output": row.output,
                "expected_route": row.expected_route,
                "expected_category": row.expected_category,
                "source": row.source,
            }
        )
