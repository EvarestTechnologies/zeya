"""
Prompt-budget gate for the Zeya antenatal chatbot (integration #G1 / Owner C).

BUDGET_BYTES = 4000  (hard cap, single-render, UTF-8 exact).

The gate measures all text the LLM receives in a single turn:
  1. The system prompt template with {temp_state.X} and {participant_data.Y}
     placeholders replaced ONCE with actual runtime values (one-pass substitution
     via re.sub callback — KB/context content is never re-interpreted).
  2. The sanitized participant question (output of llm_input, the `input` arg).

Routing decision (temp_state.budget_route):
  "VALID"       → total bytes ≤ 4000; continue to LLM.
  "OVER_BUDGET" → total bytes > 4000, OR any required state is missing / invalid;
                  route to the existing knowledge_referral fixed reply (fail-closed).

The CodeNode source is GENERATED (not static) because the system prompt template
is baked in at build time, ensuring the byte measurement is always consistent with
the LLM node's actual prompt.  Calling render_prompt_budget_node(template) also
validates the template at build time, rejecting unsupported placeholders.

Supported placeholders (checked at build time):
  {temp_state.kb_section}             — KB entries selected by kb_context node
  {temp_state.llm_context}            — context block from registration node
  {participant_data.language_preference} — stored language preference

Source evidence:
  OCS 9f5c25476555ff74a167c6a14832ce798832847a
  apps/pipelines/nodes/nodes.py        CodeNode helpers
  apps/utils/python_execution.py       RestrictedPythonExecutionMixin
"""

import re as _re

BUDGET_BYTES: int = 4000

# Placeholder pattern: {temp_state.KEY} or {participant_data.KEY}
_PLACEHOLDER_RE = _re.compile(r"\{(temp_state|participant_data)\.([^}]+)\}")

# Keys expected in a standard render (must all be present for VALID routing).
_REQUIRED_TEMP_STATE_KEYS: tuple[str, ...] = ("kb_section", "llm_context")
_REQUIRED_PARTICIPANT_DATA_KEYS: tuple[str, ...] = ("language_preference",)

# Complete set of supported placeholder strings (checked at build time).
_SUPPORTED_PLACEHOLDERS: frozenset[str] = frozenset(
    f"{{temp_state.{k}}}" for k in _REQUIRED_TEMP_STATE_KEYS
) | frozenset(f"{{participant_data.{k}}}" for k in _REQUIRED_PARTICIPANT_DATA_KEYS)

# Sentinel tokens used to inject dynamic values into the node source template
# without triggering Python str.format() brace interpretation.  These tokens
# must not appear anywhere in real node source code.
_TOKEN_TEMPLATE = "<<SYSTEM_PROMPT_TEMPLATE>>"
_TOKEN_BUDGET = "<<BUDGET_BYTES>>"


# ---------------------------------------------------------------------------
# Public pure function
# ---------------------------------------------------------------------------


def compute_prompt_bytes(
    template: str,
    kb_section: str,
    llm_context: str,
    language_pref: str,
    question: str,
) -> int:
    """Pure function: one-pass substitution then UTF-8 byte count.

    Performs a single re.sub pass over ``template`` replacing
    {temp_state.kb_section}, {temp_state.llm_context}, and
    {participant_data.language_preference} with the supplied values.  Any
    placeholder-like text introduced by substituted values is NOT expanded
    again (re.sub callback, single pass).

    Does NOT validate types or presence; call sites that need fail-closed
    behaviour should check validity before calling.
    """
    ts_values = {"kb_section": kb_section, "llm_context": llm_context}
    pd_values = {"language_preference": language_pref}

    def _sub(m: _re.Match) -> str:
        source, key = m.group(1), m.group(2)
        if source == "temp_state":
            v = ts_values.get(key)
            return v if v is not None else m.group(0)
        if source == "participant_data":
            v = pd_values.get(key)
            return v if v is not None else m.group(0)
        return m.group(0)

    rendered = _PLACEHOLDER_RE.sub(_sub, template)
    return len(rendered.encode("utf-8")) + len(question.encode("utf-8"))


# ---------------------------------------------------------------------------
# Build-time template validation
# ---------------------------------------------------------------------------


def _validate_template(template: str) -> None:
    """Raise ValueError if template contains any unsupported format field.

    Uses Python's actual string.Formatter grammar so bracket notation
    ({key[name]}), unsupported roots ({session_state.x}), conversion specs
    ({field!r}) and format specs ({field:.50s}) are all caught — a plain regex
    over {root.key} patterns would miss them.

    Called at build time by render_prompt_budget_node.  Any field not in the
    exact supported set is rejected so a prompt change that adds new
    placeholders fails loudly at build time.
    """
    import string  # noqa: PLC0415

    # The runtime counts plain supported fields, not Python's escaped-brace
    # syntax. Reject that syntax rather than count a different rendered prompt.
    if "{{" in template or "}}" in template:
        raise ValueError("prompt_budget: escaped braces are not supported in the template")

    supported_field_names: frozenset[str] = frozenset(
        {
            "temp_state.kb_section",
            "temp_state.llm_context",
            "participant_data.language_preference",
        }
    )
    for _, field_name, format_spec, conversion in string.Formatter().parse(template):
        if field_name is None:
            continue  # literal segment, no format field
        if conversion is not None:
            raise ValueError(
                f"prompt_budget: conversion spec '!{conversion}' in template field '{{{field_name}}}' is not supported."
            )
        if format_spec:
            raise ValueError(
                f"prompt_budget: format spec ':{format_spec}' in template field '{{{field_name}}}' is not supported."
            )
        if field_name not in supported_field_names:
            raise ValueError(
                f"prompt_budget: unsupported template field '{{{field_name}}}'. "
                f"Supported fields: {sorted(supported_field_names)!r}."
            )


# ---------------------------------------------------------------------------
# Build-time budget validation
# ---------------------------------------------------------------------------


def _validate_budget(budget_bytes: object) -> None:
    """Raise ValueError if budget_bytes is not a plain positive integer.

    bool is a subclass of int in Python, so the bool check must come first.
    Zero, negative values, floats, and strings are all rejected: they would
    either never trigger OVER_BUDGET (zero/negative) or cause a runtime type
    error inside the generated CodeNode (float/string comparison against int).
    """
    if isinstance(budget_bytes, bool):
        raise ValueError(f"budget_bytes must be a plain positive integer, got bool: {budget_bytes!r}")
    if not isinstance(budget_bytes, int):
        raise ValueError(
            f"budget_bytes must be a plain positive integer, got {type(budget_bytes).__name__}: {budget_bytes!r}"
        )
    if budget_bytes <= 0:
        raise ValueError(f"budget_bytes must be a positive integer, got {budget_bytes!r}")


# ---------------------------------------------------------------------------
# Node source template  (sentinel tokens, not f-string braces, to avoid
# conflicting with the Python dict literals and regex braces inside)
# ---------------------------------------------------------------------------

_NODE_SOURCE = r"""
def main(input, **kwargs):
    import re

    # System prompt template baked in at build time by ocs/prompt_budget.py.
    # Changes to ocs/prompts/system_prompt.txt are picked up at next build.
    SYSTEM_PROMPT = <<SYSTEM_PROMPT_TEMPLATE>>
    BUDGET_BYTES = <<BUDGET_BYTES>>

    if not isinstance(input, str):
        set_temp_state_key("budget_route", "OVER_BUDGET")
        set_temp_state_key("budget_bytes", 0)
        set_temp_state_key("budget_reason", "invalid_question")
        return input

    question = input

    # Fail-closed: blank sanitised question (whitespace or empty string).
    if not question.strip():
        set_temp_state_key("budget_route", "OVER_BUDGET")
        set_temp_state_key("budget_bytes", 0)
        set_temp_state_key("budget_reason", "blank_question")
        return input

    # Read runtime values — no defaults, no silent coercion.
    kb_section = get_temp_state_key("kb_section")
    llm_context = get_temp_state_key("llm_context")
    data = get_participant_data() or {}
    lang = data.get("language_preference", "")

    # Fail-closed: kb_section absent or not a string.
    if not isinstance(kb_section, str):
        set_temp_state_key("budget_route", "OVER_BUDGET")
        set_temp_state_key("budget_bytes", 0)
        set_temp_state_key("budget_reason", "missing_kb_section")
        return input

    # Fail-closed: llm_context absent or not a string.
    if not isinstance(llm_context, str):
        set_temp_state_key("budget_route", "OVER_BUDGET")
        set_temp_state_key("budget_bytes", 0)
        set_temp_state_key("budget_reason", "missing_llm_context")
        return input

    # Fail-closed: language preference absent, empty, unsupported locale, or
    # wrong type (bool/int).  Only exactly "en" or "sw" is accepted; any other
    # value — including "fr", whitespace strings, True, 42 — routes OVER_BUDGET
    # without raising a TypeError.
    if lang not in ("en", "sw"):
        set_temp_state_key("budget_route", "OVER_BUDGET")
        set_temp_state_key("budget_bytes", 0)
        set_temp_state_key("budget_reason", "missing_language")
        return input

    # One-pass substitution: replace each {source.key} placeholder exactly once.
    # Using re.sub with a callback avoids sequential replace which could
    # re-interpret placeholder-like text inserted from KB or context values.
    ts_lookup = {"kb_section": kb_section, "llm_context": llm_context}
    pd_lookup = {"language_preference": lang}

    def do_sub(m):
        source = m.group(1)
        key = m.group(2)
        if source == "temp_state":
            val = ts_lookup.get(key)
            return val if val is not None else m.group(0)
        if source == "participant_data":
            val = pd_lookup.get(key)
            return val if val is not None else m.group(0)
        return m.group(0)

    rendered = re.sub(
        r"\{(temp_state|participant_data)\.([^}]+)\}",
        do_sub,
        SYSTEM_PROMPT,
    )

    total_bytes = len(rendered.encode("utf-8")) + len(question.encode("utf-8"))
    set_temp_state_key("budget_bytes", total_bytes)

    if total_bytes > BUDGET_BYTES:
        set_temp_state_key("budget_route", "OVER_BUDGET")
        set_temp_state_key("budget_reason", "over_cap")
    else:
        set_temp_state_key("budget_route", "VALID")
        set_temp_state_key("budget_reason", "")

    return input
""".strip()


# ---------------------------------------------------------------------------
# Public generator
# ---------------------------------------------------------------------------


def render_prompt_budget_node(template: str, budget_bytes: int = BUDGET_BYTES) -> str:
    """Generate the OCS CodeNode source for the prompt_budget gate.

    The system prompt template text is baked in as a Python string literal so
    the byte measurement is always consistent with what the LLM node receives.

    Args:
        template:     The system_prompt.txt text as a string.
        budget_bytes: Override the hard cap (default 4000).  Used only in tests.

    Returns:
        A string containing the complete Python source accepted by OCS CodeNode.

    Raises:
        ValueError: if template contains fields not supported by the node,
                    or if budget_bytes is not a plain positive integer.
    """
    _validate_template(template)
    _validate_budget(budget_bytes)
    # Inject user-authored prompt text last, so sentinel-looking literal text
    # inside it is never interpreted as another generator instruction.
    return _NODE_SOURCE.replace(_TOKEN_BUDGET, repr(budget_bytes)).replace(_TOKEN_TEMPLATE, repr(template))
