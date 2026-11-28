"""
Run the generated pipeline in Open Chat Studio's own pipeline engine.

Needs an OCS checkout with its virtualenv and test database. Run it with
``make test-ocs-engine OCS_SOURCE=/path/to/open-chat-studio``. It is not part
of ``make test-ocs``.

The LLM provider is patched with OCS's FakeLlm, which records every call, so these
tests can assert that a danger-sign message never reaches an LLM.

Obsolete assertions removed (G2 integration context):
  - test_safe_message_from_registered_user_reaches_llm removed; replaced with
    test_safe_message_from_registered_user_default_no_kb_referral. With all five KB
    entries pending, kb_context bakes KB_JSON='[]', kb_available=False, and kb_router
    always routes FALSE → knowledge_referral. The old 1.0-temperature assertion is gone;
    temperature 0.3 is in the LLM node params but the LLM is never called in this path.
  - test_full_multiturn_registration_persists_and_reaches_llm_with_language_context
    renamed to test_full_multiturn_registration_default_no_kb_referral; the final
    question turn now returns the exact language-specific fixed referral (G202).
  Original emergency and onboarding tests are retained unchanged.
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
from ocs.tests.danger_corpus import BILINGUAL_EXAMPLES

LLM_REPLY = "Eat a balanced diet, Mama."

# Exact referral texts from ocs/nodes/knowledge_referral.py.
# Never changed here; changing the node is the single source of truth.
EN_REFERRAL = (
    "I do not have reviewed information to answer that question. Please ask your healthcare provider.\n\n"
    "To talk to a person, visit your nearest health facility or ask your community health promoter. "
    "In an emergency, call 922, free from any phone."
)
SW_REFERRAL = (
    "Sina taarifa iliyokaguliwa ya kujibu swali hilo. Tafadhali muulize muhudumu wa afya.\n\n"
    "Ili kuzungumza na mtu, tembelea kituo cha afya kilicho karibu nawe au muulize muhudumu wa afya ya jamii. "
    "Kwa dharura, piga 922 bila malipo."
)

REGISTERED = {
    "welcome_sent": True,
    # Anchored to "now" (not a fixed past date) so weeks_since_enrollment stays at 0
    # regardless of which day this suite runs on: registration.py computes the
    # participant's current gestational age as gestational_age_at_enrollment plus
    # whole weeks elapsed since enrolled_at, and a fixed date would eventually drift
    # the 20-week enrollment age past the second-trimester band this test asserts on.
    "enrolled_at": datetime.datetime.now(datetime.UTC).isoformat(),
    "consent_given": True,
    "name": "Akinyi",
    "name_collected": True,
    "gestational_age_at_enrollment": 20,
    "registration_complete": True,
    "language_preference": "en",
    "study_group": "intervention",
}

DANGER_CASES = [
    (category, language, message)
    for category, languages in BILINGUAL_EXAMPLES.items()
    for language, message in languages.items()
]


@pytest.fixture()
def fake_llm():
    # apps.utils.tests.langchain.build_fake_llm_service(responses, fake_llm=None,
    # llm_service_class=FakeLlmService) has no token_counts parameter (OCS checkout
    # 9f5c25476555ff74a167c6a14832ce798832847a); it defaults to FakeLlmSimpleTokenCount,
    # which derives token counts from the response text, so no explicit counts are needed.
    service = build_fake_llm_service(responses=[LLM_REPLY] * 5)
    service.llm.calls = []
    with mock.patch("apps.service_providers.models.LlmProvider.get_llm_service", return_value=service) as patched:
        yield service.llm, patched


@pytest.fixture()
def pipeline(db):
    return _import_pipeline()


def _import_pipeline() -> object:
    provider = LlmProviderFactory.create()
    provider_model = LlmProviderModelFactory.create()
    pipeline = PipelineFactory.create()
    # Official import path (apps/pipelines/management/commands/import_pipeline.py:40-52,
    # reference OCS 9f5c25476555ff74a167c6a14832ce798832847a): a full-graph save is split
    # into layout-only Pipeline.data (ADR-0049, no "nodes" key) and the node membership/
    # content mapping that update_nodes_from_data reconciles against the Node rows.
    flow = FullFlow(**build_pipeline(provider.id, provider_model.id)["data"])
    layout, node_data = split_flow_data(flow)
    pipeline.data = layout.model_dump()
    pipeline.save()
    pipeline.update_nodes_from_data(node_data)
    return pipeline


def _make_run(pipeline):
    session = ExperimentSessionFactory.create()
    runnable = PipelineGraph.build_from_pipeline(pipeline).build_runnable()
    config = {"configurable": {"repo": ORMRepository(session=session)}}

    def _run(message: str, participant_data: dict) -> dict:
        state = PipelineState(messages=[message], experiment_session=session, participant_data=participant_data)
        return runnable.invoke(state, config=config)

    return _run


@pytest.fixture()
def run(pipeline):
    return _make_run(pipeline)


@pytest.fixture()
def run_no_kb(db, all_pending_content):
    """Runner for the shipped content with every KB entry and card marked pending."""
    return _make_run(_import_pipeline())


def _tags(output) -> list[str]:
    return [name for name, _category in output.get("output_message_tags", [])]


def test_pipeline_validates(pipeline):
    # ErrorReport (apps/pipelines/exceptions.py, OCS 9f5c25476555ff74a167c6a14832ce798832847a)
    # always carries its three buckets ("node", "edge", "pipeline"); the canonical "is this
    # pipeline valid" check is has_errors(), not equality against an empty dict.
    from apps.pipelines.exceptions import has_errors

    assert has_errors(pipeline.validate()) is False


@pytest.mark.parametrize(("category", "language", "message"), DANGER_CASES)
def test_danger_message_never_reaches_llm(run, fake_llm, category, language, message):
    llm, get_llm_service = fake_llm

    output = run(message, REGISTERED | {"language_preference": language})

    reply = output["messages"][-1]
    assert reply.startswith("DHARURA:" if language == "sw" else "URGENT:")
    assert "999" in reply and "922" in reply and "0740 587 479" in reply
    assert f"danger_sign:{category}" in _tags(output)
    assert "danger_router:EMERGENCY" in _tags(output)
    assert llm.calls == []
    get_llm_service.assert_not_called()


@pytest.mark.parametrize(("category", "language", "message"), DANGER_CASES[::3])
def test_danger_message_during_registration_gets_emergency(run, fake_llm, category, language, message):
    llm, _ = fake_llm

    output = run(message, {})

    assert output["messages"][-1].startswith("URGENT:")
    assert "registration:first_contact" not in _tags(output)
    assert llm.calls == []


@pytest.mark.parametrize(("category", "language", "message"), DANGER_CASES[::5])
def test_danger_message_during_language_choice_pending_gets_emergency(run, fake_llm, category, language, message):
    # Opus review #27 suggestion: cover a danger message that arrives while the
    # participant is mid language-choice (not just the pre-onboarding data={} case).
    llm, _ = fake_llm
    pending = {"language_choice_pending": True}

    output = run(message, pending)

    assert output["messages"][-1].startswith("URGENT:")
    assert "registration" not in _tags(output)
    assert "registration:first_contact" not in _tags(output)
    assert llm.calls == []
    assert output["participant_data"]["language_choice_pending"] is True


@pytest.mark.parametrize(("category", "language", "message"), DANGER_CASES[::5])
def test_danger_message_during_partial_registration_recovery_gets_emergency(run, fake_llm, category, language, message):
    # Opus review #27 suggestion: a recovery-partial variant -- consent already given,
    # name and gestational age missing, and no valid language preference yet.
    llm, _ = fake_llm
    recovery_partial = {
        "welcome_sent": True,
        "enrolled_at": "2026-09-23T09:30:00+00:00",
        "consent_given": True,
        "registration_complete": False,
        "study_group": "intervention",
    }

    output = run(message, recovery_partial)

    assert output["messages"][-1].startswith("URGENT:")
    assert "registration" not in _tags(output)
    assert llm.calls == []
    assert output["participant_data"]["consent_given"] is True
    assert "name_collected" not in output["participant_data"]
    assert output["participant_data"]["registration_complete"] is False


def test_safe_message_from_registered_user_default_no_kb_referral(run_no_kb, fake_llm):
    """With all-pending KB content, a registered participant receives a fixed referral.

    New default-no-KB semantics: build_pipeline(approved-only) bakes KB_JSON='[]'.
    kb_context sets kb_available=False; kb_router routes FALSE → knowledge_referral → end.
    No model is called.

    Old assertion removed: 'assert ... temperature 1.0' (Zeya's original Gemini config).
    New config is temperature=0.3 (in LLM node params) but the LLM is never called on
    this path so temperature config cannot be asserted here — see G208 for LLM-path check.
    """
    llm, get_llm_service = fake_llm

    output = run_no_kb("What should I eat?", REGISTERED)

    reply = output["messages"][-1]
    assert reply == EN_REFERRAL, f"Expected EN referral, got: {reply!r}"
    assert "danger_router:SAFE" in _tags(output)
    assert "route:knowledge_referral" in _tags(output)
    assert llm.calls == [], "LLM must not be called with all-pending KB"
    get_llm_service.assert_not_called()


def test_safe_message_from_new_user_sees_language_choice_then_welcome_without_llm(run, fake_llm):
    # Stale-expectation fix: a participant with no data (data={}) is public, not a study
    # participant, so the previous assertion of Zeya's study welcome text never matched
    # current public-welcome behaviour. Updated for explicit language onboarding (#27):
    # a new participant without a stored/imported preference first sees the fixed
    # bilingual choice (no model call, first message content discarded), then the public
    # welcome in the chosen language as a separate turn -- still with no LLM call.
    llm, _ = fake_llm

    first = run("Hello", {})
    assert first["messages"][-1] == (
        "Please choose your language / Tafadhali chagua lugha yako:\n1. English\n2. Kiswahili"
    )
    assert "welcome_sent" not in first["participant_data"]
    assert llm.calls == []

    second = run("1", first["participant_data"])
    assert second["messages"][-1].startswith("Welcome to ZEYA!")
    assert second["participant_data"]["welcome_sent"] is True
    assert second["participant_data"]["language_preference"] == "en"
    assert llm.calls == []


def test_drift_check_accepts_ocs_round_trip(pipeline):
    """What OCS stores and serves back (Pipeline.flow_data) must pass the drift check."""
    from ocs.check_drift import find_drift

    pipeline.refresh_from_db()
    # Default approved-only drift check; staging flag defaults to False.
    assert find_drift({"pipeline": {"data": pipeline.flow_data}}) == []


FULL_FLOW_CASES = [
    # (is_study, language, choice_reply, consent_reply, name, weeks)
    (False, "en", "1", "YES", "Wanjiru", 20),
    (False, "sw", "Kiswahili", "Ndiyo", "Wanjiru", 20),
    (True, "en", "English", "yes", "Akinyi", 20),
    (True, "sw", "2", "ndiyo", "Akinyi", 20),
]


@pytest.mark.parametrize(("is_study", "language", "choice_reply", "consent_reply", "name", "weeks"), FULL_FLOW_CASES)
def test_full_multiturn_registration_default_no_kb_referral(
    run_no_kb, fake_llm, is_study, language, choice_reply, consent_reply, name, weeks
):
    """End-to-end multi-turn registration; final question returns language-specific referral.

    G202: original onboarding/consent/study behaviour retained; four parametrized
    full-multiturn cases (en study, en public, sw study, sw public) each ending with
    the exact fixed referral for the saved language. Zero model calls throughout.

    Old assertion removed: final turn asserted LLM_REPLY reached via LLM call.
    New assertion: knowledge_referral returns exact EN or SW referral text with zero model.

    When KB content is approved and deployed, the final turn should:
      - LLM be called (len(llm.calls) == 1) through the VALID budget path
      - Temperature 0.3 in llm_model_parameters (see G208)
      - history_type=none confirmed
      - Swahili context line present for SW participants (see G205)
    Parent runs those gates after content passes clinical and language review.
    """
    llm, get_llm_service = fake_llm
    seed = {"study_participant": True} if is_study else {}

    choice_turn = run_no_kb("Hello", seed)
    assert choice_turn["messages"][-1] == (
        "Please choose your language / Tafadhali chagua lugha yako:\n1. English\n2. Kiswahili"
    )
    assert "welcome_sent" not in choice_turn["participant_data"]
    assert llm.calls == []

    welcome_turn = run_no_kb(choice_reply, choice_turn["participant_data"])
    welcome_reply = welcome_turn["messages"][-1]
    assert welcome_turn["participant_data"]["language_preference"] == language
    assert welcome_turn["participant_data"]["welcome_sent"] is True
    assert welcome_turn["participant_data"]["consent_given"] is False
    if is_study:
        assert welcome_reply.startswith("Karibu kwenye" if language == "sw" else "Welcome to the Antenatal")
    else:
        assert welcome_reply.startswith("Karibu ZEYA!" if language == "sw" else "Welcome to ZEYA!")
    assert llm.calls == []

    consent_turn = run_no_kb(consent_reply, welcome_turn["participant_data"])
    assert consent_turn["participant_data"]["consent_given"] is True
    assert "name" in consent_turn["messages"][-1].lower() or "jina" in consent_turn["messages"][-1].lower()
    assert llm.calls == []

    name_turn = run_no_kb(name, consent_turn["participant_data"])
    assert name_turn["participant_data"]["name_collected"] is True
    assert name_turn["participant_data"]["name"] == name
    assert name in name_turn["messages"][-1]
    assert llm.calls == []

    weeks_turn = run_no_kb(str(weeks), name_turn["participant_data"])
    assert weeks_turn["participant_data"]["registration_complete"] is True
    assert weeks_turn["participant_data"]["gestational_age_at_enrollment"] == weeks
    assert "20" in weeks_turn["messages"][-1] or str(weeks) in weeks_turn["messages"][-1]
    assert llm.calls == []

    # G202: exact fixed referral per saved language; zero model calls throughout.
    question = "Ninapaswa kula nini?" if language == "sw" else "What should I eat?"
    answer_turn = run_no_kb(question, weeks_turn["participant_data"])

    expected_referral = SW_REFERRAL if language == "sw" else EN_REFERRAL
    reply = answer_turn["messages"][-1]
    assert reply == expected_referral, f"Expected exact {language!r} referral, got: {reply!r}"
    assert "danger_router:SAFE" in _tags(answer_turn)
    assert "route:knowledge_referral" in _tags(answer_turn)
    assert llm.calls == [], "LLM must not be called with all-pending KB"
    get_llm_service.assert_not_called()
