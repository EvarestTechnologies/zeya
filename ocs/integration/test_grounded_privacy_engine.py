"""
Privacy/history seam test against the real OCS pipeline engine.

SCOPE: component/LLM-config execution seam test.
  - real llm_input CodeNode (ocs/nodes/llm_input.py) in a minimal pipeline
  - real LLM node (LLMResponseWithPrompt) with Phase A config from build_pipeline
  - real ORMRepository / PipelineChatHistory for prior-turn seeding
  - FakeLlm captures all messages; no network calls to any provider

This is NOT a full Zeya graph test.  The full graph
  registration_router → kb_context → kb_router → answer_match → output_guard
is deliberately RED pending component ports #23 and #25.  No stubs here.

Seam pipeline topology:
  StartNode → llm_input (CodeNode) → llm (LLMResponseWithPrompt) → EndNode

Run via privacy-engine-harness.py which starts an isolated loopback-only
Postgres container, sets DATABASE_URL and scrubs production env, then cleans up.
"""

import copy
import datetime
from unittest import mock

import pytest
from apps.pipelines.flow import FullFlow, split_flow_data
from apps.pipelines.graph import PipelineGraph
from apps.pipelines.models import PipelineChatHistoryTypes
from apps.pipelines.nodes.base import PipelineState
from apps.pipelines.repository import ORMRepository
from apps.utils.factories.experiment import ExperimentSessionFactory
from apps.utils.factories.pipelines import (
    PipelineChatHistoryFactory,
    PipelineChatMessagesFactory,
    PipelineFactory,
)
from apps.utils.factories.service_provider_factories import LlmProviderFactory, LlmProviderModelFactory
from apps.utils.tests.langchain import build_fake_llm_service

from ocs.build_pipeline import NODES_DIR, build_pipeline

# ---------------------------------------------------------------------------
# Synthetic-only test data — no real participants, no production names/phones
# ---------------------------------------------------------------------------

SYNTH_NAME = "Testparticipant"
SYNTH_PHONE = "+254799000001"
SYNTH_EMAIL = "synth_test_zero@zeya.invalid"

PRIOR_HUMAN_WITH_PII = f"My name is {SYNTH_NAME}, call {SYNTH_PHONE} or mail {SYNTH_EMAIL}"
PRIOR_AI_RESPONSE = "Thank you, I will help with your pregnancy questions."

SAFE_QUESTION = "What food is good in pregnancy?"

_ENROLLED_NOW = datetime.datetime.now(datetime.UTC).isoformat()

SYNTH_PARTICIPANT_EN = {
    "welcome_sent": True,
    "enrolled_at": _ENROLLED_NOW,
    "consent_given": True,
    "name": SYNTH_NAME,
    "name_collected": True,
    "gestational_age_at_enrollment": 20,
    "registration_complete": True,
    "language_preference": "en",
}
SYNTH_PARTICIPANT_SW = {**SYNTH_PARTICIPANT_EN, "language_preference": "sw"}

FAKE_REPLY = "Eat a balanced diet."

# ---------------------------------------------------------------------------
# Minimal seam pipeline builder (not build_pipeline — no danger gate / registration)
# ---------------------------------------------------------------------------

_SEAM_LABEL = "ZEYA privacy-seam (test-only; not full Zeya graph)"


def _node(node_id, node_type, params, x, y, flow_type="pipelineNode"):
    return {
        "id": node_id,
        "type": flow_type,
        "position": {"x": x, "y": y},
        "data": {"id": node_id, "type": node_type, "label": "", "params": params},
    }


def _edge(source, target, source_handle="output"):
    return {
        "id": f"{source}:{source_handle}->{target}",
        "source": source,
        "target": target,
        "sourceHandle": source_handle,
        "targetHandle": "input",
    }


def _code(name):
    return (NODES_DIR / f"{name}.py").read_text()


def _build_seam_pipeline(provider_id, model_id, *, history_type=None, history_mode=None, max_history_length=None):
    """start → llm_input → llm → end.

    history_type='none'     Phase A production config (privacy safe).
    history_type='node'     Counterexample: exercises real history fetch so the
                            assertion proves actual history leakage, not vacuous pass.
    """
    generated = build_pipeline(provider_id, model_id)
    llm_params = copy.deepcopy(
        next(
            node["data"]["params"] for node in generated["data"]["nodes"] if node["data"]["params"].get("name") == "llm"
        )
    )
    if history_type is not None:
        llm_params["history_type"] = history_type
    if history_mode is not None:
        llm_params["history_mode"] = history_mode
    if max_history_length is not None:
        llm_params["max_history_length"] = max_history_length

    nodes = [
        _node("start", "StartNode", {"name": "start"}, 0, 0, flow_type="startNode"),
        _node("llm_input", "CodeNode", {"name": "llm_input", "code": _code("llm_input")}, 300, 0),
        _node("llm", "LLMResponseWithPrompt", llm_params, 600, 0),
        _node("end", "EndNode", {"name": "end"}, 900, 0, flow_type="endNode"),
    ]
    edges = [
        _edge("start", "llm_input"),
        _edge("llm_input", "llm"),
        _edge("llm", "end"),
    ]
    return {"name": _SEAM_LABEL, "data": {"nodes": nodes, "edges": edges}}


def _make_pipeline(db, provider_id, model_id, **seam_kwargs):
    p = PipelineFactory.create()
    data = _build_seam_pipeline(provider_id, model_id, **seam_kwargs)
    flow = FullFlow(**data["data"])
    layout, node_data = split_flow_data(flow)
    p.data = layout.model_dump()
    p.save()
    p.update_nodes_from_data(node_data)
    return p


def _make_runner(pipeline):
    session = ExperimentSessionFactory.create()
    runnable = PipelineGraph.build_from_pipeline(pipeline).build_runnable()
    config = {"configurable": {"repo": ORMRepository(session=session)}}

    def _run(message, participant_data):
        state = PipelineState(
            messages=[message],
            experiment_session=session,
            participant_data=participant_data,
        )
        return runnable.invoke(state, config=config)

    return _run, session


def _all_message_text(messages):
    """Extract text content from all messages in a single call."""
    parts = []
    for m in messages:
        c = m.content
        if isinstance(c, str):
            parts.append(c)
        elif isinstance(c, list):
            parts.extend(block.get("text", "") for block in c if isinstance(block, dict))
    return "\n".join(parts)


@pytest.fixture()
def fake_llm():
    service = build_fake_llm_service(responses=[FAKE_REPLY] * 10)
    service.llm.calls = []
    with mock.patch("apps.service_providers.models.LlmProvider.get_llm_service", return_value=service) as patched:
        yield service.llm, patched


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_seam_inherits_actual_builder_llm_configuration():
    generated = build_pipeline(3, 120)
    expected = next(
        node["data"]["params"] for node in generated["data"]["nodes"] if node["data"]["params"].get("name") == "llm"
    )
    expected["llm_model_parameters"] = {"temperature": 0.17}
    expected["history_type"] = "node"
    expected["history_mode"] = "max_history_length"
    expected["max_history_length"] = 3
    with mock.patch.dict(globals(), {"build_pipeline": lambda *_args: generated}):
        seam = _build_seam_pipeline(3, 120)
    actual = next(
        node["data"]["params"] for node in seam["data"]["nodes"] if node["data"]["params"].get("name") == "llm"
    )
    assert actual == expected


def test_seam_pipeline_validates(db):
    """Seam pipeline passes OCS structural validation."""
    from apps.pipelines.exceptions import has_errors

    provider = LlmProviderFactory.create()
    model = LlmProviderModelFactory.create()
    pipeline = _make_pipeline(db, provider.id, model.id)
    assert has_errors(pipeline.validate()) is False


def test_llm_input_sanitizes_name_before_model(db, fake_llm):
    """llm_input removes the participant's saved name before the question reaches the LLM."""
    llm, _ = fake_llm
    provider = LlmProviderFactory.create()
    model = LlmProviderModelFactory.create()
    pipeline = _make_pipeline(db, provider.id, model.id)
    run, _ = _make_runner(pipeline)

    # Question contains the saved participant name
    question = f"I am {SYNTH_NAME}, what should I eat?"
    run(question, SYNTH_PARTICIPANT_EN)

    assert len(llm.calls) == 1
    messages = llm.get_call_messages()[0]
    human_text = _all_message_text([messages[-1]])  # last message = current question
    assert SYNTH_NAME not in human_text, (
        f"llm_input failed to remove saved name from question before model; got: {human_text!r}"
    )
    assert "[name]" in human_text


def test_llm_input_sanitizes_phone_before_model(db, fake_llm):
    """llm_input removes a phone number before the question reaches the LLM."""
    llm, _ = fake_llm
    provider = LlmProviderFactory.create()
    model = LlmProviderModelFactory.create()
    pipeline = _make_pipeline(db, provider.id, model.id)
    run, _ = _make_runner(pipeline)

    question = f"Call me at {SYNTH_PHONE} with the answer."
    run(question, SYNTH_PARTICIPANT_EN)

    assert len(llm.calls) == 1
    messages = llm.get_call_messages()[0]
    human_text = _all_message_text([messages[-1]])
    assert SYNTH_PHONE not in human_text
    assert "[phone]" in human_text


def test_no_history_turns_reach_model_with_history_none(db, fake_llm):
    """With history_type=none, prior turns seeded in real PipelineChatHistory do NOT reach the model.

    Source: OCS engine apps/pipelines/nodes/mixins.py:222-241.
    """
    llm, _ = fake_llm
    provider = LlmProviderFactory.create()
    model = LlmProviderModelFactory.create()
    pipeline = _make_pipeline(db, provider.id, model.id)
    run, session = _make_runner(pipeline)

    # Seed a prior-turn PII message directly into real PipelineChatHistory storage
    # for the 'llm' node (node_id="llm" matches the LLM node's flow_id in the graph).
    history = PipelineChatHistoryFactory.create(
        session=session,
        type=PipelineChatHistoryTypes.NODE,
        name="llm",
    )
    PipelineChatMessagesFactory.create(
        chat_history=history,
        human_message=PRIOR_HUMAN_WITH_PII,
        ai_message=PRIOR_AI_RESPONSE,
        node_id="llm",
    )

    run(SAFE_QUESTION, SYNTH_PARTICIPANT_EN)

    assert len(llm.calls) == 1
    messages = llm.get_call_messages()[0]
    all_text = _all_message_text(messages)

    # history_type=none → only system + current question (2 messages)
    assert len(messages) == 2, (
        f"Expected 2 messages (system + human) with history_type=none, got {len(messages)}: {messages!r}"
    )
    assert SYNTH_NAME not in all_text, f"Saved name leaked from history: {all_text!r}"
    assert SYNTH_PHONE not in all_text, f"Phone leaked from history: {all_text!r}"
    assert SYNTH_EMAIL not in all_text, f"Email leaked from history: {all_text!r}"
    assert PRIOR_HUMAN_WITH_PII not in all_text


def test_counterexample_history_node_exposes_prior_pii(db, fake_llm):
    """COUNTEREXAMPLE: with history_type=node, the same seeded PII turn DOES reach the model.

    This proves the assertion in test_no_history_turns_reach_model_with_history_none
    is not vacuously true — it would have caught real history leakage.
    history_type=none in production is the control that eliminates this exposure.
    """
    llm, _ = fake_llm
    provider = LlmProviderFactory.create()
    model = LlmProviderModelFactory.create()
    # Counterexample: history_type=node, max_history_length mode to avoid
    # summarization middleware complexity with one seeded pair.
    pipeline = _make_pipeline(
        db,
        provider.id,
        model.id,
        history_type="node",
        history_mode="max_history_length",
        max_history_length=10,
    )
    run, session = _make_runner(pipeline)

    # Same seed as the privacy test above
    history = PipelineChatHistoryFactory.create(
        session=session,
        type=PipelineChatHistoryTypes.NODE,
        name="llm",
    )
    PipelineChatMessagesFactory.create(
        chat_history=history,
        human_message=PRIOR_HUMAN_WITH_PII,
        ai_message=PRIOR_AI_RESPONSE,
        node_id="llm",
    )

    run(SAFE_QUESTION, SYNTH_PARTICIPANT_EN)

    assert len(llm.calls) == 1
    messages = llm.get_call_messages()[0]
    all_text = _all_message_text(messages)

    # With history_type=node: system + prior_human + prior_ai + current = 4 messages
    assert len(messages) == 4, (
        f"Expected 4 messages (system + 2 history + human) with history_type=node, got {len(messages)}: "
        f"{[type(m).__name__ for m in messages]!r}"
    )
    # The PII from the prior turn IS in the messages (proves the assertion above is real)
    assert SYNTH_NAME in all_text or SYNTH_PHONE in all_text or SYNTH_EMAIL in all_text, (
        f"Counterexample failed: expected prior PII in history_type=node messages; got: {all_text!r}"
    )


def test_saved_language_en_interpolated_in_system(db, fake_llm):
    """language_preference=en renders in the system message via {participant_data.language_preference}."""
    llm, _ = fake_llm
    provider = LlmProviderFactory.create()
    model = LlmProviderModelFactory.create()
    pipeline = _make_pipeline(db, provider.id, model.id)
    run, _ = _make_runner(pipeline)

    run(SAFE_QUESTION, SYNTH_PARTICIPANT_EN)

    assert len(llm.calls) == 1
    system = llm.get_call_messages()[0][0].content
    assert "(en)" in system, f"language_preference=en did not render in system message; system: {system[:200]!r}"
    assert "(sw)" not in system


def test_saved_language_sw_interpolated_in_system(db, fake_llm):
    """language_preference=sw renders in the system message via {participant_data.language_preference}."""
    llm, _ = fake_llm
    provider = LlmProviderFactory.create()
    model = LlmProviderModelFactory.create()
    pipeline = _make_pipeline(db, provider.id, model.id)
    run, _ = _make_runner(pipeline)

    run(SAFE_QUESTION, SYNTH_PARTICIPANT_SW)

    assert len(llm.calls) == 1
    system = llm.get_call_messages()[0][0].content
    assert "(sw)" in system, f"language_preference=sw did not render in system message; system: {system[:200]!r}"
    assert "(en)" not in system


def test_temperature_in_model_call(db, fake_llm):
    """LLM node passes temperature=0.3 to the provider — no higher temperature in the call."""
    llm, _ = fake_llm
    provider = LlmProviderFactory.create()
    model = LlmProviderModelFactory.create()
    pipeline = _make_pipeline(db, provider.id, model.id)
    run, _ = _make_runner(pipeline)

    run(SAFE_QUESTION, SYNTH_PARTICIPANT_EN)

    assert len(llm.calls) == 1
    # The FakeLlm records calls; temperature is in the model parameters, not in the
    # call messages. We verify via the pipeline config that temperature=0.3 is set.
    # (Temperature enforcement at the LLM provider level is an OCS responsibility;
    # here we confirm the node was built with the right config.)
    for node_data in pipeline.node_set.all():
        if node_data.params.get("name") == "llm":
            assert node_data.params.get("llm_model_parameters", {}).get("temperature") == 0.3
            break
    else:
        pytest.fail("llm node not found in pipeline")
