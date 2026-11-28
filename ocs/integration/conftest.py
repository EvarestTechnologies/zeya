# Re-export Open Chat Studio's shared fixtures (team, experiment, environment
# setup). Loaded after pytest-django has configured settings.
import pytest
from apps.conftest import *  # noqa: F403

import ocs.build_pipeline as _bp_module


@pytest.fixture()
def all_pending_content(tmp_path, monkeypatch):
    """Point build_pipeline at the shipped KB and cards with every entry marked pending.

    The default build then has no approved knowledge: kb_available is False and every
    safe question goes to knowledge_referral with no model call. This is the
    "no reviewed content" path, kept testable now that real entries are approved.
    """
    kb_text = _bp_module.KB_FILE.read_text(encoding="utf-8")
    cards_text = _bp_module.CARDS_FILE.read_text(encoding="utf-8")
    pending_kb = kb_text.replace("Review-state: approved", "Review-state: pending")
    pending_cards = cards_text.replace('"review_status": "approved"', '"review_status": "pending"')
    assert pending_kb != kb_text and pending_cards != cards_text, "no approved entries found to mark pending"
    kb_path = tmp_path / "all-pending-kb.md"
    cards_path = tmp_path / "all-pending-cards.yaml"
    kb_path.write_text(pending_kb, encoding="utf-8")
    cards_path.write_text(pending_cards, encoding="utf-8")
    monkeypatch.setattr(_bp_module, "KB_FILE", kb_path)
    monkeypatch.setattr(_bp_module, "CARDS_FILE", cards_path)
