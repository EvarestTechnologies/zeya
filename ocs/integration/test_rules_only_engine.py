"""
Run the rules-only pipeline (#26) in Open Chat Studio's own pipeline engine.

Run with ``make test-ocs-engine OCS_SOURCE=/path/to/open-chat-studio``.

The LLM provider is patched with OCS's FakeLlm, which records every call. The normal
build is run next to the rules-only one as a control: the same question that calls
the model there must get the fixed reply here, with no model call at all.
"""

import datetime
from unittest import mock

import pytest
from apps.pipelines.flow import FullFlow, split_flow_data
from apps.pipelines.graph import PipelineGraph
from apps.pipelines.nodes.base import PipelineState
from apps.pipelines.repository import ORMRepository
from apps.utils.factories.experiment import ExperimentSessionFactory
from apps.utils.factories.pipelines import PipelineFactory
from apps.utils.factories.service_provider_factories import LlmProviderFactory, LlmProviderModelFactory
from apps.utils.tests.langchain import build_fake_llm_service

from ocs.build_pipeline import build_pipeline
from ocs.check_drift import find_drift
from ocs.tests.danger_corpus import BILINGUAL_EXAMPLES

LLM_REPLY = "Eat a balanced diet, Mama."

# Exact texts from ocs/nodes/rules_only_reply.py.
EN_RULES_ONLY = (
    "Sorry, ZEYA couldn’t answer your question right now. Please try again later. "
    "For pregnancy concerns, contact your healthcare provider."
)
SW_RULES_ONLY = (
    "Samahani, ZEYA imeshindwa kujibu swali lako kwa sasa. Tafadhali jaribu tena baadaye. "
    "Kwa maswali kuhusu ujauzito, wasiliana na mtoa huduma wako wa afya."
)

# No answer card covers these, so the normal build sends them to the model.
UNCOVERED = {"en": "What is the weather today?", "sw": "Hali ya hewa leo ni nini?"}
COVERED = {"en": "Why should I go to ANC?", "sw": "Kwa nini niende kliniki ya ujauzito?"}

REGISTERED = {
    "welcome_sent": True,
    # Now, so the weeks registration adds since enrolment stay at 0.
    "enrolled_at": datetime.datetime.now(datetime.UTC).isoformat(),
    "consent_given": True,
    "name": "Akinyi",
    "name_collected": True,
    "gestational_age_at_enrollment": 20,
    "registration_complete": True,
    "study_group": "intervention",
}

DANGER_CASES = [
    (category, language, message)
    for category, languages in BILINGUAL_EXAMPLES.items()
    for language, message in languages.items()
]


@pytest.fixture()
def fake_llm():
    service = build_fake_llm_service(responses=[LLM_REPLY] * 5)
    service.llm.calls = []
    with mock.patch("apps.service_providers.models.LlmProvider.get_llm_service", return_value=service) as patched:
        yield service.llm, patched


def _import(rules_only: bool):
    # Official import path (apps/pipelines/management/commands/import_pipeline.py), as in
    # test_ocs_engine.py: layout-only Pipeline.data plus the node rows.
    provider = LlmProviderFactory.create()
    provider_model = LlmProviderModelFactory.create()
    pipeline = PipelineFactory.create()
    flow = FullFlow(**build_pipeline(provider.id, provider_model.id, rules_only=rules_only)["data"])
    layout, node_data = split_flow_data(flow)
    pipeline.data = layout.model_dump()
    pipeline.save()
    pipeline.update_nodes_from_data(node_data)
    return pipeline


def _runner(pipeline):
    session = ExperimentSessionFactory.create()
    runnable = PipelineGraph.build_from_pipeline(pipeline).build_runnable()
    config = {"configurable": {"repo": ORMRepository(session=session)}}

    def _run(message: str, participant_data: dict) -> dict:
        state = PipelineState(messages=[message], experiment_session=session, participant_data=participant_data)
        return runnable.invoke(state, config=config)

    return _run


@pytest.fixture()
def rules_only_pipeline(db):
    return _import(rules_only=True)


@pytest.fixture()
def run(rules_only_pipeline):
    return _runner(rules_only_pipeline)


@pytest.fixture()
def run_normal(db):
    return _runner(_import(rules_only=False))


def _tags(output) -> list[str]:
    return [name for name, _category in output.get("output_message_tags", [])]


def test_rules_only_pipeline_validates(rules_only_pipeline):
    from apps.pipelines.exceptions import has_errors

    assert has_errors(rules_only_pipeline.validate()) is False


def test_rules_only_pipeline_has_no_llm_node_in_ocs(rules_only_pipeline):
    rules_only_pipeline.refresh_from_db()
    nodes = rules_only_pipeline.flow_data["nodes"]

    assert "LLMResponseWithPrompt" not in {node["data"]["type"] for node in nodes}
    assert "rules_only_reply" in {node["data"]["params"]["name"] for node in nodes}


@pytest.mark.parametrize(("lang", "expected"), [("en", EN_RULES_ONLY), ("sw", SW_RULES_ONLY)])
def test_uncovered_question_gets_fixed_reply_with_no_model_call(run, run_normal, fake_llm, lang, expected):
    llm, get_llm_service = fake_llm
    data = REGISTERED | {"language_preference": lang}

    control = run_normal(UNCOVERED[lang], data)
    assert control["messages"][-1] == LLM_REPLY, "control: the normal build must call the model for this question"
    assert len(llm.calls) == 1
    llm.calls.clear()
    get_llm_service.reset_mock()

    output = run(UNCOVERED[lang], data)

    assert output["messages"][-1] == expected
    assert "danger_router:SAFE" in _tags(output)
    assert "route:rules_only" in _tags(output)
    assert llm.calls == []
    get_llm_service.assert_not_called()


@pytest.mark.parametrize("lang", ["en", "sw"])
def test_covered_question_still_gets_its_card(run, run_normal, fake_llm, lang):
    llm, _ = fake_llm
    data = REGISTERED | {"language_preference": lang}

    expected = run_normal(COVERED[lang], data)["messages"][-1]
    output = run(COVERED[lang], data)

    assert output["messages"][-1] == expected
    assert "route:rules_only" not in _tags(output)
    assert llm.calls == []


@pytest.mark.parametrize(("category", "language", "message"), DANGER_CASES)
def test_danger_message_still_gets_emergency_reply(run, fake_llm, category, language, message):
    llm, get_llm_service = fake_llm

    output = run(message, REGISTERED | {"language_preference": language})

    reply = output["messages"][-1]
    assert reply.startswith("DHARURA:" if language == "sw" else "URGENT:")
    assert "999" in reply and "922" in reply and "1199" in reply
    assert f"danger_sign:{category}" in _tags(output)
    assert "danger_router:EMERGENCY" in _tags(output)
    assert "route:rules_only" not in _tags(output)
    assert llm.calls == []
    get_llm_service.assert_not_called()


@pytest.mark.parametrize(("category", "language", "message"), DANGER_CASES[::3])
def test_danger_message_before_language_choice_gets_emergency(run, fake_llm, category, language, message):
    llm, _ = fake_llm

    output = run(message, {})

    assert output["messages"][-1].startswith("URGENT:")
    assert llm.calls == []


FULL_FLOW_CASES = [
    # (is_study, language, choice_reply, consent_reply, name, weeks)
    (False, "en", "1", "YES", "Wanjiru", 20),
    (False, "sw", "Kiswahili", "Ndiyo", "Wanjiru", 20),
    (True, "en", "English", "yes", "Akinyi", 20),
    (True, "sw", "2", "ndiyo", "Akinyi", 20),
]


@pytest.mark.parametrize(("is_study", "language", "choice_reply", "consent_reply", "name", "weeks"), FULL_FLOW_CASES)
def test_full_registration_then_fixed_reply(
    run, fake_llm, is_study, language, choice_reply, consent_reply, name, weeks
):
    """Onboarding works unchanged in rules-only mode, and nothing in it calls the model."""
    llm, get_llm_service = fake_llm
    data = {"study_participant": True} if is_study else {}

    choice_turn = run("Hello", data)
    assert choice_turn["messages"][-1] == (
        "Please choose your language / Tafadhali chagua lugha yako:\n1. English\n2. Kiswahili"
    )
    welcome_turn = run(choice_reply, choice_turn["participant_data"])
    assert welcome_turn["participant_data"]["language_preference"] == language
    assert welcome_turn["participant_data"]["consent_given"] is False
    consent_turn = run(consent_reply, welcome_turn["participant_data"])
    assert consent_turn["participant_data"]["consent_given"] is True
    name_turn = run(name, consent_turn["participant_data"])
    assert name_turn["participant_data"]["name"] == name
    weeks_turn = run(str(weeks), name_turn["participant_data"])
    assert weeks_turn["participant_data"]["registration_complete"] is True
    assert weeks_turn["participant_data"]["gestational_age_at_enrollment"] == weeks

    answer_turn = run(UNCOVERED[language], weeks_turn["participant_data"])

    assert answer_turn["messages"][-1] == (SW_RULES_ONLY if language == "sw" else EN_RULES_ONLY)
    assert "route:rules_only" in _tags(answer_turn)
    # The fixed reply changes nothing she has saved.
    assert answer_turn["participant_data"] == weeks_turn["participant_data"]
    assert llm.calls == []
    get_llm_service.assert_not_called()


def test_drift_check_accepts_ocs_round_trip(rules_only_pipeline):
    """What OCS stores and serves back must pass the rules-only drift check."""
    rules_only_pipeline.refresh_from_db()
    live = {"pipeline": {"data": rules_only_pipeline.flow_data}}

    assert find_drift(live, rules_only=True) == []
    assert find_drift(live)[0] == "the live pipeline is the rules-only build; check it with --rules-only"
