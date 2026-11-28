# Explainer clips

## zeya_danger_signs.mp4

- **Content:** the nine danger signs in pregnancy, from Mother and Child Health Handbook page 14, with English and Kiswahili captions.
- **Approval:** approved by Stella Oiro, clinical reviewer, on 28 November 2026 (issue #31).
- **Kiswahili captions:** they follow the clip's original wording and are DRAFT, pending fluent-speaker review.
- **Sending:** the `attach_explainer` node sends this file with the `danger_signs` answer card. It downloads it from `https://raw.githubusercontent.com/EvarestTechnologies/zeya/main/media/explainers/zeya_danger_signs.mp4`, so the download works only once this file is on `main`.
- **Format:** 46.6 seconds, 720 × 1280, H.264 Main with a silent AAC track, which WhatsApp needs. The file is 913,976 bytes, under the 1 MB download limit of some OCS releases.
- **How it was made:** produced from `render_danger_signs.py`. The "Draft for clinical review" label was covered after approval (ffmpeg `drawbox` at x 455, y 48, 240 × 44), and the file was re-encoded at CRF 24.
- **Re-rendering:** the script needs the Inter font under `/usr/share/fonts/opentype/inter`. Remove the label in `chrome()` before re-rendering.
