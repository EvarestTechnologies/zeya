"""
Score a danger-gate node on the held-out sets in ocs/eval/heldout.py.

    python -m ocs.eval.score_heldout                                   # the live gate
    python -m ocs.eval.score_heldout --node ocs/eval/proposed_danger_gate.py

For each set it reports recall on emergencies, false alarms on routine messages and
false alarms on questions about danger signs. Set B has no separate question list.
"""

import argparse
import sys
from pathlib import Path

from ocs.eval import heldout
from ocs.eval.score_gate import DEFAULT_NODE
from ocs.tests.sandbox import NodeHarness

SETS = {
    "B": (heldout.SET_B_EMERGENCY, heldout.SET_B_ROUTINE, []),
    "C": (heldout.SET_C_EMERGENCY, heldout.SET_C_ROUTINE, heldout.SET_C_QUESTION),
    "D": (heldout.SET_D_EMERGENCY, heldout.SET_D_ROUTINE, heldout.SET_D_QUESTION),
}


def _emergency(source: str, message: str) -> bool:
    harness = NodeHarness(source)
    harness.run(message)
    return harness.temp_state["danger_route"] == "EMERGENCY"


def score(node_path: Path = DEFAULT_NODE) -> dict:
    source = node_path.read_text()
    out = {}
    for name, (emergency, routine, questions) in SETS.items():
        caught = [m for m in emergency if _emergency(source, m)]
        routine_alarms = [m for m in routine if _emergency(source, m)]
        question_alarms = [m for m in questions if _emergency(source, m)]
        out[name] = {
            "recall": (len(caught), len(emergency)),
            "routine_false_alarms": (len(routine_alarms), len(routine)),
            "question_false_alarms": (len(question_alarms), len(questions)),
            "missed": [m for m in emergency if m not in caught],
            "routine_alarm_cases": routine_alarms,
            "question_alarm_cases": question_alarms,
        }
    return out


def _pct(pair) -> str:
    n, d = pair
    return f"{n}/{d} ({100 * n / d:.0f}%)" if d else "n/a"


def render(results: dict, title: str) -> str:
    lines = [
        f"## {title}",
        "",
        "| Set | Emergencies caught | Routine false alarms | Question false alarms |",
        "|---|---|---|---|",
    ]
    for name, r in results.items():
        lines.append(
            f"| {name} | {_pct(r['recall'])} | {_pct(r['routine_false_alarms'])} | {_pct(r['question_false_alarms'])} |"
        )
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--node", type=Path, default=DEFAULT_NODE)
    parser.add_argument("--title", default="Held-out sets")
    parser.add_argument("--details", action="store_true", help="also list misses and false alarms")
    args = parser.parse_args(argv)
    results = score(args.node)
    sys.stdout.write(render(results, args.title))
    if args.details:
        for name, r in results.items():
            sys.stdout.write(f"\nSet {name} missed: {r['missed']}\n")
            sys.stdout.write(f"Set {name} routine false alarms: {r['routine_alarm_cases']}\n")
            sys.stdout.write(f"Set {name} question false alarms: {r['question_alarm_cases']}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
