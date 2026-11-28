import copy
import json

import pytest

from ocs.build_pipeline import build_pipeline
from ocs.check_drift import find_drift, main


def _live(llm_provider_id=7, llm_provider_model_id=31):
    """Shape of GET /a/<team>/pipelines/data/<id>/."""
    pipeline = build_pipeline(llm_provider_id, llm_provider_model_id)
    return {"pipeline": {"id": 12, "name": pipeline["name"], "data": pipeline["data"], "errors": {}}}


def _node(document, name):
    return next(n for n in document["pipeline"]["data"]["nodes"] if n["data"]["params"]["name"] == name)


def test_deployed_copy_matches():
    assert find_drift(_live()) == []
    assert find_drift(_live(), llm_provider_id=7, llm_provider_model_id=31) == []


def test_detects_model_switched_in_ui():
    live = _live(llm_provider_id=7, llm_provider_model_id=44)

    assert find_drift(live, llm_provider_id=7, llm_provider_model_id=31) == [
        "llm: 'llm_provider_model_id' is 44, expected 31"
    ]


def test_detects_provider_switched_in_ui():
    live = _live(llm_provider_id=3, llm_provider_model_id=31)

    assert find_drift(live, llm_provider_id=7, llm_provider_model_id=31) == ["llm: 'llm_provider_id' is 3, expected 7"]


def test_ignores_positions_labels_and_provider_ids():
    live = _live(llm_provider_id=99, llm_provider_model_id=100)
    for node in live["pipeline"]["data"]["nodes"]:
        node["position"] = {"x": 1, "y": 2}
        node["data"]["label"] = "renamed in UI"

    assert find_drift(live) == []


def test_ignores_defaults_added_by_ocs():
    live = _live()
    _node(live, "danger_gate")["data"]["params"]["tag_output_message"] = False

    assert find_drift(live) == []


def test_detects_edited_gate_code():
    live = _live()
    gate = _node(live, "danger_gate")["data"]["params"]
    gate["code"] = gate["code"].replace(r"\bchills\b", r"\bchill\b")

    assert find_drift(live) == ["danger_gate: 'code' differs from the repository"]


def test_detects_changed_router_default():
    live = _live()
    _node(live, "danger_router")["data"]["params"]["default_keyword_index"] = 1

    assert find_drift(live) == ["danger_router: 'default_keyword_index' differs from the repository"]


def test_detects_llm_added_to_emergency_branch():
    live = _live()
    flow = live["pipeline"]["data"]
    extra = copy.deepcopy(_node(live, "llm"))
    extra["id"] = extra["data"]["id"] = "extra_llm"
    extra["data"]["params"]["name"] = "emergency_followup"
    flow["nodes"].append(extra)
    flow["edges"] = [e for e in flow["edges"] if e["source"] != "emergency_response"]
    flow["edges"] += [
        {"id": "a", "source": "emergency_response", "target": "extra_llm", "sourceHandle": "output"},
        {"id": "b", "source": "extra_llm", "target": "end", "sourceHandle": "output"},
    ]

    problems = find_drift(live)

    assert "unexpected node: emergency_followup (LLMResponseWithPrompt)" in problems
    assert "missing edge: emergency_response [output] -> end" in problems
    assert "unexpected edge: emergency_response [output] -> emergency_followup" in problems


def test_detects_edited_prompt_and_temperature():
    live = _live()
    params = _node(live, "llm")["data"]["params"]
    params["prompt"] += "\nAlso recommend herbal remedies."
    params["llm_model_parameters"] = {"temperature": 0.2}

    assert sorted(find_drift(live)) == [
        "llm: 'llm_model_parameters' differs from the repository",
        "llm: 'prompt' differs from the repository",
    ]


@pytest.mark.parametrize(("mutate", "code"), [(False, 0), (True, 1)])
def test_cli_exit_code(tmp_path, capsys, mutate, code):
    live = _live()
    if mutate:
        _node(live, "emergency_response")["data"]["params"]["code"] += "\n# edited"
    path = tmp_path / "live.json"
    path.write_text(json.dumps(live))

    assert main([str(path), "--llm-provider-id", "7", "--llm-provider-model-id", "31"]) == code


def test_cli_requires_expected_model(tmp_path):
    path = tmp_path / "live.json"
    path.write_text(json.dumps(_live()))

    with pytest.raises(SystemExit):
        main([str(path)])


def _add_generic_null_instance_ids(live):
    """Mimic hosted OCS: it enriches every node's params with the generic
    llm_provider_id / llm_provider_model_id keys, set to null, even on nodes
    whose repository definition has no such param (Start/End/Code/Router)."""
    for node in live["pipeline"]["data"]["nodes"]:
        node["data"]["params"].setdefault("llm_provider_id", None)
        node["data"]["params"].setdefault("llm_provider_model_id", None)
    return live


def test_ignores_hosted_null_instance_ids_on_non_llm_nodes():
    """Hosted OCS exports generic null provider/model keys on every node, not just
    the LLM node. The strict instance-id check must not flag those as drift."""
    live = _add_generic_null_instance_ids(_live(llm_provider_id=7, llm_provider_model_id=31))

    assert find_drift(live, llm_provider_id=7, llm_provider_model_id=31) == []


def test_detects_llm_provider_id_set_to_null():
    live = _live(llm_provider_id=7, llm_provider_model_id=31)
    _node(live, "llm")["data"]["params"]["llm_provider_id"] = None

    assert find_drift(live, llm_provider_id=7, llm_provider_model_id=31) == [
        "llm: 'llm_provider_id' is None, expected 7"
    ]


def test_detects_llm_provider_model_id_missing_entirely():
    live = _live(llm_provider_id=7, llm_provider_model_id=31)
    del _node(live, "llm")["data"]["params"]["llm_provider_model_id"]

    assert find_drift(live, llm_provider_id=7, llm_provider_model_id=31) == [
        "llm: 'llm_provider_model_id' is None, expected 31"
    ]


# ---------------------------------------------------------------------------
# Staging flag tests
# ---------------------------------------------------------------------------


def test_staging_build_has_same_graph_structure_as_default():
    """Staging and production builds share the same graph; only node code may differ."""
    default = build_pipeline(0, 0, include_pending=False)
    staging = build_pipeline(0, 0, include_pending=True)

    # Same edge set (same graph shape regardless of content)
    default_edge_ids = {e["id"] for e in default["data"]["edges"]}
    staging_edge_ids = {e["id"] for e in staging["data"]["edges"]}
    assert default_edge_ids == staging_edge_ids, "Staging and production must share the same graph edges"

    # Same node set by ID
    default_node_ids = {n["id"] for n in default["data"]["nodes"]}
    staging_node_ids = {n["id"] for n in staging["data"]["nodes"]}
    assert default_node_ids == staging_node_ids


def test_staging_build_has_same_non_empty_kb_and_distinct_card_sources():
    """With all-approved starter content, staging and production KB nodes are identical.

    With all 10 KB entries and cards approved:
    - Default build: KB_JSON has 10 approved entries; answer_match bakes allow_pending=False.
    - Staging build: KB_JSON has 10 approved entries (same); answer_match bakes allow_pending=True.
    The KB node code is identical (no pending entries to additionally surface).
    The answer_match node still differs via the allow_pending flag.
    """
    default = build_pipeline(0, 0, include_pending=False)
    staging = build_pipeline(0, 0, include_pending=True)

    def _params(build, name):
        return next(n["data"]["params"] for n in build["data"]["nodes"] if n["data"]["params"]["name"] == name)

    default_kb_code = _params(default, "kb_context")["code"]
    staging_kb_code = _params(staging, "kb_context")["code"]
    # KB nodes are identical: all entries approved, no pending to additionally surface.
    assert default_kb_code == staging_kb_code, (
        "KB node code must be identical between staging and production when all entries are approved"
    )
    # KB must be non-empty in both builds (10 approved entries).
    assert "KB_JSON" in default_kb_code, "Production KB node must contain injected KB_JSON"
    assert "anc_purpose" in default_kb_code, "Production KB node must contain at least one approved entry"

    default_am_code = _params(default, "answer_match")["code"]
    staging_am_code = _params(staging, "answer_match")["code"]
    # answer_match differs: allow_pending flag distinguishes staging from production.
    assert default_am_code != staging_am_code, (
        "Answer match source must still differ (allow_pending flag) between staging and production builds"
    )


def test_staging_drift_check_accepts_staging_build():
    """find_drift(include_pending=True) finds no drift against a staging deployment."""
    staging_pipeline = build_pipeline(7, 31, include_pending=True)
    staging_live = {
        "pipeline": {"id": 12, "name": staging_pipeline["name"], "data": staging_pipeline["data"], "errors": {}}
    }
    assert find_drift(staging_live, llm_provider_id=7, llm_provider_model_id=31, include_pending=True) == []


def test_staging_pipeline_drifts_from_default_check():
    """find_drift(include_pending=False) reports drift against a staging deployment.

    A staging pipeline has different node sources (pending content included).
    The default approved-only drift check correctly detects this as drift,
    preventing a staging pipeline from being accepted as a production deployment.
    """
    staging_pipeline = build_pipeline(7, 31, include_pending=True)
    staging_live = {
        "pipeline": {"id": 12, "name": staging_pipeline["name"], "data": staging_pipeline["data"], "errors": {}}
    }
    drift = find_drift(staging_live, llm_provider_id=7, llm_provider_model_id=31, include_pending=False)
    assert len(drift) > 0, (
        "Staging pipeline must differ from production build; default drift check must detect the difference"
    )


def test_staging_flag_cli(tmp_path):
    """check_drift CLI --include-pending flag works and matches staging build."""
    staging_pipeline = build_pipeline(7, 31, include_pending=True)
    staged_live = {
        "pipeline": {"id": 12, "name": staging_pipeline["name"], "data": staging_pipeline["data"], "errors": {}}
    }
    path = tmp_path / "staging_live.json"
    path.write_text(json.dumps(staged_live))
    # Staging check: no drift expected
    assert main([str(path), "--llm-provider-id", "7", "--llm-provider-model-id", "31", "--include-pending"]) == 0


# ---------------------------------------------------------------------------
# Rules-only build (#26): no LLM node, ASK_AI gets a fixed reply
# ---------------------------------------------------------------------------


def _rules_only_live():
    pipeline = build_pipeline(0, 0, rules_only=True)
    return {"pipeline": {"id": 12, "name": pipeline["name"], "data": pipeline["data"], "errors": {}}}


def test_rules_only_deployed_copy_matches():
    assert find_drift(_rules_only_live(), rules_only=True) == []


def test_rules_only_ignores_hosted_null_instance_ids():
    assert find_drift(_add_generic_null_instance_ids(_rules_only_live()), rules_only=True) == []


def test_rules_only_live_checked_as_normal_names_the_cause_first():
    drift = find_drift(_rules_only_live(), llm_provider_id=7, llm_provider_model_id=31)

    assert drift[0] == "the live pipeline is the rules-only build; check it with --rules-only"
    assert "missing node: llm" in drift
    assert "unexpected node: rules_only_reply (CodeNode)" in drift


def test_normal_live_checked_as_rules_only_names_the_cause_first():
    drift = find_drift(_live(), rules_only=True)

    assert drift[0] == "the live pipeline is not the rules-only build; check it without --rules-only"
    assert "unexpected node: llm (LLMResponseWithPrompt)" in drift


def test_rules_only_detects_edited_reply_code():
    live = _rules_only_live()
    _node(live, "rules_only_reply")["data"]["params"]["code"] += "\n# edited"

    assert find_drift(live, rules_only=True) == ["rules_only_reply: 'code' differs from the repository"]


def test_rules_only_detects_llm_wired_back_in():
    live = _rules_only_live()
    data = live["pipeline"]["data"]
    llm = next(n for n in build_pipeline(7, 31)["data"]["nodes"] if n["id"] == "llm")
    data["nodes"].append(llm)
    for edge in data["edges"]:
        if edge["source"] == "answer_router" and edge["sourceHandle"] == "output_1":
            edge["target"] = "llm"

    assert find_drift(live, rules_only=True) == [
        "unexpected node: llm (LLMResponseWithPrompt)",
        "missing edge: answer_router [output_1] -> rules_only_reply",
        "unexpected edge: answer_router [output_1] -> llm",
    ]


def test_rules_only_cli_takes_no_provider_ids(tmp_path):
    path = tmp_path / "live.json"
    path.write_text(json.dumps(_rules_only_live()))

    assert main([str(path), "--rules-only"]) == 0
    with pytest.raises(SystemExit):
        main([str(path), "--rules-only", "--llm-provider-id", "7", "--llm-provider-model-id", "31"])


def test_rules_only_cli_reports_normal_live_as_drift(tmp_path, capsys):
    path = tmp_path / "live.json"
    path.write_text(json.dumps(_live()))

    assert main([str(path), "--rules-only"]) == 1
    assert "check it without --rules-only" in capsys.readouterr().err


def test_cli_requires_both_provider_ids_without_rules_only(tmp_path):
    path = tmp_path / "live.json"
    path.write_text(json.dumps(_live()))

    with pytest.raises(SystemExit):
        main([str(path), "--llm-provider-id", "7"])
