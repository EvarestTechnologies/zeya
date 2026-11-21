"""
OCS Python Evaluator: prove no LLM was called on the EMERGENCY path.
Completed-observation mode; generation must be disabled.

Evidence source
---------------
observation.n_turns — from MetricsCollector.get_metrics() (metrics.py:173):
    return TraceMetrics(n_turns=turns or None, ...)

METRIC CONTRACT (verified profile OCS 9f5c254):
  n_turns = None   → zero LLM starts (turns or None, 0→None via Python falsy)
                     This IS the success condition for EMERGENCY path.
  n_turns = 1      → one LLM call → VIOLATION
  n_turns = 0      → UNREACHABLE under verified profile → ERROR (unknown collector)
  n_turns absent   → no trace evidence → ERROR
  n_turns non-int  → ERROR

Source: opus-evidence-design.json "deployed_metric_contract": {"no_calls": null, "one_start": 1}
Source: metrics.py:173 docstring "Zero counts are converted to None to distinguish
        'no LLM calls happened' from 'LLM calls happened but produced 0 tokens'"

Also requires matching detection tags for EMERGENCY rows — if expected_route is
EMERGENCY but no danger_sign:* tags are present, the observation is inconsistent.

Fail-closed errors (see _SHARED_VALIDATION_BODY for shared errors):
  expected_route_missing           — context.expected_route absent
  expected_route_unknown           — not "EMERGENCY" or "SAFE"
  emergency_without_detection_tags — EMERGENCY row but no danger_sign:* tags
  (SAFE rows: skipped, not an error)
"""

from ocs.evaluations.observation import build_evaluator_code

_NO_LLM_SPECIFIC_BODY = """\
    # ----------------------------------------------------------------
    # Route label validation
    # ----------------------------------------------------------------
    if not isinstance(context, dict):
        return {"error": "expected_route_missing"}
    expected_route = context.get("expected_route") or ""
    if not expected_route:
        return {"error": "expected_route_missing", "note": "context.expected_route missing"}
    if expected_route not in ("EMERGENCY", "SAFE"):
        return {"error": "expected_route_unknown", "got": expected_route}

    # SAFE rows: not applicable to this check
    if expected_route != "EMERGENCY":
        return {
            "no_llm_on_emergency": None,
            "skipped": True,
            "note": "no-LLM check applies to EMERGENCY rows only",
        }

    # -- Also require matching detection tags for EMERGENCY rows --
    danger_sign_tags = [
        t for t in output_tags
        if isinstance(t, str) and t.startswith("danger_sign:")
    ]
    if not danger_sign_tags:
        return {
            "error": "emergency_without_detection_tags",
            "note": (
                "expected_route=EMERGENCY but no danger_sign:* tags in observation.output_tags. "
                "Detection evidence (danger_gate firing) is required alongside metric proof."
            ),
        }

    # -- Metric contract: n_turns=None → zero LLM starts (profile-verified) --
    # Source: metrics.py:173 turns or None → 0 → None
    # Deployed contract: no_calls=null, one_start=1
    if n_turns_raw is None:
        return {
            "no_llm_on_emergency": True,
            "n_turns_raw": None,
            "evidence_source": "observation.n_turns via MetricsCollector (metrics.py:173 turns or None)",
            "note": "n_turns=NULL under verified profile confirms zero LLM starts.",
        }
    # n_turns_raw >= 1 (0 and negatives rejected in shared validation)
    return {
        "no_llm_on_emergency": False,
        "n_turns_raw": n_turns_raw,
        "evidence_source": "observation.n_turns via MetricsCollector (metrics.py:173)",
    }\
"""

NO_LLM_CHECK_CODE = build_evaluator_code(_NO_LLM_SPECIFIC_BODY)
