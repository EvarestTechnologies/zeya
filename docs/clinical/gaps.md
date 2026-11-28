# Clinical gaps

Things Zeya needs that are not in the three Ministry of Health documents (HB, NG24 and BOP), or that conflict with an approved decision. Nothing listed here is in the runtime. Rule 4 of `docs/work-orders/2026-11-27-guideline-alignment.md` says to record gaps here and leave them out.

## Not covered by HB, NG24 or BOP

| Topic | Where it came up | Possible source (not read or approved) |
|---|---|---|
| Week-by-week baby development | Knowledge base, "Still missing" | Myles Textbook for Midwives |
| Back pain and leg cramps | Knowledge base, "Still missing" | Myles Textbook for Midwives |
| Swollen feet as a discomfort | Knowledge base, "Still missing"; test messages R094 and R095 | Myles Textbook for Midwives |
| A maternal postnatal chapter beyond the handbook table | Knowledge base, "Still missing" | WHO 2022 postnatal care recommendations (not a runtime source) |
| Normal bleeding after birth | Test messages R016 and R017 | None identified |
| What the baby's position on a scan means | Test message R018 | None identified |
| Bleeding gums | Test message R101 | None identified |
| Self-harm and perinatal mental health crisis | Issue #40 | None identified |
| Light hurting the eyes as a danger sign | Held-out set D ("the light hurts my eyes"), set F; not added to the danger gate in A17 | None identified |

## Approved labels that no longer have a written source

These are test labels, not runtime content. They affect how the danger gate is scored, not what Zeya says.

| Test messages | Label approved in A11 | Conflict | Decision needed |
|---|---|---|---|
| S005, S006 ("just started vomiting a lot" at 30 to 32 weeks) | SAME_DAY | B3 row 10 removed "go to the clinic if nausea first starts late in pregnancy" from section 6, because NG24 p52 to p55 does not say it | Keep SAME_DAY as clinical judgement, or relabel ROUTINE |
| S008 to S011 (low mood for three weeks, or more than two weeks, after birth) | SAME_DAY | B3 row 11 replaced the two-week rule with "worsening or prolonged low mood (NG24 p291)". S009 and S011 still fit, because they say the mood is getting worse. S008 and S010 rest only on duration. | Keep SAME_DAY as clinical judgement, or relabel S008 and S010 |

## Guideline text for those labels (answer K5, 27 November 2026)

| Test messages | NG24 text | What it supports |
|---|---|---|
| S005, S006 (vomiting that starts at 30 to 32 weeks) | p52: "Nausea and vomiting of pregnancy nearly always begins before 9 weeks of gestation; symptoms presenting later in pregnancy should prompt the clinician to consider other causes." | A clinician assessment, with no time frame given. Does not decide between SAME_DAY and ROUTINE. Does not support EMERGENCY. |
| S005, S006 (if she cannot keep fluids down) | p53: "Women who cannot tolerate oral liquids for a prolonged period or who have clinical signs of dehydration should receive intravenous hydration including dextrose and vitamins." p54: in-patient care "if: … There is evidence of dehydration and the patient is ketotic." | Clinician care and possible admission, with no time frame given. |
| S008, S010 (low mood for three weeks after birth) | p291: "Postpartum blues are transient in nature with an onset after the third postpartum day… Symptoms typically peak by day five and resolve by day ten postpartum." p291: "Careful monitoring for a worsening or prolongation of symptoms." p289: the Edinburgh Postnatal Depression Scale "can be used for screening purposes prior to referral". | Three weeks is past day ten, so this is "prolongation", and screening for postnatal depression applies. No time frame is given. Silent on SAME_DAY versus ROUTINE. Does not support EMERGENCY. |

**B3 row 10 was based on an error.** NG24 p52 does support the removed sentence. Reinstating it as "Tell your health worker if vomiting starts late in pregnancy (NG24 p52)" is sign-off item B3 row 10a.
