"""
Build the Zeya Open Chat Studio pipeline from the sources in this directory.

    python -m ocs.build_pipeline --write
        Regenerate ocs/pipeline/zeya_pipeline.json (provider ids set to 0) for review.

    python -m ocs.build_pipeline --llm-provider-id 7 --llm-provider-model-id 31 > out.json
        Build a deployable copy with the instance's Gemini provider and model ids.

    python -m ocs.build_pipeline --write --include-pending
        Regenerate with pending KB/card content eligible (synthetic staging ONLY).
        Never used for production deployment; pending review_status is preserved.

The output is OCS FlowPipelineData (apps/pipelines/flow.py), the body accepted by
POST /a/<team>/pipelines/data/<pk>/. See docs/ocs-migration.md for the shape.

Full graph (registered path):
    danger_gate -> danger_router
        EMERGENCY -> emergency_response -> end
        SAFE -> access_gate -> access_router
            NOT_TESTER -> danger_question_line -> end   (fixed reply, no AI)
            MEDIA      -> danger_question_line -> end   (fixed reply, no AI)
            OK         -> registration -> registration_router
            REPLY -> danger_question_line -> end
            REGISTERED -> kb_context -> kb_router
                FALSE (no approved KB) -> knowledge_referral -> danger_question_line -> end
                TRUE  (KB available)   -> answer_match -> answer_router
                    CARD   -> output_guard -> attach_explainer -> danger_question_line -> end
                    ASK_AI -> llm_input -> prompt_budget -> budget_router
                        OVER_BUDGET -> knowledge_referral -> danger_question_line -> end
                        VALID       -> llm -> output_guard -> attach_explainer -> danger_question_line -> end

Default approved-only build:
    All five English and five Kiswahili KB entries and answer cards are approved.
    load_knowledge and load_answer_cards return 10 entries/cards.  kb_context bakes
    KB_JSON with all 10 entries; the node sets kb_available=True at runtime when the
    participant language matches available entries; kb_router routes TRUE to answer_match.

Staging flag (--include-pending):
    Pending entries are eligible with an explicit runtime flag; pending review_status
    is never changed to 'approved'.  Use only for synthetic test fixtures.
"""

import argparse
import json
import sys
from pathlib import Path

from ocs.answer_cards import load_answer_cards, render_answer_match
from ocs.knowledge import load_knowledge, render_kb_node
from ocs.output_policy import load_output_policy, render_output_guard
from ocs.prompt_budget import render_prompt_budget_node

OCS_DIR = Path(__file__).resolve().parent
NODES_DIR = OCS_DIR / "nodes"
SYSTEM_PROMPT_FILE = OCS_DIR / "prompts" / "system_prompt.txt"
COMMITTED_PIPELINE = OCS_DIR / "pipeline" / "zeya_pipeline.json"
# Rules-only build (#26): no AI node. Publish it as an OCS version if the AI provider fails.
COMMITTED_RULES_ONLY_PIPELINE = OCS_DIR / "pipeline" / "zeya_pipeline_rules_only.json"

REPO_ROOT = OCS_DIR.parent
KB_FILE = REPO_ROOT / "docs" / "zeya-knowledge-base.md"
CARDS_FILE = REPO_ROOT / "docs" / "answer-cards.yaml"
POLICY_FILE = REPO_ROOT / "docs" / "output-policy.json"

PIPELINE_NAME = "Zeya antenatal education"


def _node(node_id: str, node_type: str, params: dict, x: int, y: int, flow_type: str = "pipelineNode") -> dict:
    return {
        "id": node_id,
        "type": flow_type,
        "position": {"x": x, "y": y},
        "data": {"id": node_id, "type": node_type, "label": "", "params": params},
    }


def _edge(source: str, target: str, source_handle: str = "output") -> dict:
    return {
        "id": f"{source}:{source_handle}->{target}",
        "source": source,
        "target": target,
        "sourceHandle": source_handle,
        "targetHandle": "input",
    }


def _code(name: str) -> str:
    return (NODES_DIR / f"{name}.py").read_text()


def build_pipeline(
    llm_provider_id: int, llm_provider_model_id: int, include_pending: bool = False, rules_only: bool = False
) -> dict:
    """Build the full pipeline.

    include_pending=False (default / production): only approved KB entries and
        answer cards are eligible.  With the approved bilingual starter content
        this produces kb_available=True at runtime for participants whose language
        matches the 10 approved entries (5 en + 5 sw).
    include_pending=True (synthetic staging ONLY): pending entries carry an
        explicit eligible=True runtime flag without changing their review_status.
        Never deployed to production; used only for integration test fixtures.
    """
    # Render knowledge-based nodes from their respective data sources.
    # check_drift compares the rendered code from these calls against the live
    # deployed code, ensuring rendered injected data matches the current state of
    # the data files.
    kb_entries = load_knowledge(KB_FILE, include_pending=include_pending)
    kb_node_source = render_kb_node(kb_entries, include_pending=include_pending)

    cards = load_answer_cards(CARDS_FILE, include_pending=include_pending)
    answer_match_source = render_answer_match(cards, include_pending=include_pending)

    policy = load_output_policy(POLICY_FILE)
    guard_source = render_output_guard(policy)

    prompt_budget_source = render_prompt_budget_node(SYSTEM_PROMPT_FILE.read_text())

    nodes = [
        _node("start", "StartNode", {"name": "start"}, 0, 200, flow_type="startNode"),
        _node("danger_gate", "CodeNode", {"name": "danger_gate", "code": _code("danger_gate")}, 300, 200),
        _node(
            "danger_router",
            "StaticRouterNode",
            {
                "name": "danger_router",
                "data_source": "temp_state",
                "route_key": "danger_route",
                # output_0 = EMERGENCY, output_1 = SAFE. EMERGENCY is the default route.
                "keywords": ["EMERGENCY", "SAFE"],
                "default_keyword_index": 0,
                "tag_output_message": True,
            },
            600,
            200,
        ),
        _node(
            "emergency_response",
            "CodeNode",
            {"name": "emergency_response", "code": _code("emergency_response")},
            900,
            0,
        ),
        _node("access_gate", "CodeNode", {"name": "access_gate", "code": _code("access_gate")}, 750, 350),
        _node(
            "access_router",
            "StaticRouterNode",
            {
                "name": "access_router",
                "data_source": "temp_state",
                "route_key": "access_route",
                # output_0 = NOT_TESTER, output_1 = MEDIA, output_2 = OK.
                # NOT_TESTER is the default: a missing or unexpected value never reaches the AI.
                "keywords": ["NOT_TESTER", "MEDIA", "OK"],
                "default_keyword_index": 0,
                "tag_output_message": False,
            },
            825,
            350,
        ),
        _node("registration", "CodeNode", {"name": "registration", "code": _code("registration")}, 900, 350),
        _node(
            "registration_router",
            "StaticRouterNode",
            {
                "name": "registration_router",
                "data_source": "temp_state",
                "route_key": "registration_route",
                # output_0 = REPLY, output_1 = REGISTERED. REPLY is the default route.
                "keywords": ["REPLY", "REGISTERED"],
                "default_keyword_index": 0,
                "tag_output_message": False,
            },
            1200,
            350,
        ),
        # --- Grounded knowledge path ---
        _node("kb_context", "CodeNode", {"name": "kb_context", "code": kb_node_source}, 1500, 350),
        _node(
            "kb_router",
            "StaticRouterNode",
            {
                "name": "kb_router",
                "data_source": "temp_state",
                "route_key": "kb_available",
                # OCS StaticRouter stringifies Python bools to "TRUE"/"FALSE".
                # output_0 = FALSE (no approved KB) → fixed referral, no model call.
                # output_1 = TRUE  (KB selected)    → answer_match.
                # Default is FALSE (fail-closed: missing KB must not call model).
                "keywords": ["FALSE", "TRUE"],
                "default_keyword_index": 0,
                "tag_output_message": False,
            },
            1800,
            350,
        ),
        _node(
            "knowledge_referral",
            "CodeNode",
            {"name": "knowledge_referral", "code": _code("knowledge_referral")},
            2100,
            150,
        ),
        _node("answer_match", "CodeNode", {"name": "answer_match", "code": answer_match_source}, 2100, 500),
        _node(
            "answer_router",
            "StaticRouterNode",
            {
                "name": "answer_router",
                "data_source": "temp_state",
                "route_key": "answer_route",
                # output_0 = CARD    → output_guard (card text already selected).
                # output_1 = ASK_AI  → llm_input → llm → output_guard.
                # Default is ASK_AI (index 1): unknown route falls to LLM, not to
                # an empty or wrong card.
                "keywords": ["CARD", "ASK_AI"],
                "default_keyword_index": 1,
                "tag_output_message": False,
            },
            2400,
            500,
        ),
        _node("llm_input", "CodeNode", {"name": "llm_input", "code": _code("llm_input")}, 2700, 600),
        _node("prompt_budget", "CodeNode", {"name": "prompt_budget", "code": prompt_budget_source}, 3000, 750),
        _node(
            "budget_router",
            "StaticRouterNode",
            {
                "name": "budget_router",
                "data_source": "temp_state",
                "route_key": "budget_route",
                # output_0 = OVER_BUDGET → knowledge_referral (fail-closed: missing state = no LLM).
                # output_1 = VALID        → llm.
                # Default is OVER_BUDGET (index 0): any unexpected value routes to referral.
                "keywords": ["OVER_BUDGET", "VALID"],
                "default_keyword_index": 0,
                "tag_output_message": False,
            },
            3300,
            750,
        ),
        _node("output_guard", "CodeNode", {"name": "output_guard", "code": guard_source}, 2700, 300),
        _node(
            "llm",
            "LLMResponseWithPrompt",
            {
                "name": "llm",
                "llm_provider_id": llm_provider_id,
                "llm_provider_model_id": llm_provider_model_id,
                # temperature<=0.3 for conservative KB-grounded responses (#24 Phase A).
                # history_type=none: historical messages are not re-sanitized by llm_input;
                # disabling history is the only supported way to prevent prior PII reaching
                # the model context (OCS engine mixins.py:222-241).
                "llm_model_parameters": {"temperature": 0.3},
                "prompt": SYSTEM_PROMPT_FILE.read_text(),
                "history_type": "none",
            },
            3000,
            600,
        ),
        _node(
            "attach_explainer",
            "CodeNode",
            {"name": "attach_explainer", "code": _code("attach_explainer")},
            3000,
            300,
        ),
        _node(
            "danger_question_line",
            "CodeNode",
            {"name": "danger_question_line", "code": _code("danger_question_line")},
            3150,
            300,
        ),
        _node("end", "EndNode", {"name": "end"}, 3300, 300, flow_type="endNode"),
    ]
    edges = [
        _edge("start", "danger_gate"),
        _edge("danger_gate", "danger_router"),
        _edge("danger_router", "emergency_response", "output_0"),
        _edge("danger_router", "access_gate", "output_1"),
        _edge("access_gate", "access_router"),
        # Fixed replies for anyone not approved, and for images or files (#21). No AI.
        _edge("access_router", "danger_question_line", "output_0"),
        _edge("access_router", "danger_question_line", "output_1"),
        _edge("access_router", "registration", "output_2"),
        _edge("emergency_response", "end"),
        _edge("registration", "registration_router"),
        _edge("registration_router", "danger_question_line", "output_0"),
        # REGISTERED → knowledge context selection (not directly to LLM)
        _edge("registration_router", "kb_context", "output_1"),
        _edge("kb_context", "kb_router"),
        _edge("kb_router", "knowledge_referral", "output_0"),  # FALSE: no KB → referral
        _edge("kb_router", "answer_match", "output_1"),  # TRUE: KB available
        _edge("knowledge_referral", "danger_question_line"),
        _edge("answer_match", "answer_router"),
        _edge("answer_router", "output_guard", "output_0"),  # CARD → guard
        _edge("answer_router", "llm_input", "output_1"),  # ASK_AI → privacy filter
        _edge("llm_input", "prompt_budget"),  # privacy-filtered input → budget gate
        _edge("prompt_budget", "budget_router"),  # measure total render bytes
        _edge("budget_router", "knowledge_referral", "output_0"),  # OVER_BUDGET → referral
        _edge("budget_router", "llm", "output_1"),  # VALID → LLM
        _edge("llm", "output_guard"),
        _edge("output_guard", "attach_explainer"),
        # Danger-signs card: attach the approved explainer clip (#31). Fixed, no AI.
        _edge("attach_explainer", "danger_question_line"),
        # Fixed line first when the gate flagged a danger-sign question (sign-off A4 (c)).
        _edge("danger_question_line", "end"),
    ]
    if rules_only:
        # Issue #26, manual rules-only mode: remove every node that leads to the AI, and send
        # questions with no answer card to the approved fixed reply (sign-off C2 and C2a).
        # Emergencies, the access gate, registration, cards and the clip are unchanged.
        ai_nodes = {"llm_input", "prompt_budget", "budget_router", "llm"}
        nodes = [n for n in nodes if n["id"] not in ai_nodes]
        edges = [e for e in edges if e["source"] not in ai_nodes and e["target"] not in ai_nodes]
        edges.append(_edge("answer_router", "knowledge_referral", "output_1"))
        return {"name": PIPELINE_NAME + " (rules only)", "data": {"nodes": nodes, "edges": edges}}

    return {"name": PIPELINE_NAME, "data": {"nodes": nodes, "edges": edges}}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--write", action="store_true", help=f"write {COMMITTED_PIPELINE.relative_to(OCS_DIR.parent)}")
    parser.add_argument("--llm-provider-id", type=int, default=0)
    parser.add_argument("--llm-provider-model-id", type=int, default=0)
    parser.add_argument(
        "--include-pending",
        action="store_true",
        default=False,
        help=(
            "Include pending KB entries and answer cards (synthetic staging only). "
            "Never use for production deployment; pending review_status is preserved."
        ),
    )
    parser.add_argument(
        "--rules-only",
        action="store_true",
        default=False,
        help="Build the rules-only pipeline (#26): no AI node; unanswered questions get the fixed reply.",
    )
    args = parser.parse_args(argv)

    pipeline = build_pipeline(
        args.llm_provider_id,
        args.llm_provider_model_id,
        include_pending=args.include_pending,
        rules_only=args.rules_only,
    )
    output = json.dumps(pipeline, indent=2, ensure_ascii=False) + "\n"
    if args.write:
        (COMMITTED_RULES_ONLY_PIPELINE if args.rules_only else COMMITTED_PIPELINE).write_text(output)
    else:
        sys.stdout.write(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
