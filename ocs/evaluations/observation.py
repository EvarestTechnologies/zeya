"""
Completed-observation envelope: shared validator, metric-profile constants,
and evaluator code builder.

ARCHITECTURE
------------
All three evaluators operate in *completed-observation mode*: the pipeline ran,
the original turn is recorded, and the evaluator inspects evidence from that
completed execution.  generated_response must be empty; original output comes
from output.content.

The observation envelope is a JSON dict stored in context["observation"] and
context["expected_source"] (a separately configured policy dict).  Both are
exported to the evaluation dataset CSV and parsed back to dicts by
parse_csv_value_as_json (tasks.py:922-926).

PROVENANCE NOTE (approved-design-reset.md §28):
  Evaluators only attest INTERNAL CONSISTENCY of observations from the trusted
  runner.  Arbitrary user-authored JSON can lie.  relationship checks happen in
  the Python-side adapter (completed_adapter.py).  Neither is cryptographic
  attestation of untrusted uploads.

METRIC PROFILE (source: opus-evidence-design.json, metrics.py:173)
--------------------------------------------------------------------
OCS engine commit: 9f5c25476555ff74a167c6a14832ce798832847a
MetricsCollector SHA256: c296ebb6b41517d85f9614ce6ee06eb4cb0906517a33c8052302f9c9fa7db9e7
OCSTracer SHA256: e9b64b52681957a1bd79ff5480840af3e20f7afa6f387908a6c72e14c2e0076e

MetricsCollector.get_metrics() (metrics.py:173):
    return TraceMetrics(n_turns=turns or None, ...)
`turns or None` -> 0 or None = None.
Deployed contract: no_calls=null, one_start=1.

EXECUTION FINGERPRINT
---------------------
execution_fingerprint.pipeline_sha256: 64-hex SHA256 of the pipeline definition
artifact captured by the trusted runner at execution time.  It is NOT the current
mutable pipeline file; the runner captures it around its own turn.
execution_fingerprint.experiment_version_number: Trace.experiment_version_number
(apps/trace/models.py:50 PositiveIntegerField, null=True).
  - May be None (Trace did not record version).
  - May be 0 (PositiveIntegerField in Django accepts >= 0 per DB constraint).
  - May be any positive integer.
  - Must NOT be a bool or string.

EXPECTED SOURCE IDENTITY
------------------------
context["expected_source"] is independently configured by the evaluation operator
and checked against the captured execution evidence.  It is separate from expected
labels (expected_route etc.) and is NOT derived from the trace records themselves.
Required fields:
  chatbot_public_id: str  # Experiment.public_id UUID (non-empty)
  pipeline_sha256: str    # 64-hex SHA256 (must match observation.execution_fingerprint)

RESTRICTEDPYTHON CONSTRAINTS
-----------------------------
  - `list` from limited_builtins is `limited_list` (function, not type).
    isinstance(x, list) fails; use negated checks.
  - Names starting with `_` are rejected; use plain names.
  - `type`, `hasattr`, `getattr` are not in safe/utility/limited_builtins.
  - `re` is globally injected and available without an import statement.
  - `float` is in safe_builtins; `dict`, `isinstance`, `bool`, `int`, `str` available.
"""

from __future__ import annotations

import json
import re as _re_module
from dataclasses import dataclass

# ---------------------------------------------------------------------------
# Verified metric profile constants
# ---------------------------------------------------------------------------

VERIFIED_METRIC_PROFILE: dict[str, str] = {
    "ocs_pin": "9f5c25476555ff74a167c6a14832ce798832847a",
    "collector_sha256": "c296ebb6b41517d85f9614ce6ee06eb4cb0906517a33c8052302f9c9fa7db9e7",
    "tracer_sha256": "e9b64b52681957a1bd79ff5480840af3e20f7afa6f387908a6c72e14c2e0076e",
}

OBSERVATION_SCHEMA_VERSION = "1"
OBSERVATION_MODE = "completed_trace"

# Standard RFC 4122 lowercase UUID pattern (8-4-4-4-12 hex groups).
_UUID_RE_PATTERN = r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
_UUID_RE = _re_module.compile(_UUID_RE_PATTERN)

# SHA-256 hex pattern: exactly 64 lowercase hex chars.
_SHA256_RE_PATTERN = r"^[0-9a-f]{64}$"
_SHA256_RE = _re_module.compile(_SHA256_RE_PATTERN)


def _is_valid_uuid(value: object) -> bool:
    return isinstance(value, str) and bool(_UUID_RE.match(value))


def _is_valid_sha256(value: object) -> bool:
    return isinstance(value, str) and bool(_SHA256_RE.match(value))


def _is_plain_positive_id(value: object) -> bool:
    """True if value is a plain positive integer (not bool, not string, not <=0)."""
    return not isinstance(value, bool) and isinstance(value, int) and value > 0


# ---------------------------------------------------------------------------
# Shared validation body — inlined into every evaluator's main()
# Variables produced for the specific body:
#   input_text, output_text, obs, n_turns_raw, output_tags
# ---------------------------------------------------------------------------

_SHARED_VALIDATION_BODY = """\
    # ================================================================
    # SHARED COMPLETED-OBSERVATION VALIDATION
    # (inlined from observation.py _SHARED_VALIDATION_BODY)
    # Profile: OCS 9f5c254; MetricsCollector metrics.py:173 turns or None
    # Adapter-completion: strict IDs, FK binding, expected source, no defaults
    # ================================================================

    # -- Mode gate: reject fresh re-generation --
    if generated_response:
        return {
            "error": "fresh_generation_rejected",
            "note": (
                "generated_response non-empty: disable Run generation step. "
                "Completed-observation mode uses original output.content."
            ),
        }

    # -- Decode quoted CSV scalar transport at the actual consumer boundary --
    # OCS parses objects/arrays only; callers must not need an extra host helper.
    if isinstance(context, dict):
        import json

        context = dict(context)
        for label in ("expected_route", "expected_category", "expected_card_id"):
            value = context.get(label)
            if isinstance(value, str) and value.startswith('"'):
                try:
                    decoded = json.loads(value)
                except ValueError:
                    return {"error": "csv_scalar_invalid", "field": label}
                if not isinstance(decoded, str):
                    return {"error": "csv_scalar_invalid", "field": label}
                context[label] = decoded

    # -- Input/output must be non-empty original turn content --
    input_text = (input.get("content") or "") if isinstance(input, dict) else ""
    output_text = (output.get("content") or "") if isinstance(output, dict) else ""
    if not input_text:
        return {"error": "input_content_missing"}
    if not output_text:
        return {"error": "output_content_missing"}

    if not isinstance(input_text, str) or not isinstance(output_text, str):
        return {"error": "message_content_invalid_type"}

    # -- Observation envelope --
    obs = (context.get("observation") if isinstance(context, dict) else None)
    if not isinstance(obs, dict):
        return {"error": "observation_missing"}

    # -- Schema version and mode --
    if obs.get("schema_version") != "1":
        return {"error": "observation_schema_mismatch", "got": obs.get("schema_version")}
    if obs.get("mode") != "completed_trace":
        return {"error": "observation_mode_mismatch", "got": obs.get("mode")}

    # -- Trace ID: required, strict lowercase UUID format (8-4-4-4-12) --
    UUID_RE = r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
    trace_id = obs.get("trace_id") or ""
    if not trace_id or not re.match(UUID_RE, str(trace_id)):
        return {
            "error": "trace_id_invalid_format",
            "note": "trace_id must be a lowercase hyphenated UUID",
        }

    # -- Session ID: required, strict lowercase UUID format --
    session_id = obs.get("session_id") or ""
    if not session_id or not re.match(UUID_RE, str(session_id)):
        return {"error": "session_id_invalid_format"}

    # -- Chatbot ID: required, non-empty string --
    chatbot_id = obs.get("chatbot_id")
    if not chatbot_id or not isinstance(chatbot_id, str):
        return {"error": "chatbot_id_missing"}

    # -- Message IDs: distinct positive integers (never bool, never string, never <=0) --
    # bool is a subclass of int in Python; check isinstance(x, bool) FIRST.
    imid = obs.get("input_message_id")
    if isinstance(imid, bool) or not isinstance(imid, int) or imid <= 0:
        return {
            "error": "input_message_id_invalid",
            "note": "input_message_id must be a positive integer (ChatMessage PK); bool/string/zero rejected",
        }
    omid = obs.get("output_message_id")
    if isinstance(omid, bool) or not isinstance(omid, int) or omid <= 0:
        return {"error": "output_message_id_invalid"}
    if imid == omid:
        return {"error": "message_id_collision"}

    # -- Trace must be successful, no error recorded --
    if obs.get("trace_status") != "success":
        return {
            "error": "trace_not_successful",
            "trace_status": obs.get("trace_status"),
            "trace_error": obs.get("trace_error") or "",
        }
    if not isinstance(obs.get("trace_error"), str):
        return {"error": "trace_error_invalid_type"}
    if obs.get("trace_error"):
        return {"error": "trace_error_present", "trace_error": obs["trace_error"]}

    # -- Input/output text binding (exact string match, no hash) --
    if obs.get("input_text") != input_text:
        return {"error": "input_binding_mismatch"}
    if obs.get("output_text") != output_text:
        return {"error": "output_binding_mismatch"}

    # -- Metric profile pins: all three hashes required, exact match --
    mp = obs.get("metric_profile")
    if not isinstance(mp, dict):
        return {"error": "metric_profile_missing"}
    EXP_PIN = "9f5c25476555ff74a167c6a14832ce798832847a"
    EXP_COLL = "c296ebb6b41517d85f9614ce6ee06eb4cb0906517a33c8052302f9c9fa7db9e7"
    EXP_TRAC = "e9b64b52681957a1bd79ff5480840af3e20f7afa6f387908a6c72e14c2e0076e"
    if mp.get("ocs_pin") != EXP_PIN:
        return {"error": "metric_profile_mismatch", "field": "ocs_pin", "got": mp.get("ocs_pin")}
    if mp.get("collector_sha256") != EXP_COLL:
        return {"error": "metric_profile_mismatch", "field": "collector_sha256"}
    if mp.get("tracer_sha256") != EXP_TRAC:
        return {"error": "metric_profile_mismatch", "field": "tracer_sha256"}

    # -- n_turns: explicit key required --
    if "n_turns" not in obs:
        return {
            "error": "n_turns_key_absent",
            "note": "observation.n_turns key must be present (None for zero LLM starts)",
        }
    n_turns_raw = obs["n_turns"]
    if n_turns_raw is not None:
        if isinstance(n_turns_raw, bool) or not isinstance(n_turns_raw, int):
            return {"error": "n_turns_invalid_type"}
        if n_turns_raw < 0:
            return {"error": "n_turns_negative"}
        if n_turns_raw == 0:
            return {
                "error": "n_turns_zero_inconsistent",
                "note": (
                    "n_turns=0 unreachable under MetricsCollector (metrics.py:173: turns or None). "
                    "Verified profile emits NULL for zero calls."
                ),
            }

    # -- Execution fingerprint: pipeline_sha256 required (64-hex) --
    SHA256_RE = r"^[0-9a-f]{64}$"
    exec_fp = obs.get("execution_fingerprint")
    if not isinstance(exec_fp, dict):
        return {"error": "execution_fingerprint_missing"}
    obs_pipeline = exec_fp.get("pipeline_sha256") or ""
    if not obs_pipeline or not re.match(SHA256_RE, str(obs_pipeline)):
        return {
            "error": "execution_fingerprint_missing_sha256",
            "note": "execution_fingerprint.pipeline_sha256 must be a 64-hex SHA256 string",
        }
    # experiment_version_number: may be None (Trace.experiment_version_number null=True)
    # or any integer (PositiveIntegerField accepts >= 0); must not be bool/string.
    # Key must be explicitly present (None != absent).
    if "experiment_version_number" not in exec_fp:
        return {"error": "execution_fingerprint_missing_version_key"}
    evn = exec_fp["experiment_version_number"]
    if evn is not None and (isinstance(evn, bool) or not isinstance(evn, int)):
        return {"error": "execution_fingerprint_invalid_version_type"}
    if evn is not None and evn < 0:
        return {"error": "execution_fingerprint_negative_version"}

    # -- Output tags: must be a list; each element must be a string --
    output_tags = obs.get("output_tags")
    if not (
        output_tags is not None
        and not isinstance(output_tags, str)
        and not isinstance(output_tags, dict)
        and not isinstance(output_tags, (int, float, bool))
    ):
        return {"error": "output_tags_invalid"}
    for tag in output_tags:
        if not isinstance(tag, str):
            return {"error": "output_tags_non_string_element"}

    # -- Expected source identity check (independent of expected labels) --
    # context["expected_source"] is configured by the evaluation operator.
    # It must match the captured execution evidence in the observation envelope.
    expected_source = context.get("expected_source") if isinstance(context, dict) else None
    if not isinstance(expected_source, dict):
        return {
            "error": "expected_source_missing",
            "note": "context.expected_source must be a dict (from CSV context.expected_source column)",
        }
    exp_chatbot = expected_source.get("chatbot_public_id") or ""
    if not exp_chatbot or not isinstance(exp_chatbot, str):
        return {"error": "expected_source_chatbot_missing"}
    if chatbot_id != exp_chatbot:
        return {
            "error": "source_chatbot_mismatch",
            "note": "observation.chatbot_id != expected_source.chatbot_public_id",
        }
    exp_pipeline = expected_source.get("pipeline_sha256") or ""
    if not exp_pipeline or not re.match(SHA256_RE, str(exp_pipeline)):
        return {
            "error": "expected_source_pipeline_missing",
            "note": "expected_source.pipeline_sha256 must be a 64-hex SHA256 string",
        }
    if obs_pipeline != exp_pipeline:
        return {
            "error": "pipeline_sha256_mismatch",
            "note": "observed pipeline hash does not match expected source pipeline hash",
        }

    # ================================================================
    # END SHARED VALIDATION
    # Local bindings now available:
    #   input_text, output_text — original turn content (binding verified)
    #   obs                     — full validated observation envelope
    #   n_turns_raw             — None (zero LLM starts) or int>=1 (calls)
    #   output_tags             — list[str], all elements strings, may be empty
    # ================================================================
"""


def build_evaluator_code(specific_body: str, module_comment: str = "") -> str:
    """
    Assemble a complete OCS PythonEvaluator code string.

    Inlines _SHARED_VALIDATION_BODY at the top of main(), then appends
    specific_body (4-space indented, for inside main()).
    """
    header = "def main(input, output, context, full_history, generated_response, **kwargs):"
    if module_comment:
        comment_lines = "\n".join(f"    # {line}" for line in module_comment.splitlines())
        return f"{header}\n{comment_lines}\n{_SHARED_VALIDATION_BODY}\n{specific_body}\n"
    return f"{header}\n{_SHARED_VALIDATION_BODY}\n{specific_body}\n"


# ---------------------------------------------------------------------------
# Observation envelope builder (Python-side, not RestrictedPython)
# ---------------------------------------------------------------------------


@dataclass
class ObservationEnvelope:
    """
    One completed-turn observation, ready to be exported as context.observation.

    Fields mirror the shared validator requirements exactly.
    The parent runner populates this from real OCS Trace + ChatMessage records.

    FIELD SEMANTICS:

    metric_profile: Explicitly captured from the actual execution environment.
      NEVER defaulted from VERIFIED_METRIC_PROFILE; must be supplied explicitly.

    execution_fingerprint: Per-turn captured record from the trusted runner.
      pipeline_sha256: 64-hex SHA256 of the pipeline artifact (immutable capture).
      experiment_version_number: Trace.experiment_version_number (may be None or 0+).

    n_turns: From MetricsCollector.get_metrics() (metrics.py:173, turns or None).
      None  = zero LLM starts (EMERGENCY path success)
      int   = number of LLM calls (>= 1); 0 is never emitted by this profile.

    output_tags: Tags written by CodeNodes via add_message_tag during the
      completed pipeline execution.  All elements must be strings.
      Empty list is valid (no tags fired).

    SOURCE: apps/trace/models.py lines 20-56 (Trace)
            apps/chat/models.py ChatMessage (line 182)
            apps/experiments/models.py ExperimentSession (line 1563)
    """

    # Required fields (no defaults) — must all be supplied explicitly by the runner
    trace_id: str  # Trace.trace_id UUID (lowercase hyphenated)
    session_id: str  # ExperimentSession.external_id (UUID string)
    chatbot_id: str  # Experiment.public_id (non-empty)
    input_message_id: int  # ChatMessage PK (positive int, not bool)
    output_message_id: int  # ChatMessage PK (must differ from input)
    input_text: str  # Exact original user message text
    output_text: str  # Exact original AI response text
    n_turns: int | None  # MetricsCollector.get_metrics().n_turns
    output_tags: list[str]  # Captured output message tags (all strings)
    execution_fingerprint: dict  # {"pipeline_sha256": "64hex", "experiment_version_number": int|None}
    metric_profile: dict  # Explicitly captured — NEVER defaulted to VERIFIED_METRIC_PROFILE

    # Optional fields with sensible defaults
    trace_status: str = "success"
    trace_error: str = ""
    schema_version: str = OBSERVATION_SCHEMA_VERSION
    mode: str = OBSERVATION_MODE

    def to_dict(self) -> dict:
        """Return a plain dict suitable for json.dumps (None preserved as JSON null)."""
        return {
            "schema_version": self.schema_version,
            "mode": self.mode,
            "trace_id": self.trace_id,
            "session_id": self.session_id,
            "chatbot_id": self.chatbot_id,
            "input_message_id": self.input_message_id,
            "output_message_id": self.output_message_id,
            "trace_status": self.trace_status,
            "trace_error": self.trace_error,
            "n_turns": self.n_turns,
            "metric_profile": dict(self.metric_profile),
            "output_tags": list(self.output_tags),
            "execution_fingerprint": dict(self.execution_fingerprint),
            "input_text": self.input_text,
            "output_text": self.output_text,
        }

    def to_json(self) -> str:
        """Serialize to JSON string for the context.observation CSV column."""
        return json.dumps(self.to_dict())

    def validate(self) -> list[str]:
        """
        Return a list of validation error strings.  Empty list = ready for export.

        Mirrors the evaluator-code checks in _SHARED_VALIDATION_BODY so the
        Python-side adapter can pre-validate before writing the CSV.
        """
        errors: list[str] = []
        if self.schema_version != OBSERVATION_SCHEMA_VERSION:
            errors.append("schema_version mismatch")
        if self.mode != OBSERVATION_MODE:
            errors.append("mode mismatch")

        if not _is_valid_uuid(self.trace_id):
            errors.append(f"trace_id must be lowercase hyphenated UUID; got {self.trace_id!r}")
        if not _is_valid_uuid(self.session_id):
            errors.append(f"session_id must be lowercase hyphenated UUID; got {self.session_id!r}")
        if not self.chatbot_id or not isinstance(self.chatbot_id, str):
            errors.append("chatbot_id must be a non-empty string")

        for name, mid in (("input_message_id", self.input_message_id), ("output_message_id", self.output_message_id)):
            if isinstance(mid, bool) or not isinstance(mid, int) or mid <= 0:
                errors.append(f"{name} must be a plain positive integer; got {mid!r} (type {type(mid).__name__})")

        if self.input_message_id == self.output_message_id:
            errors.append("input_message_id and output_message_id must differ")

        if not isinstance(self.input_text, str) or not self.input_text:
            errors.append("input_text must be a non-empty string")
        if not isinstance(self.output_text, str) or not self.output_text:
            errors.append("output_text must be a non-empty string")

        if self.n_turns is not None:
            if isinstance(self.n_turns, bool) or not isinstance(self.n_turns, int):
                errors.append("n_turns must be int or None")
            elif self.n_turns == 0:
                errors.append("n_turns=0 unreachable under verified profile (metrics.py:173 turns or None)")
            elif self.n_turns < 0:
                errors.append("n_turns negative")

        if not isinstance(self.output_tags, list):
            errors.append("output_tags must be a list")
        else:
            for i, tag in enumerate(self.output_tags):
                if not isinstance(tag, str):
                    errors.append(f"output_tags[{i}] is not a string: {tag!r}")
                    break

        if not isinstance(self.execution_fingerprint, dict):
            errors.append("execution_fingerprint must be a dict")
        else:
            sha = self.execution_fingerprint.get("pipeline_sha256")
            if not _is_valid_sha256(sha):
                errors.append(f"execution_fingerprint.pipeline_sha256 must be a 64-hex SHA256; got {sha!r}")
            if "experiment_version_number" not in self.execution_fingerprint:
                errors.append("execution_fingerprint.experiment_version_number key missing")
            else:
                evn = self.execution_fingerprint["experiment_version_number"]
                if evn is not None and (isinstance(evn, bool) or not isinstance(evn, int)):
                    errors.append(f"execution_fingerprint.experiment_version_number must be int or None; got {evn!r}")
                elif evn is not None and evn < 0:
                    errors.append("execution_fingerprint.experiment_version_number must not be negative")

        if self.trace_status != "success":
            errors.append(f"trace_status is not 'success': {self.trace_status!r}")
        if not isinstance(self.trace_error, str):
            errors.append("trace_error must be a string")
        elif self.trace_error:
            errors.append(f"trace_error present: {self.trace_error!r}")

        if not isinstance(self.metric_profile, dict):
            errors.append("metric_profile must be a dict")
        elif self.metric_profile != VERIFIED_METRIC_PROFILE:
            errors.append("metric_profile does not match VERIFIED_METRIC_PROFILE")

        return errors


# ---------------------------------------------------------------------------
# CSV scalar label normalisation — shared evaluator boundary
#
# completed_adapter.to_csv_row() encodes expected_route, expected_category,
# expected_card_id as JSON string literals (e.g. '"SAFE"', '""') so their CSV
# cells are always non-empty and survive the UPDATE-path 'and value' guard
# (apps/evaluations/tasks.py:1033, OCS 9f5c254).
#
# parse_csv_value_as_json (utils.py:210-222) only decodes objects/arrays
# (starting with '{' or '['), not string literals, so the evaluators would
# receive '"SAFE"' instead of 'SAFE' and '"" instead of '' without
# an explicit decoding step.
#
# normalize_csv_scalar_labels() must be called once at the evaluator boundary
# (after CREATE or UPDATE path extraction, before EvaluatorHarness.run()).
# ---------------------------------------------------------------------------

#: Fields written as JSON string literals by completed_adapter.to_csv_row().
_CSV_SCALAR_LABEL_FIELDS: frozenset = frozenset({"expected_route", "expected_category", "expected_card_id"})


def _decode_csv_scalar(value: object, field: str) -> str:
    """Decode one JSON-encoded string literal written by to_csv_row().

    Accepts:
      - A Python str starting with '"' that is a valid JSON string literal
        decoding to str (e.g. '"SAFE"' → 'SAFE', '""' → '', '"false"' → 'false').
      - A Python str NOT starting with '"': returned as-is for backward
        compatibility with pre-encoding data written as plain strings.

    Rejects (fail closed with ValueError):
      - Non-str input.
      - A str starting with '"' that is not a valid JSON string literal.
      - A str that decodes to a non-str JSON value (bool, None, int, etc.).

    Parameters
    ----------
    value:
        Raw value from parse_csv_value_as_json.
    field:
        Field name used in error messages.

    Raises
    ------
    ValueError
        When value is a malformed or non-str JSON literal.
    """
    import json as _json

    if not isinstance(value, str):
        raise ValueError(f"CSV scalar label {field!r}: must be a string; got {type(value).__name__!r} {value!r}")
    # Pre-encoding compatibility: plain strings not starting with '"' pass through
    # unchanged.  Missing-label vs empty-label distinction is preserved by callers;
    # this function is not invoked for absent keys.
    if not value.startswith('"'):
        return value
    # JSON string literal: decode and require result to be str.  Fail closed on
    # any other JSON type (would only occur with malformed transport values).
    try:
        decoded = _json.loads(value)
    except _json.JSONDecodeError as exc:
        raise ValueError(f"CSV scalar label {field!r}: malformed JSON string literal {value!r}: {exc}") from exc
    if not isinstance(decoded, str):
        raise ValueError(
            f"CSV scalar label {field!r}: decoded to non-str "
            f"{type(decoded).__name__!r} {decoded!r}; only string values are accepted"
        )
    return decoded


def normalize_csv_scalar_labels(context: dict) -> dict:
    """Decode JSON-encoded scalar context labels at the evaluator boundary.

    Returns a **copy** of *context* with the three scalar label fields decoded
    from their JSON string literal representation back to their original string
    values.  The original dict is never mutated.

    Decoding rules
    --------------
    - ``expected_route``, ``expected_category``, ``expected_card_id`` are the
      only fields touched; all other keys are copied as-is.
    - A field that is **absent** from *context* remains absent (no defaulting).
    - A field whose value does **not** start with ``'"'`` is passed through
      unchanged (backward-compatible with pre-encoding plain string values).
    - A field whose value starts with ``'"'`` is JSON-decoded and must yield a
      ``str``.  Malformed or non-str quoted values raise ``ValueError``
      (fail closed).

    Value examples
    --------------
    ``'"SAFE"'``   → ``'SAFE'``
    ``'""'``       → ``''``       (empty string; no-card-negative preserved)
    ``'"false"'``  → ``'false'``  (string, not bool)
    ``'"null"'``   → ``'null'``   (string, not None)
    ``'"123"'``    → ``'123'``    (string, not int)
    ``'SAFE'``     → ``'SAFE'``   (pre-encoding plain string; pass-through)

    Parameters
    ----------
    context:
        Raw context dict as returned by parse_csv_value_as_json (via CREATE
        path tasks.py:922-926 or UPDATE path tasks.py:1030-1035).

    Returns
    -------
    dict
        New dict with scalar labels decoded.

    Raises
    ------
    TypeError
        When *context* is not a dict.
    ValueError
        When a named field holds a malformed or non-str quoted value.
    """
    if not isinstance(context, dict):
        raise TypeError(f"context must be a dict; got {type(context).__name__!r}")
    result = dict(context)  # shallow copy; never mutate the original
    for field in _CSV_SCALAR_LABEL_FIELDS:
        if field in result:
            result[field] = _decode_csv_scalar(result[field], field)
    return result
