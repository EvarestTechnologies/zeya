# Scores

Generated 18 November 2026 from `ocs/tests/danger_eval_corpus.csv` (310 messages). Full reports:

- Live gate: [docs/eval/danger-gate-baseline.md](eval/danger-gate-baseline.md)
- Draft gate (not live, awaiting Achar's sign-off in #19): [docs/eval/danger-gate-draft.md](eval/danger-gate-draft.md)

Rerun:

```
python -m ocs.eval.score_gate --report docs/eval/danger-gate-baseline.md
python -m ocs.eval.score_gate --node ocs/eval/proposed_danger_gate.py --report docs/eval/danger-gate-draft.md
```

## Danger gate

| Measure | Live gate | Draft gate |
|---|---|---|
| Emergencies caught, all (132) | 14 (11%) | 108 (82%) |
| Emergencies caught, **v2 only (40, never tuned on)** | **2 (5%)** | **16 (40%)** |
| Routine false alarms, all (140) | 5 (4%) | 8 (6%) |
| Routine false alarms, v2 only (64) | 2 (3%) | 8 (12%) |
| Questions about danger signs sent to emergency (22) | 4 (18%) | 1 (5%) |
| Same-day messages sent to emergency (28) | 0 | 0 |
| Newborn emergencies caught (10, outside the gate's scope) | 1 | 2 |

**Read the v2 row.** The draft gate was written while looking at the v1 messages, so its 100% on v1 is overfitting. v2 was added afterwards: Sheng, spelling mistakes, and routine messages that use danger words. On v2 the draft catches 40% and raises false alarms on 12% of routine messages. The v3 target is at least 95% recall with under 10% false alarms.

By language, all batches, draft gate: English 85%, Swahili 85%, Sheng 53%, mixed 100% (4 messages).

## Answer cards

Not scored yet. 126 routine questions name the card they should match (`expected_card`); card IDs are in `ocs/eval/cards.py`. Scoring starts with #23.

## Caveats

- All labels, and all Swahili, Sheng and mixed text, are drafts that need Achar's review. Sheng rows also need a native speaker.
- None of these messages come from a real mother.
