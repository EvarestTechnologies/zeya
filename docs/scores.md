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

| Measure | Gate on `main` | After A1 to A12 | After A13 and A14 | After A15 and A16 (live) |
|---|---|---|---|---|
| **Held-out set E, emergencies caught (26), untuned** | n/a | n/a | **16 (62%)** | **25 (96%)** |
| Held-out set E routine false alarms (12) | n/a | n/a | 5 | 0 |
| Held-out set E question false alarms (8) | n/a | n/a | 1 | 1 |
| **Held-out set D, emergencies caught (39), untuned** | n/a | **28 (72%)** | **33 (85%)** | **33 (85%)** |
| Held-out set C, emergencies caught (39), used for A14 | 4 (10%) | 14 (36%) | 37 (95%) | 37 (95%) |
| Held-out set B, emergencies caught (30) | 0 (0%) | 15 (50%) | 29 (97%) | 29 (97%) |
| Corpus, emergencies caught (132) | 14 (11%) | 108 (82%) | 118 (89%) | 118 (89%) |
| Corpus routine false alarms (140) | 5 (4%) | 0 | 0 | 1 |
| Held-out set D routine false alarms (12) | n/a | 0 | 0 | 0 |
| Held-out set D question false alarms (10) | n/a | 3 | 3 | 3 |

**Set E is narrow.** It was written for the messages A15 and A16 change: history mixed with what is happening now, other people's emergencies, and ordinary words that typo tolerance misread. Its 96% shows the fix works on wording it was not written from. Use set D (85%) for the gate overall.

The new corpus false alarm is R083, "will the nurse check if I am pale?". A15 lets "I am" win over the "nurse … check" history rule.

The work order target is at least 95% recall with under 10% false alarms. On untuned set D the gate reaches 85%, so the target is not yet met on wording it has never seen.

## Answer cards

Not scored yet. 126 routine questions in the corpus name a card from the earlier draft catalogue in `ocs/eval/cards.py`. The live cards are the five Ministry entries in `docs/answer-cards.yaml`, so those labels need mapping before scoring.

## Caveats

- All labels, and all Swahili, Sheng and mixed text, are drafts that need clinical review. Sheng rows also need a native speaker.
- None of these messages come from a real mother.
- 14 of set C's 39 emergencies also appear in set B, so set C's score partly re-scores set B.
