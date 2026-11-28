# Scores

Generated 27 November 2026 from `ocs/tests/danger_eval_corpus.csv` (310 messages). Full reports:

- Gate before sign-off (on `main`): [docs/eval/danger-gate-baseline.md](eval/danger-gate-baseline.md)
- Gate after sign-off (live on this branch): [docs/eval/danger-gate-draft.md](eval/danger-gate-draft.md)

Rerun:

```
python -m ocs.eval.score_gate --report docs/eval/danger-gate-draft.md
python -m ocs.eval.score_heldout --details
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

Not scored yet. 126 routine questions in the corpus name a card from the earlier draft catalogue in `ocs/eval/cards.py`. The live cards are the five Ministry entries in `docs/answer-cards.yaml`, so those labels need mapping before scoring.

## Caveats

- All labels, and all Swahili, Sheng and mixed text, are drafts that need clinical review. Sheng rows also need a native speaker.
- None of these messages come from a real mother.
