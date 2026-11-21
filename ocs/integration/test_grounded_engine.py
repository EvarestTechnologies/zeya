"""
G2 full-graph acceptance tests for the Zeya grounded-starter pipeline.

Requires OCS engine (see external full-graph-engine-harness.py).
DB/container execution lease granted under g2-execution-corrections.md.

Twelve finite acceptance checks (parametrised where named):

  G201 emergency precedence: registered/unregistered, en/sw, no model, no mutation.
  G202 original onboarding/consent/study behaviour retained + four full-multiturn
       default-noKB (en/sw study/public), exact language-specific referral, zero model.
  G203 default all-pending KB/card corpus excluded; full registered -> fixed referral.
  G204 staged synthetic eligible KB+card -> exact authored card text, CARD/card-ID tags,
       zero model; pending review_status + allow_pending preserved in baked source.
  G205 staged eligible KB + unsupported query -> ASK_AI -> one FakeLlm -> safe reply;
       name sanitized, ASK_AI tag, both languages.
  G206 guard blocks unsafe CARD text and unsafe fake-AI text; parametrised en/sw;
       exact policy blocked_referral_en/sw; selection vs delivery distinguished.
  G207 actual kb_ids/kb_section from temp_state prove language and week eligibility;
       elapsed-week transition; KB-language-empty falls to referral.
  G208 actual UTF-8 bytes == budget_bytes from temp_state; seeded history absent from
       FakeLlm call (proves history_type=none); name/phone PII sanitized; language
       interpolated; no tools; temperature 0.3 from executed artifact.
  G209 live-calibrated 4001-byte overflow -> referral, no model; exact-4000 -> one start;
       nonASCII multibyte boundary (UTF-8 byte count != character count confirmed).
  G210 missing/invalid required budget state -> OVER_BUDGET fail-closed; isolated mutated
       artifact blanks budget_route; router default = OVER_BUDGET; labelled mutation.
  G211 one-pass rendering: placeholder-like text in KB not re-expanded; LLM-call
       precondition mandatory; actual captured prompt agrees with budget helper; no PII
       in budget-node tags; no participant_data mutation from budget node.
  G212 source drift compares regenerated default/staging artifacts; staging does not
       relabel content; baked JSON parsed via ast.literal_eval then json.loads.

Synthetic fixture policy:
  Synthetic KB entries and cards use review_status="pending" with an explicit
  eligible=True runtime flag added by render_kb_node(include_pending=True).
  Review status is NEVER changed to "approved"; pending content is never clinical.
  Synthetic file content is test-only authored text, not sourced clinical guidance.

Budget boundary (G208/G209):
  Rendered bytes measured live via _calibrate_rendered_bytes() on first staging run.
  Formula: re.sub placeholders in template using actual kb_section/llm_context/lang,
  then len(rendered.encode("utf-8")). Boundaries = 4000 - rendered_bytes and + 1.
  Analytical estimates rejected; derivation repeated fresh each test session.
"""

import ast
import copy
import datetime
import hashlib
import json
import os
import re
import tempfile
from pathlib import Path

import pytest
from apps.chat.models import ChatMessage, ChatMessageType
from apps.pipelines.flow import FullFlow, split_flow_data
from apps.pipelines.graph import PipelineGraph
from apps.pipelines.nodes.base import PipelineState
from apps.pipelines.repository import ORMRepository
from apps.utils.factories.experiment import ExperimentSessionFactory
from apps.utils.factories.pipelines import PipelineFactory
from apps.utils.factories.service_provider_factories import (
    LlmProviderFactory,
    LlmProviderModelFactory,
)
from apps.utils.tests.langchain import build_fake_llm_service

import ocs.build_pipeline as _bp_module
from ocs.build_pipeline import SYSTEM_PROMPT_FILE, build_pipeline
from ocs.check_drift import find_drift
from ocs.tests.danger_corpus import BILINGUAL_EXAMPLES

# ---------------------------------------------------------------------------
# Evidence
# ---------------------------------------------------------------------------

EVIDENCE_DIR = (
    Path(os.environ["ZEYA_G2_EVIDENCE_DIR"])
    if os.environ.get("ZEYA_G2_EVIDENCE_DIR")
    else Path(tempfile.mkdtemp(prefix="zeya-g2-evidence-"))
)
EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Guard blocked texts -- single source of truth is docs/output-policy.json
# ---------------------------------------------------------------------------

GUARD_BLOCKED_EN = "I can't share more details safely. Please speak with your health worker."
GUARD_BLOCKED_SW = "Sina maelezo zaidi ya kushiriki kwa usalama. Zungumza na mhudumu wa afya wako."

# ---------------------------------------------------------------------------
# Knowledge-referral texts -- single source of truth is ocs/nodes/knowledge_referral.py
# ---------------------------------------------------------------------------

EN_REFERRAL = "I do not have reviewed information to answer that question. Please ask your healthcare provider."
SW_REFERRAL = "Sina taarifa iliyokaguliwa kujibu swali hilo. Tafadhali uliza mtoa huduma wako wa afya."

# ---------------------------------------------------------------------------
# Synthetic fixture content (test-only authored text, not clinical guidance)
# ---------------------------------------------------------------------------

_SYNTH_CARD_ANSWER_SAFE_EN = "Antenatal care supports your health and your baby during pregnancy."
_SYNTH_CARD_ANSWER_SAFE_SW = "Huduma ya uzazi inasaidia afya yako na mtoto wako wakati wa ujauzito."
# drug + dose -> output_guard blocks both EN and SW unsafe cards
_SYNTH_CARD_ANSWER_UNSAFE_EN = "Take paracetamol 500mg twice daily for headache relief."
_SYNTH_CARD_ANSWER_UNSAFE_SW = "Tumia paracetamol 500mg mara mbili kwa siku kwa maumivu ya kichwa."

_LLM_REPLY_SAFE = "A varied diet with vegetables and whole grains supports a healthy pregnancy."
_LLM_REPLY_UNSAFE = "Take amoxicillin 250mg three times a day to prevent infection."

# ---------------------------------------------------------------------------
# Participant fixtures
# ---------------------------------------------------------------------------

REGISTERED_EN = {
    "welcome_sent": True,
    "enrolled_at": datetime.datetime.now(datetime.UTC).isoformat(),
    "consent_given": True,
    "name": "Akinyi",
    "name_collected": True,
    "gestational_age_at_enrollment": 20,
    "registration_complete": True,
    "language_preference": "en",
    "study_group": "intervention",
}

REGISTERED_SW = {**REGISTERED_EN, "language_preference": "sw"}

REGISTERED_THIRD_TRIM = {
    **REGISTERED_EN,
    "gestational_age_at_enrollment": 30,
}

# 14 days ago -> current GA = 20 + floor(14/7) = 22 weeks
_ENROLLED_14D_AGO = (datetime.datetime.now(datetime.UTC) - datetime.timedelta(days=14)).isoformat()
REGISTERED_22W = {
    **REGISTERED_EN,
    "enrolled_at": _ENROLLED_14D_AGO,
    "gestational_age_at_enrollment": 20,
}

DANGER_CASES = [
    (category, language, message)
    for category, languages in BILINGUAL_EXAMPLES.items()
    for language, message in languages.items()
]


# ---------------------------------------------------------------------------
# Synthetic KB/card fixture files
# ---------------------------------------------------------------------------


def _synth_kb_markdown(entries: list[dict]) -> str:
    """Format synthetic entries as zeya-knowledge-base.md Markdown."""
    sections = []
    for e in entries:
        min_w = str(e["min_week"]) if e.get("min_week") is not None else ""
        max_w = str(e["max_week"]) if e.get("max_week") is not None else ""
        sections.append(
            f"## {e['id']}\n\n"
            f"Review-state: {e['review_status']}\n"
            f"Language: {e['language']}\n"
            f"Topics: {e.get('topics', 'test')}\n"
            f"Min-week: {min_w}\n"
            f"Max-week: {max_w}\n"
            f"Source-refs: https://example.com/fixture\n\n"
            f"{e['text']}\n\n---\n"
        )
    header = (
        "# Synthetic test KB\n\n"
        "Status: TEST FIXTURE ONLY. Not reviewed. Not approved.\n\n"
        "Sources:\n[F] https://example.com/fixture\n\n---\n\n"
    )
    return header + "\n".join(sections)


@pytest.fixture()
def synthetic_kb_file(tmp_path):
    """Standard staging KB: en x2, sw x1, week-bound en x1."""
    entries = [
        {
            "id": "anc_fixture_en",
            "review_status": "pending",
            "language": "en",
            "topics": "anc, test",
            "min_week": None,
            "max_week": None,
            "text": "Antenatal care visits help monitor your health and your baby.",
        },
        {
            "id": "food_fixture_en",
            "review_status": "pending",
            "language": "en",
            "topics": "food, test",
            "min_week": None,
            "max_week": None,
            "text": "Eating vegetables, fruits and grains supports pregnancy.",
        },
        {
            "id": "anc_fixture_sw",
            "review_status": "pending",
            "language": "sw",
            "topics": "anc, test",
            "min_week": None,
            "max_week": None,
            "text": "Huduma ya uzazi husaidia kufuatilia afya yako na mtoto wako.",
        },
        {
            # Week-bound: eligible only weeks 28-42 (G207)
            "id": "third_trim_fixture_en",
            "review_status": "pending",
            "language": "en",
            "topics": "birth, test",
            "min_week": 28,
            "max_week": 42,
            "text": "Birth planning includes choosing your delivery facility.",
        },
    ]
    path = tmp_path / "synthetic-kb.md"
    path.write_text(_synth_kb_markdown(entries), encoding="utf-8")
    return path


@pytest.fixture()
def synthetic_kb_en_only_file(tmp_path):
    """KB fixture with only EN entries -- SW participant gets empty selection (G207)."""
    entries = [
        {
            "id": "anc_en_only",
            "review_status": "pending",
            "language": "en",
            "topics": "anc, test",
            "min_week": None,
            "max_week": None,
            "text": "EN-only test entry for language eligibility test.",
        },
    ]
    path = tmp_path / "synthetic-kb-en-only.md"
    path.write_text(_synth_kb_markdown(entries), encoding="utf-8")
    return path


@pytest.fixture()
def synthetic_cards_file(tmp_path):
    """Standard cards: safe en, safe sw, food en, unsafe en, unsafe sw."""
    cards = [
        {
            "id": "anc_fixture_en",
            "review_status": "pending",
            "language": "en",
            "kb_ref": "anc_fixture_en",
            "topic_anchors": ["anc", "antenatal"],
            "triggers": [
                "What is ANC?",
                "Why should I go to antenatal care?",
                "Tell me about ANC",
            ],
            "answer": _SYNTH_CARD_ANSWER_SAFE_EN,
        },
        {
            "id": "food_fixture_en",
            "review_status": "pending",
            "language": "en",
            "kb_ref": "food_fixture_en",
            "topic_anchors": ["food", "eat"],
            "triggers": [
                "What food should I eat?",
                "What kinds of food during pregnancy?",
            ],
            "answer": "Eat a variety of foods including vegetables, fruit and whole grains.",
        },
        {
            "id": "anc_fixture_sw",
            "review_status": "pending",
            "language": "sw",
            "kb_ref": "anc_fixture_sw",
            "topic_anchors": ["anc", "uzazi"],
            "triggers": ["Nini ANC?", "Kwa nini niende kliniki ya uzazi?"],
            "answer": _SYNTH_CARD_ANSWER_SAFE_SW,
        },
        {
            # G206 EN CARD guard: answer has drug+dose -> guard blocks
            "id": "unsafe_card_en",
            "review_status": "pending",
            "language": "en",
            "kb_ref": "food_fixture_en",
            "topic_anchors": ["medication", "drug"],
            "triggers": ["What medication can I take for headaches?"],
            "answer": _SYNTH_CARD_ANSWER_UNSAFE_EN,
        },
        {
            # G206 SW CARD guard: answer has drug+dose -> guard blocks with SW referral
            "id": "unsafe_card_sw",
            "review_status": "pending",
            "language": "sw",
            "kb_ref": "anc_fixture_sw",
            "topic_anchors": ["dawa", "tembe"],
            "triggers": ["Niweze kutumia dawa gani kwa maumivu ya kichwa?"],
            "answer": _SYNTH_CARD_ANSWER_UNSAFE_SW,
        },
    ]
    path = tmp_path / "synthetic-cards.yaml"
    path.write_text(json.dumps(cards, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    return path


@pytest.fixture()
def synthetic_cards_en_only_file(tmp_path):
    """Cards fixture for the en-only KB fixture (G207 KB-language-empty test)."""
    cards = [
        {
            "id": "anc_en_only",
            "review_status": "pending",
            "language": "en",
            "kb_ref": "anc_en_only",
            "topic_anchors": ["anc", "antenatal"],
            "triggers": ["What is ANC?"],
            "answer": "EN-only safe answer.",
        },
    ]
    path = tmp_path / "synthetic-cards-en-only.yaml"
    path.write_text(json.dumps(cards, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Artifact freeze
# ---------------------------------------------------------------------------


def _freeze_artifact(pipeline: dict, label: str) -> str:
    """Hash the pipeline artifact, write to evidence. Returns sha256 hex."""
    canonical = json.dumps(pipeline, sort_keys=True, separators=(",", ":")).encode("utf-8")
    sha = hashlib.sha256(canonical).hexdigest()
    (EVIDENCE_DIR / f"{label}-{sha}-sha256.txt").write_text(sha + "\n", encoding="utf-8")
    (EVIDENCE_DIR / f"{label}-{sha}-pipeline.json").write_text(
        json.dumps(pipeline, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return sha


# ---------------------------------------------------------------------------
# Pipeline loader -- deepcopy frozen artifact, inject provider IDs, then load
# ---------------------------------------------------------------------------


def _load_pipeline(pipeline_data: dict, label: str):
    """Inject real provider IDs into frozen artifact, freeze, then load exactly that.

    Critical: does NOT call build_pipeline() again. Rebuilding would silently drop
    the staged include_pending=True content and use approved-only defaults. Instead
    we deepcopy the frozen artifact, inject only the LLM-node provider IDs (required
    by OCS to resolve the LlmProvider ORM row), hash that exact dict, then load it.
    """
    provider = LlmProviderFactory.create()
    provider_model = LlmProviderModelFactory.create()

    data = copy.deepcopy(pipeline_data)
    for node in data["data"]["nodes"]:
        params = node["data"]["params"]
        if params.get("name") == "llm":
            params["llm_provider_id"] = provider.id
            params["llm_provider_model_id"] = provider_model.id
            break

    # Hash AFTER provider injection -- this is the actual executed artifact identity.
    sha = _freeze_artifact(data, label)

    pipeline_obj = PipelineFactory.create()
    flow = FullFlow(**data["data"])
    layout, node_data = split_flow_data(flow)
    pipeline_obj.data = layout.model_dump()
    pipeline_obj.save()
    pipeline_obj.update_nodes_from_data(node_data)
    return pipeline_obj, sha


# ---------------------------------------------------------------------------
# Pipeline fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def pipeline_default(db):
    """Default approved-only pipeline -- all KB/cards pending -> referral always."""
    pl = build_pipeline(0, 0, include_pending=False)
    return _load_pipeline(pl, "default")


@pytest.fixture()
def pipeline_staging(db, monkeypatch, synthetic_kb_file, synthetic_cards_file):
    """Staging pipeline with synthetic eligible KB/cards (include_pending=True).

    Monkeypatches KB_FILE and CARDS_FILE so render functions read synthetic fixtures.
    review_status stays "pending" in the baked JSON; eligible=True runtime flag added
    by render_kb_node(include_pending=True). Real content never relabelled.
    """
    monkeypatch.setattr(_bp_module, "KB_FILE", synthetic_kb_file)
    monkeypatch.setattr(_bp_module, "CARDS_FILE", synthetic_cards_file)
    pl = build_pipeline(0, 0, include_pending=True)
    return _load_pipeline(pl, "staging")


@pytest.fixture()
def pipeline_staging_en_only(db, monkeypatch, synthetic_kb_en_only_file, synthetic_cards_en_only_file):
    """Staging pipeline with EN-only KB (G207: SW participant -> empty selection)."""
    monkeypatch.setattr(_bp_module, "KB_FILE", synthetic_kb_en_only_file)
    monkeypatch.setattr(_bp_module, "CARDS_FILE", synthetic_cards_en_only_file)
    pl = build_pipeline(0, 0, include_pending=True)
    return _load_pipeline(pl, "staging-en-only")


# ---------------------------------------------------------------------------
# FakeLlm fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def fake_llm_safe():
    """FakeLlm safe replies via pytest monkeypatch."""
    service = build_fake_llm_service(responses=[_LLM_REPLY_SAFE] * 20)
    service.llm.calls = []
    with pytest.MonkeyPatch().context() as mp:
        mp.setattr(
            "apps.service_providers.models.LlmProvider.get_llm_service",
            lambda *a, **kw: service,
        )
        yield service.llm


@pytest.fixture()
def fake_llm_safe_mock():
    """FakeLlm safe replies with mock.patch for call-count assertions."""
    from unittest import mock

    service = build_fake_llm_service(responses=[_LLM_REPLY_SAFE] * 20)
    service.llm.calls = []
    with mock.patch(
        "apps.service_providers.models.LlmProvider.get_llm_service",
        return_value=service,
    ) as patched:
        yield service.llm, patched


@pytest.fixture()
def fake_llm_unsafe():
    """FakeLlm that always returns a drug+dose reply (output_guard blocks it)."""
    from unittest import mock

    service = build_fake_llm_service(responses=[_LLM_REPLY_UNSAFE] * 10)
    service.llm.calls = []
    with mock.patch(
        "apps.service_providers.models.LlmProvider.get_llm_service",
        return_value=service,
    ) as patched:
        yield service.llm, patched


# ---------------------------------------------------------------------------
# Runner helper
# ---------------------------------------------------------------------------


def _make_runner(pipeline_obj):
    """Return (run_fn, session). run_fn(message, participant_data) -> output dict."""
    session = ExperimentSessionFactory.create()
    runnable = PipelineGraph.build_from_pipeline(pipeline_obj).build_runnable()
    config = {"configurable": {"repo": ORMRepository(session=session)}}

    def _run(message: str, participant_data: dict) -> dict:
        state = PipelineState(
            messages=[message],
            experiment_session=session,
            participant_data=participant_data,
        )
        return runnable.invoke(state, config=config)

    return _run, session


def _tags(output) -> list[str]:
    return [name for name, _category in output.get("output_message_tags", [])]


# ---------------------------------------------------------------------------
# Budget calibration helper (G208/G209)
# ---------------------------------------------------------------------------


def _calibrate_rendered_bytes(run_fn, participant: dict) -> tuple[int, str, str]:
    """Measure actual rendered system-prompt bytes from a live calibration run.

    Uses a CARD-eligible question so zero model calls are made.
    Returns (rendered_bytes, kb_section, llm_context).

    The boundary derivation is then:
        q_4000 = "A" * (4000 - rendered_bytes)   -> total == 4000 -> VALID
        q_4001 = "A" * (4001 - rendered_bytes)   -> total == 4001 -> OVER_BUDGET
    """
    question = "Nini ANC?" if participant["language_preference"] == "sw" else "Why should I go to antenatal care?"
    cal = run_fn(question, participant)
    assert "answer_route:CARD" in _tags(cal), "Calibration must use the zero-model CARD branch"
    kb_section = cal.get("temp_state", {}).get("kb_section", "")
    llm_context = cal.get("temp_state", {}).get("llm_context", "")
    lang = participant.get("language_preference", "en")

    template = Path(SYSTEM_PROMPT_FILE).read_text(encoding="utf-8")
    ts_lookup = {"kb_section": kb_section, "llm_context": llm_context}
    pd_lookup = {"language_preference": lang}

    def _do_sub(m: re.Match) -> str:
        ns, key = m.group(1), m.group(2)
        return (ts_lookup if ns == "temp_state" else pd_lookup).get(key, "")

    rendered = re.sub(r"\{(temp_state|participant_data)\.([^}]+)\}", _do_sub, template)
    return len(rendered.encode("utf-8")), kb_section, llm_context


# ---------------------------------------------------------------------------
# Baked JSON extractor helper (G204/G212)
# ---------------------------------------------------------------------------


def _extract_baked(node_code: str) -> dict:
    """Extract the baked data dict from an answer_match node source.

    The node source contains a line:
        baked_json = "<double-encoded JSON string>"
    ast.literal_eval extracts the inner string; json.loads parses the structure.
    Raises AssertionError if the line is absent; never swallows parse failures.
    """
    for line in node_code.splitlines():
        stripped = line.strip()
        if stripped.startswith("baked_json ="):
            rhs = stripped.split("baked_json =", 1)[1].strip()
            inner_json = ast.literal_eval(rhs)  # outer Python string literal
            return json.loads(inner_json)  # inner JSON
    raise AssertionError("baked_json assignment not found in answer_match node source")


# ---------------------------------------------------------------------------
# G201 -- Emergency precedence
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(("category", "language", "message"), DANGER_CASES)
def test_g201_emergency_registered_no_model(pipeline_default, fake_llm_safe, category, language, message):
    """G201: danger message from registered participant (en/sw) -> emergency, no model."""
    pipeline_obj, _ = pipeline_default
    run, _ = _make_runner(pipeline_obj)
    output = run(message, REGISTERED_EN | {"language_preference": language})
    reply = output["messages"][-1]
    prefix = "DHARURA:" if language == "sw" else "URGENT:"
    assert reply.startswith(prefix), f"G201: expected {prefix!r}, got: {reply[:50]!r}"
    assert "999" in reply and "922" in reply and "1199" in reply
    assert f"danger_sign:{category}" in _tags(output)
    assert "danger_router:EMERGENCY" in _tags(output)
    assert fake_llm_safe.calls == []


@pytest.mark.parametrize(("category", "language", "message"), DANGER_CASES[::3])
def test_g201_emergency_unregistered_no_onboarding_mutation(
    pipeline_default, fake_llm_safe, category, language, message
):
    """G201: danger message before registration -> emergency; onboarding state untouched."""
    pipeline_obj, _ = pipeline_default
    run, _ = _make_runner(pipeline_obj)
    for pre_state in [{}, {"language_choice_pending": True}]:
        fake_llm_safe.calls.clear()
        output = run(message, pre_state)
        assert output["messages"][-1].startswith("URGENT:")
        assert "registration:first_contact" not in _tags(output)
        assert fake_llm_safe.calls == []
        for key in ("welcome_sent", "consent_given", "registration_complete"):
            assert key not in output["participant_data"]


# ---------------------------------------------------------------------------
# G202 -- Onboarding/study + four full-multiturn default-noKB referral
# ---------------------------------------------------------------------------

FULL_FLOW_CASES = [
    (False, "en", "1", "YES", "Wanjiru", 20),
    (False, "sw", "Kiswahili", "Ndiyo", "Wanjiru", 20),
    (True, "en", "English", "yes", "Akinyi", 20),
    (True, "sw", "2", "ndiyo", "Akinyi", 20),
]


@pytest.mark.parametrize(
    ("is_study", "language", "choice_reply", "consent_reply", "name", "weeks"),
    FULL_FLOW_CASES,
)
def test_g202_full_multiturn_default_no_kb_exact_referral(
    pipeline_default,
    fake_llm_safe,
    is_study,
    language,
    choice_reply,
    consent_reply,
    name,
    weeks,
):
    """G202: full multi-turn registration; each turn correct; final -> exact referral."""
    pipeline_obj, _ = pipeline_default
    run, _ = _make_runner(pipeline_obj)
    seed = {"study_participant": True} if is_study else {}

    t1 = run("Hello", seed)
    assert t1["messages"][-1] == (
        "Please choose your language / Tafadhali chagua lugha yako:\n1. English\n2. Kiswahili"
    )
    assert fake_llm_safe.calls == []

    t2 = run(choice_reply, t1["participant_data"])
    assert t2["participant_data"]["language_preference"] == language
    assert t2["participant_data"]["welcome_sent"] is True
    assert t2["participant_data"]["consent_given"] is False
    expected_prefix = (
        ("Karibu kwenye" if language == "sw" else "Welcome to the Antenatal")
        if is_study
        else ("Karibu ZEYA!" if language == "sw" else "Welcome to ZEYA!")
    )
    assert t2["messages"][-1].startswith(expected_prefix)
    assert fake_llm_safe.calls == []

    t3 = run(consent_reply, t2["participant_data"])
    assert t3["participant_data"]["consent_given"] is True
    assert fake_llm_safe.calls == []

    t4 = run(name, t3["participant_data"])
    assert t4["participant_data"]["name_collected"] is True
    assert t4["participant_data"]["name"] == name
    assert fake_llm_safe.calls == []

    t5 = run(str(weeks), t4["participant_data"])
    assert t5["participant_data"]["registration_complete"] is True
    assert t5["participant_data"]["gestational_age_at_enrollment"] == weeks
    assert fake_llm_safe.calls == []

    question = "Ninapaswa kula nini?" if language == "sw" else "What should I eat?"
    t6 = run(question, t5["participant_data"])
    expected = SW_REFERRAL if language == "sw" else EN_REFERRAL
    assert t6["messages"][-1] == expected, f"G202: expected {language!r} referral, got: {t6['messages'][-1]!r}"
    assert "route:knowledge_referral" in _tags(t6)
    assert fake_llm_safe.calls == []


# ---------------------------------------------------------------------------
# G203 -- Default all-pending -> referral, zero model
# ---------------------------------------------------------------------------


def test_g203_default_registered_en_referral(pipeline_default, fake_llm_safe):
    """G203: default pipeline, fully registered EN participant -> EN referral, zero model."""
    pipeline_obj, _ = pipeline_default
    run, _ = _make_runner(pipeline_obj)
    output = run("What should I eat?", REGISTERED_EN)
    assert output["messages"][-1] == EN_REFERRAL
    assert "route:knowledge_referral" in _tags(output)
    assert fake_llm_safe.calls == []


def test_g203_default_registered_sw_referral(pipeline_default, fake_llm_safe):
    """G203: default pipeline, SW registered participant -> SW referral, zero model."""
    pipeline_obj, _ = pipeline_default
    run, _ = _make_runner(pipeline_obj)
    output = run("Ninapaswa kula nini?", REGISTERED_SW)
    assert output["messages"][-1] == SW_REFERRAL
    assert "route:knowledge_referral" in _tags(output)
    assert fake_llm_safe.calls == []


# ---------------------------------------------------------------------------
# G204 -- Staged eligible KB+card -> exact card text, baked JSON verified
# ---------------------------------------------------------------------------


def test_g204_staged_eligible_card_exact_text_en(pipeline_staging, fake_llm_safe):
    """G204 EN: staged card matched -> exact card answer, CARD/card-ID tags, zero model."""
    pipeline_obj, _ = pipeline_staging
    run, _ = _make_runner(pipeline_obj)
    output = run("Why should I go to antenatal care?", REGISTERED_EN)
    reply = output["messages"][-1]
    assert reply == _SYNTH_CARD_ANSWER_SAFE_EN, f"G204 EN: expected exact card answer, got: {reply!r}"
    tags = _tags(output)
    assert "answer_route:CARD" in tags, f"G204 EN: answer_route:CARD missing; {tags}"
    assert "answer_card:anc_fixture_en" in tags, f"G204 EN: card ID tag missing; {tags}"
    assert fake_llm_safe.calls == []


def test_g204_staged_eligible_card_sw(pipeline_staging, fake_llm_safe):
    """G204 SW: staged SW card -> exact SW answer, CARD tags, zero model."""
    pipeline_obj, _ = pipeline_staging
    run, _ = _make_runner(pipeline_obj)
    output = run("Nini ANC?", REGISTERED_SW)
    reply = output["messages"][-1]
    assert reply == _SYNTH_CARD_ANSWER_SAFE_SW, f"G204 SW: got: {reply!r}"
    tags = _tags(output)
    assert "answer_route:CARD" in tags
    assert "answer_card:anc_fixture_sw" in tags
    assert fake_llm_safe.calls == []


def test_g204_baked_json_pending_status_allow_pending(monkeypatch, synthetic_kb_file, synthetic_cards_file):
    """G204: baked answer_match source preserves pending review_status and allow_pending=True.

    Parsed via ast.literal_eval then json.loads -- no silent exception swallowing.
    """
    monkeypatch.setattr(_bp_module, "KB_FILE", synthetic_kb_file)
    monkeypatch.setattr(_bp_module, "CARDS_FILE", synthetic_cards_file)
    staging_pl = build_pipeline(0, 0, include_pending=True)
    am_code = next(
        n["data"]["params"]["code"]
        for n in staging_pl["data"]["nodes"]
        if n["data"]["params"].get("name") == "answer_match"
    )
    baked = _extract_baked(am_code)

    assert len(baked.get("cards", [])) > 0, "G204: baked cards list must be non-empty"
    assert baked.get("allow_pending") is True, (
        f"G204: allow_pending must be True in staging, got {baked.get('allow_pending')!r}"
    )
    for card in baked["cards"]:
        assert card.get("review_status") != "approved", (
            f"G204: card {card.get('id')!r} relabelled 'approved' in staging -- not permitted"
        )

    # Default build: allow_pending=False, cards list empty (all pending excluded)
    default_pl = build_pipeline(0, 0, include_pending=False)
    am_default = next(
        n["data"]["params"]["code"]
        for n in default_pl["data"]["nodes"]
        if n["data"]["params"].get("name") == "answer_match"
    )
    baked_default = _extract_baked(am_default)
    assert baked_default.get("allow_pending") is False, (
        f"G204: default allow_pending must be False, got {baked_default.get('allow_pending')!r}"
    )
    assert baked_default.get("cards", []) == [], "G204: default baked cards must be empty (all pending)"


# ---------------------------------------------------------------------------
# G205 -- Staged eligible KB + unsupported query -> ASK_AI -> one FakeLlm -> safe reply
# ---------------------------------------------------------------------------


def test_g205_ask_ai_one_llm_call_safe_reply_en(pipeline_staging, fake_llm_safe_mock):
    """G205 EN: KB available, no matching card -> ASK_AI -> budget VALID -> one LLM call."""
    llm, get_llm_service = fake_llm_safe_mock
    pipeline_obj, _ = pipeline_staging
    run, _ = _make_runner(pipeline_obj)
    output = run("What about vaccination schedules?", REGISTERED_EN)

    reply = output["messages"][-1]
    assert reply == _LLM_REPLY_SAFE, f"G205 EN: expected safe LLM reply, got: {reply!r}"
    tags = _tags(output)
    assert "answer_route:ASK_AI" in tags, f"G205 EN: ASK_AI tag missing; {tags}"
    assert len(llm.calls) == 1, f"G205 EN: expected 1 LLM call, got {len(llm.calls)}"
    get_llm_service.assert_called_once()
    # Privacy: participant name must not reach the model
    messages = llm.get_call_messages()[0]
    human = messages[-1].content
    if isinstance(human, list):
        human = "".join(b.get("text", "") for b in human if isinstance(b, dict))
    assert REGISTERED_EN["name"] not in human, "G205 EN: participant name must be sanitized from model input"


def test_g205_ask_ai_one_llm_call_safe_reply_sw(pipeline_staging, fake_llm_safe_mock):
    """G205 SW: KB available, no matching card -> ASK_AI -> one LLM call -> safe reply."""
    llm, _ = fake_llm_safe_mock
    pipeline_obj, _ = pipeline_staging
    run, _ = _make_runner(pipeline_obj)
    output = run("Chanjo gani ninahitaji?", REGISTERED_SW)
    assert output["messages"][-1] == _LLM_REPLY_SAFE
    assert "answer_route:ASK_AI" in _tags(output)
    assert len(llm.calls) == 1


# ---------------------------------------------------------------------------
# G206 -- Guard blocks unsafe CARD and unsafe LLM; en/sw parametrised; exact fallback
# ---------------------------------------------------------------------------

_G206_CARD_CASES = [
    (REGISTERED_EN, "What medication can I take for headaches?", GUARD_BLOCKED_EN),
    (REGISTERED_SW, "Niweze kutumia dawa gani kwa maumivu ya kichwa?", GUARD_BLOCKED_SW),
]

_G206_AI_CASES = [
    (REGISTERED_EN, "What about travel vaccinations?", GUARD_BLOCKED_EN),
    (REGISTERED_SW, "Chanjo gani ninahitaji kwa safari?", GUARD_BLOCKED_SW),
]


@pytest.mark.parametrize(("participant", "question", "expected_referral"), _G206_CARD_CASES)
def test_g206_guard_blocks_unsafe_card_exact_referral(
    pipeline_staging, fake_llm_safe, participant, question, expected_referral
):
    """G206 CARD: unsafe card answer (drug+dose) -> guard blocks -> exact policy referral."""
    pipeline_obj, _ = pipeline_staging
    run, _ = _make_runner(pipeline_obj)
    output = run(question, participant)
    tags = _tags(output)
    reply = output["messages"][-1]
    lang = participant["language_preference"]
    assert "route:guard_blocked" in tags, f"G206 CARD {lang}: guard_blocked missing; {tags}"
    assert reply == expected_referral, f"G206 CARD {lang}: expected {expected_referral!r}, got {reply!r}"
    assert fake_llm_safe.calls == [], "G206 CARD: LLM must not be called on CARD route"


@pytest.mark.parametrize(("participant", "question", "expected_referral"), _G206_AI_CASES)
def test_g206_guard_blocks_unsafe_ai_exact_referral(
    pipeline_staging, fake_llm_unsafe, participant, question, expected_referral
):
    """G206 AI: unsafe LLM reply -> guard blocks -> exact policy referral; LLM WAS called."""
    llm, _ = fake_llm_unsafe
    pipeline_obj, _ = pipeline_staging
    run, _ = _make_runner(pipeline_obj)
    output = run(question, participant)
    tags = _tags(output)
    reply = output["messages"][-1]
    lang = participant["language_preference"]
    assert "route:guard_blocked" in tags, f"G206 AI {lang}: guard_blocked missing; {tags}"
    assert reply == expected_referral, f"G206 AI {lang}: expected {expected_referral!r}, got {reply!r}"
    assert len(llm.calls) == 1, "G206 AI: LLM must be called; guard acts after delivery"


def test_g206_selection_vs_delivery_distinguished(pipeline_staging, fake_llm_safe):
    """G206: answer_route:CARD (selection) and route:guard_blocked (delivery) are separate tags."""
    pipeline_obj, _ = pipeline_staging
    run, _ = _make_runner(pipeline_obj)
    output = run("What medication can I take for headaches?", REGISTERED_EN)
    tags = _tags(output)
    assert "answer_route:CARD" in tags, f"G206: answer_route:CARD selection tag missing; {tags}"
    assert "route:guard_blocked" in tags, f"G206: route:guard_blocked delivery tag missing; {tags}"
    assert fake_llm_safe.calls == []


# ---------------------------------------------------------------------------
# G207 -- KB language and week eligibility via actual temp_state.kb_ids/kb_section
# ---------------------------------------------------------------------------


def test_g207_en_participant_kb_ids_en_only(pipeline_staging, fake_llm_safe):
    """G207: EN participant -> kb_ids contains EN entries, excludes SW entries."""
    pipeline_obj, _ = pipeline_staging
    run, _ = _make_runner(pipeline_obj)
    output = run("Why should I go to antenatal care?", REGISTERED_EN)
    kb_ids = output.get("temp_state", {}).get("kb_ids", [])
    assert "anc_fixture_en" in kb_ids, f"G207: anc_fixture_en missing; kb_ids={kb_ids}"
    assert "anc_fixture_sw" not in kb_ids, f"G207: SW entry must not appear in EN kb_ids={kb_ids}"
    assert output.get("temp_state", {}).get("kb_available") is True


def test_g207_sw_participant_kb_ids_sw_only(pipeline_staging, fake_llm_safe):
    """G207: SW participant -> kb_ids contains SW entries, excludes EN entries."""
    pipeline_obj, _ = pipeline_staging
    run, _ = _make_runner(pipeline_obj)
    output = run("Kwa nini niende kliniki ya uzazi?", REGISTERED_SW)
    kb_ids = output.get("temp_state", {}).get("kb_ids", [])
    assert "anc_fixture_sw" in kb_ids, f"G207: anc_fixture_sw missing; kb_ids={kb_ids}"
    assert "anc_fixture_en" not in kb_ids, f"G207: EN entry must not appear in SW kb_ids={kb_ids}"


def test_g207_week_bound_excluded_at_20w(pipeline_staging, fake_llm_safe):
    """G207: third_trim_fixture_en (min_week=28) excluded for 20-week participant."""
    pipeline_obj, _ = pipeline_staging
    run, _ = _make_runner(pipeline_obj)
    output = run("Why should I go to antenatal care?", REGISTERED_EN)
    kb_ids = output.get("temp_state", {}).get("kb_ids", [])
    assert "third_trim_fixture_en" not in kb_ids, (
        f"G207: third-trimester entry must be excluded at 20w; kb_ids={kb_ids}"
    )


def test_g207_week_bound_excluded_at_22w_elapsed(pipeline_staging, fake_llm_safe):
    """G207: enrolled 14 days ago at 20w -> current 22w; min_week=28 still excluded."""
    pipeline_obj, _ = pipeline_staging
    run, _ = _make_runner(pipeline_obj)
    output = run("Why should I go to antenatal care?", REGISTERED_22W)
    assert "22 weeks" in output["temp_state"]["llm_context"]
    kb_ids = output.get("temp_state", {}).get("kb_ids", [])
    assert "third_trim_fixture_en" not in kb_ids, (
        f"G207: third-trimester entry must be excluded at 22w; kb_ids={kb_ids}"
    )


def test_g207_week_bound_included_at_30w(pipeline_staging, fake_llm_safe):
    """G207: 30-week participant -> third_trim_fixture_en (min_week=28) included."""
    pipeline_obj, _ = pipeline_staging
    run, _ = _make_runner(pipeline_obj)
    output = run("Why should I go to antenatal care?", REGISTERED_THIRD_TRIM)
    kb_ids = output.get("temp_state", {}).get("kb_ids", [])
    assert "third_trim_fixture_en" in kb_ids, f"G207: third-trimester entry must be included at 30w; kb_ids={kb_ids}"


def test_g207_no_matching_language_kb_empty_referral(pipeline_staging_en_only, fake_llm_safe):
    """G207: SW participant with EN-only KB -> kb_available=False -> referral, zero model.

    Uses valid sw participant with an en-only KB fixture (kb-language-empty path).
    Does NOT use 'fr' participant (intercepted by registration node before KB selection).
    """
    pipeline_obj, _ = pipeline_staging_en_only
    run, _ = _make_runner(pipeline_obj)
    output = run("Kwa nini niende kliniki?", REGISTERED_SW)
    ts = output.get("temp_state", {})
    assert ts.get("kb_available") is False, "G207: SW participant with EN-only KB must have kb_available=False"
    assert ts.get("kb_ids", []) == [], "G207: kb_ids must be empty for SW participant with EN-only KB"
    assert "route:knowledge_referral" in _tags(output)
    assert output["messages"][-1] == SW_REFERRAL
    assert fake_llm_safe.calls == []


# ---------------------------------------------------------------------------
# G208 -- Actual UTF-8 byte count vs budget_bytes; history absent; PII sanitized
# ---------------------------------------------------------------------------


def test_g208_budget_bytes_match_actual_utf8_history_absent_pii_sanitized(pipeline_staging, fake_llm_safe_mock):
    """G208: budget_bytes from temp_state == actual UTF-8 bytes of system+human.

    Seeded ChatMessage history (global prior turns) absent from FakeLlm call because
    history_type=none. Name+phone PII in question sanitized by llm_input. Language
    interpolated (not raw placeholder). temperature=0.3 and no tools from artifact.
    """
    llm, _ = fake_llm_safe_mock
    pipeline_obj, _ = pipeline_staging
    run, session = _make_runner(pipeline_obj)

    # Seed prior ChatMessage history that history_type=none must NOT inject
    ChatMessage.objects.create(
        chat=session.chat,
        message_type=ChatMessageType.HUMAN,
        content="Previous question about ANC visits.",
    )
    ChatMessage.objects.create(
        chat=session.chat,
        message_type=ChatMessageType.AI,
        content="Previous AI response about ANC.",
    )

    # Question with phone number and name as PII sentinels
    pii_question = "My name is Akinyi and my phone is 0712345678. What about vaccination schedules?"
    output = run(pii_question, REGISTERED_EN)

    # G208: LLM must have been called (ASK_AI -> VALID budget -> LLM)
    assert len(llm.calls) == 1, f"G208: expected one LLM call; tags={_tags(output)}, reply={output['messages'][-1]!r}"
    messages = llm.get_call_messages()[0]

    # history_type=none -> exactly [system, human], no seeded prior turns
    assert len(messages) == 2, f"G208: history_type=none must produce exactly [system,human]; got {len(messages)}"

    system_content = messages[0].content
    human_content = messages[-1].content
    if isinstance(human_content, list):
        human_content = "".join(b.get("text", "") for b in human_content if isinstance(b, dict))

    # PII sanitized: phone and name must not reach model
    assert "0712345678" not in human_content, "G208: phone number must be sanitized from model human message"
    assert "Akinyi" not in human_content, "G208: participant name must be sanitized from model human message"

    # Language interpolated (not a raw placeholder)
    assert "{participant_data.language_preference}" not in system_content, (
        "G208: language_preference placeholder must be substituted, not literal"
    )
    assert "en" in system_content, "G208: 'en' language must appear in system prompt"

    # Exact byte parity
    actual_bytes = len(system_content.encode("utf-8")) + len(human_content.encode("utf-8"))
    recorded_bytes = output.get("temp_state", {}).get("budget_bytes")
    assert recorded_bytes is not None, "G208: temp_state.budget_bytes must be set"
    assert actual_bytes == recorded_bytes, (
        f"G208: actual UTF-8 bytes ({actual_bytes}) != budget_bytes ({recorded_bytes})"
    )

    # temperature=0.3 and no tools from the actual artifact definition
    llm_params = next(
        n["data"]["params"] for n in pipeline_obj.flow_data["nodes"] if n["data"]["params"].get("name") == "llm"
    )
    assert llm_params["llm_model_parameters"]["temperature"] == 0.3
    assert llm_params.get("history_type") == "none"
    assert llm_params.get("tools", []) == []


# ---------------------------------------------------------------------------
# G209 -- Live-calibrated budget boundary; nonASCII multibyte confirmation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("participant", [REGISTERED_EN, REGISTERED_SW], ids=["en", "sw"])
def test_g209_exact_4000_valid_one_llm_call(pipeline_staging, fake_llm_safe_mock, participant):
    """G209: live-calibrated 4000-byte question -> VALID -> one LLM call."""
    llm, _ = fake_llm_safe_mock
    pipeline_obj, _ = pipeline_staging
    run, _ = _make_runner(pipeline_obj)

    rendered_bytes, _, _ = _calibrate_rendered_bytes(run, participant)
    n = 4000 - rendered_bytes
    assert n > 0, f"G209: rendered_bytes={rendered_bytes} already exceeds 4000"
    q_4000 = "A" * n  # single giant token; no topic anchor -> ASK_AI

    llm.calls.clear()
    output = run(q_4000, participant)
    budget_bytes = output.get("temp_state", {}).get("budget_bytes")
    assert budget_bytes == 4000, f"G209: expected budget_bytes=4000, got {budget_bytes} (rendered={rendered_bytes})"
    assert output.get("temp_state", {}).get("budget_route") == "VALID", (
        f"G209: 4000 bytes must be VALID; route={output.get('temp_state', {}).get('budget_route')!r}"
    )
    assert len(llm.calls) == 1, "G209: exact 4000 bytes must admit one LLM start"
    messages = llm.get_call_messages()[0]
    human = messages[-1].content
    if isinstance(human, list):
        human = "".join(block.get("text", "") for block in human if isinstance(block, dict))
    assert len(messages[0].content.encode("utf-8")) + len(human.encode("utf-8")) == 4000


@pytest.mark.parametrize("participant", [REGISTERED_EN, REGISTERED_SW], ids=["en", "sw"])
def test_g209_exact_4001_over_budget_no_llm(pipeline_staging, fake_llm_safe_mock, participant):
    """G209: live-calibrated 4001-byte question -> OVER_BUDGET -> referral, no LLM."""
    llm, _ = fake_llm_safe_mock
    pipeline_obj, _ = pipeline_staging
    run, _ = _make_runner(pipeline_obj)

    rendered_bytes, _, _ = _calibrate_rendered_bytes(run, participant)
    n = 4001 - rendered_bytes
    assert n > 0, f"G209: rendered_bytes={rendered_bytes} already exceeds 4001"
    q_4001 = "A" * n

    llm.calls.clear()
    output = run(q_4001, participant)
    budget_bytes = output.get("temp_state", {}).get("budget_bytes")
    assert budget_bytes == 4001, f"G209: expected budget_bytes=4001, got {budget_bytes} (rendered={rendered_bytes})"
    assert output.get("temp_state", {}).get("budget_route") == "OVER_BUDGET"
    assert output["messages"][-1] == (SW_REFERRAL if participant["language_preference"] == "sw" else EN_REFERRAL)
    assert llm.calls == []


@pytest.mark.parametrize("participant", [REGISTERED_EN, REGISTERED_SW], ids=["en", "sw"])
def test_g209_non_ascii_multibyte_boundary(pipeline_staging, fake_llm_safe_mock, participant):
    """G209: UTF-8 byte count != character count; e-acute (U+00E9, 2 bytes) counted as 2.

    q = 'A'*(n-2) + 'e-acute': byte_count = n bytes; char_count = n-1.
    With n = 4001-rendered_bytes: total = rendered_bytes + n = 4001 -> OVER_BUDGET.
    """
    llm, _ = fake_llm_safe_mock
    pipeline_obj, _ = pipeline_staging
    run, _ = _make_runner(pipeline_obj)

    rendered_bytes, _, _ = _calibrate_rendered_bytes(run, participant)
    n = 4001 - rendered_bytes
    assert n >= 2, f"G209: rendered_bytes={rendered_bytes} leaves no room for nonASCII boundary"

    q_nonascii = "A" * (n - 2) + "\u00e9"  # e-acute = 2 UTF-8 bytes
    byte_count = len(q_nonascii.encode("utf-8"))
    char_count = len(q_nonascii)
    assert byte_count == n, f"G209: expected {n} bytes, got {byte_count}"
    assert char_count == n - 1, f"G209: char_count must be n-1={n - 1}, got {char_count}"

    llm.calls.clear()
    output = run(q_nonascii, participant)
    budget_bytes = output.get("temp_state", {}).get("budget_bytes")
    assert budget_bytes == 4001, f"G209: nonASCII: expected budget_bytes=4001, got {budget_bytes}"
    assert output.get("temp_state", {}).get("budget_route") == "OVER_BUDGET"
    assert output["messages"][-1] == (SW_REFERRAL if participant["language_preference"] == "sw" else EN_REFERRAL)
    assert llm.calls == []


# ---------------------------------------------------------------------------
# G210 -- Missing/invalid budget state -> OVER_BUDGET; isolated mutation; labelled
# ---------------------------------------------------------------------------

# Mutation: prompt_budget sets no budget_route at all.
# budget_router default_keyword_index=0 (OVER_BUDGET) therefore routes to
# knowledge_referral without reaching the LLM.
_G210_MUTATION_SOURCE = """\
def main(input, **kwargs):
    # G210 mutation: prompt_budget baked source does not set budget_route.
    # Proves budget_router default_keyword_index=0 routes OVER_BUDGET
    # (knowledge_referral) when no routing decision is emitted.
    return input
"""


def test_g210_blank_question_budget_failclosed(pipeline_staging, fake_llm_safe):
    """G210: blank question -> prompt_budget blank_question OVER_BUDGET -> referral, no LLM."""
    pipeline_obj, _ = pipeline_staging
    run, _ = _make_runner(pipeline_obj)
    for blank in ["", "   ", "\t"]:
        fake_llm_safe.calls.clear()
        output = run(blank, REGISTERED_EN)
        ts = output.get("temp_state", {})
        assert ts.get("budget_route") == "OVER_BUDGET", (
            f"G210: blank {blank!r} must route OVER_BUDGET; got {ts.get('budget_route')!r}"
        )
        assert ts.get("budget_reason") == "blank_question"
        assert output["messages"][-1] == EN_REFERRAL
        assert fake_llm_safe.calls == []


def test_g210_partial_registration_onboarding_control(pipeline_staging, fake_llm_safe):
    """G210 onboarding control: partial registration routes REPLY -> end before budget node.

    Not a budget failclosed proof -- registration_router exits at REPLY before kb_context.
    Labelled as onboarding control, not missing-budget evidence.
    """
    pipeline_obj, _ = pipeline_staging
    run, _ = _make_runner(pipeline_obj)
    partial = {
        "welcome_sent": True,
        "consent_given": True,
        "name": "Wanjiru",
        "name_collected": True,
        "language_preference": "en",
        "registration_complete": False,
    }
    output = run("What should I eat?", partial)
    assert fake_llm_safe.calls == []
    assert output.get("temp_state", {}).get("budget_route") is None, (
        "G210 onboarding control: budget node must not be reached by partial participant"
    )


def test_g210_mutated_budget_no_route_router_default_over_budget(
    db, monkeypatch, synthetic_kb_file, synthetic_cards_file, fake_llm_safe
):
    """G210 mutation: blanked budget_route -> router default=OVER_BUDGET -> referral.

    Isolated synthetic artifact. prompt_budget node source replaced with mutation
    that returns without setting budget_route. budget_router default_keyword_index=0
    (OVER_BUDGET) is exercised. Mutation explicitly labelled; original source preserved.
    """
    monkeypatch.setattr(_bp_module, "KB_FILE", synthetic_kb_file)
    monkeypatch.setattr(_bp_module, "CARDS_FILE", synthetic_cards_file)
    staged = build_pipeline(0, 0, include_pending=True)

    mutated = copy.deepcopy(staged)
    patched = False
    for node in mutated["data"]["nodes"]:
        if node["data"]["params"].get("name") == "prompt_budget":
            node["data"]["params"]["code"] = _G210_MUTATION_SOURCE
            patched = True
            break
    assert patched, "G210: prompt_budget node not found in staged pipeline"

    mutated_obj, _ = _load_pipeline(mutated, "g210-mutation")
    run_mut, _ = _make_runner(mutated_obj)
    output = run_mut("What about vaccination schedules?", REGISTERED_EN)

    # budget_route not set -> router default -> OVER_BUDGET -> referral
    ts = output.get("temp_state", {})
    assert ts.get("budget_route") is None, (
        f"G210: mutated node must not set budget_route; got {ts.get('budget_route')!r}"
    )
    assert output["messages"][-1] == EN_REFERRAL, (
        f"G210: router default must route to referral; got {output['messages'][-1]!r}"
    )
    assert fake_llm_safe.calls == [], "G210: mutated path must not reach LLM"


# ---------------------------------------------------------------------------
# G211 -- One-pass rendering; no mutation; no PII in budget-node tags
# ---------------------------------------------------------------------------


def test_g211_placeholder_in_kb_not_re_expanded(db, monkeypatch, synthetic_cards_file, fake_llm_safe_mock, tmp_path):
    """G211: KB text with placeholder-like content is not recursively expanded.

    If kb_section contains '{temp_state.kb_section}', one-pass re.sub leaves it
    literally in the rendered system prompt. LLM-call precondition is mandatory;
    skip guard makes vacuous success impossible.
    """
    llm, _ = fake_llm_safe_mock

    poison_text = "Important: {temp_state.kb_section} should not reappear."
    entries = [
        {
            "id": "poison_en",
            "review_status": "pending",
            "language": "en",
            "topics": "test",
            "min_week": None,
            "max_week": None,
            "text": poison_text,
        }
    ]
    poison_kb = tmp_path / "poison-kb.md"
    poison_kb.write_text(_synth_kb_markdown(entries), encoding="utf-8")

    poison_cards = [
        {
            "id": "dummy_en",
            "review_status": "pending",
            "language": "en",
            "kb_ref": "poison_en",
            "topic_anchors": ["dummy"],
            "triggers": ["dummy question"],
            "answer": "Dummy safe answer.",
        }
    ]
    poison_cards_file = tmp_path / "poison-cards.yaml"
    poison_cards_file.write_text(json.dumps(poison_cards, indent=2) + "\n", encoding="utf-8")

    monkeypatch.setattr(_bp_module, "KB_FILE", poison_kb)
    monkeypatch.setattr(_bp_module, "CARDS_FILE", poison_cards_file)
    poison_pl = build_pipeline(0, 0, include_pending=True)
    poison_obj, _ = _load_pipeline(poison_pl, "g211-poison")
    run_p, _ = _make_runner(poison_obj)

    output = run_p("What about vaccination schedules?", REGISTERED_EN)

    # Mandatory precondition: LLM must have been called (ASK_AI path)
    assert len(llm.calls) == 1, (
        f"G211: LLM must be called (ASK_AI); tags={_tags(output)}, reply={output['messages'][-1]!r}"
    )

    messages = llm.get_call_messages()[0]
    system_content = messages[0].content

    # One-pass: literal placeholder text must appear exactly once
    assert poison_text in system_content, "G211: placeholder-like KB text must appear literally in system prompt"
    occurrences = system_content.count("{temp_state.kb_section}")
    assert occurrences == 1, f"G211: placeholder-like text must appear exactly once; found {occurrences}"

    # Byte parity: system + human == budget_bytes
    human_content = messages[-1].content
    if isinstance(human_content, list):
        human_content = "".join(b.get("text", "") for b in human_content if isinstance(b, dict))
    actual_bytes = len(system_content.encode("utf-8")) + len(human_content.encode("utf-8"))
    recorded = output.get("temp_state", {}).get("budget_bytes")
    assert recorded is not None, "G211: budget_bytes must be set"
    assert actual_bytes == recorded, f"G211: actual bytes ({actual_bytes}) != budget_bytes ({recorded})"


def test_g211_no_pii_in_budget_node_tags(pipeline_staging, fake_llm_safe):
    """G211: prompt_budget must not emit question text or PII as message tags."""
    pipeline_obj, _ = pipeline_staging
    run, _ = _make_runner(pipeline_obj)
    question = "What vaccination schedules should I follow?"
    output = run(question, REGISTERED_EN)
    for tag in _tags(output):
        assert question not in tag, f"G211: question text leaked to tag {tag!r}"
        assert REGISTERED_EN["name"] not in tag, f"G211: participant name leaked to tag {tag!r}"


def test_g211_budget_node_no_participant_data_mutation(pipeline_staging, fake_llm_safe):
    """G211: participant_data must not be mutated by prompt_budget node."""
    pipeline_obj, _ = pipeline_staging
    run, _ = _make_runner(pipeline_obj)
    before = dict(REGISTERED_EN)
    output = run("What vaccination schedules?", REGISTERED_EN)
    for key, val in before.items():
        assert output.get("participant_data", {}).get(key) == val, (
            f"G211: participant_data[{key!r}] mutated by budget node"
        )


# ---------------------------------------------------------------------------
# G212 -- Source drift; baked JSON verified; no content relabelling
# ---------------------------------------------------------------------------


def test_g212_default_and_staging_artifacts_differ(monkeypatch, synthetic_kb_file, synthetic_cards_file):
    """G212: default and staging pipeline artifacts have different node sources."""
    default_pl = build_pipeline(0, 0, include_pending=False)
    default_sha = _freeze_artifact(default_pl, "g212-default")

    monkeypatch.setattr(_bp_module, "KB_FILE", synthetic_kb_file)
    monkeypatch.setattr(_bp_module, "CARDS_FILE", synthetic_cards_file)
    staging_pl = build_pipeline(0, 0, include_pending=True)
    staging_sha = _freeze_artifact(staging_pl, "g212-staging")

    assert default_sha != staging_sha, "G212: default and staging builds must produce different artifacts"

    def _code(pl, name):
        return next(n["data"]["params"]["code"] for n in pl["data"]["nodes"] if n["data"]["params"].get("name") == name)

    assert _code(default_pl, "kb_context") != _code(staging_pl, "kb_context")
    assert _code(default_pl, "answer_match") != _code(staging_pl, "answer_match")


def test_g212_staging_does_not_relabel_content(monkeypatch, synthetic_kb_file, synthetic_cards_file):
    """G212: staging build must not set review_status='approved' in baked JSON."""
    monkeypatch.setattr(_bp_module, "KB_FILE", synthetic_kb_file)
    monkeypatch.setattr(_bp_module, "CARDS_FILE", synthetic_cards_file)
    staging_pl = build_pipeline(0, 0, include_pending=True)
    am_code = next(
        n["data"]["params"]["code"]
        for n in staging_pl["data"]["nodes"]
        if n["data"]["params"].get("name") == "answer_match"
    )
    baked = _extract_baked(am_code)
    for card in baked.get("cards", []):
        assert card.get("review_status") != "approved", (
            f"G212: card {card.get('id')!r} must not be relabelled 'approved'"
        )
    assert baked.get("allow_pending") is True


def test_g212_default_drift_check_passes(monkeypatch):
    """G212: regenerated default artifact passes find_drift(include_pending=False)."""
    default_pl = build_pipeline(0, 0, include_pending=False)
    live = {"pipeline": {"data": default_pl["data"]}}
    assert find_drift(live, include_pending=False) == [], "G212: default artifact must pass default drift check"


def test_g212_default_drift_check_rejects_staging(monkeypatch, synthetic_kb_file, synthetic_cards_file):
    """G212: default drift check detects staging artifact as drift."""
    monkeypatch.setattr(_bp_module, "KB_FILE", synthetic_kb_file)
    monkeypatch.setattr(_bp_module, "CARDS_FILE", synthetic_cards_file)
    staging_pl = build_pipeline(0, 0, include_pending=True)
    live = {"pipeline": {"data": staging_pl["data"]}}
    drift = find_drift(live, include_pending=False)
    assert len(drift) > 0, "G212: default drift check must detect staging artifact as different"


def test_g212_staging_drift_check_accepts_staging(monkeypatch, synthetic_kb_file, synthetic_cards_file):
    """G212: staging drift check accepts staging artifact."""
    monkeypatch.setattr(_bp_module, "KB_FILE", synthetic_kb_file)
    monkeypatch.setattr(_bp_module, "CARDS_FILE", synthetic_cards_file)
    staging_pl = build_pipeline(0, 0, include_pending=True)
    live = {"pipeline": {"data": staging_pl["data"]}}
    assert find_drift(live, include_pending=True) == [], "G212: staging drift check must accept staging artifact"
