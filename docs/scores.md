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

| Measure | Gate on `main` | After A1 to A12 | After A13 and A14 (live) |
|---|---|---|---|
| **Held-out set D, emergencies caught (39), untuned** | n/a | **28 (72%)** | **33 (85%)** |
| Held-out set C, emergencies caught (39), used for A14 | 4 (10%) | 14 (36%) | 37 (95%) |
| Held-out set B, emergencies caught (30) | 0 (0%) | 15 (50%) | 29 (97%) |
| Corpus, emergencies caught (132) | 14 (11%) | 108 (82%) | 118 (89%) |
| Corpus routine false alarms (140) | 5 (4%) | 0 | 0 |
| Held-out set D routine false alarms (12) | n/a | 0 | 0 |
| Held-out set D question false alarms (10) | n/a | 3 | 3 |

The work order target is at least 95% recall with under 10% false alarms. On untuned set D the gate reaches 85%, so the target is not yet met on wording it has never seen.

## Answer cards

Not scored yet. 126 routine questions in the corpus name a card from the earlier draft catalogue in `ocs/eval/cards.py`. The live cards are the five Ministry entries in `docs/answer-cards.yaml`, so those labels need mapping before scoring.

## Caveats

- All labels, and all Swahili, Sheng and mixed text, are drafts that need clinical review. Sheng rows also need a native speaker.
- None of these messages come from a real mother.
