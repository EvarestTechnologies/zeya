"""
RED-first TDD tests for the prompt_budget gate (Zeya integration #G1 / Owner C).

Contract:
- Hard 4000 UTF-8 byte cap on (rendered system prompt) + (sanitized question).
- One-pass substitution: {temp_state.X} and {participant_data.Y} replaced
  ONCE with actual runtime values; KB/context content is never re-interpreted.
- Fail-closed: missing or invalid state, absent language, blank question,
  and over-budget payloads all route OVER_BUDGET without calling the LLM.
- Input returned unchanged in all branches (the node is a gate, not a mutator).

Source evidence (OCS commit 9f5c25476555ff74a167c6a14832ce798832847a):
  apps/pipelines/nodes/nodes.py  CodeNode helpers
  apps/utils/python_execution.py RestrictedPythonExecutionMixin
"""

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from ocs.tests.sandbox import NodeHarness, make_executor  # noqa: E402

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

BUDGET_BYTES = 4000  # hard cap; must match ocs/prompt_budget.BUDGET_BYTES

# Minimal template with all three supported placeholders.  Exact rendered bytes
# depend on the substituted values, making boundary tests deterministic.
TINY_TEMPLATE = "SYS\n{temp_state.kb_section}\n{temp_state.llm_context}\nLang:{participant_data.language_preference}"

# Rendered form with baseline values used in most tests:
#   "SYS\n" (4) + "" (0) + "\n" (1) + "" (0) + "\nLang:" (6) + "en" (2) = 13
# + question
_BASELINE_RENDERED_STATIC = 13  # bytes for TINY_TEMPLATE with kb_section="", llm_context="", lang="en"


def _base_state(kb_section: str = "", llm_context: str = "") -> dict:
    return {"kb_section": kb_section, "llm_context": llm_context}


def _base_participant(lang: str = "en") -> dict:
    return {"language_preference": lang}


def _run(
    question: str,
    template: str = TINY_TEMPLATE,
    temp_state: dict | None = None,
    participant_data: dict | None = None,
) -> NodeHarness:
    from ocs.prompt_budget import render_prompt_budget_node  # noqa: PLC0415

    source = render_prompt_budget_node(template)
    h = NodeHarness(
        source,
        temp_state=temp_state if temp_state is not None else _base_state(),
        participant_data=participant_data if participant_data is not None else _base_participant(),
    )
    h.output = h.run(question)
    return h


# ---------------------------------------------------------------------------
# TestComputePromptBytes — pure function, no sandbox
# ---------------------------------------------------------------------------


class TestComputePromptBytes:
    def test_basic_ascii_count(self):
        from ocs.prompt_budget import compute_prompt_bytes  # noqa: PLC0415

        # TINY_TEMPLATE rendered with empties + lang="en":
        # "SYS\n\n\nLang:en" = 13 bytes, question "Q" = 1 byte → 14
        result = compute_prompt_bytes(TINY_TEMPLATE, "", "", "en", "Q")
        assert result == 14

    def test_exactly_at_budget_boundary(self):
        from ocs.prompt_budget import compute_prompt_bytes  # noqa: PLC0415

        # Pad the question to bring total to exactly 4000 bytes.
        static = _BASELINE_RENDERED_STATIC
        q = "A" * (BUDGET_BYTES - static)
        result = compute_prompt_bytes(TINY_TEMPLATE, "", "", "en", q)
        assert result == BUDGET_BYTES

    def test_one_over_budget_boundary(self):
        from ocs.prompt_budget import compute_prompt_bytes  # noqa: PLC0415

        static = _BASELINE_RENDERED_STATIC
        q = "A" * (BUDGET_BYTES - static + 1)
        result = compute_prompt_bytes(TINY_TEMPLATE, "", "", "en", q)
        assert result == BUDGET_BYTES + 1

    def test_multibyte_unicode_in_kb_section(self):
        from ocs.prompt_budget import compute_prompt_bytes  # noqa: PLC0415

        # Swahili phrase: 2-3 bytes per UTF-8 character.
        # Verify byte count equals len(rendered.encode()) + len(q.encode()).
        kb = "Karibu \u2764"  # U+2764 is 3 UTF-8 bytes
        expected_kb_bytes = len(kb.encode("utf-8"))  # "Karibu " (7) + "\u2764" (3) = 10
        static_without_kb = _BASELINE_RENDERED_STATIC  # with kb=""
        expected = static_without_kb + expected_kb_bytes + 1  # +1 for question "Q"
        result = compute_prompt_bytes(TINY_TEMPLATE, kb, "", "en", "Q")
        assert result == expected

    def test_multibyte_unicode_in_question(self):
        from ocs.prompt_budget import compute_prompt_bytes  # noqa: PLC0415

        # Swahili question with 3-byte chars
        q = "Nina ujauzito wa wiki ngapi \U0001f930"  # U+1F930 is 4 bytes
        expected_q_bytes = len(q.encode("utf-8"))
        result = compute_prompt_bytes(TINY_TEMPLATE, "", "", "en", q)
        assert result == _BASELINE_RENDERED_STATIC + expected_q_bytes

    def test_multibyte_unicode_in_llm_context(self):
        from ocs.prompt_budget import compute_prompt_bytes  # noqa: PLC0415

        ctx = "Trimestre ya kwanza: \u2192 miaka 1-12"  # U+2192 is 3 UTF-8 bytes
        result = compute_prompt_bytes(TINY_TEMPLATE, "", ctx, "en", "Q")
        rendered = "SYS\n" + "" + "\n" + ctx + "\nLang:en"
        expected = len(rendered.encode("utf-8")) + len(b"Q")
        assert result == expected

    def test_placeholder_text_in_kb_not_re_expanded(self):
        """KB content that looks like a placeholder is NOT substituted again (one-pass)."""
        from ocs.prompt_budget import compute_prompt_bytes  # noqa: PLC0415

        # kb_section contains text that looks like a placeholder
        kb = "{temp_state.llm_context}"  # 26 bytes as literal ASCII
        result = compute_prompt_bytes(TINY_TEMPLATE, kb, "", "en", "Q")
        # The KB text is substituted in ONCE; the {temp_state.llm_context} inside it
        # is NOT expanded again (one-pass substitution via re.sub with callable).
        rendered = "SYS\n" + kb + "\n" + "" + "\nLang:en"
        expected = len(rendered.encode("utf-8")) + 1  # +1 for "Q"
        assert result == expected

    def test_all_values_empty_still_counts_template_static(self):
        from ocs.prompt_budget import compute_prompt_bytes  # noqa: PLC0415

        result = compute_prompt_bytes(TINY_TEMPLATE, "", "", "", "")
        # Rendered with all empty: "SYS\n\n\nLang:" = 11 bytes, question "" = 0 → 11
        assert result == 11

    def test_swahili_language_pref_counts_bytes(self):
        from ocs.prompt_budget import compute_prompt_bytes  # noqa: PLC0415

        result_en = compute_prompt_bytes(TINY_TEMPLATE, "", "", "en", "Q")
        result_sw = compute_prompt_bytes(TINY_TEMPLATE, "", "", "sw", "Q")
        assert result_sw == result_en  # "en" and "sw" are both 2 bytes


# ---------------------------------------------------------------------------
# TestBuildTimeValidation — render_prompt_budget_node
# ---------------------------------------------------------------------------


class TestBuildTimeValidation:
    def test_render_accepts_supported_template(self):
        from ocs.prompt_budget import render_prompt_budget_node  # noqa: PLC0415

        source = render_prompt_budget_node(TINY_TEMPLATE)
        assert isinstance(source, str)
        assert len(source) > 0

    def test_render_rejects_unsupported_placeholder(self):
        from ocs.prompt_budget import render_prompt_budget_node  # noqa: PLC0415

        bad = "Hello {temp_state.unknown_key} world"
        with pytest.raises(ValueError, match="unsupported template field"):
            render_prompt_budget_node(bad)

    def test_render_rejects_unsupported_participant_data_key(self):
        from ocs.prompt_budget import render_prompt_budget_node  # noqa: PLC0415

        bad = "Lang: {participant_data.phone_number}"
        with pytest.raises(ValueError, match="unsupported template field"):
            render_prompt_budget_node(bad)

    def test_rendered_source_validates_as_code_node(self):
        from ocs.prompt_budget import render_prompt_budget_node  # noqa: PLC0415

        source = render_prompt_budget_node(TINY_TEMPLATE)
        # make_executor raises CodeValidationError if the source does not meet OCS
        # CodeNode contract (single main(input, **kwargs) function).
        make_executor(source)

    def test_template_literal_baked_into_source(self):
        """The system prompt template text is embedded in the generated source."""
        from ocs.prompt_budget import render_prompt_budget_node  # noqa: PLC0415

        source = render_prompt_budget_node(TINY_TEMPLATE)
        # The template content (or its repr) must be present in the source.
        assert "SYS" in source  # minimal check on template text presence

    def test_budget_bytes_baked_into_source(self):
        from ocs.prompt_budget import render_prompt_budget_node  # noqa: PLC0415

        source = render_prompt_budget_node(TINY_TEMPLATE, budget_bytes=3500)
        assert "3500" in source

    def test_no_placeholder_template_accepted(self):
        """A template with no placeholders is valid (renders statically)."""
        from ocs.prompt_budget import render_prompt_budget_node  # noqa: PLC0415

        source = render_prompt_budget_node("You are a helpful assistant.")
        make_executor(source)

    def test_actual_system_prompt_accepted(self):
        """The real system_prompt.txt must be accepted by render_prompt_budget_node."""
        from ocs.prompt_budget import render_prompt_budget_node  # noqa: PLC0415

        template = (REPO / "ocs" / "prompts" / "system_prompt.txt").read_text()
        source = render_prompt_budget_node(template)
        make_executor(source)

    # ----- budget_bytes validation (parent boundary failures 5-9) -----

    def test_render_rejects_bool_budget(self):
        """bool is a subclass of int — must be caught before the int check."""
        from ocs.prompt_budget import render_prompt_budget_node  # noqa: PLC0415

        with pytest.raises(ValueError, match="bool"):
            render_prompt_budget_node(TINY_TEMPLATE, budget_bytes=True)

    def test_render_rejects_zero_budget(self):
        from ocs.prompt_budget import render_prompt_budget_node  # noqa: PLC0415

        with pytest.raises(ValueError, match="positive integer"):
            render_prompt_budget_node(TINY_TEMPLATE, budget_bytes=0)

    def test_render_rejects_negative_budget(self):
        from ocs.prompt_budget import render_prompt_budget_node  # noqa: PLC0415

        with pytest.raises(ValueError, match="positive integer"):
            render_prompt_budget_node(TINY_TEMPLATE, budget_bytes=-1)

    def test_render_rejects_float_budget(self):
        from ocs.prompt_budget import render_prompt_budget_node  # noqa: PLC0415

        with pytest.raises(ValueError, match="plain positive integer"):
            render_prompt_budget_node(TINY_TEMPLATE, budget_bytes=3.5)

    def test_render_rejects_string_budget(self):
        from ocs.prompt_budget import render_prompt_budget_node  # noqa: PLC0415

        with pytest.raises(ValueError, match="plain positive integer"):
            render_prompt_budget_node(TINY_TEMPLATE, budget_bytes="4000")

    def test_render_accepts_one_budget(self):
        """Smallest valid positive integer budget must be accepted."""
        from ocs.prompt_budget import render_prompt_budget_node  # noqa: PLC0415

        source = render_prompt_budget_node(TINY_TEMPLATE, budget_bytes=1)
        assert "1" in source

    def test_default_budget_is_4000(self):
        """Conservative 4000-byte default preserved after validation changes."""
        from ocs.prompt_budget import BUDGET_BYTES  # noqa: PLC0415

        assert BUDGET_BYTES == 4000

    # ----- template grammar validation (parent boundary failures 10-11) -----

    def test_render_rejects_bracket_notation_field(self):
        """{participant_data[name]} uses bracket notation — must be rejected."""
        from ocs.prompt_budget import render_prompt_budget_node  # noqa: PLC0415

        bad = "Hello {participant_data[name]} world"
        with pytest.raises(ValueError, match="unsupported template field"):
            render_prompt_budget_node(bad)

    def test_render_rejects_unsupported_root(self):
        """{session_state.anything} is not a supported root — must be rejected."""
        from ocs.prompt_budget import render_prompt_budget_node  # noqa: PLC0415

        bad = "Context: {session_state.anything}"
        with pytest.raises(ValueError, match="unsupported template field"):
            render_prompt_budget_node(bad)

    def test_render_rejects_conversion_spec(self):
        """{temp_state.kb_section!r} has a conversion — must be rejected."""
        from ocs.prompt_budget import render_prompt_budget_node  # noqa: PLC0415

        bad = "KB: {temp_state.kb_section!r}"
        with pytest.raises(ValueError, match="conversion spec"):
            render_prompt_budget_node(bad)

    def test_render_rejects_format_spec(self):
        """{temp_state.kb_section:.50s} has a format spec — must be rejected."""
        from ocs.prompt_budget import render_prompt_budget_node  # noqa: PLC0415

        bad = "KB: {temp_state.kb_section:.50s}"
        with pytest.raises(ValueError, match="format spec"):
            render_prompt_budget_node(bad)


# ---------------------------------------------------------------------------
# TestNodeBehaviour — via NodeHarness sandbox
# ---------------------------------------------------------------------------


class TestNodeBehaviour:
    def test_valid_state_routes_valid(self):
        h = _run("What should I eat?")
        assert h.temp_state["budget_route"] == "VALID"

    def test_valid_state_sets_byte_count(self):
        q = "What should I eat?"
        h = _run(q)
        expected = compute_prompt_bytes_direct(TINY_TEMPLATE, "", "", "en", q)
        assert h.temp_state["budget_bytes"] == expected

    def test_valid_state_returns_input_unchanged(self):
        q = "What should I eat?"
        h = _run(q)
        assert h.output == q

    def test_over_budget_routes_over_budget(self):
        static = _BASELINE_RENDERED_STATIC
        q = "A" * (BUDGET_BYTES - static + 1)
        h = _run(q)
        assert h.temp_state["budget_route"] == "OVER_BUDGET"

    def test_over_budget_returns_input_unchanged(self):
        static = _BASELINE_RENDERED_STATIC
        q = "A" * (BUDGET_BYTES - static + 1)
        h = _run(q)
        assert h.output == q

    def test_exactly_at_budget_is_valid(self):
        static = _BASELINE_RENDERED_STATIC
        q = "A" * (BUDGET_BYTES - static)
        h = _run(q)
        assert h.temp_state["budget_route"] == "VALID"

    def test_missing_kb_section_routes_over_budget(self):
        """kb_section absent from temp_state → fail-closed, no default."""
        h = _run(
            "question",
            temp_state={"llm_context": "some context"},  # kb_section absent
        )
        assert h.temp_state["budget_route"] == "OVER_BUDGET"
        assert h.temp_state["budget_reason"] == "missing_kb_section"

    def test_missing_llm_context_routes_over_budget(self):
        """llm_context absent from temp_state → fail-closed, no default."""
        h = _run(
            "question",
            temp_state={"kb_section": "some kb"},  # llm_context absent
        )
        assert h.temp_state["budget_route"] == "OVER_BUDGET"
        assert h.temp_state["budget_reason"] == "missing_llm_context"

    def test_none_kb_section_routes_over_budget(self):
        """Explicit None kb_section (temp state key present, value None) → fail-closed."""
        h = _run(
            "question",
            temp_state={"kb_section": None, "llm_context": "ctx"},
        )
        assert h.temp_state["budget_route"] == "OVER_BUDGET"
        assert h.temp_state["budget_reason"] == "missing_kb_section"

    def test_none_llm_context_routes_over_budget(self):
        h = _run(
            "question",
            temp_state={"kb_section": "kb", "llm_context": None},
        )
        assert h.temp_state["budget_route"] == "OVER_BUDGET"
        assert h.temp_state["budget_reason"] == "missing_llm_context"

    def test_integer_kb_section_routes_over_budget(self):
        """Non-string kb_section (e.g. 42) → fail-closed."""
        h = _run(
            "question",
            temp_state={"kb_section": 42, "llm_context": "ctx"},
        )
        assert h.temp_state["budget_route"] == "OVER_BUDGET"
        assert h.temp_state["budget_reason"] == "missing_kb_section"

    def test_missing_language_preference_routes_over_budget(self):
        h = _run(
            "question",
            participant_data={},  # no language_preference key
        )
        assert h.temp_state["budget_route"] == "OVER_BUDGET"
        assert h.temp_state["budget_reason"] == "missing_language"

    def test_empty_language_preference_routes_over_budget(self):
        h = _run(
            "question",
            participant_data={"language_preference": ""},
        )
        assert h.temp_state["budget_route"] == "OVER_BUDGET"
        assert h.temp_state["budget_reason"] == "missing_language"

    # ----- language validation regressions (parent boundary failures 1-4) -----

    def test_unsupported_language_routes_over_budget(self):
        """'fr' is not en/sw — must route OVER_BUDGET, not VALID."""
        h = _run("question", participant_data={"language_preference": "fr"})
        assert h.temp_state["budget_route"] == "OVER_BUDGET"
        assert h.temp_state["budget_reason"] == "missing_language"

    def test_whitespace_only_language_routes_over_budget(self):
        """Whitespace string '  ' is truthy but not en/sw — must route OVER_BUDGET."""
        h = _run("question", participant_data={"language_preference": "  "})
        assert h.temp_state["budget_route"] == "OVER_BUDGET"
        assert h.temp_state["budget_reason"] == "missing_language"

    def test_boolean_language_routes_over_budget_not_typeerror(self):
        """bool language_preference (True) must route OVER_BUDGET, not raise TypeError."""
        h = _run("question", participant_data={"language_preference": True})
        assert h.temp_state["budget_route"] == "OVER_BUDGET"
        assert h.temp_state["budget_reason"] == "missing_language"
        assert h.output == "question"

    def test_integer_language_routes_over_budget_not_typeerror(self):
        """int language_preference (42) must route OVER_BUDGET, not raise TypeError."""
        h = _run("question", participant_data={"language_preference": 42})
        assert h.temp_state["budget_route"] == "OVER_BUDGET"
        assert h.temp_state["budget_reason"] == "missing_language"
        assert h.output == "question"

    # ----- positive controls: en and sw are the only valid language values -----

    def test_english_language_routes_valid(self):
        """'en' is an accepted language — valid state produces VALID route."""
        h = _run("What should I eat?", participant_data={"language_preference": "en"})
        assert h.temp_state["budget_route"] == "VALID"

    def test_swahili_language_routes_valid(self):
        """'sw' is an accepted language — valid state produces VALID route."""
        h = _run("Nina ujauzito wa wiki ngapi?", participant_data={"language_preference": "sw"})
        assert h.temp_state["budget_route"] == "VALID"

    def test_uppercase_en_routes_over_budget(self):
        """'EN' is not exactly 'en' — must route OVER_BUDGET (exact match required)."""
        h = _run("question", participant_data={"language_preference": "EN"})
        assert h.temp_state["budget_route"] == "OVER_BUDGET"

    def test_blank_question_routes_over_budget(self):
        h = _run("   ")  # whitespace only
        assert h.temp_state["budget_route"] == "OVER_BUDGET"
        assert h.temp_state["budget_reason"] == "blank_question"

    def test_empty_question_routes_over_budget(self):
        h = _run("")
        assert h.temp_state["budget_route"] == "OVER_BUDGET"
        assert h.temp_state["budget_reason"] == "blank_question"

    def test_blank_question_returns_input_unchanged(self):
        """Even on failure, input is returned (not substituted)."""
        h = _run("   ")
        assert h.output == "   "

    def test_missing_state_returns_input_unchanged(self):
        h = _run("question", temp_state={})
        assert h.output == "question"

    def test_valid_route_sets_empty_reason(self):
        h = _run("What should I eat?")
        assert h.temp_state["budget_reason"] == ""

    def test_does_not_mutate_participant_data(self):
        orig = {"language_preference": "en", "name": "Akinyi"}
        h = _run("question", participant_data=orig.copy())
        # Node must not write any new participant-data keys
        assert set(h.participant_data.keys()) == {"language_preference", "name"}

    def test_does_not_set_unexpected_temp_state(self):
        """Node sets ONLY budget_route, budget_bytes, budget_reason."""
        h = _run("question")
        budget_keys = {k for k in h.temp_state if k.startswith("budget")}
        assert budget_keys == {"budget_route", "budget_bytes", "budget_reason"}

    def test_swahili_placeholder_in_question_is_literal(self):
        """A participant question that looks like a placeholder is NOT expanded."""
        q = "{temp_state.kb_section} - what does this mean?"
        h = _run(q)
        assert h.output == q  # returned unchanged
        # budget_bytes includes the literal placeholder text, not an expanded value
        expected = compute_prompt_bytes_direct(TINY_TEMPLATE, "", "", "en", q)
        assert h.temp_state["budget_bytes"] == expected

    def test_kb_placeholder_text_not_re_expanded(self):
        """KB section containing placeholder-like text is never re-substituted."""
        kb = "{temp_state.llm_context}"  # would add llm_context again if re-expanded
        h = _run("Q", temp_state={"kb_section": kb, "llm_context": "ACTUAL_CTX"})
        # Rendered system: "SYS\n{temp_state.llm_context}\nACTUAL_CTX\nLang:en"
        # (the KB content is substituted once; not re-processed)
        rendered = "SYS\n" + kb + "\n" + "ACTUAL_CTX" + "\nLang:en"
        expected = len(rendered.encode("utf-8")) + len(b"Q")
        assert h.temp_state["budget_bytes"] == expected

    def test_multibyte_unicode_budget_uses_utf8_bytes_not_chars(self):
        """UTF-8 byte count ≠ character count for non-ASCII text."""
        q = "\u2764" * 100  # 100 × U+2764 = 100 chars but 300 bytes
        h = _run(q)
        expected = compute_prompt_bytes_direct(TINY_TEMPLATE, "", "", "en", q)
        assert h.temp_state["budget_bytes"] == expected
        assert h.temp_state["budget_bytes"] == _BASELINE_RENDERED_STATIC + 300

    def test_no_message_tags_added(self):
        h = _run("question")
        assert h.message_tags == []

    def test_no_session_tags_added(self):
        h = _run("question")
        assert h.session_tags == []

    def test_actual_system_prompt_valid_with_typical_state(self):
        """Real system_prompt.txt with typical registration context is under budget."""
        from ocs.prompt_budget import render_prompt_budget_node  # noqa: PLC0415

        template = (REPO / "ocs" / "prompts" / "system_prompt.txt").read_text()
        source = render_prompt_budget_node(template)
        h = NodeHarness(
            source,
            temp_state={
                "kb_section": "Entry 1: ANC visits are important.\nEntry 2: Eat iron-rich foods.",
                "llm_context": "User's current gestational age: 24 weeks.\nSecond trimester guidance.",
            },
            participant_data={"language_preference": "en"},
        )
        h.output = h.run("What should I eat during pregnancy?")
        assert h.temp_state["budget_route"] == "VALID"
        assert h.temp_state["budget_bytes"] <= BUDGET_BYTES

    def test_over_budget_does_not_set_budget_bytes_to_zero(self):
        """Over-budget path MUST record the actual byte count, not zero."""
        static = _BASELINE_RENDERED_STATIC
        q = "A" * (BUDGET_BYTES - static + 1)
        h = _run(q)
        assert h.temp_state["budget_route"] == "OVER_BUDGET"
        # budget_bytes should be the actual count, not 0
        assert h.temp_state["budget_bytes"] == BUDGET_BYTES + 1

    def test_missing_state_budget_bytes_is_zero(self):
        """Fail-closed branches for missing state set budget_bytes=0 (no measurement)."""
        h = _run("question", temp_state={})
        assert h.temp_state["budget_bytes"] == 0


# ---------------------------------------------------------------------------
# TestGraphContract — build_pipeline includes prompt_budget gate
# ---------------------------------------------------------------------------


class TestIndependentBudgetBoundaries:
    @pytest.mark.parametrize("question", [True, 42, ["Q"]])
    def test_non_string_question_fails_closed(self, question):
        h = _run(question)
        assert h.temp_state["budget_route"] == "OVER_BUDGET"

    def test_generator_sentinel_in_prompt_is_literal(self):
        template = "<<BUDGET_BYTES>> " + TINY_TEMPLATE
        h = _run("Q", template=template)
        expected = compute_prompt_bytes_direct(template, "", "", "en", "Q")
        assert h.temp_state["budget_bytes"] == expected

    @pytest.mark.parametrize("template", ["{{literal}}", "{{temp_state.kb_section}}"])
    def test_escaped_braces_rejected_as_unsupported_template(self, template):
        from ocs.prompt_budget import render_prompt_budget_node  # noqa: PLC0415

        with pytest.raises(ValueError):
            render_prompt_budget_node(template)


class TestGraphContract:
    def test_llm_input_no_longer_connects_directly_to_llm(self):
        """The direct llm_input→llm edge must NOT exist after adding prompt_budget."""
        from ocs.build_pipeline import build_pipeline  # noqa: PLC0415

        edges = {(e["source"], e["target"], e["sourceHandle"]) for e in build_pipeline(0, 0)["data"]["edges"]}
        assert ("llm_input", "llm", "output") not in edges

    def test_llm_input_connects_to_prompt_budget(self):
        from ocs.build_pipeline import build_pipeline  # noqa: PLC0415

        edges = {(e["source"], e["target"], e["sourceHandle"]) for e in build_pipeline(0, 0)["data"]["edges"]}
        assert ("llm_input", "prompt_budget", "output") in edges

    def test_prompt_budget_connects_to_budget_router(self):
        from ocs.build_pipeline import build_pipeline  # noqa: PLC0415

        edges = {(e["source"], e["target"], e["sourceHandle"]) for e in build_pipeline(0, 0)["data"]["edges"]}
        assert ("prompt_budget", "budget_router", "output") in edges

    def test_budget_router_over_budget_routes_to_knowledge_referral(self):
        """OVER_BUDGET (output_0) must route to the existing knowledge_referral node."""
        from ocs.build_pipeline import build_pipeline  # noqa: PLC0415

        edges = {(e["source"], e["target"], e["sourceHandle"]) for e in build_pipeline(0, 0)["data"]["edges"]}
        assert ("budget_router", "knowledge_referral", "output_0") in edges

    def test_budget_router_valid_routes_to_llm(self):
        """VALID (output_1) must route to the LLM node."""
        from ocs.build_pipeline import build_pipeline  # noqa: PLC0415

        edges = {(e["source"], e["target"], e["sourceHandle"]) for e in build_pipeline(0, 0)["data"]["edges"]}
        assert ("budget_router", "llm", "output_1") in edges

    def test_budget_router_config_is_fail_closed(self):
        """budget_router default must be OVER_BUDGET (index 0): missing state → referral."""
        from ocs.build_pipeline import build_pipeline  # noqa: PLC0415

        nodes = {n["id"]: n for n in build_pipeline(0, 0)["data"]["nodes"]}
        assert "budget_router" in nodes
        params = nodes["budget_router"]["data"]["params"]

        assert params["data_source"] == "temp_state"
        assert params["route_key"] == "budget_route"
        assert params["keywords"] == ["OVER_BUDGET", "VALID"]
        assert params["default_keyword_index"] == 0
        assert params["keywords"][params["default_keyword_index"]] == "OVER_BUDGET"

    def test_prompt_budget_node_present_and_code_valid(self):
        """prompt_budget must be a CodeNode with validating source."""
        from ocs.build_pipeline import build_pipeline  # noqa: PLC0415

        nodes = {n["id"]: n for n in build_pipeline(0, 0)["data"]["nodes"]}
        assert "prompt_budget" in nodes
        node = nodes["prompt_budget"]
        assert node["data"]["type"] == "CodeNode"
        # Source must compile as a valid CodeNode.
        make_executor(node["data"]["params"]["code"])

    def test_prompt_budget_uses_actual_system_prompt(self):
        """prompt_budget source must reference the real system_prompt.txt content."""
        from ocs.build_pipeline import build_pipeline  # noqa: PLC0415

        nodes = {n["id"]: n for n in build_pipeline(0, 0)["data"]["nodes"]}
        code = nodes["prompt_budget"]["data"]["params"]["code"]
        # The first line of system_prompt.txt is embedded as a string literal.
        template = (REPO / "ocs" / "prompts" / "system_prompt.txt").read_text()
        # At minimum the first 20 chars of the template must appear in the source.
        assert template[:20] in code


# ---------------------------------------------------------------------------
# Helper — call compute_prompt_bytes directly without import at module level
# ---------------------------------------------------------------------------


def compute_prompt_bytes_direct(template: str, kb_section: str, llm_context: str, lang: str, question: str) -> int:
    from ocs.prompt_budget import compute_prompt_bytes  # noqa: PLC0415

    return compute_prompt_bytes(template, kb_section, llm_context, lang, question)
