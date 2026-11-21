"""
CSV scalar transport unit tests — Owner A, F1 (repair-1).

FINDING F1
----------
completed_adapter.to_csv_row() encodes expected_route, expected_category,
expected_card_id as JSON string literals (e.g. '"SAFE"', '""') so their CSV
cells survive the UPDATE-path 'and value' guard
(apps/evaluations/tasks.py:1033, OCS 9f5c254).

However parse_csv_value_as_json (utils.py:210-222, OCS 9f5c254) only decodes
objects/arrays; it returns JSON string literals as-is.  Without explicit
decoding the evaluators receive '"SAFE"' and report expected_route_unknown,
and '""' is treated as a named card slug (not no-card-negative).

FIX
---
  completed_adapter.py: JSON-encode the three scalar labels (cells non-empty).
  observation.py:       normalize_csv_scalar_labels() decodes the three labels
                        once at the evaluator boundary (copy, not mutate).

PORTABILITY
-----------
Core tests run without an OCS checkout.  The pinned OCS 9f5c254 source of
parse_csv_value_as_json and the UPDATE-path context extraction logic are
embedded below as documented string constants.  When the OCS_SOURCE
environment variable is set to the path of an OCS checkout, an optional probe
test verifies that the pinned functions match the actual checkout source.

Pinned source (OCS commit 9f5c25476555ff74a167c6a14832ce798832847a)
  parse_csv_value_as_json  apps/evaluations/utils.py:210-222
  _extract_row_data ctx    apps/evaluations/tasks.py:1030-1035
  CREATE path              apps/evaluations/tasks.py:922-926
"""

from __future__ import annotations

import csv
import io
import json
import os

import pytest

from ocs.evaluations.card_accuracy import CARD_ACCURACY_CODE
from ocs.evaluations.completed_adapter import (
    COMPLETED_OBS_COLUMN_MAPPING,
    CompletedObservationRow,
    write_completed_observations_csv,
)
from ocs.evaluations.evaluator_harness import EvaluatorHarness
from ocs.evaluations.no_llm_check import NO_LLM_CHECK_CODE
from ocs.evaluations.observation import (
    VERIFIED_METRIC_PROFILE,
    ObservationEnvelope,
    normalize_csv_scalar_labels,
)
from ocs.evaluations.route_check import ROUTE_CHECK_CODE

# ---------------------------------------------------------------------------
# Pinned OCS 9f5c254 source — parse_csv_value_as_json (utils.py:210-222)
#
# Embedded verbatim from OCS commit 9f5c25476555ff74a167c6a14832ce798832847a.
# This is the ACTUAL function the production CSV import path calls.
# No OCS checkout required for the core test suite.
# ---------------------------------------------------------------------------
_OCS_PINNED_COMMIT = "9f5c25476"

_PINNED_NS: dict = {}
exec(
    r"""
import json as _json


def normalize_json_quotes(text):
    text = text.replace('\u201c', '"').replace('\u201d', '"')
    return text.replace('\u2018', "'").replace('\u2019', "'")


def parse_csv_value_as_json(value):
    # Parse value as JSON if it's an object or array, otherwise return as-is.
    if not value:
        return value
    value_stripped = value.strip()
    if value_stripped.startswith(('{', '[')):
        try:
            normalized_value = normalize_json_quotes(value)
            return _json.loads(normalized_value)
        except (_json.JSONDecodeError, TypeError):
            return value
    return value
""",
    _PINNED_NS,
)
_parse_csv = _PINNED_NS["parse_csv_value_as_json"]


# ---------------------------------------------------------------------------
# Pinned UPDATE-path context extraction — tasks.py:1030-1035 (OCS 9f5c254)
#
# Exact five lines of _extract_row_data that scan context.* columns with the
# 'and value' truthy guard.  Source: tasks.py lines 1030-1035, commit 9f5c254.
# ---------------------------------------------------------------------------


def _update_path_extract(row: dict) -> dict:
    """UPDATE-path context extraction — tasks.py:1030-1035, OCS 9f5c254.

    'and value' at line 1033 is the guard that drops falsy (empty) cells.
    """
    context: dict = {}
    for col_name, value in row.items():
        if col_name.startswith("context.") and value:  # tasks.py:1033
            context[col_name.removeprefix("context.")] = _parse_csv(value)
    return context


def _create_path_extract(csv_row: dict) -> dict:
    """CREATE-path context extraction — tasks.py:922-926, OCS 9f5c254.

    Uses COMPLETED_OBS_COLUMN_MAPPING with column-presence check ('if csv_col
    in row'), not 'and value', so it always includes mapped fields regardless
    of cell value.
    """
    context: dict = {}
    for field_name, csv_col in COMPLETED_OBS_COLUMN_MAPPING["context"].items():
        if csv_col in csv_row:
            context[field_name] = _parse_csv(csv_row[csv_col])
    return context


# ---------------------------------------------------------------------------
# Optional OCS-SOURCE probe (skipped when OCS_SOURCE not set)
# ---------------------------------------------------------------------------
_OCS_SOURCE = os.environ.get("OCS_SOURCE")
_OCS_AVAILABLE = bool(_OCS_SOURCE)


@pytest.mark.skipif(not _OCS_AVAILABLE, reason="OCS_SOURCE env var not set; pinned source used")
def test_pinned_parse_csv_matches_actual_ocs_checkout():
    """Optional: verify pinned parse_csv_value_as_json matches OCS checkout source."""
    import ast
    import textwrap
    from pathlib import Path

    utils_path = Path(_OCS_SOURCE) / "apps" / "evaluations" / "utils.py"
    source = utils_path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    lines = source.splitlines()
    fn_source = None
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "parse_csv_value_as_json":
            fn_source = textwrap.dedent("\n".join(lines[node.lineno - 1 : node.end_lineno]))
            break
    assert fn_source is not None, "parse_csv_value_as_json not found in OCS checkout"

    # Verify behavioural equivalence on F1-critical inputs
    actual_ns: dict = {"_json": json}
    exec("def normalize_json_quotes(text): return text", actual_ns)  # minimal stub
    exec(fn_source, actual_ns)
    for val in ('""', '"SAFE"', '"EMERGENCY"', '"false"', '"null"', '"123"', "", "SAFE"):
        expected = _parse_csv(val)
        actual = actual_ns["parse_csv_value_as_json"](val)
        assert expected == actual, f"Pinned vs actual OCS mismatch for {val!r}: pinned={expected!r} actual={actual!r}"


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

_SHA = "aa" * 32  # 64-char hex, valid SHA256 format
_SOURCE_CONFIG = {
    "chatbot_public_id": "aabbccdd-0000-0000-0000-000000000003",
    "pipeline_sha256": _SHA,
}
_IN = "What should I eat during pregnancy?"
_OUT = "Eat iron-rich foods."


def _env(output_tags=None, n_turns=1) -> ObservationEnvelope:
    return ObservationEnvelope(
        trace_id="aabbccdd-0000-0000-0000-000000000001",
        session_id="aabbccdd-0000-0000-0000-000000000002",
        chatbot_id="aabbccdd-0000-0000-0000-000000000003",
        input_message_id=100,
        output_message_id=101,
        input_text=_IN,
        output_text=_OUT,
        n_turns=n_turns,
        output_tags=output_tags if output_tags is not None else [],
        execution_fingerprint={"pipeline_sha256": _SHA, "experiment_version_number": 1},
        metric_profile=dict(VERIFIED_METRIC_PROFILE),
    )


def _row(
    expected_route: str = "SAFE",
    expected_category: str = "",
    expected_card_id: str = "",
    output_tags=None,
    n_turns=1,
) -> CompletedObservationRow:
    return CompletedObservationRow(
        observation=_env(output_tags=output_tags, n_turns=n_turns),
        expected_route=expected_route,
        expected_source_config=_SOURCE_CONFIG,
        expected_category=expected_category,
        expected_card_id=expected_card_id,
    )


def _csv_dict(row: CompletedObservationRow) -> dict:
    buf = io.StringIO()
    write_completed_observations_csv([row], buf)
    buf.seek(0)
    return next(csv.DictReader(buf))


def _run(code: str, ctx: dict) -> dict:
    return EvaluatorHarness(code).run(
        input={"content": _IN},
        output={"content": _OUT},
        context=ctx,
        full_history="",
        generated_response="",
    )


# ---------------------------------------------------------------------------
# F1-BUG: exporter encoding — raw CSV cell values
# ---------------------------------------------------------------------------


class TestF1ExporterEncoding:
    """to_csv_row() must write JSON string literals so cells are non-empty."""

    def test_expected_route_safe_cell_encoded(self):
        assert _row(expected_route="SAFE").to_csv_row()["context.expected_route"] == '"SAFE"'

    def test_expected_route_emergency_cell_encoded(self):
        assert _row(expected_route="EMERGENCY").to_csv_row()["context.expected_route"] == '"EMERGENCY"'

    def test_expected_category_empty_cell_non_empty_and_truthy(self):
        cell = _row(expected_category="").to_csv_row()["context.expected_category"]
        assert cell == '""'
        assert bool(cell)  # truthy — survives 'and value' guard

    def test_expected_card_id_empty_cell_non_empty_and_truthy(self):
        cell = _row(expected_card_id="").to_csv_row()["context.expected_card_id"]
        assert cell == '""'
        assert bool(cell)  # truthy — survives 'and value' guard

    def test_expected_card_id_named_card_encoded(self):
        assert _row(expected_card_id="nutrition-01").to_csv_row()["context.expected_card_id"] == '"nutrition-01"'

    def test_slug_false_encoded_as_string_literal(self):
        assert _row(expected_card_id="false").to_csv_row()["context.expected_card_id"] == '"false"'

    def test_slug_null_encoded_as_string_literal(self):
        assert _row(expected_card_id="null").to_csv_row()["context.expected_card_id"] == '"null"'

    def test_slug_123_encoded_as_string_literal(self):
        assert _row(expected_card_id="123").to_csv_row()["context.expected_card_id"] == '"123"'


# ---------------------------------------------------------------------------
# F1-BUG: UPDATE-path dropping — existing bug proof (bug-doc tests)
# ---------------------------------------------------------------------------


class TestF1UpdatePathDropsBug:
    """Demonstrate the bug: raw '' dropped by UPDATE-path 'and value' guard.

    These tests PASS against current code and document the exact failure mode
    that JSON-encoding in to_csv_row() was introduced to fix.
    """

    def test_update_path_drops_empty_expected_card_id_raw(self):
        """_extract_row_data drops expected_card_id when CSV cell is ''."""
        raw_row = {
            "input_content": _IN,
            "output_content": _OUT,
            "context.expected_route": "SAFE",
            "context.expected_category": "",  # falsy → guard drops it
            "context.expected_card_id": "",  # falsy → guard drops it
            "context.observation": "{}",
            "context.expected_source": "{}",
        }
        ctx = _update_path_extract(raw_row)
        assert "expected_card_id" not in ctx, (
            f"Bug confirmed: empty expected_card_id dropped by UPDATE-path guard; ctx={ctx}"
        )

    def test_update_path_drops_empty_expected_category_raw(self):
        """_extract_row_data drops expected_category when CSV cell is ''."""
        raw_row = {
            "input_content": _IN,
            "output_content": _OUT,
            "context.expected_route": "EMERGENCY",
            "context.expected_category": "",  # falsy
            "context.expected_card_id": "some-card",
            "context.observation": "{}",
            "context.expected_source": "{}",
        }
        ctx = _update_path_extract(raw_row)
        assert "expected_category" not in ctx

    def test_update_path_includes_nonempty_route(self):
        """Non-empty expected_route survives the UPDATE-path guard (not affected by F1)."""
        raw_row = {
            "input_content": _IN,
            "output_content": _OUT,
            "context.expected_route": "SAFE",
            "context.observation": "{}",
            "context.expected_source": "{}",
        }
        ctx = _update_path_extract(raw_row)
        assert "expected_route" in ctx
        assert ctx["expected_route"] == "SAFE"


# ---------------------------------------------------------------------------
# F1-FIX: JSON-encoded cells survive UPDATE-path guard
# ---------------------------------------------------------------------------


class TestF1JsonEncodedCellsSurviveUpdatePath:
    """After the fix: JSON-encoded scalar cells survive the UPDATE-path guard as STRINGs."""

    def test_empty_expected_card_id_survives_update_path(self):
        row = _row(expected_card_id="")
        ctx = _update_path_extract(_csv_dict(row))
        assert "expected_card_id" in ctx, f"expected_card_id must be present in UPDATE-path context; got {ctx}"
        assert isinstance(ctx["expected_card_id"], str)

    def test_empty_expected_category_survives_update_path(self):
        row = _row(expected_route="EMERGENCY", expected_category="")
        ctx = _update_path_extract(_csv_dict(row))
        assert "expected_category" in ctx
        assert isinstance(ctx["expected_category"], str)

    def test_expected_route_survives_update_path(self):
        row = _row(expected_route="SAFE")
        ctx = _update_path_extract(_csv_dict(row))
        assert "expected_route" in ctx
        assert isinstance(ctx["expected_route"], str)

    def test_all_three_scalars_present_in_update_path(self):
        row = _row(expected_route="EMERGENCY", expected_category="bleeding", expected_card_id="")
        ctx = _update_path_extract(_csv_dict(row))
        for key in ("expected_route", "expected_category", "expected_card_id"):
            assert key in ctx, f"UPDATE path must include {key!r}; got keys: {set(ctx)}"
            assert isinstance(ctx[key], str)

    def test_slug_false_survives_as_string_not_bool(self):
        ctx = _update_path_extract(_csv_dict(_row(expected_card_id="false")))
        assert "expected_card_id" in ctx
        assert isinstance(ctx["expected_card_id"], str)
        assert ctx["expected_card_id"] is not False

    def test_slug_null_survives_as_string_not_none(self):
        ctx = _update_path_extract(_csv_dict(_row(expected_card_id="null")))
        assert "expected_card_id" in ctx
        assert isinstance(ctx["expected_card_id"], str)
        assert ctx["expected_card_id"] is not None

    def test_slug_123_survives_as_string_not_int(self):
        ctx = _update_path_extract(_csv_dict(_row(expected_card_id="123")))
        assert "expected_card_id" in ctx
        assert isinstance(ctx["expected_card_id"], str)
        assert ctx["expected_card_id"] != 123


# ---------------------------------------------------------------------------
# F1-FIX: normalize_csv_scalar_labels — decode JSON-encoded labels
# ---------------------------------------------------------------------------


class TestNormalizeCsvScalarLabels:
    """normalize_csv_scalar_labels() decodes JSON-encoded string literals."""

    def test_quoted_safe_decoded(self):
        assert normalize_csv_scalar_labels({"expected_route": '"SAFE"'})["expected_route"] == "SAFE"

    def test_quoted_emergency_decoded(self):
        assert normalize_csv_scalar_labels({"expected_route": '"EMERGENCY"'})["expected_route"] == "EMERGENCY"

    def test_quoted_empty_decoded_to_empty_string(self):
        result = normalize_csv_scalar_labels({"expected_card_id": '""'})
        assert result["expected_card_id"] == ""

    def test_quoted_named_card_decoded(self):
        assert normalize_csv_scalar_labels({"expected_card_id": '"nutrition-01"'})["expected_card_id"] == "nutrition-01"

    def test_quoted_false_slug_decoded_as_string_not_bool(self):
        result = normalize_csv_scalar_labels({"expected_card_id": '"false"'})
        assert result["expected_card_id"] == "false"
        assert isinstance(result["expected_card_id"], str)
        assert result["expected_card_id"] is not False

    def test_quoted_null_slug_decoded_as_string_not_none(self):
        result = normalize_csv_scalar_labels({"expected_card_id": '"null"'})
        assert result["expected_card_id"] == "null"
        assert result["expected_card_id"] is not None

    def test_quoted_numeric_slug_decoded_as_string_not_int(self):
        result = normalize_csv_scalar_labels({"expected_card_id": '"123"'})
        assert result["expected_card_id"] == "123"
        assert result["expected_card_id"] != 123

    def test_absent_field_stays_absent_not_defaulted(self):
        """Missing field is not defaulted; missing-label vs empty-label distinction preserved."""
        result = normalize_csv_scalar_labels({"expected_route": '"SAFE"'})
        assert "expected_card_id" not in result
        assert "expected_category" not in result

    def test_plain_string_passthrough_preencoding_compat(self):
        """Pre-encoding plain strings (not starting with '"') pass through unchanged."""
        result = normalize_csv_scalar_labels({"expected_route": "SAFE"})
        assert result["expected_route"] == "SAFE"

    def test_empty_plain_string_passthrough(self):
        """Empty string (pre-encoding, no-card-negative) passes through unchanged."""
        result = normalize_csv_scalar_labels({"expected_card_id": ""})
        assert result["expected_card_id"] == ""

    def test_other_keys_not_touched(self):
        """Non-label keys are copied as-is; observation and expected_source unchanged."""
        ctx = {
            "expected_route": '"SAFE"',
            "observation": {"key": "value"},
            "expected_source": {"chatbot_public_id": "abc"},
        }
        result = normalize_csv_scalar_labels(ctx)
        assert result["observation"] is ctx["observation"]
        assert result["expected_source"] is ctx["expected_source"]

    def test_original_context_not_mutated(self):
        """normalize_csv_scalar_labels must not mutate the input dict."""
        original = {"expected_route": '"SAFE"', "expected_card_id": '""'}
        copy_before = dict(original)
        normalize_csv_scalar_labels(original)
        assert original == copy_before, "Input context was mutated"

    def test_malformed_quoted_value_raises_valueerror(self):
        with pytest.raises(ValueError, match="[Mm]alformed"):
            normalize_csv_scalar_labels({"expected_route": '"broken'})

    def test_non_dict_raises_typeerror(self):
        with pytest.raises(TypeError, match="dict"):
            normalize_csv_scalar_labels("not a dict")  # type: ignore[arg-type]

    def test_all_three_decoded_simultaneously(self):
        ctx = {
            "expected_route": '"EMERGENCY"',
            "expected_category": '"bleeding"',
            "expected_card_id": '""',
        }
        result = normalize_csv_scalar_labels(ctx)
        assert result["expected_route"] == "EMERGENCY"
        assert result["expected_category"] == "bleeding"
        assert result["expected_card_id"] == ""


# ---------------------------------------------------------------------------
# F1-FIX: CREATE-path preservation — no regression
# ---------------------------------------------------------------------------


class TestF1CreatePathPreservation:
    """CREATE-path always retains context fields; normalize decodes them correctly."""

    def test_create_path_always_includes_empty_card_id(self):
        ctx = _create_path_extract(_csv_dict(_row(expected_card_id="")))
        assert "expected_card_id" in ctx

    def test_create_path_route_is_string_before_normalize(self):
        ctx = _create_path_extract(_csv_dict(_row(expected_route="SAFE")))
        assert isinstance(ctx["expected_route"], str)

    def test_create_path_then_normalize_all_three_fields(self):
        row = _row(expected_route="EMERGENCY", expected_category="bleeding", expected_card_id="")
        ctx = _create_path_extract(_csv_dict(row))
        norm = normalize_csv_scalar_labels(ctx)
        assert norm["expected_route"] == "EMERGENCY"
        assert norm["expected_category"] == "bleeding"
        assert norm["expected_card_id"] == ""


# ---------------------------------------------------------------------------
# F1-FIX: Full roundtrip consumer tests
#   exporter → CSV → extract (UPDATE or CREATE) → normalize → evaluator
#
# RED before normalize_csv_scalar_labels:
#   - expected_route='"SAFE"' → route_check: expected_route_unknown
#   - expected_card_id='""'   → card_accuracy: expected_no_card=False (wrong)
#
# GREEN after normalize_csv_scalar_labels:
#   - expected_route='SAFE'   → route_check passes
#   - expected_card_id=''     → card_accuracy: expected_no_card=True (correct)
# ---------------------------------------------------------------------------


class TestF1FullRoundtripConsumer:
    """Full roundtrip: exporter → CSV → extract → normalize → evaluator."""

    def _roundtrip_ctx(self, row: CompletedObservationRow, extract_fn) -> dict:
        """Export → CSV → extract → normalize → ready for evaluator."""
        csv_d = _csv_dict(row)
        raw_ctx = extract_fn(csv_d)
        norm_ctx = normalize_csv_scalar_labels(raw_ctx)
        norm_ctx["observation"] = json.loads(csv_d["context.observation"])
        norm_ctx["expected_source"] = json.loads(csv_d["context.expected_source"])
        return norm_ctx

    @pytest.mark.parametrize("extract_fn", [_update_path_extract, _create_path_extract])
    def test_route_safe_consumer_pass(self, extract_fn):
        """SAFE route: normalized context passes route_check."""
        row = _row(expected_route="SAFE", output_tags=[])
        ctx = self._roundtrip_ctx(row, extract_fn)
        assert ctx["expected_route"] == "SAFE"
        result = _run(ROUTE_CHECK_CODE, ctx)
        assert result.get("error") is None, f"Unexpected error: {result}"
        assert result["route_match"] is True
        assert result["actual_route"] == "SAFE"

    @pytest.mark.parametrize("extract_fn", [_update_path_extract, _create_path_extract])
    def test_route_emergency_consumer_pass(self, extract_fn):
        """EMERGENCY with danger_sign tag: normalized context passes route_check."""
        row = _row(
            expected_route="EMERGENCY",
            expected_category="bleeding",
            output_tags=["danger_sign:bleeding"],
        )
        ctx = self._roundtrip_ctx(row, extract_fn)
        assert ctx["expected_route"] == "EMERGENCY"
        result = _run(ROUTE_CHECK_CODE, ctx)
        assert result.get("error") is None, f"Unexpected error: {result}"
        assert result["route_match"] is True
        assert result["category_match"] is True

    @pytest.mark.parametrize("extract_fn", [_update_path_extract, _create_path_extract])
    def test_no_card_negative_ask_ai(self, extract_fn):
        """No-card-negative: expected_card_id='' after normalize → expected_no_card=True."""
        row = _row(expected_card_id="", output_tags=["answer_route:ASK_AI"])
        ctx = self._roundtrip_ctx(row, extract_fn)
        assert ctx["expected_card_id"] == ""  # exact empty string preserved
        result = _run(CARD_ACCURACY_CODE, ctx)
        assert result.get("error") is None, f"Unexpected error: {result}"
        assert result["expected_no_card"] is True
        assert result["no_card_correct"] is True
        assert result["spurious_card"] is False

    @pytest.mark.parametrize("extract_fn", [_update_path_extract, _create_path_extract])
    def test_named_card_match(self, extract_fn):
        """Named card match: expected_card_id='nutrition-01' → card_match=True."""
        row = _row(
            expected_card_id="nutrition-01",
            output_tags=["answer_route:CARD", "answer_card:nutrition-01"],
        )
        ctx = self._roundtrip_ctx(row, extract_fn)
        assert ctx["expected_card_id"] == "nutrition-01"
        result = _run(CARD_ACCURACY_CODE, ctx)
        assert result.get("error") is None, f"Unexpected error: {result}"
        assert result["card_match"] is True

    @pytest.mark.parametrize("extract_fn", [_update_path_extract, _create_path_extract])
    def test_slug_false_as_card_id(self, extract_fn):
        """Card slug 'false' survives roundtrip as string; card_match against 'false'."""
        row = _row(
            expected_card_id="false",
            output_tags=["answer_route:CARD", "answer_card:false"],
        )
        ctx = self._roundtrip_ctx(row, extract_fn)
        assert ctx["expected_card_id"] == "false"
        result = _run(CARD_ACCURACY_CODE, ctx)
        assert result.get("error") is None
        assert result["card_match"] is True

    @pytest.mark.parametrize("extract_fn", [_update_path_extract, _create_path_extract])
    def test_no_llm_emergency_null_turns(self, extract_fn):
        """EMERGENCY + NULL n_turns roundtrip with no_llm_check evaluator."""
        env = ObservationEnvelope(
            trace_id="aabbccdd-0000-0000-0000-000000000001",
            session_id="aabbccdd-0000-0000-0000-000000000002",
            chatbot_id="aabbccdd-0000-0000-0000-000000000003",
            input_message_id=100,
            output_message_id=101,
            input_text=_IN,
            output_text=_OUT,
            n_turns=None,  # zero LLM calls
            output_tags=["danger_sign:bleeding"],
            execution_fingerprint={"pipeline_sha256": _SHA, "experiment_version_number": 1},
            metric_profile=dict(VERIFIED_METRIC_PROFILE),
        )
        row = CompletedObservationRow(
            observation=env,
            expected_route="EMERGENCY",
            expected_source_config=_SOURCE_CONFIG,
        )
        ctx = self._roundtrip_ctx(row, extract_fn)
        assert ctx["expected_route"] == "EMERGENCY"
        result = _run(NO_LLM_CHECK_CODE, ctx)
        assert result.get("error") is None, f"Unexpected error: {result}"
        assert result["no_llm_on_emergency"] is True

    def test_normalize_not_applied_still_passes_route(self):
        """Generated evaluator handles transport without host-side preprocessing."""
        row = _row(expected_route="SAFE", output_tags=[])
        csv_d = _csv_dict(row)
        raw_ctx = _update_path_extract(csv_d)
        raw_ctx["observation"] = json.loads(csv_d["context.observation"])
        raw_ctx["expected_source"] = json.loads(csv_d["context.expected_source"])
        result = _run(ROUTE_CHECK_CODE, raw_ctx)
        assert result.get("route_match") is True, result

    def test_normalize_not_applied_still_recognizes_no_card(self):
        """No-card transport is decoded inside the generated evaluator."""
        row = _row(expected_card_id="", output_tags=["answer_route:ASK_AI"])
        csv_d = _csv_dict(row)
        raw_ctx = _update_path_extract(csv_d)
        raw_ctx["observation"] = json.loads(csv_d["context.observation"])
        raw_ctx["expected_source"] = json.loads(csv_d["context.expected_source"])
        result = _run(CARD_ACCURACY_CODE, raw_ctx)
        assert result.get("no_card_correct") is True, result


# ---------------------------------------------------------------------------
# F1-FIX: Malformed transport values fail closed
# ---------------------------------------------------------------------------


class TestGeneratedEvaluatorTransportBoundary:
    @pytest.mark.parametrize("extract_fn", [_update_path_extract, _create_path_extract])
    def test_raw_imported_route_needs_no_external_normalizer(self, extract_fn):
        ctx = extract_fn(_csv_dict(_row()))
        before = dict(ctx)
        result = _run(ROUTE_CHECK_CODE, ctx)
        assert result.get("route_match") is True, result
        assert ctx == before

    @pytest.mark.parametrize("extract_fn", [_update_path_extract, _create_path_extract])
    def test_raw_imported_empty_card_is_no_card(self, extract_fn):
        ctx = extract_fn(_csv_dict(_row(output_tags=["answer_route:ASK_AI"])))
        result = _run(CARD_ACCURACY_CODE, ctx)
        assert result.get("no_card_correct") is True, result

    def test_malformed_transport_refused_inside_generated_evaluator(self):
        ctx = _update_path_extract(_csv_dict(_row()))
        ctx["expected_route"] = '"broken'
        result = _run(ROUTE_CHECK_CODE, ctx)
        assert result.get("error") == "csv_scalar_invalid", result


class TestF1MalformedTransportValues:
    """Malformed quoted labels raise ValueError at normalize (fail closed)."""

    def test_unclosed_quote_raises(self):
        with pytest.raises(ValueError):
            normalize_csv_scalar_labels({"expected_route": '"broken'})

    def test_bare_true_string_passthrough_as_string(self):
        """'true' (not quoted) passes through as plain string; no bool coercion."""
        result = normalize_csv_scalar_labels({"expected_card_id": "true"})
        assert result["expected_card_id"] == "true"
        assert isinstance(result["expected_card_id"], str)

    def test_non_string_value_raises(self):
        with pytest.raises((ValueError, TypeError)):
            normalize_csv_scalar_labels({"expected_route": 123})  # type: ignore[arg-type]

    def test_all_three_scalars_exact_logical_equality(self):
        """Roundtrip preserves exact original values including empty string."""
        originals = {
            "expected_route": "EMERGENCY",
            "expected_category": "",
            "expected_card_id": "nutrition-01",
        }
        encoded = {k: json.dumps(v) for k, v in originals.items()}
        result = normalize_csv_scalar_labels(encoded)
        assert result["expected_route"] == originals["expected_route"]
        assert result["expected_category"] == originals["expected_category"]
        assert result["expected_card_id"] == originals["expected_card_id"]


# ---------------------------------------------------------------------------
# Pinned parse_csv_value_as_json string-type contract (OCS 9f5c254)
# ---------------------------------------------------------------------------


class TestPinnedParseCsvStringTypeContract:
    """Pinned parse_csv_value_as_json (OCS 9f5c254) on F1-relevant inputs."""

    def test_json_encoded_empty_string_is_truthy(self):
        """'""' must be truthy (survives UPDATE-path 'and value' guard)."""
        v = _parse_csv('""')
        assert bool(v) is True
        assert isinstance(v, str)

    def test_raw_empty_string_is_falsy(self):
        """Raw '' triggers UPDATE-path guard — this is the bug JSON-encoding fixes."""
        v = _parse_csv("")
        assert not v

    def test_json_encoded_safe_returned_as_is_requires_normalize(self):
        """'"SAFE"' returned as-is — why normalize_csv_scalar_labels is needed."""
        v = _parse_csv('"SAFE"')
        assert v == '"SAFE"'  # NOT decoded — normalize decodes it
        assert isinstance(v, str)

    def test_json_encoded_emergency_returned_as_is(self):
        assert _parse_csv('"EMERGENCY"') == '"EMERGENCY"'

    def test_json_encoded_false_slug_string_not_bool(self):
        v = _parse_csv('"false"')
        assert isinstance(v, str)
        assert v is not False

    def test_json_encoded_null_slug_string_not_none(self):
        v = _parse_csv('"null"')
        assert isinstance(v, str)
        assert v is not None

    def test_json_encoded_numeric_slug_string_not_int(self):
        v = _parse_csv('"123"')
        assert isinstance(v, str)
        assert v != 123

    def test_object_decoded(self):
        v = _parse_csv('{"key": "val"}')
        assert isinstance(v, dict)

    def test_array_decoded(self):
        v = _parse_csv('["a"]')
        assert isinstance(v, list)
