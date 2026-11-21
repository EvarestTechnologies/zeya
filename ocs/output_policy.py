"""
Zeya #25 output-guard module.

Exposes:
  load_output_policy(path)       -- read and validate docs/output-policy.json
  validate_output_policy(policy) -- validate a policy dict
  render_output_guard(policy)    -- generate the OCS CodeNode source

The single content classifier lives in ocs/guard_classifier.py.
validate_output_policy imports and calls it directly for referral checks.
render_output_guard embeds its source into the generated node so the same
code path runs both on the host and inside the OCS sandbox.

URL allowlist semantics:
  Each entry must be a full https:// URL.
  Canonicalisation: lowercase scheme+host, preserve path/query case,
  preserve path slashes, strip fragment.
  Only an exact match (after canonicalisation) is accepted.
"""

import inspect
import json
import re
import textwrap
from pathlib import Path
from urllib.parse import urlsplit

from ocs.guard_classifier import guard_classify

_REQUIRED_KEYS: list[tuple[str, type]] = [
    ("verified_phone_allowlist", list),
    ("verified_url_allowlist", list),
    ("blocked_referral_en", str),
    ("blocked_referral_sw", str),
    ("max_words", int),
    ("never_say_patterns", list),
    ("medicine_patterns", list),
    ("dose_patterns", list),
    ("diagnosis_patterns", list),
    ("suspicious_url_patterns", list),
    ("short_helpline_patterns", list),
]


def validate_output_policy(policy: dict) -> None:
    """Validate a policy dict against all schema rules.

    Single authoritative validator; called by both load_output_policy and
    render_output_guard.  Referral texts are checked through the same
    guard_classify function used at runtime.

    Raises ValueError with the offending key name in the message.
    """
    if not isinstance(policy, dict):
        raise ValueError("Policy must be a JSON object (dict)")

    # 1. Required keys: existence and top-level type
    for key, expected_type in _REQUIRED_KEYS:
        if key not in policy:
            raise ValueError(f"Policy missing required key: {key!r}")
        val = policy[key]
        if isinstance(val, bool) and expected_type is int:
            raise ValueError(f"max_words must be a plain int, not a bool (got {val!r})")
        if not isinstance(val, expected_type):
            raise ValueError(f"Policy key {key!r} must be {expected_type.__name__}, got {type(val).__name__!r}")

    # 2. max_words range
    mw = policy["max_words"]
    if mw <= 0 or mw > 120:
        raise ValueError(f"max_words must be between 1 and 120 inclusive, got {mw}")

    # 3. Phone allowlist elements
    for i, elem in enumerate(policy["verified_phone_allowlist"]):
        if not isinstance(elem, str):
            raise ValueError(f"verified_phone_allowlist[{i}] must be a string")
        if not elem.strip():
            raise ValueError(f"verified_phone_allowlist[{i}] must be non-empty")

    # 4. URL allowlist: full https:// URLs without credentials
    for i, elem in enumerate(policy["verified_url_allowlist"]):
        if not isinstance(elem, str):
            raise ValueError(f"verified_url_allowlist[{i}] must be a string")
        if not elem.strip():
            raise ValueError(f"verified_url_allowlist[{i}] must be non-empty")
        if not elem.lower().startswith("https://"):
            raise ValueError(f"verified_url_allowlist[{i}] must be a full https:// URL (got {elem!r})")
        if "@" in elem:
            raise ValueError(f"verified_url_allowlist[{i}] must not contain credentials (@)")
        if re.search(r"[\s\\\x00-\x1f\x7f]", elem):
            raise ValueError(f"verified_url_allowlist[{i}] contains whitespace, controls or backslashes")
        try:
            parsed = urlsplit(elem)
            host = parsed.hostname
            port = parsed.port
        except ValueError as exc:
            raise ValueError(f"verified_url_allowlist[{i}] has an invalid authority") from exc
        if not host or not parsed.netloc or parsed.netloc.endswith(":") or port == 0:
            raise ValueError(f"verified_url_allowlist[{i}] must have a valid HTTPS authority")
        # This finite policy supports ASCII DNS names and IPv4, not arbitrary IRIs.
        labels = host.rstrip(".").split(".")
        if len(host) > 253 or any(
            not re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?", label) for label in labels
        ):
            raise ValueError(f"verified_url_allowlist[{i}] must have a valid ASCII hostname")

    # 5. Referral texts: non-empty check
    for key in ("blocked_referral_en", "blocked_referral_sw"):
        if not policy[key].strip():
            raise ValueError(f"{key} must be a non-empty string")

    # 6. Compile all regex pattern lists
    for pattern_key in (
        "never_say_patterns",
        "medicine_patterns",
        "dose_patterns",
        "diagnosis_patterns",
        "suspicious_url_patterns",
        "short_helpline_patterns",
    ):
        for i, pattern_str in enumerate(policy[pattern_key]):
            if not isinstance(pattern_str, str):
                raise ValueError(f"{pattern_key}[{i}] must be a string")
            try:
                re.compile(pattern_str, re.IGNORECASE)
            except re.error as exc:
                raise ValueError(f"{pattern_key}[{i}] is not a valid regex: {exc}") from exc

    # 7. Referral content: use the same classifier the runtime node uses.
    # Parity guarantee: a referral cannot contain content the guard blocks.
    for key in ("blocked_referral_en", "blocked_referral_sw"):
        gresult = guard_classify(policy[key], policy)
        if gresult["blocked"]:
            raise ValueError(
                f"{key} contains prohibited content (guard would block it: {gresult['reason']!r});"
                " the fixed referral cannot trigger the guard's own checks"
            )


def load_output_policy(path: str) -> dict:
    """Read and validate the output-guard policy JSON.

    Raises FileNotFoundError if absent, ValueError on schema violations.
    """
    policy_path = Path(path)
    if not policy_path.exists():
        raise FileNotFoundError(f"Output policy not found: {path}")
    with policy_path.open(encoding="utf-8") as fh:
        try:
            policy = json.load(fh)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Output policy is not valid JSON: {exc}") from exc
    if not isinstance(policy, dict):
        raise ValueError("Output policy must be a JSON object at the top level")
    validate_output_policy(policy)
    return policy


def render_output_guard(policy: dict) -> str:
    """Generate the OCS CodeNode source for the output guard.

    validate_output_policy is called before rendering.

    The guard_classify function from ocs/guard_classifier.py is embedded
    verbatim inside main via inspect.getsource so the SAME predicate runs
    both on the host (validate_output_policy) and in the OCS sandbox (main).
    """
    validate_output_policy(policy)

    # Embed classifier source indented 4 spaces (inside main).
    classifier_src = textwrap.indent(inspect.getsource(guard_classify), "    ")

    # Embed only the runtime keys the classifier needs.
    runtime_keys = [
        "max_words",
        "verified_phone_allowlist",
        "verified_url_allowlist",
        "blocked_referral_en",
        "blocked_referral_sw",
        "never_say_patterns",
        "medicine_patterns",
        "dose_patterns",
        "diagnosis_patterns",
        "suspicious_url_patterns",
        "short_helpline_patterns",
    ]
    runtime_policy = {k: policy[k] for k in runtime_keys}
    # Adjacent safe literals preserve long regex data without unlintable lines.
    policy_json = json.dumps(runtime_policy, ensure_ascii=True)
    chunks = [
        json.dumps(policy_json[i : i + 40]) if '"' not in policy_json[i : i + 40] else repr(policy_json[i : i + 40])
        for i in range(0, len(policy_json), 40)
    ]
    policy_repr = "json.loads(\n" + "\n".join("        " + chunk for chunk in chunks) + "\n    )"

    return _NODE_TEMPLATE.replace("###POLICY###", policy_repr).replace("###CLASSIFIER###", classifier_src)


# ---------------------------------------------------------------------------
# Node source template
# Two sentinels:
#   ###POLICY###     replaced with JSON decoded from safely escaped literals
#   ###CLASSIFIER### replaced with inspect.getsource(guard_classify) indented
# ---------------------------------------------------------------------------

_NODE_TEMPLATE = (
    '"""\n'
    "Open Chat Studio Python node: output guard.\n"
    "\n"
    "Generated by render_output_guard.  Do not edit this file directly.\n"
    "Change docs/output-policy.json and re-run render_output_guard to update.\n"
    "\n"
    "Classifier source embedded from ocs/guard_classifier.py -- the same predicate\n"
    "used for host-side referral validation (source reuse, not hand-copy).\n"
    "\n"
    "Scope limits (do not remove):\n"
    "  - Medicine patterns: conservative starter set, protocol list not supplied.\n"
    "  - Sheng slang not covered; no equivalences without source.\n"
    "  - Unicode hostname lookalikes not caught.\n"
    "  - Short helpline set finite and review-pending.\n"
    "  - ZW normalisation covers six specific chars; not exhaustive.\n"
    "\n"
    "Guard constraints:\n"
    "  - No model, network, file I/O or credentials.\n"
    "  - Non-sensitive reason codes only; no raw input in tags/logs.\n"
    "  - Does not mutate participant data.\n"
    "  - Applies to AI/card output only.\n"
    '"""\n'
    "\n"
    "\n"
    "def main(input: str, **kwargs) -> str:\n"
    "    import json\n"
    "\n"
    "    # Embedded policy (re-generate via render_output_guard)\n"
    "    gpolicy = ###POLICY###\n"
    "\n"
    "    # Embedded classifier from ocs/guard_classifier.py\n"
    "###CLASSIFIER###"
    "\n"
    "    # Participant language (read-only)\n"
    "    gparticipant = get_participant_data() or {}\n"
    '    glang = gparticipant.get("language_preference", "en")\n'
    '    greferral = gpolicy["blocked_referral_sw"] if glang == "sw" else gpolicy["blocked_referral_en"]\n'
    "\n"
    '    gtext = input if input is not None else ""\n'
    "\n"
    "    gresult = guard_classify(gtext, gpolicy)\n"
    '    if gresult["blocked"]:\n'
    '        set_temp_state_key("guard_route", "guard_blocked")\n'
    '        add_message_tag("route:guard_blocked")\n'
    '        add_message_tag("guard_blocked_reason:" + gresult["reason"])\n'
    "        return greferral\n"
    "\n"
    '    set_temp_state_key("guard_route", "PASS")\n'
    "    return input\n"
)
