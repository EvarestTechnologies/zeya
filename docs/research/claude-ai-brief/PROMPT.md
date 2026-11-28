# Claude.ai research brief: Zeya content source, guidelines and policies

Paste everything below the line into a new Claude.ai chat with Research turned on. Upload these files to the same chat first.

**From `~/Downloads`**
1. `Mother-Child-Health-Handbook-MOH-NEW-LAYOUT-10th-Sep-2020.pdf` (48 pages)
2. `NATIONAL GUIDELINES ON QUALITY OBSTETRICS AND PERINATAL CARE_ August 2024.pdf` (836 pages, 24 MB)
3. `Basic Obstetric Protocol_Shareable.pdf` (64 pages)
4. `KEN_Kenya_National-Guidelines-for-Quality-Obstetrics-and-Perinatal-Care_2010.pdf` (410 pages)

**From `docs/research/claude-ai-brief/`**
5. `upload-1-moh-knowledge-base-achar.md`
6. `upload-2-who-starter-knowledge-base-main.md`
7. `upload-3-research-report-18-nov.md`

Optional: the 2021 and 2022 drafts of the national guidelines are also in Downloads (about 50 MB each). Upload them only if Claude.ai asks which edition NG12 refers to.

---

I'm the founder of Evarest Technologies. We are building Zeya, a WhatsApp antenatal education chatbot for pregnant women in Migori County, Kenya, in English and Kiswahili. It runs on Dimagi's Open Chat Studio. We demo it to funders at the Global Digital Health Forum in Bangkok on 2 to 4 December 2026. Code freeze is 29 November. Achar Oiro, a licensed clinical officer, approves all clinical wording. Only synthetic test participants are used before ethics approval.

**The problem.** Our repository now has two knowledge bases with the same file name.

- File 5 is Achar's knowledge base. It has 13 sections built from the Kenya Ministry of Health Mother and Child Health Handbook 2020 (HB), the National Guidelines on Quality Obstetrics and Perinatal Care 2024 (NG24), the Basic Obstetric Protocols 2026 (BOP), and an older national guideline (NG12) used only for items marked "pending". Our rule is that this is the only clinical source of truth.
- File 6 is what the live code actually uses. It is a five-topic starter written by a developer from two WHO "Your life, your health" web pages. It is marked approved, but no clinical sign-off was recorded.

File 7 is our earlier research on Kenyan law, models, security and competitors. Build on it and don't repeat it.

Please research and answer the following.

**Part A. Which content source should Zeya use?**
1. For a mother-facing chatbot in Kenya, should the content come from the Kenya MOH documents, from WHO, or from both? Consider what the Digital Health Act 2023, the 2025 digital health regulations, the KMPDC notice on AI of 4 November 2026 and the MOH Guideline for Development of IEC Materials for Health (2025) expect. Also consider what funders such as the Gates Foundation Grand Challenges ask for, and what a county health department partner would accept.
2. Licences. Can we reuse wording from the MCH Handbook and the national guidelines in a chatbot? Is there a stated licence or copyright notice in the PDFs? What are the reuse terms for WHO "Your life, your health" content? What attribution does each need?
3. Recommend one of: replace the WHO starter with Achar's MOH knowledge base, run both with a clear rule for which wins, or keep WHO only for the demo. Say what we must tell funders about the choice.

**Part B. Check Achar's knowledge base (file 5) against the PDFs (files 1 to 4).**
1. For every fact in file 5, check that the cited document and page say what the knowledge base says. List each mismatch, wrong page or unsupported claim, with the correct page and the exact wording.
2. NG12 is described as the "2012 edition", but the file I have is dated 2010. Find out which edition exists and which one the "pending" items actually come from.
3. Check the "Things Zeya must never say" list and the danger-sign list in section 7 against HB page 14 and the BOP.
4. Do not add clinical content from general knowledge. If something we need is missing from all four documents, say so and name where it could come from.

**Part C. The guides and policies we need, and which ones we don't have yet.**
1. Find the official, current version of each document below. Give the issuing body, the date, the exact URL (prefer kenyalaw.org, odpc.go.ke, health.go.ke, dha.go.ke and other primary sources), and three to five lines on what it requires of Zeya specifically:
   - Data Protection Act 2019, and the Data Protection (General) Regulations 2021
   - Data Protection (Registration of Data Controllers and Processors) Regulations 2021
   - ODPC Guidance Note on Cross-border Data Transfers (2026), and any ODPC guidance on AI or health data
   - Digital Health Act 2023, and Legal Notices 76 and 77 of 2025
   - KMPDC notice on AI in medical practice (4 November 2026)
   - Pharmacy and Poisons Board guideline on medical device software (February 2026)
   - MOH Guideline for Development of IEC Materials for Health (2025)
   - NACOSTI research licensing and ethics committee requirements for a pilot with pregnant women, including under-18s
   - WhatsApp Business Messaging Policy, and the Meta rules for health content and opt-in
2. List the policy documents Zeya itself must have before a real participant is enrolled. For example: privacy notice, consent text in English and Kiswahili, DPIA, retention schedule, data processing agreement with Evarest, breach and incident runbook, and clinical governance and sign-off record. For each one, say which law or guideline requires it, and give a one-paragraph outline of what it must contain.
3. Which of these must be ready for the demo on 2 December, with synthetic participants only, and which can wait until before the trial?

**How to answer**
- Plain language for a founder and a clinical officer.
- Cite every claim with a link or a document and page.
- Mark anything you could not confirm from a primary source as "unverified".
- This is not legal advice. Say where a Kenyan lawyer must confirm.
- End with a short action list in priority order for the next two days.
