# Scores

Generated 27 November 2026 from `ocs/tests/danger_eval_corpus.csv` (310 messages). Full reports:

- Live gate: [docs/eval/danger-gate-baseline.md](eval/danger-gate-baseline.md)
- Draft gate (not live, awaiting Achar's sign-off in #19): [docs/eval/danger-gate-draft.md](eval/danger-gate-draft.md)

Rerun:

```
python -m ocs.eval.score_gate --report docs/eval/danger-gate-baseline.md
python -m ocs.eval.score_gate --node ocs/eval/proposed_danger_gate.py --report docs/eval/danger-gate-draft.md
```

## Danger gate

Full detail: [docs/review/danger-gate.md](review/danger-gate.md), section 0.

| Measure | Before (gate on `main`) | After sign-off (live) |
|---|---|---|
| **Held-out set C, emergencies caught (39)** | **4 (10%)** | **14 (36%)** |
| **Held-out set B, emergencies caught (30)** | **0 (0%)** | **15 (50%)** |
| Held-out routine false alarms, B and C (35) | 0 | 2 |
| Held-out question false alarms, C (9) | 1 | 1 |
| Corpus, emergencies caught (132) | 14 (11%) | 108 (82%) |
| Corpus, v2 only (40) | 2 (5%) | 16 (40%) |
| Corpus routine false alarms (140) | 5 (4%) | 0 |
| Corpus questions sent to emergency (22) | 4 (18%) | 0 |

The work order target is at least 95% recall with under 10% false alarms. The held-out numbers show it is not met.

## Answer cards

Not scored yet. 126 routine questions name the card they should match (`expected_card`); card IDs are in `ocs/eval/cards.py`. Scoring starts with #23.

## Caveats

- All labels, and all Swahili, Sheng and mixed text, are drafts that need Achar's review. Sheng rows also need a native speaker.
- None of these messages come from a real mother.
