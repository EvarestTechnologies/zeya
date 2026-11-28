"""
Completed-observation / CSV / PythonEvaluator acceptance (corrected, E01–E14).

CORRECTIONS FROM PARENT AUDIT (evaluation-engine-completion.md):
  E01/E02: actual OCSTracer.trace() context manager (not TraceFactory) persists
           n_turns to DB; Trace.objects.get(trace_id=...) reads back actual values.
  E02:     OCSCallbackHandler propagated as LangChain callback; MetricsCollector
           counts on_llm_start events from actual FakeLlm invocation.
  E03:     pipeline.flow_data hashed ONCE before execution; same hash in both
           observation.execution_fingerprint and expected_source_config.
           Seam pipeline uses seam pipeline hash; Zeya pipeline uses Zeya hash.
           Never rebuild a different graph to hash — _compute_pipeline_sha256(p)
           hashes the EXACT pipeline that was just saved and will execute.
  E04:     actual create_dataset_from_csv_task with real File + EvaluationDataset;
           not a manually-copied CSV parsing loop.
  E05:     actual evaluate_message() with EvaluationRun(generation_experiment=None);
           verifies EvaluationResult.output["generated_response"]=="".
  E06:     same-chat, different-turn message rejected (FK identity, not foreign-chat).
           Trace.output_message_id=ai_msg_turn1.id; supply output snapshot with
           ai_msg_turn2.id (same session.chat, different turn).
  E07/E08: missing profile and unknown profile via actual PythonEvaluator.
  E11:     actual inspect.getfile() source hash readback vs VERIFIED_METRIC_PROFILE.
  Harness: importlib.util.spec_from_file_location imports hardened lifecycle functions.

LABEL TRANSPORT NOTE:
  OCS decodes only JSON objects/arrays. Quoted scalar transport therefore needs
  explicit decoding at the shared evaluator boundary, not a platform parser edit.
  E04/E05 exercise actual CSV creation and evaluation tasks after that correction.

SCOPE: component execution seam test against the real OCS engine.
  EMERGENCY path: full Zeya pipeline, danger message, zero LLM calls.
  LLM-one-start:  start→llm_input→llm→end seam, registered safe question.
NOT complete full-graph proof: staged card/AI/guard paths are a separate G2 gate.
"""

from __future__ import annotations

import hashlib
import inspect
import io
import json
from pathlib import Path
from unittest import mock
from uuid import uuid4

import pytest
from apps.chat.models import ChatMessageType
from apps.evaluations.evaluators import PythonEvaluator
from apps.evaluations.models import EvaluationDataset, EvaluationMessage, EvaluationMessageContent, Evaluator
from apps.evaluations.tasks import create_dataset_from_csv_task, evaluate_message
from apps.files.models import File, FilePurpose
from apps.pipelines.flow import FullFlow, split_flow_data
from apps.pipelines.graph import PipelineGraph
from apps.pipelines.nodes.base import PipelineState
from apps.pipelines.repository import ORMRepository
from apps.service_providers.tracing.base import TraceContext
from apps.service_providers.tracing.ocs_tracer import OCSCallbackHandler, OCSTracer
from apps.trace.models import Trace, TraceStatus
from apps.utils.factories.evaluations import EvaluationRunFactory
from apps.utils.factories.experiment import (
    ChatMessageFactory,
    ExperimentSessionFactory,
)
from apps.utils.factories.pipelines import PipelineFactory
from apps.utils.factories.service_provider_factories import (
    LlmProviderFactory,
    LlmProviderModelFactory,
)
from apps.utils.tests.langchain import build_fake_llm_service
from django.core.files.uploadedfile import SimpleUploadedFile

from ocs.build_pipeline import SYSTEM_PROMPT_FILE, build_pipeline
from ocs.evaluations.card_accuracy import CARD_ACCURACY_CODE
from ocs.evaluations.completed_adapter import (
    COMPLETED_OBS_COLUMN_MAPPING,
    CompletedObservationRow,
    RelationshipError,
    write_completed_observations_csv,
)
from ocs.evaluations.no_llm_check import NO_LLM_CHECK_CODE
from ocs.evaluations.observation import VERIFIED_METRIC_PROFILE
from ocs.evaluations.route_check import ROUTE_CHECK_CODE
from ocs.tests.danger_corpus import BILINGUAL_EXAMPLES

# ---------------------------------------------------------------------------
# Synthetic constants
# ---------------------------------------------------------------------------

LLM_REPLY = "Eat a balanced diet."

REGISTERED = {
    "welcome_sent": True,
    "enrolled_at": "2026-01-01T00:00:00+00:00",
    "consent_given": True,
    "name": "Akinyi",
    "name_collected": True,
    "gestational_age_at_enrollment": 20,
    "registration_complete": True,
    "language_preference": "en",
    "study_group": "intervention",
}

_DANGER_CATEGORY = "bleeding"
_DANGER_MSG = next(
    msg
    for cat, langs in BILINGUAL_EXAMPLES.items()
    for lang, examples in langs.items()
    for msg in ([examples] if isinstance(examples, str) else examples)
    if cat == _DANGER_CATEGORY and lang == "en"
)
_SAFE_MSG = "What food is safe during pregnancy?"

# ---------------------------------------------------------------------------
# Source hash readback helper (E11)
# ---------------------------------------------------------------------------


def _source_hash(module) -> str:
    """SHA256 of the actual on-disk source file for an imported module."""
    path = Path(inspect.getfile(module))
    return hashlib.sha256(path.read_bytes()).hexdigest()


# ---------------------------------------------------------------------------
# Frozen artifact hash (E03)
# MUST be called after pipeline is fully saved and before any execution.
# ---------------------------------------------------------------------------


def _freeze_pipeline_sha256(pipeline) -> str:
    """
    Hash the pipeline's exact executed artifact (flow_data), frozen before execution.
    Returns 64-hex SHA256.

    pipeline.flow_data reconstructs the full pipeline JSON from the saved layout
    and Node rows.  Call once per pipeline and store the result; never rebuild
    from a different pipeline's data.
    """
    artifact = pipeline.flow_data  # dict with full node data
    return hashlib.sha256(json.dumps(artifact, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


# ---------------------------------------------------------------------------
# Seam pipeline builder (LLM-one-start path only)
# ---------------------------------------------------------------------------


def _build_seam_pipeline_data(provider_id: int, model_id: int) -> dict:
    """
    start → llm_input → llm → end.
    BOUNDED: LLM-config seam only.  Not the full Zeya graph.
    """
    from ocs.build_pipeline import _code, _node  # private helpers, explicit import

    return {
        "name": "zeya-eval-seam (test-only; not full Zeya graph)",
        "data": {
            "nodes": [
                _node("start", "StartNode", {"name": "start"}, 0, 0, flow_type="startNode"),
                _node(
                    "llm_input",
                    "CodeNode",
                    {"name": "llm_input", "code": _code("llm_input")},
                    300,
                    0,
                ),
                _node(
                    "llm",
                    "LLMResponseWithPrompt",
                    {
                        "name": "llm",
                        "llm_provider_id": provider_id,
                        "llm_provider_model_id": model_id,
                        "llm_model_parameters": {"temperature": 0.3},
                        "prompt": SYSTEM_PROMPT_FILE.read_text(),
                        "history_type": "none",
                    },
                    600,
                    0,
                ),
                _node("end", "EndNode", {"name": "end"}, 900, 0, flow_type="endNode"),
            ],
            "edges": [
                {
                    "id": "s:o->li",
                    "source": "start",
                    "target": "llm_input",
                    "sourceHandle": "output",
                    "targetHandle": "input",
                },
                {
                    "id": "li:o->l",
                    "source": "llm_input",
                    "target": "llm",
                    "sourceHandle": "output",
                    "targetHandle": "input",
                },
                {"id": "l:o->e", "source": "llm", "target": "end", "sourceHandle": "output", "targetHandle": "input"},
            ],
        },
    }


# ---------------------------------------------------------------------------
# Pipeline factory helpers
# ---------------------------------------------------------------------------


def _make_zeya_pipeline(db, provider_id, model_id):
    p = PipelineFactory.create()
    flow = FullFlow(**build_pipeline(provider_id, model_id)["data"])
    layout, node_data = split_flow_data(flow)
    p.data = layout.model_dump()
    p.save()
    p.update_nodes_from_data(node_data)
    return p


def _make_seam_pipeline(db, provider_id, model_id):
    p = PipelineFactory.create()
    flow = FullFlow(**_build_seam_pipeline_data(provider_id, model_id)["data"])
    layout, node_data = split_flow_data(flow)
    p.data = layout.model_dump()
    p.save()
    p.update_nodes_from_data(node_data)
    return p


# ---------------------------------------------------------------------------
# Actual OCSTracer execution (E01, E02)
# ---------------------------------------------------------------------------


def _run_with_ocsTracer(pipeline, session, message, participant_data):
    """
    Run pipeline INSIDE actual OCSTracer.trace() context.

    - Creates and persists a real Trace record (Trace.objects.create) via OCSTracer
    - FakeLlm triggers OCSCallbackHandler → MetricsCollector.on_llm_start
    - After context exit: Trace.n_turns persisted from actual MetricsCollector.get_metrics()
    - Returns (trace_context_uuid, actual_pipeline_output)
    """
    pipeline.team = session.team
    pipeline.save(update_fields=["team"])
    session.experiment.pipeline = pipeline
    session.experiment.save(update_fields=["pipeline"])
    tracer = OCSTracer(session.experiment, session.team.id)
    trace_ctx = TraceContext(id=uuid4(), name="zeya-eval-seam-test")
    runnable = PipelineGraph.build_from_pipeline(pipeline).build_runnable()
    config = {
        "configurable": {"repo": ORMRepository(session=session)},
        "callbacks": [OCSCallbackHandler(tracer=tracer)],
    }
    # The access gate (#21) lets only approved testers through; these engine tests exercise
    # the pipeline after it, so the synthetic participant is an approved tester by default.
    participant_data = {"approved_tester": True, **participant_data}
    state = PipelineState(
        messages=[message],
        experiment_session=session,
        participant_data=participant_data,
    )
    actual_output = {}
    with tracer.trace(trace_context=trace_ctx, session=session):
        raw = runnable.invoke(state, config=config)
        actual_output = raw
    return trace_ctx.id, actual_output


def _output_tags_from_state(raw_output: dict) -> list[str]:
    """
    Collect actual output_message_tags from pipeline state output.
    Tags come from add_message_tag() CodeNode calls during actual execution.
    NEVER authored or defaulted.
    """
    return [name for name, _category in raw_output["output_message_tags"]]


# ---------------------------------------------------------------------------
# Snapshot helpers for from_trace_dict
# ---------------------------------------------------------------------------


def _snap_trace(trace, human_msg, ai_msg, pipeline_sha, captured_tags):
    """
    Build trace snapshot dict from actual DB-persisted Trace fields (via refresh_from_db).
    metric_profile is VERIFIED_METRIC_PROFILE — explicitly supplied, never defaulted.
    captured_output_tags comes from actual pipeline execution (never authored).
    pipeline_sha comes from _freeze_pipeline_sha256() called BEFORE execution.
    """
    return {
        "trace_id": str(trace.trace_id),
        "input_message_id": trace.input_message_id,
        "output_message_id": trace.output_message_id,
        "session_id": trace.session_id,
        "experiment_id": trace.experiment_id,
        "team_id": trace.team_id,
        "status": trace.status,
        "error": trace.error,
        "n_turns": trace.n_turns,  # actual value from DB
        "metric_profile": dict(VERIFIED_METRIC_PROFILE),  # explicitly supplied
        "captured_output_tags": list(captured_tags),  # actual execution
        "pipeline_sha256": pipeline_sha,  # frozen before execution
        "experiment_version_number": trace.experiment_version_number,
    }


def _snap_session(session):
    return {
        "id": session.id,
        "external_id": str(session.external_id),
        "experiment_id": session.experiment.id,
        "chat_id": session.chat.id,
        "team_id": session.team.id,
    }


def _snap_experiment(experiment):
    return {
        "id": experiment.id,
        "public_id": str(experiment.public_id),
        "team_id": experiment.team.id,
    }


def _snap_msg(msg, expected_type: str):
    return {
        "id": msg.id,
        "chat_id": msg.chat.id,
        "message_type": msg.message_type,
        "content": msg.content,
    }


def _expected_source(session, pipeline_sha: str) -> dict:
    """Independently configured expected source identity; fixed before execution."""
    return {
        "chatbot_public_id": str(session.experiment.public_id),
        "pipeline_sha256": pipeline_sha,
    }


# ---------------------------------------------------------------------------
# CSV import helper (E04) — calls actual create_dataset_from_csv_task
# ---------------------------------------------------------------------------


def _write_csv_to_bytes(rows: list[CompletedObservationRow]) -> bytes:
    buf = io.StringIO()
    write_completed_observations_csv(rows, buf)
    return buf.getvalue().encode("utf-8")


def _run_csv_import(session, csv_bytes: bytes, expected_message_count: int):
    """
    Call actual create_dataset_from_csv_task with a real File and EvaluationDataset.

    NOTE: label transport sensitivity (pending Owner A callback).
    The current exporter writes expected_route/expected_card_id as raw strings.
    parse_csv_value_as_json returns them unchanged.  E04/E05 are the decisive
    acceptance tests once Owner A's label transport fix is in and DB hold lifts.
    """
    csv_upload = SimpleUploadedFile("eval_obs.csv", csv_bytes, content_type="text/csv")
    db_file = File.create(
        filename="eval_obs.csv",
        file_obj=csv_upload,
        team_id=session.team.id,
        purpose=FilePurpose.EVALUATION_DATASET,
    )
    dataset = EvaluationDataset.objects.create(team=session.team, name="completed-observation CSV")
    assert dataset.messages.count() == 0
    result = create_dataset_from_csv_task.apply(
        args=[],
        kwargs={
            "dataset_id": dataset.id,
            "file_id": db_file.id,
            "team_id": session.team.id,
            "column_mapping": COMPLETED_OBS_COLUMN_MAPPING,
        },
    )
    assert result.successful(), f"CSV import task failed: {result.result}"
    dataset.refresh_from_db()
    assert dataset.messages.count() == expected_message_count, (
        f"Expected {expected_message_count} messages after CSV import; got {dataset.messages.count()}"
    )
    return dataset


# ---------------------------------------------------------------------------
# Minimal valid observation dict factory (rejection-control tests E07–E13)
# ---------------------------------------------------------------------------


def _minimal_obs_dict(
    *,
    n_turns=None,
    metric_profile="USE_VERIFIED",  # str sentinel or dict; dict overrides VERIFIED_METRIC_PROFILE
    pipeline_sha=None,
    experiment_version_number=None,
    input_text="What food is safe?",
    output_text="Eat a balanced diet.",
):
    """Build a minimal observation dict for direct evaluator rejection-path tests."""
    sha = pipeline_sha or ("a" * 64)
    tid = str(uuid4())
    sid = str(uuid4())
    cid = str(uuid4())
    mp = dict(VERIFIED_METRIC_PROFILE) if metric_profile == "USE_VERIFIED" else metric_profile
    result = {
        "schema_version": "1",
        "mode": "completed_trace",
        "trace_id": tid,
        "session_id": sid,
        "chatbot_id": cid,
        "input_message_id": 1,
        "output_message_id": 2,
        "trace_status": "success",
        "trace_error": "",
        "n_turns": n_turns,
        "output_tags": [],
        "execution_fingerprint": {
            "pipeline_sha256": sha,
            "experiment_version_number": experiment_version_number,
        },
        "input_text": input_text,
        "output_text": output_text,
    }
    if mp is not None:
        result["metric_profile"] = mp
    return result


def _eval_msg_with_obs(obs_dict: dict, expected_source: dict | None = None, expected_route: str = "SAFE"):
    if expected_source is None:
        expected_source = {
            "chatbot_public_id": obs_dict.get("chatbot_id", str(uuid4())),
            "pipeline_sha256": obs_dict.get("execution_fingerprint", {}).get("pipeline_sha256", "a" * 64),
        }
    return EvaluationMessage.objects.create(
        input={"content": obs_dict["input_text"], "role": "human"},
        output={"content": obs_dict["output_text"], "role": "ai"},
        context={
            "observation": obs_dict,
            "expected_source": expected_source,
            "expected_route": expected_route,
        },
    )


def _run_evaluator(code: str, message: EvaluationMessage, generated_response: str = "") -> dict:
    """Invoke actual OCS PythonEvaluator on a real EvaluationMessage."""
    return PythonEvaluator(code=code).run(message, generated_response=generated_response).result


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def isolated_media(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path / "media"
    settings.STORAGES = {"default": {"BACKEND": "django.core.files.storage.FileSystemStorage"}}


@pytest.fixture()
def fake_llm():
    service = build_fake_llm_service(responses=[LLM_REPLY] * 10)
    service.llm.calls = []
    with mock.patch(
        "apps.service_providers.models.LlmProvider.get_llm_service",
        return_value=service,
    ) as patched:
        yield service.llm, patched


# ===========================================================================
# Tests
# ===========================================================================


# ---------------------------------------------------------------------------
# E11 — actual collector + tracer source-hash readback (no DB needed)
# ---------------------------------------------------------------------------


def test_e11_actual_collector_tracer_source_hash_matches_profile():
    """
    E11: actual SHA256 of MetricsCollector and OCSTracer source files at OCS pin
    9f5c254 matches VERIFIED_METRIC_PROFILE.

    Uses inspect.getfile() to locate the actual on-disk .py for the imported
    modules — no hard-coded absolute paths.
    """
    from apps.service_providers.tracing import metrics as metrics_mod
    from apps.service_providers.tracing import ocs_tracer as tracer_mod

    actual_collector_sha = _source_hash(metrics_mod)
    actual_tracer_sha = _source_hash(tracer_mod)

    assert actual_collector_sha == VERIFIED_METRIC_PROFILE["collector_sha256"], (
        f"E11: MetricsCollector source hash mismatch.\n"
        f"  actual:   {actual_collector_sha}\n"
        f"  expected: {VERIFIED_METRIC_PROFILE['collector_sha256']}\n"
        "  OCS pin mismatch — VERIFIED_METRIC_PROFILE must be updated if pin changes."
    )
    assert actual_tracer_sha == VERIFIED_METRIC_PROFILE["tracer_sha256"], (
        f"E11: OCSTracer source hash mismatch.\n"
        f"  actual:   {actual_tracer_sha}\n"
        f"  expected: {VERIFIED_METRIC_PROFILE['tracer_sha256']}"
    )
    assert VERIFIED_METRIC_PROFILE["ocs_pin"] == "9f5c25476555ff74a167c6a14832ce798832847a"


# ---------------------------------------------------------------------------
# E01, E12 — actual tracer-persisted zero-model NULL + actual tags (EMERGENCY)
# ---------------------------------------------------------------------------


def test_e01_e12_emergency_zero_model_tracer_persisted_null_actual_tags(db, fake_llm):
    """
    E01: actual OCSTracer.trace() persists n_turns=NULL for zero LLM calls.
         DB readback: Trace.objects.get(trace_id=trace_ctx.id).n_turns is None.
         Source: MetricsCollector.get_metrics() metrics.py:173 — turns or None.
    E12: output_tags captured from actual pipeline output_message_tags; never authored.

    Zeya pipeline. Danger message → danger_gate → emergency_response → no LLM.
    MetricsCollector._turns=0 → get_metrics() → 0 or None → NULL stored.
    """
    llm, _ = fake_llm
    provider = LlmProviderFactory.create()
    model = LlmProviderModelFactory.create()
    session = ExperimentSessionFactory.create()

    # E03: freeze exact artifact hash BEFORE execution
    pipeline = _make_zeya_pipeline(db, provider.id, model.id)
    pipeline_sha = _freeze_pipeline_sha256(pipeline)

    trace_ctx_id, raw_output = _run_with_ocsTracer(
        pipeline,
        session,
        _DANGER_MSG,
        REGISTERED | {"language_preference": "en"},
    )

    # E12: actual tags from execution — never authored
    actual_tags = _output_tags_from_state(raw_output)
    reply = raw_output["messages"][-1]
    assert reply.startswith("URGENT:")
    assert any(t.startswith("danger_sign:") for t in actual_tags), (
        f"E12: Expected danger_sign:* tag in actual execution; got {actual_tags}"
    )

    # E01: actual DB readback
    trace = Trace.objects.get(trace_id=trace_ctx_id)
    assert trace.status == TraceStatus.SUCCESS, f"Trace status: {trace.status!r}"
    assert trace.n_turns is None, (
        f"E01 FAIL: OCSTracer must persist n_turns=NULL for zero LLM calls; "
        f"got {trace.n_turns!r}. Source: metrics.py:173 turns or None → 0 or None → None"
    )
    assert isinstance(trace.error, str) and trace.error == "", (
        f"trace.error must be '' for success path; got {trace.error!r}"
    )

    # Create ChatMessages in session's chat; attach FKs to Trace
    human_msg = ChatMessageFactory.create(message_type=ChatMessageType.HUMAN, content=_DANGER_MSG, chat=session.chat)
    ai_msg = ChatMessageFactory.create(message_type=ChatMessageType.AI, content=reply, chat=session.chat)
    trace.input_message = human_msg
    trace.output_message = ai_msg
    trace.save(update_fields=["input_message", "output_message"])
    trace.refresh_from_db()

    # Build from_trace_dict with actual persisted values
    exp_src = _expected_source(session, pipeline_sha)
    row = CompletedObservationRow.from_trace_dict(
        trace=_snap_trace(trace, human_msg, ai_msg, pipeline_sha, actual_tags),
        session=_snap_session(session),
        experiment=_snap_experiment(session.experiment),
        input_message=_snap_msg(human_msg, "human"),
        output_message=_snap_msg(ai_msg, "ai"),
        expected_route="EMERGENCY",
        expected_source_config=exp_src,
        expected_category=_DANGER_CATEGORY,
        source="e01-e12-emergency",
    )

    # Prove n_turns=null preserved in observation JSON
    obs_dict = json.loads(row.observation.to_json())
    assert "n_turns" in obs_dict, "n_turns key must be present (None != absent)"
    assert obs_dict["n_turns"] is None, f"n_turns must be JSON null for zero-model path; got {obs_dict['n_turns']!r}"

    # Route/no-llm evaluators confirm evidence (direct EvaluationMessage, not CSV import)
    # NOTE: direct context construction avoids label-transport dependency on Owner A callback.
    eval_msg = EvaluationMessage.objects.create(
        input=EvaluationMessageContent(content=_DANGER_MSG, role="human").model_dump(),
        output=EvaluationMessageContent(content=reply, role="ai").model_dump(),
        context={
            "observation": obs_dict,
            "expected_source": exp_src,
            "expected_route": "EMERGENCY",
            "expected_category": _DANGER_CATEGORY,
            "expected_card_id": "",
        },
    )
    r_no_llm = _run_evaluator(NO_LLM_CHECK_CODE, eval_msg)
    assert r_no_llm.get("no_llm_on_emergency") is True, r_no_llm
    assert r_no_llm.get("n_turns_raw") is None, r_no_llm

    r_route = _run_evaluator(ROUTE_CHECK_CODE, eval_msg)
    assert r_route.get("route_match") is True, r_route
    assert r_route.get("actual_route") == "EMERGENCY", r_route


# ---------------------------------------------------------------------------
# E02, E03 — actual tracer-persisted one-start + frozen artifact hash (seam)
# ---------------------------------------------------------------------------


def test_e02_e03_llm_one_start_tracer_persisted_actual_hash(db, fake_llm):
    """
    E02: actual OCSTracer.trace() persists n_turns=1 for one LLM call.
         OCSCallbackHandler.on_llm_start → MetricsCollector._turns=1 → DB n_turns=1.
    E03: exact seam pipeline artifact frozen BEFORE execution; same 64-hex hash
         used in both observation.execution_fingerprint and expected_source_config.

    BOUNDED: start→llm_input→llm→end seam. NOT full Zeya graph.
    """
    llm, _ = fake_llm
    provider = LlmProviderFactory.create()
    model = LlmProviderModelFactory.create()
    session = ExperimentSessionFactory.create()

    # E03: build seam pipeline; freeze artifact hash ONCE before execution
    pipeline = _make_seam_pipeline(db, provider.id, model.id)
    pipeline_sha = _freeze_pipeline_sha256(pipeline)
    assert len(pipeline_sha) == 64 and all(c in "0123456789abcdef" for c in pipeline_sha)

    trace_ctx_id, raw_output = _run_with_ocsTracer(pipeline, session, _SAFE_MSG, REGISTERED)

    actual_tags = _output_tags_from_state(raw_output)
    reply = raw_output["messages"][-1]
    assert reply == LLM_REPLY

    # E02: actual DB readback
    trace = Trace.objects.get(trace_id=trace_ctx_id)
    assert trace.status == TraceStatus.SUCCESS
    assert trace.n_turns == 1, f"E02 FAIL: OCSTracer must persist n_turns=1 for one LLM call; got {trace.n_turns!r}"

    human_msg = ChatMessageFactory.create(message_type=ChatMessageType.HUMAN, content=_SAFE_MSG, chat=session.chat)
    ai_msg = ChatMessageFactory.create(message_type=ChatMessageType.AI, content=reply, chat=session.chat)
    trace.input_message = human_msg
    trace.output_message = ai_msg
    trace.save(update_fields=["input_message", "output_message"])
    trace.refresh_from_db()

    # E03: same frozen pipeline_sha in both trace snapshot and expected_source
    exp_src = _expected_source(session, pipeline_sha)
    row = CompletedObservationRow.from_trace_dict(
        trace=_snap_trace(trace, human_msg, ai_msg, pipeline_sha, actual_tags),
        session=_snap_session(session),
        experiment=_snap_experiment(session.experiment),
        input_message=_snap_msg(human_msg, "human"),
        output_message=_snap_msg(ai_msg, "ai"),
        expected_route="SAFE",
        expected_source_config=exp_src,
        expected_card_id="",
        source="e02-e03-llm-one-start",
    )

    # E03: hashes consistent in the envelope
    obs_dict = json.loads(row.observation.to_json())
    assert obs_dict["execution_fingerprint"]["pipeline_sha256"] == pipeline_sha
    assert obs_dict["n_turns"] == 1

    # Direct EvaluationMessage (avoids label-transport dependency on Owner A callback)
    eval_msg = EvaluationMessage.objects.create(
        input=EvaluationMessageContent(content=_SAFE_MSG, role="human").model_dump(),
        output=EvaluationMessageContent(content=reply, role="ai").model_dump(),
        context={
            "observation": obs_dict,
            "expected_source": exp_src,
            "expected_route": "SAFE",
            "expected_card_id": "",
        },
    )
    r_no_llm = _run_evaluator(NO_LLM_CHECK_CODE, eval_msg)
    assert r_no_llm.get("skipped") is True, f"no_llm_check must skip for SAFE rows; got {r_no_llm}"
    r_route = _run_evaluator(ROUTE_CHECK_CODE, eval_msg)
    assert r_route.get("route_match") is True, r_route
    assert r_route.get("actual_route") == "SAFE", r_route


# ---------------------------------------------------------------------------
# E04 — actual CSV import creates dataset + messages
# (Label-transport-sensitive: decisive after Owner A callback + DB hold lifts)
# ---------------------------------------------------------------------------


def test_e04_actual_csv_import_creates_dataset_messages(db, fake_llm):
    """
    E04: actual create_dataset_from_csv_task creates EvaluationMessages with
         observation.n_turns=null and expected_source preserved.

    LABEL TRANSPORT NOTE: this test exercises the full CSV → task path.
    It is the decisive acceptance for Owner A's label transport fix.
    With current exporter (plain string labels), parse_csv_value_as_json returns
    expected_route as the raw string — currently correct behavior.
    DB execution hold: not to be run until Owner A callback settles.
    """
    _, _ = fake_llm
    provider = LlmProviderFactory.create()
    model = LlmProviderModelFactory.create()
    session = ExperimentSessionFactory.create()

    pipeline = _make_zeya_pipeline(db, provider.id, model.id)
    pipeline_sha = _freeze_pipeline_sha256(pipeline)

    trace_ctx_id, raw_output = _run_with_ocsTracer(
        pipeline,
        session,
        _DANGER_MSG,
        REGISTERED | {"language_preference": "en"},
    )
    actual_tags = _output_tags_from_state(raw_output)
    reply = raw_output["messages"][-1]

    trace = Trace.objects.get(trace_id=trace_ctx_id)
    human_msg = ChatMessageFactory.create(message_type=ChatMessageType.HUMAN, content=_DANGER_MSG, chat=session.chat)
    ai_msg = ChatMessageFactory.create(message_type=ChatMessageType.AI, content=reply, chat=session.chat)
    trace.input_message = human_msg
    trace.output_message = ai_msg
    trace.save(update_fields=["input_message", "output_message"])
    trace.refresh_from_db()

    exp_src = _expected_source(session, pipeline_sha)
    row = CompletedObservationRow.from_trace_dict(
        trace=_snap_trace(trace, human_msg, ai_msg, pipeline_sha, actual_tags),
        session=_snap_session(session),
        experiment=_snap_experiment(session.experiment),
        input_message=_snap_msg(human_msg, "human"),
        output_message=_snap_msg(ai_msg, "ai"),
        expected_route="EMERGENCY",
        expected_source_config=exp_src,
        expected_category=_DANGER_CATEGORY,
        source="e04-csv-import",
    )

    csv_bytes = _write_csv_to_bytes([row])
    dataset = _run_csv_import(session, csv_bytes, expected_message_count=1)

    imported_msg = dataset.messages.first()
    assert imported_msg is not None

    obs = imported_msg.context.get("observation")
    assert isinstance(obs, dict), f"context.observation must be dict; got {type(obs)}"
    assert "n_turns" in obs, "n_turns key must be present in imported observation"
    assert obs["n_turns"] is None, f"E04: n_turns must be null for EMERGENCY path; got {obs['n_turns']!r}"

    exp_src_imported = imported_msg.context.get("expected_source")
    assert isinstance(exp_src_imported, dict), "context.expected_source must survive CSV roundtrip"
    assert exp_src_imported.get("pipeline_sha256") == pipeline_sha

    assert imported_msg.input.get("content") == _DANGER_MSG
    assert imported_msg.output.get("content") == reply


# ---------------------------------------------------------------------------
# E05 — actual evaluation-task no-generation path
# (Label-transport-sensitive: decisive after Owner A callback + DB hold lifts)
# ---------------------------------------------------------------------------


def test_e05_actual_evaluation_task_no_generation_empty_response(db, fake_llm):
    """
    E05: actual evaluate_message() with EvaluationRun(generation_experiment=None)
         produces EvaluationResult with generated_response='' and starts no fresh model.

    LABEL TRANSPORT NOTE: decisive acceptance test after Owner A callback.
    generation_experiment=None → BotGeneration(session_id=None, response='') →
    evaluator.run(message, '') → no new LLM call.  Source: tasks.py:254-258.
    """
    llm, _ = fake_llm
    provider = LlmProviderFactory.create()
    model = LlmProviderModelFactory.create()
    session = ExperimentSessionFactory.create()

    pipeline = _make_zeya_pipeline(db, provider.id, model.id)
    pipeline_sha = _freeze_pipeline_sha256(pipeline)

    trace_ctx_id, raw_output = _run_with_ocsTracer(
        pipeline,
        session,
        _DANGER_MSG,
        REGISTERED | {"language_preference": "en"},
    )
    actual_tags = _output_tags_from_state(raw_output)
    reply = raw_output["messages"][-1]
    calls_before_eval = len(llm.calls)

    trace = Trace.objects.get(trace_id=trace_ctx_id)
    human_msg = ChatMessageFactory.create(message_type=ChatMessageType.HUMAN, content=_DANGER_MSG, chat=session.chat)
    ai_msg = ChatMessageFactory.create(message_type=ChatMessageType.AI, content=reply, chat=session.chat)
    trace.input_message = human_msg
    trace.output_message = ai_msg
    trace.save(update_fields=["input_message", "output_message"])
    trace.refresh_from_db()

    exp_src = _expected_source(session, pipeline_sha)
    row = CompletedObservationRow.from_trace_dict(
        trace=_snap_trace(trace, human_msg, ai_msg, pipeline_sha, actual_tags),
        session=_snap_session(session),
        experiment=_snap_experiment(session.experiment),
        input_message=_snap_msg(human_msg, "human"),
        output_message=_snap_msg(ai_msg, "ai"),
        expected_route="EMERGENCY",
        expected_source_config=exp_src,
        source="e05-eval-task",
    )

    csv_bytes = _write_csv_to_bytes([row])
    dataset = _run_csv_import(session, csv_bytes, expected_message_count=1)
    imported_msg = dataset.messages.first()

    # Create a PythonEvaluator Django model with ROUTE_CHECK_CODE
    evaluator_obj = Evaluator.objects.create(
        team=session.team,
        type="PythonEvaluator",
        name="e05-route-check",
        evaluation_mode="message",
        params={"code": ROUTE_CHECK_CODE},
        llm_provider=None,
        llm_provider_model=None,
    )

    run = EvaluationRunFactory.create(
        team=session.team,
        evaluator_ids=[evaluator_obj.id],
        generation_experiment=None,
    )

    supplied_responses = []
    original_run = PythonEvaluator.run

    def capture_run(evaluator, message, generated_response, **kwargs):
        supplied_responses.append(generated_response)
        return original_run(evaluator, message, generated_response, **kwargs)

    with (
        mock.patch.object(PythonEvaluator, "run", new=capture_run),
        mock.patch("apps.evaluations.tasks.run_bot_generation") as generation,
    ):
        evaluate_message(run.id, [evaluator_obj.id], imported_msg.id)
    generation.assert_not_called()
    assert supplied_responses == [""]

    from apps.evaluations.models import EvaluationResult  # noqa: PLC0415

    result = EvaluationResult.objects.get(run=run, message=imported_msg, evaluator=evaluator_obj)
    assert result.output.get("generated_response") == "", (
        f"E05: generated_response must be '' when generation_experiment=None; "
        f"got {result.output.get('generated_response')!r}"
    )
    assert result.output.get("result", {}).get("route_match") is True, result.output
    assert len(llm.calls) == calls_before_eval, (
        f"E05: no new model calls expected; got {len(llm.calls) - calls_before_eval} new calls"
    )


# ---------------------------------------------------------------------------
# E06 — foreign same-chat message (different turn) rejected
# ---------------------------------------------------------------------------


def test_e06_foreign_same_chat_different_turn_message_rejected(db, fake_llm):
    """
    E06: same-chat, different-turn AI message rejected by from_trace_dict.

    Trace.output_message_id = ai_msg_turn1.id.
    Supplying output_message snapshot with ai_msg_turn2.id (same session.chat,
    different turn) triggers RelationshipError: trace.output_message_id != output_message.id.

    Both messages are in the same session.chat — not a foreign-chat test.
    The rejection is on FK identity, not chat membership (apps/trace/models.py:36-38).
    """
    _, _ = fake_llm
    provider = LlmProviderFactory.create()
    model = LlmProviderModelFactory.create()
    session = ExperimentSessionFactory.create()

    pipeline = _make_zeya_pipeline(db, provider.id, model.id)
    pipeline_sha = _freeze_pipeline_sha256(pipeline)

    trace_ctx_id, raw_output = _run_with_ocsTracer(
        pipeline,
        session,
        _DANGER_MSG,
        REGISTERED | {"language_preference": "en"},
    )
    actual_tags = _output_tags_from_state(raw_output)
    reply = raw_output["messages"][-1]

    trace = Trace.objects.get(trace_id=trace_ctx_id)

    human_msg = ChatMessageFactory.create(message_type=ChatMessageType.HUMAN, content=_DANGER_MSG, chat=session.chat)
    ai_msg_turn1 = ChatMessageFactory.create(message_type=ChatMessageType.AI, content=reply, chat=session.chat)
    # Same chat, DIFFERENT turn — mutation
    ai_msg_turn2 = ChatMessageFactory.create(
        message_type=ChatMessageType.AI,
        content=reply,  # Identical text must not hide a different turn's FK.
        chat=session.chat,
    )
    assert ai_msg_turn1.chat_id == ai_msg_turn2.chat_id == session.chat.id

    trace.input_message = human_msg
    trace.output_message = ai_msg_turn1  # Trace FK → turn1
    trace.save(update_fields=["input_message", "output_message"])
    trace.refresh_from_db()

    exp_src = _expected_source(session, pipeline_sha)
    trace_snap = _snap_trace(trace, human_msg, ai_msg_turn1, pipeline_sha, actual_tags)

    # Mutation: ai_msg_turn2 — same chat, wrong FK identity
    with pytest.raises(RelationshipError) as exc_info:
        CompletedObservationRow.from_trace_dict(
            trace=trace_snap,
            session=_snap_session(session),
            experiment=_snap_experiment(session.experiment),
            input_message=_snap_msg(human_msg, "human"),
            output_message=_snap_msg(ai_msg_turn2, "ai"),  # wrong turn
            expected_route="EMERGENCY",
            expected_source_config=exp_src,
        )
    err = str(exc_info.value)
    assert "output_message_id" in err, f"E06: error must mention output_message_id; got: {err!r}"

    # Positive control: correct turn1 snapshot passes
    CompletedObservationRow.from_trace_dict(
        trace=trace_snap,
        session=_snap_session(session),
        experiment=_snap_experiment(session.experiment),
        input_message=_snap_msg(human_msg, "human"),
        output_message=_snap_msg(ai_msg_turn1, "ai"),  # correct
        expected_route="EMERGENCY",
        expected_source_config=exp_src,
    )


# ---------------------------------------------------------------------------
# E07 — missing metric_profile rejected
# ---------------------------------------------------------------------------


def test_e07_missing_metric_profile_rejected(db):
    """E07: metric_profile key absent → evaluator returns metric_profile_missing."""
    obs = _minimal_obs_dict()
    del obs["metric_profile"]
    eval_msg = _eval_msg_with_obs(obs, expected_route="SAFE")
    result = _run_evaluator(ROUTE_CHECK_CODE, eval_msg)
    assert result.get("error") == "metric_profile_missing", f"E07: expected metric_profile_missing; got {result}"


# ---------------------------------------------------------------------------
# E08 — unknown metric_profile rejected
# ---------------------------------------------------------------------------


def test_e08_unknown_metric_profile_rejected(db):
    """E08: wrong hash values in metric_profile → metric_profile_mismatch."""
    wrong_profile = {
        "ocs_pin": "0" * 40,
        "collector_sha256": "0" * 64,
        "tracer_sha256": "0" * 64,
    }
    obs = _minimal_obs_dict(metric_profile=wrong_profile)
    eval_msg = _eval_msg_with_obs(obs, expected_route="SAFE")
    result = _run_evaluator(ROUTE_CHECK_CODE, eval_msg)
    assert result.get("error") == "metric_profile_mismatch", f"E08: expected metric_profile_mismatch; got {result}"
    assert result.get("field") in ("ocs_pin", "collector_sha256", "tracer_sha256"), result


# ---------------------------------------------------------------------------
# E09 — missing expected_source rejected
# ---------------------------------------------------------------------------


def test_e09_missing_expected_source_rejected(db):
    """E09: context.expected_source absent → evaluator returns expected_source_missing."""
    obs = _minimal_obs_dict()
    eval_msg = EvaluationMessage.objects.create(
        input={"content": obs["input_text"], "role": "human"},
        output={"content": obs["output_text"], "role": "ai"},
        context={"observation": obs, "expected_route": "SAFE"},
    )
    result = _run_evaluator(ROUTE_CHECK_CODE, eval_msg)
    assert result.get("error") == "expected_source_missing", f"E09: expected expected_source_missing; got {result}"


# ---------------------------------------------------------------------------
# E10 — wrong pipeline fingerprint rejected
# ---------------------------------------------------------------------------


def test_e10_wrong_pipeline_fingerprint_rejected(db):
    """
    E10: obs.execution_fingerprint.pipeline_sha256 != expected_source.pipeline_sha256
         → evaluator returns pipeline_sha256_mismatch.
    """
    real_sha = "a" * 64
    wrong_sha = "b" * 64
    obs = _minimal_obs_dict(pipeline_sha=real_sha)
    eval_msg = _eval_msg_with_obs(
        obs,
        expected_source={
            "chatbot_public_id": obs["chatbot_id"],
            "pipeline_sha256": wrong_sha,
        },
        expected_route="SAFE",
    )
    result = _run_evaluator(ROUTE_CHECK_CODE, eval_msg)
    assert result.get("error") == "pipeline_sha256_mismatch", f"E10: expected pipeline_sha256_mismatch; got {result}"


# ---------------------------------------------------------------------------
# E13 — identity-guard mutation controls
# ---------------------------------------------------------------------------


def test_e13_identity_guard_mutation_controls(db, fake_llm):
    """
    E13: two mutations verify identity guards are real (not vacuously passing).

    Mutation A: wrong chatbot_public_id → RelationshipError mentioning 'chatbot'.
    Mutation B: wrong pipeline_sha256 → RelationshipError mentioning 'pipeline'.
    Positive control: correct expected_source_config passes.
    """
    _, _ = fake_llm
    provider = LlmProviderFactory.create()
    model = LlmProviderModelFactory.create()
    session = ExperimentSessionFactory.create()

    pipeline = _make_zeya_pipeline(db, provider.id, model.id)
    pipeline_sha = _freeze_pipeline_sha256(pipeline)

    trace_ctx_id, raw_output = _run_with_ocsTracer(
        pipeline,
        session,
        _DANGER_MSG,
        REGISTERED | {"language_preference": "en"},
    )
    actual_tags = _output_tags_from_state(raw_output)
    reply = raw_output["messages"][-1]

    trace = Trace.objects.get(trace_id=trace_ctx_id)
    human_msg = ChatMessageFactory.create(message_type=ChatMessageType.HUMAN, content=_DANGER_MSG, chat=session.chat)
    ai_msg = ChatMessageFactory.create(message_type=ChatMessageType.AI, content=reply, chat=session.chat)
    trace.input_message = human_msg
    trace.output_message = ai_msg
    trace.save(update_fields=["input_message", "output_message"])
    trace.refresh_from_db()

    trace_snap = _snap_trace(trace, human_msg, ai_msg, pipeline_sha, actual_tags)
    session_snap = _snap_session(session)
    exp_snap = _snap_experiment(session.experiment)
    in_snap = _snap_msg(human_msg, "human")
    out_snap = _snap_msg(ai_msg, "ai")

    # Mutation A: wrong chatbot public_id
    with pytest.raises(RelationshipError) as exc_a:
        CompletedObservationRow.from_trace_dict(
            trace=trace_snap,
            session=session_snap,
            experiment=exp_snap,
            input_message=in_snap,
            output_message=out_snap,
            expected_route="EMERGENCY",
            expected_source_config={
                "chatbot_public_id": str(uuid4()),  # wrong
                "pipeline_sha256": pipeline_sha,
            },
        )
    assert "chatbot" in str(exc_a.value).lower(), f"E13A: expected chatbot mention; got {exc_a.value!r}"

    # Mutation B: wrong pipeline sha
    with pytest.raises(RelationshipError) as exc_b:
        CompletedObservationRow.from_trace_dict(
            trace=trace_snap,
            session=session_snap,
            experiment=exp_snap,
            input_message=in_snap,
            output_message=out_snap,
            expected_route="EMERGENCY",
            expected_source_config={
                "chatbot_public_id": str(session.experiment.public_id),
                "pipeline_sha256": "c" * 64,  # wrong
            },
        )
    assert "pipeline" in str(exc_b.value).lower(), f"E13B: expected pipeline mention; got {exc_b.value!r}"

    # Positive control: correct expected_source passes
    row = CompletedObservationRow.from_trace_dict(
        trace=trace_snap,
        session=session_snap,
        experiment=exp_snap,
        input_message=in_snap,
        output_message=out_snap,
        expected_route="EMERGENCY",
        expected_source_config=_expected_source(session, pipeline_sha),
    )
    assert row.observation.chatbot_id == str(session.experiment.public_id)


# ---------------------------------------------------------------------------
# Card accuracy is inapplicable on emergency bypass (no answer-route tag).
# ---------------------------------------------------------------------------


def test_card_accuracy_reports_answer_route_tag_missing_honest(db, fake_llm):
    """
    HONEST NEGATIVE: CARD_ACCURACY_CODE returns answer_route_tag_missing.
    Emergency bypass deliberately never executes the deployed answer_match node.
    Missing answer-route evidence here says nothing about its deployment status.
    Fabricating tags to make a card score pass would violate the
    'no authored observed tags' constraint.  G2 is a separate gate.
    """
    _, _ = fake_llm
    provider = LlmProviderFactory.create()
    model = LlmProviderModelFactory.create()
    session = ExperimentSessionFactory.create()

    pipeline = _make_zeya_pipeline(db, provider.id, model.id)
    pipeline_sha = _freeze_pipeline_sha256(pipeline)

    trace_ctx_id, raw_output = _run_with_ocsTracer(
        pipeline,
        session,
        _DANGER_MSG,
        REGISTERED | {"language_preference": "en"},
    )
    actual_tags = _output_tags_from_state(raw_output)
    reply = raw_output["messages"][-1]

    trace = Trace.objects.get(trace_id=trace_ctx_id)
    human_msg = ChatMessageFactory.create(message_type=ChatMessageType.HUMAN, content=_DANGER_MSG, chat=session.chat)
    ai_msg = ChatMessageFactory.create(message_type=ChatMessageType.AI, content=reply, chat=session.chat)
    trace.input_message = human_msg
    trace.output_message = ai_msg
    trace.save(update_fields=["input_message", "output_message"])
    trace.refresh_from_db()

    exp_src = _expected_source(session, pipeline_sha)
    row = CompletedObservationRow.from_trace_dict(
        trace=_snap_trace(trace, human_msg, ai_msg, pipeline_sha, actual_tags),
        session=_snap_session(session),
        experiment=_snap_experiment(session.experiment),
        input_message=_snap_msg(human_msg, "human"),
        output_message=_snap_msg(ai_msg, "ai"),
        expected_route="EMERGENCY",
        expected_source_config=exp_src,
        expected_card_id="",
        source="card-no-issue23",
    )
    obs_dict = json.loads(row.observation.to_json())
    eval_msg = EvaluationMessage.objects.create(
        input=EvaluationMessageContent(content=_DANGER_MSG, role="human").model_dump(),
        output=EvaluationMessageContent(content=reply, role="ai").model_dump(),
        context={
            "observation": obs_dict,
            "expected_source": exp_src,
            "expected_route": "EMERGENCY",
            "expected_card_id": "",
        },
    )
    result = _run_evaluator(CARD_ACCURACY_CODE, eval_msg)
    assert result.get("error") == "answer_route_tag_missing", (
        f"Expected answer_route_tag_missing (issue-23 not deployed); got {result}"
    )
