"""
CSV export adapter for completed-observation evaluation datasets.

Produces the CSV that the OCS Dataset CSV import consumes.  Each row encodes
one completed pipeline turn.  All relationship and type checks run BEFORE the
observation envelope is built; no raw source values are coerced or defaulted.

PROVENANCE BOUNDARY:
  from_trace_dict builds from SEPARATE trusted snapshots and validates all
  cross-record relationships.  Direct CompletedObservationRow construction is
  also validated via __post_init__.  write_completed_observations_csv validates
  before writing.  No export path bypasses validation.

OCS import path (tasks.py:917-926):
  column_mapping["input"]   → CSV column for input text
  column_mapping["output"]  → CSV column for output text
  column_mapping["context"] → {field_name: csv_column} for each context field

Source models used for relationship fields:
  apps/trace/models.py lines 20-56 (Trace):
    input_message  = FK → ChatMessage (line 33-34)
    output_message = FK → ChatMessage (line 36-38)
    session        = FK → ExperimentSession (line 27-29)
    experiment     = FK → Experiment (line 24-26)
    team           = FK → Team (line 39)
    n_turns        = IntegerField(null=True) (line 55)
    experiment_version_number = PositiveIntegerField(null=True) (line 50)
    error          = TextField(blank=True) (line 54)
  apps/chat/models.py ChatMessage (line 182):
    message_type = CharField choices "human"/"ai"
    chat         = FK → Chat
  apps/experiments/models.py ExperimentSession (line 1563):
    external_id  = CharField(max_length=255, default=uuid.uuid4, unique=True)
    experiment   = FK → Experiment
    chat         = OneToOneField(Chat) (line 1581)
  apps/experiments/models.py Experiment (line 496):
    public_id    = UUIDField(default=uuid.uuid4, unique=True) (line 574)
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from typing import IO

from ocs.evaluations.observation import ObservationEnvelope, _is_valid_sha256

# Exact CSV column names.
COMPLETED_OBS_CSV_COLUMNS: list[str] = [
    "input_content",
    "output_content",
    "context.expected_route",
    "context.expected_category",
    "context.expected_card_id",
    "context.observation",
    "context.expected_source",
    "source",
]

# Exact column_mapping for OCS dataset CSV import.
COMPLETED_OBS_COLUMN_MAPPING: dict = {
    "input": "input_content",
    "output": "output_content",
    "context": {
        "expected_route": "context.expected_route",
        "expected_category": "context.expected_category",
        "expected_card_id": "context.expected_card_id",
        "observation": "context.observation",
        "expected_source": "context.expected_source",
    },
}


class RelationshipError(ValueError):
    """
    Raised when a trace/message/session record fails a relationship or type check.

    Raised by from_trace_dict before any envelope is built.  Also raised by
    CompletedObservationRow.__post_init__ for direct-construction validation.
    """


def _require_key(d: dict, key: str, ctx: str) -> object:
    """Raise RelationshipError if key is absent from d.  Returns the value."""
    if key not in d:
        raise RelationshipError(f"{ctx}: required key {key!r} absent from snapshot")
    return d[key]


def _require_plain_positive_id(value: object, name: str) -> int:
    """
    Raise RelationshipError if value is not a plain positive integer.
    Never calls int() to coerce; bool/string/float are all rejected.
    """
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise RelationshipError(
            f"{name} must be a plain positive integer; "
            f"got {value!r} (type {type(value).__name__}). "
            "Never coerce with int() — supply correctly typed source data."
        )
    return value


def _require_nonempty_string(value: object, name: str) -> str:
    """Raise RelationshipError if value is not a non-empty string."""
    if not isinstance(value, str) or not value:
        raise RelationshipError(f"{name} must be a non-empty string; got {value!r}")
    return value


@dataclass
class CompletedObservationRow:
    """
    One CSV row for the completed-observation evaluation dataset.

    Combines the ObservationEnvelope (execution evidence) with the
    authored expected labels and independently configured expected source.

    __post_init__ validates both the envelope and expected_source_config.
    Direct construction is fully validated — no bypass.

    expected_card_id: explicitly set ('' for no-card-negative rows; absent key is error).
    expected_source_config: independently configured by the evaluation operator;
      NOT derived from trace records; validates chatbot_public_id + pipeline_sha256.
    """

    observation: ObservationEnvelope
    expected_route: str
    expected_source_config: dict
    expected_category: str = ""
    expected_card_id: str = ""
    source: str = ""

    def __post_init__(self) -> None:
        """Validate observation and expected_source_config at construction time."""
        errors = self.observation.validate()
        if errors:
            raise RelationshipError("ObservationEnvelope validation failed: " + "; ".join(errors))
        self._validate_expected_source_config()

    def _validate_expected_source_config(self) -> None:
        """Validate that expected_source_config has required identity fields."""
        cfg = self.expected_source_config
        if not isinstance(cfg, dict) or not cfg:
            raise RelationshipError("expected_source_config must be a non-empty dict")
        cp = cfg.get("chatbot_public_id") or ""
        if not cp or not isinstance(cp, str):
            raise RelationshipError("expected_source_config.chatbot_public_id must be a non-empty string")
        sha = cfg.get("pipeline_sha256") or ""
        if not _is_valid_sha256(sha):
            raise RelationshipError("expected_source_config.pipeline_sha256 must be a 64-hex SHA256 string")
        if cp != self.observation.chatbot_id:
            raise RelationshipError("expected_source_config chatbot does not match the captured observation")
        if sha != self.observation.execution_fingerprint["pipeline_sha256"]:
            raise RelationshipError("expected_source_config pipeline does not match the captured observation")

    # ------------------------------------------------------------------
    # Trusted-runner factory: validates ALL relationships before building
    # ------------------------------------------------------------------

    @classmethod
    def from_trace_dict(
        cls,
        trace: dict,
        session: dict,
        experiment: dict,
        input_message: dict,
        output_message: dict,
        expected_route: str,
        expected_source_config: dict,
        expected_category: str = "",
        expected_card_id: str = "",
        source: str = "",
    ) -> CompletedObservationRow:
        """
        Build a CompletedObservationRow from separate trusted record snapshots,
        performing strict relationship and type checks before creating any envelope.

        NEVER calls int(), str(), float() to repair bad source values.
        NEVER defaults absent metric_profile, n_turns, captured_output_tags,
        or pipeline_sha256.  Missing keys raise RelationshipError explicitly.

        Parameters
        ----------
        trace: Snapshot of Trace model fields:
          trace_id              str    Trace.trace_id (UUID string)
          input_message_id      int    Trace.input_message FK PK (source: models.py:33-34)
          output_message_id     int    Trace.output_message FK PK (source: models.py:36-38)
          session_id            int    Trace.session FK PK (source: models.py:27-29)
          experiment_id         int    Trace.experiment FK PK (source: models.py:24-26)
          team_id               int    Trace.team FK PK (source: models.py:39)
          status                str    Trace.status — must be "success"
          error                 str    Trace.error (source: models.py:54) — must be ""
          n_turns               int|None  EXPLICIT KEY; Trace.n_turns (source: models.py:55)
          metric_profile        dict   Explicitly captured — never defaulted
          captured_output_tags  list   Explicitly captured — never defaulted to []
          pipeline_sha256       str    64-hex SHA256 of pipeline artifact
          experiment_version_number int|None  Trace.experiment_version_number (models.py:50)

        session: Snapshot of ExperimentSession fields:
          id           int  PK
          external_id  str  ExperimentSession.external_id (UUID-format string)
          experiment_id int  FK → Experiment PK
          chat_id      int  FK → Chat PK (from OneToOneField, models.py:1581)
          team_id      int  from BaseTeamModel

        experiment: Snapshot of Experiment fields:
          id        int  PK
          public_id str  Experiment.public_id (UUID, source: models.py:574)
          team_id   int  from BaseTeamModel

        input_message: Snapshot of ChatMessage (the human turn):
          id           int  ChatMessage PK
          chat_id      int  FK → Chat PK
          message_type str  must be "human" (ChatMessageType.HUMAN)
          content      str  original text (non-empty)

        output_message: Snapshot of ChatMessage (the AI turn):
          id           int  ChatMessage PK
          chat_id      int  FK → Chat PK
          message_type str  must be "ai" (ChatMessageType.AI)
          content      str  original text (non-empty)

        expected_source_config: Independently configured by the evaluation operator.
          chatbot_public_id  str  expected Experiment.public_id
          pipeline_sha256    str  expected 64-hex SHA256 of pipeline artifact

        Raises RelationshipError if any check fails.
        """
        # --- Validate all required keys are present BEFORE reading values ---
        for key in (
            "trace_id",
            "input_message_id",
            "output_message_id",
            "session_id",
            "experiment_id",
            "team_id",
            "status",
            "error",
            "metric_profile",
            "captured_output_tags",
            "pipeline_sha256",
            "experiment_version_number",
        ):
            _require_key(trace, key, "trace")
        # n_turns key must be present (explicit); value may be None
        _require_key(trace, "n_turns", "trace")

        for key in ("id", "external_id", "experiment_id", "chat_id", "team_id"):
            _require_key(session, key, "session")
        for key in ("id", "public_id", "team_id"):
            _require_key(experiment, key, "experiment")
        for key in ("id", "chat_id", "message_type", "content"):
            _require_key(input_message, key, "input_message")
            _require_key(output_message, key, "output_message")

        # --- Type checks: never coerce bad values ---

        # Integer PKs / FKs: must be plain positive integers (not bool, not string)
        trace_session_id = _require_plain_positive_id(trace["session_id"], "trace.session_id")
        trace_experiment_id = _require_plain_positive_id(trace["experiment_id"], "trace.experiment_id")
        trace_team_id = _require_plain_positive_id(trace["team_id"], "trace.team_id")
        trace_input_msg_id = _require_plain_positive_id(trace["input_message_id"], "trace.input_message_id")
        trace_output_msg_id = _require_plain_positive_id(trace["output_message_id"], "trace.output_message_id")

        session_id = _require_plain_positive_id(session["id"], "session.id")
        session_exp_id = _require_plain_positive_id(session["experiment_id"], "session.experiment_id")
        session_chat_id = _require_plain_positive_id(session["chat_id"], "session.chat_id")
        session_team_id = _require_plain_positive_id(session["team_id"], "session.team_id")

        experiment_id = _require_plain_positive_id(experiment["id"], "experiment.id")
        experiment_team_id = _require_plain_positive_id(experiment["team_id"], "experiment.team_id")

        in_msg_id = _require_plain_positive_id(input_message["id"], "input_message.id")
        in_msg_chat_id = _require_plain_positive_id(input_message["chat_id"], "input_message.chat_id")
        out_msg_id = _require_plain_positive_id(output_message["id"], "output_message.id")
        out_msg_chat_id = _require_plain_positive_id(output_message["chat_id"], "output_message.chat_id")

        # String fields: must be non-empty strings
        trace_id = _require_nonempty_string(trace["trace_id"], "trace.trace_id")
        session_external_id = _require_nonempty_string(session["external_id"], "session.external_id")
        experiment_public_id = _require_nonempty_string(experiment["public_id"], "experiment.public_id")
        in_msg_content = _require_nonempty_string(input_message["content"], "input_message.content")
        out_msg_content = _require_nonempty_string(output_message["content"], "output_message.content")

        # --- Trace status and error: never overwrite ---
        if trace["status"] != "success":
            raise RelationshipError(
                f"trace_status must be 'success'; got {trace['status']!r}. trace.error={trace['error']!r}"
            )
        if not isinstance(trace["error"], str):
            raise RelationshipError("trace.error must be an actual string, not a falsy substitute")
        if trace["error"]:
            raise RelationshipError(
                f"trace.error is non-empty: {trace['error']!r}. "
                "A recorded trace error cannot be ignored or overwritten."
            )

        # --- n_turns: validate value type (key already confirmed present) ---
        n_turns = trace["n_turns"]
        if n_turns is not None:
            if isinstance(n_turns, bool) or not isinstance(n_turns, int):
                raise RelationshipError(
                    f"trace.n_turns must be int or None; got {n_turns!r} (type {type(n_turns).__name__})"
                )

        # --- metric_profile: must be a dict (never defaulted) ---
        metric_profile = trace["metric_profile"]
        if not isinstance(metric_profile, dict):
            raise RelationshipError(
                f"trace.metric_profile must be a dict; got {type(metric_profile).__name__}. "
                "Never default to VERIFIED_METRIC_PROFILE."
            )

        # --- captured_output_tags: must be a list, all strings (never defaulted) ---
        raw_tags = trace["captured_output_tags"]
        if not isinstance(raw_tags, list):
            raise RelationshipError(
                f"trace.captured_output_tags must be a list; got {type(raw_tags).__name__}. Never default to []."
            )
        for i, tag in enumerate(raw_tags):
            if not isinstance(tag, str):
                raise RelationshipError(f"trace.captured_output_tags[{i}] is not a string: {tag!r}")

        # --- pipeline_sha256: must be valid 64-hex string ---
        pipeline_sha256 = trace["pipeline_sha256"]
        if not _is_valid_sha256(pipeline_sha256):
            raise RelationshipError(f"trace.pipeline_sha256 must be a 64-hex SHA256 string; got {pipeline_sha256!r}")

        # --- experiment_version_number: may be None; if int, must not be bool ---
        evn = trace["experiment_version_number"]
        if evn is not None and (isinstance(evn, bool) or not isinstance(evn, int)):
            raise RelationshipError(f"trace.experiment_version_number must be int or None; got {evn!r}")

        # --- Relationship checks ---

        # Trace FK bindings: exact message IDs (source: trace/models.py:33-38)
        if trace_input_msg_id != in_msg_id:
            raise RelationshipError(
                f"trace.input_message_id={trace_input_msg_id} != input_message.id={in_msg_id}. "
                "Must be the exact Trace.input_message FK (apps/trace/models.py:33-34)."
            )
        if trace_output_msg_id != out_msg_id:
            raise RelationshipError(
                f"trace.output_message_id={trace_output_msg_id} != output_message.id={out_msg_id}. "
                "Must be the exact Trace.output_message FK (apps/trace/models.py:36-38)."
            )

        # Trace session FK
        if trace_session_id != session_id:
            raise RelationshipError(f"trace.session_id={trace_session_id} != session.id={session_id}")

        # Trace experiment FK
        if trace_experiment_id != experiment_id:
            raise RelationshipError(f"trace.experiment_id={trace_experiment_id} != experiment.id={experiment_id}")

        # Session's experiment matches the experiment snapshot
        if session_exp_id != experiment_id:
            raise RelationshipError(f"session.experiment_id={session_exp_id} != experiment.id={experiment_id}")

        # Team IDs must match across all snapshots
        if trace_team_id != session_team_id:
            raise RelationshipError(f"trace.team_id={trace_team_id} != session.team_id={session_team_id}")
        if trace_team_id != experiment_team_id:
            raise RelationshipError(f"trace.team_id={trace_team_id} != experiment.team_id={experiment_team_id}")

        # Messages must belong to session's chat
        if in_msg_chat_id != session_chat_id:
            raise RelationshipError(f"input_message.chat_id={in_msg_chat_id} != session.chat_id={session_chat_id}")
        if out_msg_chat_id != session_chat_id:
            raise RelationshipError(f"output_message.chat_id={out_msg_chat_id} != session.chat_id={session_chat_id}")

        # Message IDs must be distinct
        if in_msg_id == out_msg_id:
            raise RelationshipError(f"same_id: input and output messages have the same PK ({in_msg_id})")

        # Message types (ChatMessageType.HUMAN="human", AI="ai", apps/chat/models.py:111-114)
        if input_message["message_type"] != "human":
            raise RelationshipError(
                f"input_message.message_type must be 'human'; got {input_message['message_type']!r}"
            )
        if output_message["message_type"] != "ai":
            raise RelationshipError(f"output_message.message_type must be 'ai'; got {output_message['message_type']!r}")

        # Build the envelope with captured values (no defaults injected)
        env = ObservationEnvelope(
            trace_id=trace_id,
            session_id=session_external_id,
            chatbot_id=experiment_public_id,
            input_message_id=in_msg_id,
            output_message_id=out_msg_id,
            input_text=in_msg_content,
            output_text=out_msg_content,
            n_turns=n_turns,
            output_tags=list(raw_tags),
            execution_fingerprint={
                "pipeline_sha256": pipeline_sha256,
                "experiment_version_number": evn,
            },
            metric_profile=dict(metric_profile),
            trace_status="success",
            trace_error="",
        )

        # CompletedObservationRow.__post_init__ will validate the envelope
        return cls(
            observation=env,
            expected_route=expected_route,
            expected_source_config=expected_source_config,
            expected_category=expected_category,
            expected_card_id=expected_card_id,
            source=source,
        )

    # ------------------------------------------------------------------
    # CSV export
    # ------------------------------------------------------------------

    def to_csv_row(self) -> dict[str, str]:
        """
        Return a dict keyed by COMPLETED_OBS_CSV_COLUMNS for csv.DictWriter.

        JSON null inside the envelope JSON string is preserved by json.dumps.

        Scalar context labels (expected_route, expected_category, expected_card_id)
        are JSON-encoded as string literals (e.g. '"SAFE"', '""').  This ensures
        their CSV cells are always non-empty, so the UPDATE path
        (_extract_row_data tasks.py:1033 'and value' guard) keeps them alongside
        the CREATE path (tasks.py:922-926 column-presence check).  Values remain
        STRING type after parse_csv_value_as_json — bool/None/int are never
        produced, including for slugs that look like JSON primitives ('false',
        'null', '123').
        """
        import json as _json

        self.__post_init__()
        return {
            "input_content": self.observation.input_text,
            "output_content": self.observation.output_text,
            "context.expected_route": _json.dumps(self.expected_route),
            "context.expected_category": _json.dumps(self.expected_category),
            "context.expected_card_id": _json.dumps(self.expected_card_id),
            "context.observation": self.observation.to_json(),
            "context.expected_source": _json.dumps(self.expected_source_config),
            "source": self.source,
        }


def write_completed_observations_csv(rows: list[CompletedObservationRow], dest: IO[str]) -> None:
    """Write rows to dest as an OCS-compatible completed-observation dataset CSV.

    Validates every row before writing.  Raises RelationshipError if any row
    has an invalid envelope or expected_source_config.
    """
    for i, row in enumerate(rows):
        try:
            row.__post_init__()
        except RelationshipError as exc:
            raise RelationshipError(f"Row {i}: {exc}") from exc

    writer = csv.DictWriter(dest, fieldnames=COMPLETED_OBS_CSV_COLUMNS)
    writer.writeheader()
    for row in rows:
        writer.writerow(row.to_csv_row())
