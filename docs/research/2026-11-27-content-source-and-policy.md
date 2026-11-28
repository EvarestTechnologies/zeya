# Zeya content source, knowledge base check and policy requirements

27 November 2026. Research prepared for Stella Oiro. Exported from the shared research document. Event and audience names are replaced with "release 1" and "partners", per the naming rule in `docs/work-orders/2026-11-27-guideline-alignment.md`.

## Decisions and the next two days

Zeya should run on the Kenya Ministry of Health knowledge base only. The WHO starter comes out of the runtime before the 29 November freeze. Its "approved" label goes back to "pending", because nobody recorded a clinical sign-off.

1. **Content source.** The MOH knowledge base (HB, NG24, BOP) is the only source Zeya speaks from. WHO is used only as a background cross-check that the clinical reviewer can read, never as text sent to a mother.
2. **Knowledge base fixes.** The page-by-page check found 9 places where the knowledge base says more than, or something different from, the cited page. Two of them change what Zeya tells mothers: deworming, and where high-risk mothers deliver. Part B lists every one with the correct page and wording.
3. **NG12 edition.** The file named "2010" is the 2012 edition. The PDF was created on 28 February 2012, its foreword is signed by the Ministry of Public Health and Sanitation, and its newest data is from 2010. Keep the code NG12 and correct the filename.
4. **Licences.** Only the Basic Obstetric Protocols carry a reuse statement. It allows quoting with acknowledgement and forbids commercial use. The handbook and the 2024 guidelines carry no licence statement, so Evarest should ask the Division of RMNCAH in writing before Zeya quotes them in a funded product.
5. **Release 1 versus the trial.** Release 1 uses synthetic participants only. It needs four documents: an intended-use statement, a draft AI and privacy notice, a clinical sign-off record, and a source and attribution page. Everything else in Part C is needed before the first real mother is enrolled.

### Action list in priority order, 28 and 29 November

- [ ] The clinical reviewer approves or rejects the 9 knowledge base corrections in Part B, then signs the clinical sign-off record for every answer card going live.
- [ ] Claude Code switches the runtime knowledge to the MOH knowledge base, sets every WHO starter entry to "pending", and adds the source line "Ministry of Health Kenya" to each card.
- [ ] Claude Code adds a human escalation line to the fallback reply. WhatsApp requires one for automated chats.
- [ ] The clinical reviewer writes a one-paragraph intended-use statement that says Zeya educates and refers, and does not diagnose or treat.
- [ ] Raymond confirms where the OCS server and the Groq endpoint process data, for the cross-border section of the DPIA.
- [ ] The clinical reviewer emails the Division of RMNCAH asking permission to adapt the handbook and NG24 wording for a non-commercial pilot.
- [ ] Book a Kenyan data protection lawyer for the three questions in the last section: pregnant under-18s, sensitive data leaving Kenya, and whether any regulator treats Zeya as medical device software.

## Part A. Which content source Zeya should use

Use the MOH documents. Every authority that will judge Zeya in Kenya points to national content, and none of them asks for WHO web pages.

### What each authority expects

| Authority | What it expects of content | Source |
|---|---|---|
| MOH Guideline for Development of IEC Materials for Health, 1st edition 2025 | Drafts reviewed by subject experts, pretested with the audience (70% understanding counts as success), validated by a technical committee, then approved by the Director General for Health. WhatsApp is named as a channel; chatbots are not. It does not say content must come from national guidelines, but its situation analysis starts from national policy. | Guideline PDF, pages 8 to 15 |
| Digital Health Act 2023 and Legal Notices 76 and 77 of 2025 | These govern health information systems, data exchange and the Digital Health Agency. They set no rules on education content. They matter for data, not for which guideline Zeya quotes. | Act, LN 76, LN 77 |
| KMPDC notice, 4 November 2026 | AI is a support tool only, and practitioners stay accountable. It names the Digital Health Act and the data protection law. It says nothing about content sources. | News report. The notice itself is unverified |
| Grand Challenges Africa AI call | Solutions that are locally driven and locally owned, with local thresholds for safe use. | Grand Challenges Africa AI call |
| Migori County health department | Unverified. A county team will check Zeya against the handbook its nurses already hand out and the national guidelines its staff are trained on. | Reasoning, not a document |

### Licences and attribution

| Document | What the PDF says about reuse | What Zeya must do |
|---|---|---|
| Basic Obstetric Protocols 2026 | Page 2 says any part may be quoted or reproduced if the source is acknowledged, and it may not be sold or used commercially. © 2026 Government of Kenya. | Cite "Ministry of Health, Basic Obstetric Protocols, January 2026". Keep Zeya free to mothers. |
| MCH Handbook (MOH 216) 2020 | No licence statement. The cover says "Not for sale". Every page carries a "Draft" watermark, and page 18 still says "Image to be approved". | Ask the Division of RMNCAH in writing. Cite "Ministry of Health, Mother and Child Health Handbook, 2020". Check the wording against the printed booklet. |
| National Guidelines on Quality Obstetrics and Perinatal Care 2024 | No licence statement. Page 3 gives only the citation "Ministry of Health 2024". | Ask in writing. Cite as page 3 asks. |
| NG12 (2012 edition) | No licence statement. | It is superseded, so avoid quoting it at all. |
| WHO "Your life, your health" pages | WHO publications are licensed CC BY-NC-SA 3.0 IGO. That allows non-commercial adaptation if the adaptation carries the same licence and WHO's disclaimer. WHO's website terms ask for acknowledgement with the page URL. Whether these web pages fall under the open licence is unverified. | If ever used, cite WHO and the URL, add "This is an adaptation… WHO is not responsible", and do not imply WHO endorsement. |

Two questions are for a Kenyan lawyer: copyright in Kenyan government works, and whether a grant-funded pilot by a company counts as "commercial".

**Recommendation.** Replace the WHO starter with the MOH knowledge base.
- **Not both sources with a rule for which wins.** Two sources double the clinical review work, and a partner will ask why a Kenyan product quotes Geneva over Nairobi.
- **Not WHO kept for release 1 either.** The live system would then show content with no recorded clinical sign-off.

**What to tell partners.** "Zeya speaks only from the Kenya Ministry of Health handbook, national guidelines and protocols. A licensed clinical officer signs off every answer card, and each answer names its source page. We chose national content over international web material so the county can adopt Zeya without re-checking it." If a partner asks about the earlier WHO starter, say it was a developer placeholder that never went to a mother and was removed before release 1.

## Part B. Knowledge base check against the four PDFs

The knowledge base holds up. I checked 105 cited facts across all 13 sections, by extracting every page of the four PDFs and searching the cited page. 96 matched the cited page, and the 9 below need a fix.

Page numbers are the printed numbers. In the handbook PDF, printed page = PDF page minus 2. In the other three, printed page = PDF page.

### Mismatches, wrong pages and overstated claims

| # | Section | Knowledge base says | The document actually says | Fix |
|---|---|---|---|---|
| 1 | 8. Higher risk | These mothers "should attend and deliver at a level 4 hospital or above" (BOP p12) | BOP p12 says lower-tier health professionals "should refer the client to a level 4 OR above facility for further assessment". | Say "your health worker may refer you to a hospital for more checks". Do not tell her where to deliver. **Changes what mothers hear.** |
| 2 | 4. Deworming | "Once from the second trimester" (NG24 p110) | NG24 p110 recommends it as a public health intervention for pregnant women living in hookworm-infested areas, from the second trimester. | Keep "ask your health worker about deworming". The clinical reviewer to confirm whether Migori counts as such an area. **Changes what mothers hear.** |
| 3 | 2. ANC profile | Includes hepatitis B, cited NG24 p112 and HB p7 | NG24 p112 lists TB, HIV, VDRL, blood sugar, full haemogram, malaria slide, blood group and rhesus, urinalysis. No hepatitis B. HB p7 does include it. | Cite hepatitis B to HB p7 only. |
| 4 | 1. What to teach | Contact 1 teaches "Welcome, what ANC is" (NG24 p107) | NG24 p107 is the group ANC rollout table. Contact 1 (8 to 12 weeks) is "Physical exam and full history, ANC profile, recruitment into the group". "Importance and components of ANC" is contact 2. | Correct contact 1. Note the table is for group ANC. |
| 5 | 5. Food, pending | "Calcium from milk, yoghurt and omena" (NG12 p38 to p44) | Omena is on NG12 p48, in the breastfeeding section, as "at least 3 additional servings of calcium rich foods". NG24 p51 says the same for breastfeeding. | Move omena to section 11, food while breastfeeding. |
| 6 | 10. Labour | Skin to skin straight away (NG24 p305) | It is on NG24 p306, recommendation 48. Cord clamping is on p305. | Change the page to p306. |
| 7 | Never say | Salt restriction "appears only in NG12" | NG24 p58 also restricts sodium, for women with pre-eclampsia. NG12 p53 has the same list. | Keep it on the list. Change the reason to "condition-specific advice for the health worker to give". |
| 8 | 7. Danger signs | "Any one means go to a health facility now" (HB p14) | HB p14 says "Be prepared always to seek skilled care at the health facility in case of any of the above signs." It does not say "now". HB p19 (baby) does say "immediately visit a health facility". | The clinical reviewer decides. "Go now" is stronger than the pregnancy page. The video uses "now". |
| 9 | 7. Related symptoms, pending | "Fewer than 10 baby movements in a day" (NG12 p173) | NG12 p173 is a question the clinician asks at labour admission: "find out if they are less than 10 in a day". It is not a counting instruction for mothers. | Keep it out of mother-facing text, or have the clinical reviewer approve it as a new instruction. |

**Two smaller notes:**
- The baby blues figures are on NG24 p291 and the depression figures on p289, both inside the cited range.
- The vitamin A wording is safe, but NG24 p109 allows supplementation where deficiency is a public health problem. "Never" should stay "not routinely".

**NG12 edition.** The file is the 2012 edition. Evidence from the PDF:
- its metadata shows it was created on 28 February 2012
- the foreword is signed by Dr Anna Wamae for the Ministry of Public Health and Sanitation, a ministry that existed from 2008 to 2013
- its newest cited data is KDHS 2008–09 and KSPA 2010

No date is printed on the cover or the foreword, so the publication month is unverified. Every "pending" item in the knowledge base cites this file, so the pending items come from the 2012 edition. The 2021 and 2022 drafts were not checked.

### Danger signs and the never-say list

- The nine handbook signs in section 7 match HB p14 word for word. The handbook calls one sign "Reduced or no movement of the unborn baby". It is listed as "Reduced or no movement of the baby", which is fine.
- BOP has no mother-facing danger-sign list. It tells the clinician to "educate the patient on danger signs" (BOP p16, p17). HB p14 stays the only source for the nine signs.
- Vitamin A after birth is confirmed as NG12 only (p43, p48 and p243 give 200,000 IU at delivery). NG24 does not recommend it. It stays on the list.
- Stopping breastfeeding an older child is confirmed as NG12 only (p66, "until seven months gestation"). It stays on the list.
- Drugs and doses. The BOP and NG24 pages checked include doses for aspirin, calcium, labetalol, nifedipine, albendazole and mebendazole. The rule that Zeya never sends a drug name or dose stays.

**Missing from all four documents:**
- week-by-week baby development
- back pain and leg cramps
- swollen feet as a discomfort
- a maternal postnatal chapter beyond the handbook table

Candidate sources are Myles Textbook for Midwives and the WHO 2022 postnatal care recommendations. Neither has been read or approved, so nothing from them goes into Zeya yet.

## Part C. Laws, guidance and Zeya's own policy documents

Zeya processes health data, which the Data Protection Act treats as sensitive, so the data protection rules weigh more than any content rule. Most of the work is needed before the first real mother, not before release 1.

### The laws and guidance that apply

| Document | Issuer and date | What it requires of Zeya |
|---|---|---|
| Data Protection Act, No. 24 of 2019 (Cap 411C) | Parliament, 2019 | Health data is sensitive personal data. A DPIA is needed for high-risk processing (s.31). Children's data needs parental consent and age checks (s.33). People can ask for human review of automated decisions (s.35). Breaches go to ODPC within 72 hours (s.43). Sensitive data leaving Kenya needs consent and safeguards (s.49, lawyer to confirm). |
| Data Protection (General) Regulations 2021 | Cabinet Secretary, 2021 | Detail on consent, data subject rights, retention and the DPIA. |
| Registration of Data Controllers and Processors Regulations, LN 265 of 2021 | Cabinet Secretary, in force 14 July 2022 | The small-business exemption (under KES 5 million and under 10 staff) does not apply to health administration and patient care. Evarest must register as controller or processor before real data flows. |
| ODPC Guidance Note on Processing of Health Data | ODPC, December 2023 | Covers mHealth and eHealth apps by name. Has a compliance checklist and a registration section. |
| ODPC Guidance Note on Cross-border Data Transfers | ODPC, draft April 2026, final 8 September 2026 | Processing on cloud servers outside Kenya is a transfer, so Groq's US servers count. It needs a lawful basis, a transfer agreement and notice to ODPC. The link is the April draft; the final text URL is unverified. |
| ODPC Guidance Note on Artificial Intelligence | ODPC, July 2026 | A DPIA is mandatory for AI health processing. The privacy notice must say AI is used. Human review must be tested before launch. No training on chats without a fresh legal basis. A data processing agreement with any AI provider. |
| ODPC Guidance Notes for Processing Children's Data | ODPC, adopted 6 November 2025 | Age verification and parental consent. It has an exemption section (9.7) whose scope for pregnant 16 and 17 year olds is unverified. |
| Digital Health Act, No. 15 of 2023, LN 76 of 2025, LN 77 of 2025 | Parliament 2023; Cabinet Secretary, 11 April 2025 | LN 76 covers health information management, and LN 77 the national data exchange and registries. Whether a pilot chatbot must register or connect is unverified; lawyer to confirm. |
| KMPDC notice on technology-based healthcare | KMPDC, 4 November 2026 | AI is a support tool, the practitioner stays accountable, and records must be secure. It binds doctors and KMPDC-registered institutions. Clinical officers are regulated by the Clinical Officers Council, so it applies to Zeya only by analogy. The notice text is unverified (news report). |
| PPB Guideline on Regulation of Medical Device Software | Pharmacy and Poisons Board, 2026 (February per The Standard, April per The Star) | Covers standalone software with a medical purpose, such as symptom checkers. Zeya's danger-sign triage could be read as one. A written intended-use statement saying education only is the defence. Primary PDF unverified. |
| MOH Guideline for Development of IEC Materials for Health | MOH, 1st edition 2025 | Expert review, pretesting, validation and Director General approval for health education material. MOH logo placement rules apply if MOH branding is used. |
| NACOSTI research licence and biomedical research ethics guidelines | NACOSTI | Ethics approval from an accredited ISERC first, then the licence, about 30 days. Pregnant women are a vulnerable group. For under-18s, see the 2015 MOH adolescent SRH research guidelines. Whether pregnancy makes a minor able to consent alone is unverified. |
| WhatsApp Business Messaging Policy | Meta, updated 23 September 2026 | Opt-in naming the business, honouring every opt-out, a published privacy policy, and a clear escalation path when chats are automated. It restricts sending health information where local law needs heightened safeguards. |

### Zeya's own documents, and when each is needed

| Document | Required by | What it must contain | Needed by |
|---|---|---|---|
| Intended-use statement | PPB software guideline, KMPDC notice | One paragraph. Zeya gives antenatal education from MOH sources and refers to facilities. It does not diagnose, prescribe or replace ANC. | Release 1 |
| AI and privacy notice (English and Kiswahili) | DPA s.29, ODPC AI note s.4.1, WhatsApp policy | Who Evarest is, what data is collected, that an AI model (Groq, US) writes some answers, where data goes, how long it is kept, rights, how to reach a human, and how to stop. | Draft for release 1, final for the trial |
| Clinical sign-off record | IEC guideline, KMPDC accountability principle | Every answer card and prompt version, with source page, reviewer name, date and decision. | Release 1 |
| Source and attribution page | BOP page 2, WHO licence if used | The MOH documents used, their citations, and the note that Zeya is not an official MOH product. | Release 1 |
| Consent text (English and Kiswahili) | DPA s.32 and s.33, NACOSTI and ISERC | Study purpose, voluntary participation, withdrawal, data use, AI use, cross-border transfer, contacts, and the minors route agreed with the ethics committee. | Trial |
| DPIA | DPA s.31, ODPC AI note | System description; data flows (WhatsApp, OCS server, Groq); risks such as wrong advice, leakage and re-identification; and mitigations with owners. | Trial |
| ODPC registration | Registration Regulations 2021 | A certificate for Evarest as controller or processor. | Trial |
| Data processing agreements | DPA s.42, ODPC AI note s.7.8 | Evarest with Groq, with the WhatsApp provider and with the study sponsor, covering purpose, security, sub-processors, deletion, breach notice and audit. | Trial |
| Cross-border transfer record | ODPC cross-border note, DPA s.48 and s.49 | Each country data goes to, the safeguard used, and the ODPC notification. | Trial |
| Retention and deletion schedule | DPA s.39, General Regulations | How long chats, registration data and exports are kept, and how deletion in OCS is done and checked. | Trial |
| Breach and incident runbook | DPA s.43 | Who is called, how to contain, the 72-hour ODPC notice, telling participants, and a clinical incident path for wrong advice. | Trial |
| Data protection policy | ODPC Guidance Note on Data Protection Policies 2026 | Roles, a DPO or contact person, access control, 2FA, training and a review cycle. | Trial |
| Research protocol, ISERC approval and NACOSTI licence | Science, Technology and Innovation Act, NACOSTI | The protocol, safety monitoring, adverse event reporting, and the approvals themselves. | Trial |
| MOH permission letter | Copyright in MOH documents | Written permission to adapt the handbook and NG24 wording. | Before a funded launch |

## Unverified items and questions for a Kenyan lawyer

This is research, not legal advice. These items could not be confirmed from a primary source, or need a lawyer's reading.

### Questions for the lawyer

1. A pregnant 16 or 17 year old wants to join. Does DPA s.33 need a parent's consent, or does section 9.7 of the ODPC children's note, or emancipated-minor practice, allow her own consent?
2. Does sending chat text to Groq in the United States need each mother's explicit consent under s.49, or is a transfer agreement enough?
3. Is Zeya medical device software under the PPB guideline, given that it flags danger signs and tells a mother to go to a facility?
4. Does a grant-funded pilot by a private company count as "commercial" under the BOP reuse statement and the WHO licence?
5. Must a pilot chatbot register with, or connect to, the Digital Health Agency under LN 76 or LN 77?

### Not confirmed from a primary source

- The KMPDC notice of 4 November 2026. Only news reports were found.
- The PPB medical device software guideline. Only news reports were found, and they disagree on February or April.
- The final URL of the ODPC cross-border guidance of 8 September 2026. The linked file is the April draft.
- The licence that applies to WHO "Your life, your health" web pages. WHO's copyright page could not be opened.
- The NG12 publication month. The 2012 date comes from the PDF's metadata, not a printed date.
- The Data Protection Act section numbers 29, 39, 42, 43, 48 and 49. They come from memory of the Act and should be checked against the Kenya Law text.
- How a Migori County health department would judge the content source. This is reasoning, not a document.

**Not available for this check.** The research report of 18 November was not provided, so Part C was built from fresh primary sources rather than on that report. The repository's live WHO starter was read from `docs/zeya-knowledge-base.md` on `main`, commit b77f0ea.
