"""Behaviour of the output-guard module and node inside the OCS Python-node sandbox.

Covers:
  - load_output_policy / render_output_guard module contract
  - Node sandbox validation (single main, no module globals)
  - Positive controls: ordinary educational answers must NOT block
  - Medicine / dose / diagnosis / never-say blocking (EN, SW, Sheng-mixed)
  - Unverified phone and URL blocking (empty allowlist → all blocked)
  - Verified phone/URL allowlist pass-through
  - >120-word answer blocking
  - Correct language-aware referral (EN vs SW)
  - route:guard_blocked tag with non-sensitive reason
  - Documented boundary/obfuscation gaps

Guard itself must not use a model, network, or credentials; must not log raw
input content; must not mutate participant state; must not claim comprehensive
medical vocabulary coverage.
"""

import copy
import json
import os
import tempfile
from pathlib import Path

import pytest

from ocs.output_policy import load_output_policy, render_output_guard, validate_output_policy
from ocs.tests.sandbox import NodeHarness

REPO_ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = REPO_ROOT / "docs" / "output-policy.json"
CASES_PATH = Path(__file__).resolve().parent / "output_guard_cases.json"


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def policy():
    return load_output_policy(str(POLICY_PATH))


@pytest.fixture(scope="module")
def guard_code(policy):
    return render_output_guard(policy)


def _harness(code: str, lang: str = "en", temp_state: dict | None = None) -> NodeHarness:
    """Build a NodeHarness with the given participant language."""
    participant_data = {"language_preference": lang} if lang else {}
    return NodeHarness(code, temp_state=temp_state or {}, participant_data=participant_data)


# ---------------------------------------------------------------------------
# Module-level contract: load_output_policy
# ---------------------------------------------------------------------------


class TestLoadOutputPolicy:
    def test_loads_policy_json(self):
        policy = load_output_policy(str(POLICY_PATH))
        assert isinstance(policy, dict)

    def test_missing_file_raises(self):
        with pytest.raises((FileNotFoundError, OSError, ValueError)):
            load_output_policy("/nonexistent/path/output-policy.json")

    def test_verified_phone_allowlist_present(self, policy):
        assert "verified_phone_allowlist" in policy
        assert isinstance(policy["verified_phone_allowlist"], list)

    def test_verified_url_allowlist_present(self, policy):
        assert "verified_url_allowlist" in policy
        assert isinstance(policy["verified_url_allowlist"], list)

    def test_allowlists_empty_by_default(self, policy):
        """The starter policy ships with empty allowlists; no unreviewed contacts."""
        assert policy["verified_phone_allowlist"] == []
        assert policy["verified_url_allowlist"] == []

    def test_blocked_referral_en_present(self, policy):
        assert "blocked_referral_en" in policy
        assert len(policy["blocked_referral_en"]) > 10

    def test_blocked_referral_sw_present(self, policy):
        assert "blocked_referral_sw" in policy
        assert len(policy["blocked_referral_sw"]) > 10

    def test_max_words_present_and_positive(self, policy):
        assert "max_words" in policy
        assert isinstance(policy["max_words"], int)
        assert policy["max_words"] > 0

    def test_max_words_is_120(self, policy):
        assert policy["max_words"] == 120

    def test_limits_note_or_pending_vocabulary_present(self, policy):
        """Policy must document its own scope limitations; conservative, not comprehensive."""
        has_limits = any(k in policy for k in ("_limits_note", "_pending_vocabulary", "limits_note"))
        assert has_limits, "Policy must include a limits note documenting conservative scope"

    def test_never_say_patterns_present(self, policy):
        assert "never_say_patterns" in policy
        assert isinstance(policy["never_say_patterns"], list)
        assert len(policy["never_say_patterns"]) >= 1

    def test_medicine_patterns_present(self, policy):
        assert "medicine_patterns" in policy
        assert isinstance(policy["medicine_patterns"], list)
        assert len(policy["medicine_patterns"]) >= 1

    def test_dose_patterns_present(self, policy):
        assert "dose_patterns" in policy
        assert isinstance(policy["dose_patterns"], list)
        assert len(policy["dose_patterns"]) >= 1


# ---------------------------------------------------------------------------
# Module-level contract: render_output_guard
# ---------------------------------------------------------------------------


class TestRenderOutputGuard:
    def test_returns_string(self, guard_code):
        assert isinstance(guard_code, str)

    def test_returned_code_defines_main(self, guard_code):
        assert "def main(" in guard_code

    def test_returned_code_validates_in_sandbox(self, guard_code):
        """Rendered code must pass OCS CodeNode validation (single main, correct sig)."""
        from ocs.tests.sandbox import make_executor

        # make_executor raises CodeValidationError on invalid code
        make_executor(guard_code)

    def test_no_module_level_globals_beyond_main(self, guard_code):
        """OCS executor uses separate globals/locals; module-level constants are
        not visible to main.  render_output_guard must embed everything inside main."""
        import ast

        tree = ast.parse(guard_code)
        # Only 'main' is a top-level function definition; data must live inside main
        top_level_defs = [node for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]
        assert len(top_level_defs) == 1
        assert top_level_defs[0].name == "main"

    def test_policy_embedded_verified_phone_allowlist(self, guard_code):
        """Rendered code must contain the allowlist value so the node runs correctly."""
        # An empty list as [] should appear
        assert "[]" in guard_code or "verified_phone" in guard_code

    def test_blocked_referral_en_is_delivered_exactly(self, policy, guard_code):
        # Encoded source need not contain a contiguous plaintext substring.
        assert _harness(guard_code).run("") == policy["blocked_referral_en"]

    def test_blocked_referral_sw_embedded(self, policy, guard_code):
        snippet = policy["blocked_referral_sw"][:20]
        assert snippet in guard_code


# ---------------------------------------------------------------------------
# Cases from fixture file
# ---------------------------------------------------------------------------

_cases_data = json.loads(CASES_PATH.read_text())
_cases = _cases_data["cases"]


@pytest.mark.parametrize("case", _cases, ids=[c["id"] for c in _cases])
def test_guard_case(guard_code, case):
    """Parametrized over output_guard_cases.json.

    Positive controls prove ordinary educational answers do NOT block.
    Blocking cases prove the guard catches medicine/dose/diagnosis/contact/length violations.
    Boundary cases document known limitations (expect='pass') without claiming coverage.
    """
    h = _harness(guard_code, lang=case.get("lang", "en"))
    output = h.run(case["input"])

    if case["expect"] == "pass":
        assert h.temp_state.get("guard_route") == "PASS", (
            f"Case {case['id']!r}: expected PASS but got guard_route="
            f"{h.temp_state.get('guard_route')!r}. Output: {output!r}"
        )
        assert output == case["input"], f"Case {case['id']!r}: expected input returned unchanged"
        assert "route:guard_blocked" not in h.message_tags

    else:  # block
        assert h.temp_state.get("guard_route") == "guard_blocked", (
            f"Case {case['id']!r}: expected guard_blocked but guard_route={h.temp_state.get('guard_route')!r}"
        )
        assert "route:guard_blocked" in h.message_tags

        reason_key = case.get("block_reason_contains")
        if reason_key:
            reason_tags = [t for t in h.message_tags if t.startswith("guard_blocked_reason:")]
            assert any(reason_key in t for t in reason_tags), (
                f"Case {case['id']!r}: expected reason tag containing {reason_key!r}, got tags: {reason_tags}"
            )


# ---------------------------------------------------------------------------
# Language-aware referral
# ---------------------------------------------------------------------------


class TestBlockedReferralLanguage:
    def test_blocked_en_returns_en_referral(self, guard_code, policy):
        h = _harness(guard_code, lang="en")
        output = h.run("Take 500mg amoxicillin.")
        # Must return a non-empty referral (not the blocked input, not empty)
        assert output == policy["blocked_referral_en"]
        assert output != "Take 500mg amoxicillin."

    def test_blocked_sw_returns_sw_referral(self, guard_code, policy):
        h = _harness(guard_code, lang="sw")
        output = h.run("Tumia 500mg amoxicillin.")
        assert output == policy["blocked_referral_sw"]
        assert output != "Tumia 500mg amoxicillin."

    def test_blocked_unknown_lang_defaults_to_en_referral(self, guard_code, policy):
        """Unknown language_preference defaults to English referral (not Swahili)."""
        h = _harness(guard_code, lang="fr")
        output = h.run("Take 500mg amoxicillin.")
        assert output == policy["blocked_referral_en"]

    def test_blocked_no_lang_defaults_to_en_referral(self, guard_code, policy):
        """Missing language_preference defaults to English referral."""
        h = NodeHarness(guard_code, participant_data={})
        output = h.run("Take 500mg amoxicillin.")
        assert output == policy["blocked_referral_en"]


# ---------------------------------------------------------------------------
# Tags: non-sensitive reasons
# ---------------------------------------------------------------------------


class TestTags:
    def test_blocked_adds_route_tag(self, guard_code):
        h = _harness(guard_code)
        h.run("Take 500mg amoxicillin.")
        assert "route:guard_blocked" in h.message_tags

    def test_blocked_reason_tag_non_sensitive(self, guard_code):
        """Reason tag must not contain raw input content (no PII/query echo)."""
        sensitive_input = "My name is Jane. Take 500mg amoxicillin."
        h = _harness(guard_code)
        h.run(sensitive_input)
        reason_tags = [t for t in h.message_tags if t.startswith("guard_blocked_reason:")]
        assert len(reason_tags) >= 1
        for tag in reason_tags:
            assert "Jane" not in tag
            assert "amoxicillin" not in tag.lower() or tag == "guard_blocked_reason:medicine_name"

    def test_pass_sets_guard_route_pass(self, guard_code):
        h = _harness(guard_code)
        h.run("Antenatal visits help you stay healthy during pregnancy.")
        assert h.temp_state.get("guard_route") == "PASS"

    def test_pass_adds_no_blocked_tags(self, guard_code):
        h = _harness(guard_code)
        h.run("Visit your health worker regularly.")
        blocked_tags = [t for t in h.message_tags if "guard_blocked" in t]
        assert blocked_tags == []


# ---------------------------------------------------------------------------
# Allowlist pass-through (non-empty allowlists rendered on the fly)
# ---------------------------------------------------------------------------


class TestAllowlist:
    @pytest.fixture
    def policy_with_phone(self, policy):
        import copy

        p = copy.deepcopy(policy)
        p["verified_phone_allowlist"] = ["+254800000000"]
        return p

    @pytest.fixture
    def policy_with_url(self, policy):
        import copy

        p = copy.deepcopy(policy)
        p["verified_url_allowlist"] = ["https://www.who.int/tools"]
        return p

    def test_verified_phone_passes(self, policy_with_phone):
        code = render_output_guard(policy_with_phone)
        h = _harness(code, lang="en")
        output = h.run("If you need help you can call +254800000000 for support.")
        assert h.temp_state.get("guard_route") == "PASS"
        assert output == "If you need help you can call +254800000000 for support."

    def test_unverified_phone_still_blocked(self, policy_with_phone):
        code = render_output_guard(policy_with_phone)
        h = _harness(code, lang="en")
        h.run("Call 0712345678 instead.")
        assert h.temp_state.get("guard_route") == "guard_blocked"

    def test_verified_url_passes(self, policy_with_url):
        code = render_output_guard(policy_with_url)
        h = _harness(code, lang="en")
        output = h.run("Visit https://www.who.int/tools for information.")
        assert h.temp_state.get("guard_route") == "PASS"
        assert output == "Visit https://www.who.int/tools for information."

    def test_unverified_url_still_blocked(self, policy_with_url):
        code = render_output_guard(policy_with_url)
        h = _harness(code, lang="en")
        h.run("Visit https://example.com for more.")
        assert h.temp_state.get("guard_route") == "guard_blocked"


# ---------------------------------------------------------------------------
# Word-count boundary
# ---------------------------------------------------------------------------


class TestWordCount:
    def test_exactly_120_words_passes(self, guard_code):
        # 120 words, no blocked terms
        words = ["Antenatal"] + ["care"] * 119
        text = " ".join(words)
        assert len(text.split()) == 120
        h = _harness(guard_code)
        h.run(text)
        assert h.temp_state.get("guard_route") == "PASS"

    def test_121_words_blocked(self, guard_code):
        words = ["Antenatal"] + ["care"] * 120
        text = " ".join(words)
        assert len(text.split()) == 121
        h = _harness(guard_code)
        h.run(text)
        assert h.temp_state.get("guard_route") == "guard_blocked"

    def test_too_long_reason_tag(self, guard_code):
        words = ["visit"] * 125
        h = _harness(guard_code)
        h.run(" ".join(words))
        reason_tags = [t for t in h.message_tags if t.startswith("guard_blocked_reason:")]
        assert any("too_long" in t for t in reason_tags)


# ---------------------------------------------------------------------------
# Guard does not mutate participant data
# ---------------------------------------------------------------------------


class TestNoParticipantMutation:
    def test_blocked_does_not_mutate_participant_data(self, guard_code):
        initial = {"language_preference": "en", "name": "Mama", "weeks": "24"}
        h = NodeHarness(guard_code, participant_data=dict(initial))
        h.run("Take 500mg amoxicillin.")
        assert h.participant_data == initial

    def test_pass_does_not_mutate_participant_data(self, guard_code):
        initial = {"language_preference": "en", "name": "Mama", "weeks": "24"}
        h = NodeHarness(guard_code, participant_data=dict(initial))
        h.run("Visit your health worker regularly.")
        assert h.participant_data == initial


# =============================================================================
# REPAIR-1: acceptance findings from coordinator pass 1
# =============================================================================
#
# Tests in this section were added BEFORE the implementation fix.
# Each class title maps to a defect in acceptance-findings-1.md §25.
# =============================================================================


def _make_policy_file(overrides: dict) -> str:
    """Write a minimal valid policy dict (with overrides) to a temp file."""
    base = json.loads((REPO_ROOT / "docs" / "output-policy.json").read_text())
    base.update(overrides)
    fd, path = tempfile.mkstemp(suffix=".json")
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        json.dump(base, fh)
    return path


class TestPolicySchemaValidation:
    """Policy schema: bool/negative/over-120 max_words, invalid allowlist
    elements and unsafe referrals must all raise ValueError, not silently
    pass through to render.  render_output_guard must also validate.
    """

    @pytest.fixture
    def base_policy(self, policy):
        return copy.deepcopy(policy)

    # --- max_words type/range ---

    def test_max_words_bool_true_rejected(self, base_policy):
        """True is a bool subclass of int; must be rejected explicitly."""
        from ocs.output_policy import validate_output_policy

        base_policy["max_words"] = True
        with pytest.raises(ValueError, match="max_words"):
            validate_output_policy(base_policy)

    def test_max_words_bool_false_rejected(self, base_policy):
        from ocs.output_policy import validate_output_policy

        base_policy["max_words"] = False
        with pytest.raises(ValueError, match="max_words"):
            validate_output_policy(base_policy)

    def test_max_words_negative_rejected(self, base_policy):
        from ocs.output_policy import validate_output_policy

        base_policy["max_words"] = -1
        with pytest.raises(ValueError, match="max_words"):
            validate_output_policy(base_policy)

    def test_max_words_zero_rejected(self, base_policy):
        from ocs.output_policy import validate_output_policy

        base_policy["max_words"] = 0
        with pytest.raises(ValueError, match="max_words"):
            validate_output_policy(base_policy)

    def test_max_words_over_120_rejected(self, base_policy):
        from ocs.output_policy import validate_output_policy

        base_policy["max_words"] = 200
        with pytest.raises(ValueError, match="max_words"):
            validate_output_policy(base_policy)

    def test_max_words_120_accepted(self, base_policy):
        from ocs.output_policy import validate_output_policy

        base_policy["max_words"] = 120
        validate_output_policy(base_policy)  # must not raise

    def test_max_words_1_accepted(self, base_policy):
        """max_words=1 is a valid integer; referral must also fit (parity applies)."""
        from ocs.output_policy import validate_output_policy

        base_policy["max_words"] = 1
        # Referral must be <=1 word so the parity check passes
        base_policy["blocked_referral_en"] = "Help."
        base_policy["blocked_referral_sw"] = "Saidia."
        validate_output_policy(base_policy)  # must not raise

    # --- allowlist element validation ---

    def test_phone_allowlist_int_element_rejected(self, base_policy):
        from ocs.output_policy import validate_output_policy

        base_policy["verified_phone_allowlist"] = [9195551234]
        with pytest.raises(ValueError, match="verified_phone_allowlist"):
            validate_output_policy(base_policy)

    def test_phone_allowlist_empty_string_rejected(self, base_policy):
        from ocs.output_policy import validate_output_policy

        base_policy["verified_phone_allowlist"] = [""]
        with pytest.raises(ValueError, match="verified_phone_allowlist"):
            validate_output_policy(base_policy)

    def test_url_allowlist_int_element_rejected(self, base_policy):
        from ocs.output_policy import validate_output_policy

        base_policy["verified_url_allowlist"] = [42]
        with pytest.raises(ValueError, match="verified_url_allowlist"):
            validate_output_policy(base_policy)

    def test_url_allowlist_empty_string_rejected(self, base_policy):
        from ocs.output_policy import validate_output_policy

        base_policy["verified_url_allowlist"] = [""]
        with pytest.raises(ValueError, match="verified_url_allowlist"):
            validate_output_policy(base_policy)

    # --- referral safety ---

    def test_referral_en_empty_rejected(self, base_policy):
        from ocs.output_policy import validate_output_policy

        base_policy["blocked_referral_en"] = ""
        with pytest.raises(ValueError, match="blocked_referral_en"):
            validate_output_policy(base_policy)

    def test_referral_en_whitespace_only_rejected(self, base_policy):
        from ocs.output_policy import validate_output_policy

        base_policy["blocked_referral_en"] = "   "
        with pytest.raises(ValueError, match="blocked_referral_en"):
            validate_output_policy(base_policy)

    def test_referral_en_containing_url_rejected(self, base_policy):
        from ocs.output_policy import validate_output_policy

        base_policy["blocked_referral_en"] = "Please visit https://example.com for help."
        with pytest.raises(ValueError, match="blocked_referral_en"):
            validate_output_policy(base_policy)

    def test_referral_en_containing_phone_rejected(self, base_policy):
        from ocs.output_policy import validate_output_policy

        base_policy["blocked_referral_en"] = "Call 0712345678 for assistance."
        with pytest.raises(ValueError, match="blocked_referral_en"):
            validate_output_policy(base_policy)

    def test_referral_sw_empty_rejected(self, base_policy):
        from ocs.output_policy import validate_output_policy

        base_policy["blocked_referral_sw"] = ""
        with pytest.raises(ValueError, match="blocked_referral_sw"):
            validate_output_policy(base_policy)

    def test_referral_sw_containing_url_rejected(self, base_policy):
        from ocs.output_policy import validate_output_policy

        base_policy["blocked_referral_sw"] = "Angalia www.example.ke kwa maelezo zaidi."
        with pytest.raises(ValueError, match="blocked_referral_sw"):
            validate_output_policy(base_policy)

    # --- render_output_guard also validates ---

    def test_render_validates_bool_max_words(self, base_policy):
        """render_output_guard must reject an invalid policy, not just trust callers."""
        base_policy["max_words"] = True
        with pytest.raises(ValueError, match="max_words"):
            render_output_guard(base_policy)

    def test_render_validates_over_120_max_words(self, base_policy):
        base_policy["max_words"] = 999
        with pytest.raises(ValueError, match="max_words"):
            render_output_guard(base_policy)

    # --- load_output_policy propagates validation ---

    def test_load_rejects_bool_max_words(self):
        path = _make_policy_file({"max_words": True})
        try:
            with pytest.raises(ValueError, match="max_words"):
                load_output_policy(path)
        finally:
            os.unlink(path)

    def test_load_rejects_over_120_max_words(self):
        path = _make_policy_file({"max_words": 500})
        try:
            with pytest.raises(ValueError, match="max_words"):
                load_output_policy(path)
        finally:
            os.unlink(path)


class TestEmptyOutputHandling:
    """Empty or whitespace-only AI output must be blocked, not forwarded to End."""

    def test_empty_string_blocked(self, guard_code):
        h = _harness(guard_code)
        h.run("")
        assert h.temp_state.get("guard_route") == "guard_blocked"
        assert any("empty_output" in t for t in h.message_tags)

    def test_whitespace_only_blocked(self, guard_code):
        h = _harness(guard_code)
        h.run("   \n\t  ")
        assert h.temp_state.get("guard_route") == "guard_blocked"
        assert any("empty_output" in t for t in h.message_tags)

    def test_newlines_only_blocked(self, guard_code):
        h = _harness(guard_code)
        h.run("\n\n\n")
        assert h.temp_state.get("guard_route") == "guard_blocked"


class TestSuspiciousURLPatterns:
    """Obfuscated schemes, bare domains, Markdown links, URL shorteners and
    credential-bearing URLs must all be blocked.  These cases bypass the
    https:// / www. prefix that the main allowlist URL check requires.
    """

    def test_hxxps_blocked(self, guard_code):
        """hxxps:// is the standard defang notation; must be explicitly blocked."""
        h = _harness(guard_code)
        h.run("Visit hxxps://example.com for more information.")
        assert h.temp_state.get("guard_route") == "guard_blocked"

    def test_hxxp_blocked(self, guard_code):
        h = _harness(guard_code)
        h.run("See hxxp://example.com/health")
        assert h.temp_state.get("guard_route") == "guard_blocked"

    def test_ftp_scheme_blocked(self, guard_code):
        h = _harness(guard_code)
        h.run("Download from ftp://example.com/guide.pdf")
        assert h.temp_state.get("guard_route") == "guard_blocked"

    def test_data_scheme_blocked(self, guard_code):
        h = _harness(guard_code)
        h.run("See data:text/html,<b>hello</b> for details.")
        assert h.temp_state.get("guard_route") == "guard_blocked"

    def test_javascript_scheme_blocked(self, guard_code):
        h = _harness(guard_code)
        h.run("Run javascript:alert(1) in browser.")
        assert h.temp_state.get("guard_route") == "guard_blocked"

    def test_markdown_link_blocked_explicit_reason(self, guard_code):
        """Markdown links embed URLs that bypass prefix detection."""
        h = _harness(guard_code)
        h.run("Please [click here](https://example.com/health) for more.")
        assert h.temp_state.get("guard_route") == "guard_blocked"

    def test_url_with_credentials_blocked_explicit(self, guard_code):
        """user:pass@ in URL indicates credential exfiltration risk."""
        h = _harness(guard_code)
        h.run("Visit https://user:pass@example.com for help.")
        assert h.temp_state.get("guard_route") == "guard_blocked"

    def test_url_shortener_bit_ly_blocked(self, guard_code):
        h = _harness(guard_code)
        h.run("Visit bit.ly/healthinfo for more details.")
        assert h.temp_state.get("guard_route") == "guard_blocked"

    def test_url_shortener_tinyurl_blocked(self, guard_code):
        h = _harness(guard_code)
        h.run("See tinyurl.com/abc123 for guidance.")
        assert h.temp_state.get("guard_route") == "guard_blocked"

    def test_bare_domain_com_blocked(self, guard_code):
        """Bare domain reference without scheme must be blocked."""
        h = _harness(guard_code)
        h.run("For information visit example.com and check the resources.")
        assert h.temp_state.get("guard_route") == "guard_blocked"

    def test_bare_domain_ke_blocked(self, guard_code):
        """Bare .ke domain reference must be blocked."""
        h = _harness(guard_code)
        h.run("Visit health.ke for local guidance on antenatal care.")
        assert h.temp_state.get("guard_route") == "guard_blocked"


class TestExactURLAllowlistSemantics:
    """URL allowlist must use exact hostname match (after www. strip).
    Arbitrary subdomains of an allowlisted domain must NOT be approved.
    """

    @pytest.fixture
    def code_with_who(self, policy):
        p = copy.deepcopy(policy)
        p["verified_url_allowlist"] = ["https://www.who.int/tools"]
        return render_output_guard(p)

    def test_exact_full_url_passes(self, code_with_who):
        """Exact full URL in allowlist passes."""
        h = _harness(code_with_who)
        h.run("Visit https://www.who.int/tools for information.")
        assert h.temp_state.get("guard_route") == "PASS"

    def test_www_bare_without_https_blocked(self, code_with_who):
        """www.who.int/tools without https:// scheme must be blocked (non-HTTPS)."""
        h = _harness(code_with_who)
        h.run("See www.who.int/tools for details.")
        assert h.temp_state.get("guard_route") == "guard_blocked"

    def test_subdomain_not_approved(self, code_with_who):
        """news.who.int is NOT who.int; must be blocked.

        Previous implementation used endswith('.who.int') which allowed any
        subdomain.  Exact hostname match only.
        """
        h = _harness(code_with_who)
        h.run("Visit https://news.who.int/tools for more.")
        assert h.temp_state.get("guard_route") == "guard_blocked", (
            "news.who.int must be blocked; exact hostname match only, no arbitrary subdomain approval"
        )

    def test_attacker_domain_not_approved(self, code_with_who):
        """malicious.who.int.attack.com must be blocked."""
        h = _harness(code_with_who)
        h.run("Visit https://who.int.attacker.com for more.")
        assert h.temp_state.get("guard_route") == "guard_blocked"


class TestShortHelplinesBlocked:
    """Short 3-4 digit emergency/helpline numbers appearing in AI output must
    be blocked when not in verified_phone_allowlist (which is empty by default).

    The emergency response BRANCH bypasses this guard entirely (separate pipeline
    path); no changes to emergency_response.py are required or made.  This test
    verifies that an AI-generated output containing these numbers is blocked.
    """

    def test_999_blocked(self, guard_code):
        h = _harness(guard_code)
        h.run("If there is an emergency please call 999 immediately.")
        assert h.temp_state.get("guard_route") == "guard_blocked"
        assert any("unverified_phone" in t for t in h.message_tags)

    def test_112_blocked(self, guard_code):
        h = _harness(guard_code)
        h.run("You can call 112 for emergency services in Kenya.")
        assert h.temp_state.get("guard_route") == "guard_blocked"

    def test_1199_blocked(self, guard_code):
        h = _harness(guard_code)
        h.run("Contact Red Cross at 1199 for support.")
        assert h.temp_state.get("guard_route") == "guard_blocked"

    def test_922_blocked(self, guard_code):
        h = _harness(guard_code)
        h.run("Call the national ambulance on 922.")
        assert h.temp_state.get("guard_route") == "guard_blocked"

    def test_pregnancy_week_32_not_blocked(self, guard_code):
        """Week 32 (2 digits) must NOT trigger short helpline detection."""
        h = _harness(guard_code)
        h.run("At 32 weeks you should discuss your birth plan with your health worker.")
        assert h.temp_state.get("guard_route") == "PASS"

    def test_pregnancy_week_36_not_blocked(self, guard_code):
        """Week 36 (2 digits) must NOT trigger short helpline detection."""
        h = _harness(guard_code)
        h.run("At 36 weeks your baby is nearly ready.")
        assert h.temp_state.get("guard_route") == "PASS"

    def test_short_helpline_in_allowlist_passes(self, policy):
        """999 in the verified_phone_allowlist must pass (operator override)."""
        p = copy.deepcopy(policy)
        p["verified_phone_allowlist"] = ["999"]
        code = render_output_guard(p)
        h = _harness(code)
        h.run("In an emergency call 999.")
        assert h.temp_state.get("guard_route") == "PASS"


class TestOverlongDigitRunBoundary:
    """Phone pattern must NOT partially match within overlong digit sequences.
    A 20-digit batch reference is not a phone number; blocking it is a false
    positive.  10-digit Kenyan numbers must still be caught.
    """

    def test_20_digit_run_not_partially_matched(self, guard_code):
        """12345678901234567890 must PASS — no partial phone match inside it."""
        h = _harness(guard_code)
        h.run("The reference batch number is 12345678901234567890.")
        assert h.temp_state.get("guard_route") == "PASS", (
            "20-digit batch number should not be partially matched as a phone number"
        )

    def test_10_digit_phone_still_blocked(self, guard_code):
        """10-digit Kenyan number must still be caught after boundary fix."""
        h = _harness(guard_code)
        h.run("Call 0712345678 for help.")
        assert h.temp_state.get("guard_route") == "guard_blocked"

    def test_12_digit_intl_phone_still_blocked(self, guard_code):
        """12-digit international format must still be caught."""
        h = _harness(guard_code)
        h.run("Contact +254712345678 for assistance.")
        assert h.temp_state.get("guard_route") == "guard_blocked"


class TestZeroWidthNormalization:
    """Zero-width characters inserted to split keyword or URL patterns must
    be stripped before all guard checks.  This prevents trivial bypass.
    """

    def test_zero_width_space_in_medicine_blocked(self, guard_code):
        """U+200B (ZERO WIDTH SPACE) inside 'amoxicillin' must not bypass check."""
        h = _harness(guard_code)
        h.run("Take amox\u200bicillin for the infection.")
        assert h.temp_state.get("guard_route") == "guard_blocked"

    def test_zero_width_joiner_in_medicine_blocked(self, guard_code):
        """U+200D (ZERO WIDTH JOINER) inside 'paracetamol'."""
        h = _harness(guard_code)
        h.run("Use parace\u200dtamol for mild pain.")
        assert h.temp_state.get("guard_route") == "guard_blocked"

    def test_soft_hyphen_in_medicine_blocked(self, guard_code):
        """U+00AD (SOFT HYPHEN) inside 'diazepam'."""
        h = _harness(guard_code)
        h.run("Avoid diaze\u00adpam during pregnancy.")
        assert h.temp_state.get("guard_route") == "guard_blocked"

    def test_zero_width_in_never_say_blocked(self, guard_code):
        """ZWSP splitting 'diagnosis' must not bypass never-say check."""
        h = _harness(guard_code)
        h.run("The diag\u200bnosis is confirmed.")
        assert h.temp_state.get("guard_route") == "guard_blocked"


# =============================================================================
# REPAIR-2: bounded fix for parent acceptance findings
# R1  (example.com) bypasses bare-domain guard
# R2  +1 (202) 555-0100 bypasses phone guard
# R3  blocked_referral_en='Call 999.' passes policy validation
# R4  blocked_referral_en='Take amoxicillin.' passes policy validation
# R5  exact full HTTPS URL in allowlist cannot pass (hostname comparison wrong)
# R6  verified_phone_allowlist='999' (string) passes validate_output_policy
# =============================================================================


class TestRepair2ParenContacts:
    """R1 + R2: parenthesised bare domains and international phone formats must
    be caught.  Positive controls (pregnancy weeks, plain educational text) must
    still pass untouched.
    """

    # --- R1: parenthesised bare domain ---

    def test_paren_bare_domain_blocked(self, guard_code):
        """(example.com) in parentheses must be blocked."""
        h = _harness(guard_code)
        h.run("Read (example.com) for more information.")
        assert h.temp_state.get("guard_route") == "guard_blocked"

    def test_paren_bare_domain_ke_blocked(self, guard_code):
        h = _harness(guard_code)
        h.run("Visit (health.ke) for more details.")
        assert h.temp_state.get("guard_route") == "guard_blocked"

    def test_comma_then_bare_domain_blocked(self, guard_code):
        """Comma immediately before domain should still be caught."""
        h = _harness(guard_code)
        h.run("For more see example.org, which has information.")
        # 'example' preceded by space; this already passes via current pattern
        assert h.temp_state.get("guard_route") == "guard_blocked"

    # --- R2: international phone with parentheses ---

    def test_north_american_paren_phone_blocked(self, guard_code):
        """+1 (202) 555-0100 — area code in parentheses must be blocked."""
        h = _harness(guard_code)
        h.run("Call +1 (202) 555-0100 for help.")
        assert h.temp_state.get("guard_route") == "guard_blocked"
        assert any("unverified_phone" in t for t in h.message_tags)

    def test_us_area_code_paren_format_blocked(self, guard_code):
        """(800) 555-1234 format without country code."""
        h = _harness(guard_code)
        h.run("Contact (800) 555-1234 for assistance.")
        assert h.temp_state.get("guard_route") == "guard_blocked"

    def test_kenya_paren_format_blocked(self, guard_code):
        """(+254) 712 345 678 format."""
        h = _harness(guard_code)
        h.run("Call (+254) 712 345 678 for more information.")
        assert h.temp_state.get("guard_route") == "guard_blocked"

    # --- positive controls: weeks and ordinary text untouched ---

    def test_pregnancy_weeks_in_parens_not_blocked(self, guard_code):
        """'32 weeks (or about 8 months)' must not trigger phone detection."""
        h = _harness(guard_code)
        h.run("At 32 weeks (or about 8 months) you should discuss your birth plan.")
        assert h.temp_state.get("guard_route") == "PASS"

    def test_ordinary_paren_text_not_blocked(self, guard_code):
        h = _harness(guard_code)
        h.run("Antenatal care (also called prenatal care) helps you have a healthy pregnancy.")
        assert h.temp_state.get("guard_route") == "PASS"

    def test_en_educational_still_passes(self, guard_code):
        h = _harness(guard_code)
        h.run("Ask your health worker for advice about your dietary needs.")
        assert h.temp_state.get("guard_route") == "PASS"


class TestRepair2ReferralValidation:
    """R3 + R4: fixed referral texts must pass through the same content checks
    as ordinary AI output.  An unsafe referral cannot be a leakage vector.
    Current valid default referrals must still be accepted.
    """

    def test_referral_en_with_999_rejected(self, policy):
        p = copy.deepcopy(policy)
        p["blocked_referral_en"] = "Call 999."
        with pytest.raises(ValueError, match="blocked_referral_en"):
            validate_output_policy(p)

    def test_referral_en_with_112_rejected(self, policy):
        p = copy.deepcopy(policy)
        p["blocked_referral_en"] = "Dial 112 immediately."
        with pytest.raises(ValueError, match="blocked_referral_en"):
            validate_output_policy(p)

    def test_referral_en_with_medicine_rejected(self, policy):
        p = copy.deepcopy(policy)
        p["blocked_referral_en"] = "Take amoxicillin for the infection."
        with pytest.raises(ValueError, match="blocked_referral_en"):
            validate_output_policy(p)

    def test_referral_en_with_diagnosis_wording_rejected(self, policy):
        p = copy.deepcopy(policy)
        p["blocked_referral_en"] = "Your condition is preeclampsia, see a doctor."
        with pytest.raises(ValueError, match="blocked_referral_en"):
            validate_output_policy(p)

    def test_referral_sw_with_999_rejected(self, policy):
        p = copy.deepcopy(policy)
        p["blocked_referral_sw"] = "Piga simu 999 sasa hivi."
        with pytest.raises(ValueError, match="blocked_referral_sw"):
            validate_output_policy(p)

    def test_referral_sw_with_medicine_rejected(self, policy):
        p = copy.deepcopy(policy)
        p["blocked_referral_sw"] = "Tumia metronidazole kutibu maambukizi."
        with pytest.raises(ValueError, match="blocked_referral_sw"):
            validate_output_policy(p)

    def test_valid_default_en_referral_accepted(self, policy):
        """Current default EN referral must still pass."""
        validate_output_policy(policy)  # must not raise

    def test_valid_default_sw_referral_accepted(self, policy):
        """Current default SW referral must still pass."""
        validate_output_policy(policy)  # must not raise

    def test_render_rejects_unsafe_referral(self, policy):
        """render_output_guard must also reject an unsafe referral."""
        p = copy.deepcopy(policy)
        p["blocked_referral_en"] = "Call 999."
        with pytest.raises(ValueError):
            render_output_guard(p)


class TestRepair2ExactURLAllowlist:
    """R5: allowlist entries are exact full https:// URL destinations.
    Non-HTTPS, different paths/queries and lookalike hosts all block.
    The original host-only semantics are corrected here.
    """

    @pytest.fixture
    def approved_code(self, policy):
        p = copy.deepcopy(policy)
        p["verified_url_allowlist"] = ["https://www.who.int/approved"]
        return render_output_guard(p)

    def test_exact_approved_url_passes(self, approved_code):
        h = _harness(approved_code)
        h.run("Visit https://www.who.int/approved for information.")
        assert h.temp_state.get("guard_route") == "PASS"

    def test_exact_approved_url_with_trailing_period_passes(self, approved_code):
        """Sentence-ending period after URL must be stripped."""
        h = _harness(approved_code)
        h.run("Visit https://www.who.int/approved.")
        assert h.temp_state.get("guard_route") == "PASS"

    def test_same_host_different_path_blocked(self, approved_code):
        """Same host, different path: blocked (not host-wide approval)."""
        h = _harness(approved_code)
        h.run("Visit https://www.who.int/other-page for information.")
        assert h.temp_state.get("guard_route") == "guard_blocked"

    def test_same_host_different_query_blocked(self, approved_code):
        """Same host+path with query string: blocked."""
        h = _harness(approved_code)
        h.run("Visit https://www.who.int/approved?foo=bar for more.")
        assert h.temp_state.get("guard_route") == "guard_blocked"

    def test_lookalike_host_blocked(self, approved_code):
        """Lookalike domain: blocked."""
        h = _harness(approved_code)
        h.run("Visit https://www.who.int.evil.com/approved for info.")
        assert h.temp_state.get("guard_route") == "guard_blocked"

    def test_http_scheme_blocked_even_if_same_path(self, approved_code):
        """http:// (non-HTTPS) is always blocked."""
        h = _harness(approved_code)
        h.run("Visit http://www.who.int/approved for information.")
        assert h.temp_state.get("guard_route") == "guard_blocked"

    def test_www_bare_without_https_blocked(self, approved_code):
        """www.who.int/approved without https:// scheme is blocked."""
        h = _harness(approved_code)
        h.run("See www.who.int/approved for details.")
        assert h.temp_state.get("guard_route") == "guard_blocked"

    # --- allowlist entry validation ---

    def test_url_allowlist_entry_non_https_rejected(self, policy):
        """URL allowlist entry that is not https:// must be rejected at load time."""
        p = copy.deepcopy(policy)
        p["verified_url_allowlist"] = ["http://www.who.int/approved"]
        with pytest.raises(ValueError, match="verified_url_allowlist"):
            validate_output_policy(p)

    def test_url_allowlist_entry_hostname_only_rejected(self, policy):
        """Hostname-only entry (no https://) must be rejected."""
        p = copy.deepcopy(policy)
        p["verified_url_allowlist"] = ["who.int"]  # hostname only, not a full URL
        with pytest.raises(ValueError, match="verified_url_allowlist"):
            validate_output_policy(p)

    def test_url_allowlist_entry_with_credentials_rejected(self, policy):
        p = copy.deepcopy(policy)
        p["verified_url_allowlist"] = ["https://user:pass@example.com/path"]
        with pytest.raises(ValueError, match="verified_url_allowlist"):
            validate_output_policy(p)

    def test_url_allowlist_valid_https_entry_accepted(self, policy):
        p = copy.deepcopy(policy)
        p["verified_url_allowlist"] = ["https://www.who.int/approved"]
        validate_output_policy(p)  # must not raise


class TestRepair2SchemaValidator:
    """R6: validate_output_policy must check REQUIRED_KEY types explicitly;
    .get() or [] must not silently accept wrong-typed or missing values.
    """

    def test_string_phone_allowlist_rejected(self, policy):
        """verified_phone_allowlist='999' (string not list) must be rejected."""
        p = copy.deepcopy(policy)
        p["verified_phone_allowlist"] = "999"
        with pytest.raises(ValueError, match="verified_phone_allowlist"):
            validate_output_policy(p)

    def test_string_url_allowlist_rejected(self, policy):
        p = copy.deepcopy(policy)
        p["verified_url_allowlist"] = "who.int"
        with pytest.raises(ValueError, match="verified_url_allowlist"):
            validate_output_policy(p)

    def test_missing_max_words_rejected(self, policy):
        p = copy.deepcopy(policy)
        del p["max_words"]
        with pytest.raises(ValueError, match="max_words"):
            validate_output_policy(p)

    def test_missing_short_helpline_patterns_rejected(self, policy):
        p = copy.deepcopy(policy)
        del p["short_helpline_patterns"]
        with pytest.raises(ValueError, match="short_helpline_patterns"):
            validate_output_policy(p)

    def test_int_referral_en_rejected(self, policy):
        p = copy.deepcopy(policy)
        p["blocked_referral_en"] = 42
        with pytest.raises(ValueError, match="blocked_referral_en"):
            validate_output_policy(p)

    def test_none_suspicious_url_patterns_rejected(self, policy):
        p = copy.deepcopy(policy)
        p["suspicious_url_patterns"] = None
        with pytest.raises(ValueError, match="suspicious_url_patterns"):
            validate_output_policy(p)


# =============================================================================
# DESIGN-RESET: one authoritative predicate, URL path/query/slash semantics
#
# All findings from evidence/25/repair-2/parent-policy-parity-and-url-probe.json
# =============================================================================


class TestDesignResetParity:
    """Single classifier must be used for both host validation and runtime node.

    Parity means: if guard_classify(text, policy) returns blocked, then
    validate_output_policy with that text as a referral must raise ValueError.
    If not, the two code paths diverge and can be bypassed.
    """

    def _assert_referral_rejected(self, policy, text, key="blocked_referral_en"):
        p = copy.deepcopy(policy)
        p[key] = text
        with pytest.raises(ValueError, match=key):
            validate_output_policy(p)

    def test_parenthesized_domain_referral_rejected(self, policy):
        """(example.com) is blocked at runtime; validator must also reject it."""
        self._assert_referral_rejected(policy, "Read (example.com) for more information.")

    def test_bare_domain_referral_rejected(self, policy):
        """example.com bare domain is blocked at runtime; validator must also reject it."""
        self._assert_referral_rejected(policy, "Visit example.com for details.")

    def test_zero_width_medicine_referral_rejected(self, policy):
        """amox\u200bicillin (ZW-split) is blocked by runtime after ZW normalization;
        validator must apply same normalization before checking."""
        self._assert_referral_rejected(policy, "Take amox\u200bicillin for the infection.")

    def test_overlong_referral_rejected(self, policy):
        """A referral exceeding max_words is blocked at runtime; validator must catch it."""
        long_text = " ".join(["Antenatal"] + ["care"] * 120)  # 121 words
        self._assert_referral_rejected(policy, long_text)

    def test_parity_via_guard_classify(self, policy):
        """Direct call to guard_classify must agree with the runtime node for each
        blocked case (source-reuse parity proof under NodeHarness)."""
        from ocs.guard_classifier import guard_classify

        blocked_cases = [
            "Take amoxicillin.",
            "The diagnosis is anemia.",
            "Call 999 now.",
            "Visit https://evil.com for help.",
            "(example.com) bare parenthesized contact",
            "Take amox\u200bicillin.",
        ]
        code = render_output_guard(policy)
        for text in blocked_cases:
            _gc_result = guard_classify(text, policy)
            direct_blocked = _gc_result["blocked"]
            h = _harness(code)
            h.run(text)
            runtime_blocked = h.temp_state.get("guard_route") == "guard_blocked"
            assert direct_blocked == runtime_blocked, (
                f"Parity failure for {text!r}: direct={direct_blocked!r} runtime={runtime_blocked!r}"
            )

    def test_parity_valid_educational_cases(self, policy):
        """Educational positive controls must agree between direct call and runtime."""
        from ocs.guard_classifier import guard_classify

        pass_cases = [
            "Antenatal care helps you have a healthy pregnancy.",
            "Eat a variety of foods including vegetables, fruit and beans.",
            "At 32 weeks you should discuss your birth plan.",
            "Huduma ya ujauzito inakusaidia kukaa na afya.",
        ]
        code = render_output_guard(policy)
        for text in pass_cases:
            direct_blocked = guard_classify(text, policy)["blocked"]
            h = _harness(code)
            h.run(text)
            runtime_blocked = h.temp_state.get("guard_route") == "guard_blocked"
            assert direct_blocked == runtime_blocked, f"Parity failure for {text!r}"
            assert not direct_blocked, f"Positive control incorrectly blocked: {text!r}"


class TestDesignResetURLCanonicalization:
    """URL allowlist: lowercase scheme+host, preserve path/query case,
    preserve meaningful trailing slashes, reject non-HTTPS.
    Parent probe cases reproduced verbatim.
    """

    @pytest.fixture
    def approved_code(self, policy):
        p = copy.deepcopy(policy)
        p["verified_url_allowlist"] = ["https://www.who.int/approved"]
        return render_output_guard(p)

    # --- positive controls (must PASS) ---

    def test_exact_url_passes(self, approved_code):
        h = _harness(approved_code)
        h.run("Visit https://www.who.int/approved for information.")
        assert h.temp_state.get("guard_route") == "PASS"

    def test_unapproved_trailing_slash_is_a_different_path(self, approved_code):
        h = _harness(approved_code)
        h.run("Visit https://www.who.int/approved/ for information.")
        assert h.temp_state.get("guard_route") == "guard_blocked"

    def test_uppercase_host_passes(self, approved_code):
        """Host is case-insensitive; WWW.WHO.INT must match www.who.int."""
        h = _harness(approved_code)
        h.run("Visit https://WWW.WHO.INT/approved for information.")
        assert h.temp_state.get("guard_route") == "PASS"

    # --- negative controls (must BLOCK) ---

    def test_different_case_path_blocked(self, approved_code):
        """Path is case-sensitive; /Approved must NOT match /approved.
        Parent probe: different_case_path_query expected guard_blocked but got PASS.
        """
        h = _harness(approved_code)
        h.run("Visit https://www.who.int/Approved for information.")
        assert h.temp_state.get("guard_route") == "guard_blocked"

    def test_different_path_blocked(self, approved_code):
        h = _harness(approved_code)
        h.run("Visit https://www.who.int/other-page for information.")
        assert h.temp_state.get("guard_route") == "guard_blocked"

    def test_different_query_blocked(self, approved_code):
        h = _harness(approved_code)
        h.run("Visit https://www.who.int/approved?foo=bar for information.")
        assert h.temp_state.get("guard_route") == "guard_blocked"

    def test_subdomain_blocked(self, approved_code):
        h = _harness(approved_code)
        h.run("Visit https://news.who.int/approved for information.")
        assert h.temp_state.get("guard_route") == "guard_blocked"

    def test_http_non_https_blocked(self, approved_code):
        h = _harness(approved_code)
        h.run("Visit http://www.who.int/approved for information.")
        assert h.temp_state.get("guard_route") == "guard_blocked"

    def test_allowlist_case_sensitive_path(self, policy):
        """Allowlist entry /Approved (capital A) only approves /Approved, not /approved."""
        p = copy.deepcopy(policy)
        p["verified_url_allowlist"] = ["https://www.who.int/Approved"]
        code = render_output_guard(p)
        # capital-A path matches capital-A allowlist
        h = _harness(code)
        h.run("Visit https://www.who.int/Approved for information.")
        assert h.temp_state.get("guard_route") == "PASS"
        # lowercase path does NOT match capital-A allowlist
        h2 = _harness(code)
        h2.run("Visit https://www.who.int/approved for information.")
        assert h2.temp_state.get("guard_route") == "guard_blocked"

    def test_allowlist_trailing_slash_entry(self, policy):
        """An explicitly approved slash path passes; removing its slash does not."""
        p = copy.deepcopy(policy)
        p["verified_url_allowlist"] = ["https://www.who.int/approved/"]
        code = render_output_guard(p)
        for url, expected in [
            ("https://www.who.int/approved/", "PASS"),
            ("https://www.who.int/approved", "guard_blocked"),
        ]:
            h = _harness(code)
            h.run(f"Visit {url} for information.")
            assert h.temp_state.get("guard_route") == expected

    # --- positive education untouched ---

    def test_educational_no_url_still_passes(self, approved_code):
        h = _harness(approved_code)
        h.run("Ask your health worker for advice about your dietary needs.")
        assert h.temp_state.get("guard_route") == "PASS"


class TestPolicyURLStructure:
    @pytest.mark.parametrize(
        "url",
        [
            "https://",
            "https:///approved",
            "https://bad host/approved",
            "https://www.who.int:bad/approved",
        ],
    )
    def test_malformed_url_allowlist_is_rejected(self, policy, url):
        p = copy.deepcopy(policy)
        p["verified_url_allowlist"] = [url]
        with pytest.raises(ValueError):
            validate_output_policy(p)


class TestDesignResetGuardClassifyAPI:
    """Direct API tests for the new guard_classify function in guard_classifier.py."""

    def test_module_importable(self):
        from ocs.guard_classifier import guard_classify  # noqa: F401

    def test_returns_tuple(self, policy):
        from ocs.guard_classifier import guard_classify

        result = guard_classify("hello", policy)
        assert isinstance(result, dict)
        assert "blocked" in result and "reason" in result

    def test_pass_returns_false_pass(self, policy):
        from ocs.guard_classifier import guard_classify

        result = guard_classify("Ask your health worker for advice.", policy)
        assert result["blocked"] is False
        assert result["reason"] == "PASS"

    def test_medicine_returns_true(self, policy):
        from ocs.guard_classifier import guard_classify

        result = guard_classify("Take amoxicillin daily.", policy)
        assert result["blocked"] is True
        assert result["reason"] == "medicine_name"

    def test_zw_normalization_in_classifier(self, policy):
        from ocs.guard_classifier import guard_classify

        result = guard_classify("Take amox\u200bicillin.", policy)
        assert result["blocked"] is True, "ZW-split medicine must be normalized and caught"

    def test_url_case_sensitive_path(self, policy):
        from ocs.guard_classifier import guard_classify

        p = copy.deepcopy(policy)
        p["verified_url_allowlist"] = ["https://www.who.int/approved"]
        result = guard_classify("https://www.who.int/Approved", p)
        assert result["blocked"] is True, "Capital-A path must not match lowercase allowlist entry"

    def test_url_trailing_slash_is_preserved(self, policy):
        from ocs.guard_classifier import guard_classify

        p = copy.deepcopy(policy)
        p["verified_url_allowlist"] = ["https://www.who.int/approved"]
        result = guard_classify("Visit https://www.who.int/approved/ for more.", p)
        assert result["blocked"] is True, "A different path is not an exact approved destination"

    def test_overlong_blocked(self, policy):
        from ocs.guard_classifier import guard_classify

        long_text = " ".join(["word"] * 121)
        result = guard_classify(long_text, policy)
        assert result["blocked"] is True
        assert result["reason"] == "too_long"

    def test_empty_blocked(self, policy):
        from ocs.guard_classifier import guard_classify

        result = guard_classify("", policy)
        assert result["blocked"] is True
        assert result["reason"] == "empty_output"
