"""The scorer's arithmetic, checked on hand-made results (no gate involved)."""

from ocs.eval.corpus import Case
from ocs.eval.score_gate import Result, summarise


def _res(label, triggered, category=None, lang="en", kb="7"):
    return Result(Case("X", lang, "t", label, category, kb), triggered, [])


def test_recall_counts_only_in_scope_emergencies():
    results = [
        _res("EMERGENCY", True, "fever"),
        _res("EMERGENCY", False, "fever"),
        _res("EMERGENCY", False, "newborn"),
    ]
    s = summarise(results)
    assert s["recall"] == (1, 2)
    assert s["newborn_recall"] == (0, 1)
    assert s["by_category"]["fever"] == (1, 2)


def test_false_alarm_rate_uses_routine_and_same_day_is_separate():
    results = [
        _res("ROUTINE", True), _res("ROUTINE", False), _res("ROUTINE", False), _res("ROUTINE", False),
        _res("SAME_DAY", True, kb="6"),
    ]
    s = summarise(results)
    assert s["false_alarms"] == (1, 4)
    assert s["same_day_to_emergency"] == (1, 1)


def test_misses_and_false_alarms_are_listed():
    miss = _res("EMERGENCY", False, "pallor")
    alarm = _res("ROUTINE", True)
    s = summarise([miss, alarm])
    assert s["misses"] == [miss]
    assert s["false_alarm_cases"] == [alarm]


def test_recall_and_false_alarms_are_split_by_batch():
    def r(label, triggered, batch, category=None):
        return Result(Case("X", "en", "t", label, category, "7", batch=batch), triggered, [])
    s = summarise([
        r("EMERGENCY", True, "v1", "fever"), r("EMERGENCY", False, "v2", "fever"),
        r("EMERGENCY", True, "v2", "fever"), r("ROUTINE", True, "v2"), r("ROUTINE", False, "v1"),
    ])
    assert s["recall_by_batch"] == {"v1": (1, 1), "v2": (1, 2)}
    assert s["false_alarms_by_batch"] == {"v1": (0, 1), "v2": (1, 1)}
