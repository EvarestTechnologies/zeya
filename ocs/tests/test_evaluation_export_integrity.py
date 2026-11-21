"""Independent export-boundary regressions for trusted completed observations."""

import io

import pytest

from ocs.evaluations.card_accuracy import CARD_ACCURACY_CODE
from ocs.evaluations.completed_adapter import (
    CompletedObservationRow,
    RelationshipError,
    write_completed_observations_csv,
)
from ocs.evaluations.evaluator_harness import EvaluatorHarness
from ocs.evaluations.no_llm_check import NO_LLM_CHECK_CODE
from ocs.tests.test_evaluations import TestOrmAdapter as AdapterFixtures


@pytest.fixture
def row():
    result = AdapterFixtures()._make()
    result.expected_source_config = dict(result.expected_source_config)
    return result


@pytest.mark.parametrize("change", ["metric", "source_sha", "source_bot", "mode", "schema", "input_type"])
@pytest.mark.parametrize("export", ["direct", "writer"])
def test_mutated_observation_cannot_bypass_export_validation(row, change, export):
    if change == "metric":
        row.observation.n_turns = True
    elif change == "source_sha":
        row.expected_source_config["pipeline_sha256"] = "bb" * 32
    elif change == "source_bot":
        row.expected_source_config["chatbot_public_id"] = "aabbccdd-0000-0000-0000-000000000099"
    elif change == "mode":
        row.observation.mode = "fresh_generation"
    elif change == "schema":
        row.observation.schema_version = "unknown"
    else:
        row.observation.input_text = True
    with pytest.raises(RelationshipError):
        if export == "direct":
            row.to_csv_row()
        else:
            dest = io.StringIO()
            try:
                write_completed_observations_csv([row], dest)
            finally:
                assert dest.getvalue() == "", "Validation must precede even the CSV header"


def test_direct_construction_rejects_different_expected_source(row):
    cfg = dict(row.expected_source_config, pipeline_sha256="bb" * 32)
    with pytest.raises(RelationshipError):
        CompletedObservationRow(
            observation=row.observation,
            expected_route=row.expected_route,
            expected_source_config=cfg,
        )


@pytest.mark.parametrize("error", [False, None, 0, []])
def test_trace_error_requires_an_actual_string(error):
    fixtures = AdapterFixtures()
    with pytest.raises(RelationshipError):
        fixtures._make(trace=fixtures._trace(error=error))


def test_negative_recorded_version_is_not_a_valid_positive_integer_field():
    fixtures = AdapterFixtures()
    with pytest.raises(RelationshipError):
        fixtures._make(trace=fixtures._trace(experiment_version_number=-1))


def test_valid_row_exports_without_changing_raw_null_or_source(row):
    exported = row.to_csv_row()
    assert exported["input_content"] == row.observation.input_text
    assert row.observation.n_turns is None
    assert exported["context.expected_source"]


@pytest.mark.parametrize("change", ["negative_version", "invalid_error_type", "invalid_content_type"])
def test_shared_evaluator_rejects_malformed_record_types(row, change):
    obs = row.observation.to_dict()
    obs["output_tags"] = ["danger_sign:bleeding"]
    if change == "negative_version":
        obs["execution_fingerprint"]["experiment_version_number"] = -1
    elif change == "invalid_error_type":
        obs["trace_error"] = False
    else:
        obs["input_text"] = True
    result = EvaluatorHarness(NO_LLM_CHECK_CODE).run(
        input={"content": obs["input_text"]},
        output={"content": obs["output_text"]},
        context={
            "observation": obs,
            "expected_source": row.expected_source_config,
            "expected_route": "EMERGENCY",
        },
        generated_response="",
    )
    assert result.get("error"), "Malformed evidence cannot produce a positive no-call result"


@pytest.mark.parametrize(
    "tags",
    [
        ["answer_route:UNKNOWN"],
        ["answer_route:ASK_AI", "answer_card:anc_purpose_en"],
        ["answer_route:CARD"],
        ["answer_route:CARD", "answer_card:first", "answer_card:second"],
    ],
)
def test_invalid_card_evidence_is_not_a_correct_match_or_nonmatch(row, tags):
    obs = row.observation.to_dict()
    obs["output_tags"] = tags
    result = EvaluatorHarness(CARD_ACCURACY_CODE).run(
        input={"content": obs["input_text"]},
        output={"content": obs["output_text"]},
        context={"observation": obs, "expected_source": row.expected_source_config, "expected_card_id": ""},
        generated_response="",
    )
    assert result.get("error")


def test_actual_guard_blocked_tag_is_reported_separately(row):
    obs = row.observation.to_dict()
    obs["output_tags"] = ["answer_route:CARD", "answer_card:anc_purpose_en", "route:guard_blocked"]
    result = EvaluatorHarness(CARD_ACCURACY_CODE).run(
        input={"content": obs["input_text"]},
        output={"content": obs["output_text"]},
        context={
            "observation": obs,
            "expected_source": row.expected_source_config,
            "expected_card_id": "anc_purpose_en",
        },
        generated_response="",
    )
    assert result.get("card_match") is True
    assert result.get("guard_blocked") is True
