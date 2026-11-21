"""
SUPERSEDED by ocs/evaluations/observation.py + completed_adapter.py (repair-2).

The trace_export_schema approach (separate session_state.trace_n_turns column)
is replaced by the unified JSON observation envelope in context.observation.
Retained to preserve import history; do not use in new code.

New interfaces:
  from ocs.evaluations.observation import ObservationEnvelope, VERIFIED_METRIC_PROFILE
  from ocs.evaluations.completed_adapter import CompletedObservationRow, COMPLETED_OBS_CSV_COLUMNS
"""

# Legacy exports for backwards-compatibility with old tests (repair-1 regression history).
# These are NOT used by the repair-2 evaluators.

from __future__ import annotations

from dataclasses import dataclass

TRACE_EVIDENCE_SESSION_STATE_KEYS: list[str] = ["trace_n_turns", "trace_id"]

TRACE_EXPORT_CSV_COLUMNS: list[str] = [
    "input",
    "output",
    "expected_route",
    "expected_category",
    "source",
    "session_state.trace_n_turns",
    "session_state.trace_id",
]


@dataclass
class TraceEvidenceRow:
    """SUPERSEDED. Use CompletedObservationRow from completed_adapter.py."""

    session_external_id: str
    message_input: str
    trace_n_turns: int | None
    trace_id: str
    expected_route: str = ""
    expected_category: str = ""
    output: str = ""
    source: str = ""

    def to_csv_row(self) -> dict[str, str]:
        return {
            "input": self.message_input,
            "output": self.output,
            "expected_route": self.expected_route,
            "expected_category": self.expected_category,
            "source": self.source,
            "session_state.trace_n_turns": ("" if self.trace_n_turns is None else str(self.trace_n_turns)),
            "session_state.trace_id": self.trace_id,
        }
