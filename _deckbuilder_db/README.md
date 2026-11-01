# DBZ TCG deckbuilder database (work in progress)

Builds a searchable database of every PanZ (Sets 1-7) and FanZ (Sets 8+) card from the card
images in this repository. Original images are never modified; all output goes in
`_deckbuilder_db/`. The full schema will be documented here once Phase 1 is approved.

## Setup
- Python 3.11+ with `pip install pillow numpy pytesseract`
- Tesseract OCR 5 (Windows: `winget install UB-Mannheim.TesseractOCR`; Debian/Ubuntu:
  `apt-get install tesseract-ocr`)
- `pdftotext` (poppler-utils) for the rules PDFs in `_rules/`

## Pipeline (run from `_deckbuilder_db/scripts`)
1. `python inventory.py`: lists every image with folder/filename metadata and a stable
   `card_id` -> `work/inventory.json`
2. `python ocr.py --sets S01,S14,PZP`: Tesseract on cropped regions -> `cache/ocr/<card_id>.json`
   (resumable; cached cards are skipped)
3. `python sheets.py --sets S01,S14,PZP`: review sheets for the vision pass ->
   `work/sheets/<set>/` (git-ignored, regenerable)
4. Vision transcriptions are appended to `work/vision/*.jsonl` (format in `ingest.py`)
5. `python ingest.py`: merges inventory + OCR + vision -> `cache/<card_id>.json`

Set codes: `S01`..`S19`, `OP1`..`OP6`, `PZP` (PanZ MP & Ally Promos).

## Status (2026-10-31)
- Phase 0 done: 3,113 images inventoried.
- Phase 1 pilot (S01, S14, PZP = 652 images): OCR complete; vision pass not started.
- Open questions for the owner: how MP vs Ally is decided for Personality cards (same
  printed layout); how to treat Trait cards (`T_` files); meaning of the `DR` prefix; era
  label for the PZP and OP folders (printed by FanZ, currently `era = FanZ`).
- Layout findings so far: Masteries are the landscape images (385). MPs and Allies share one
  printed "Personality" layout (Level, 11 stages, PUR, alignment) with no MP/Ally label; the
  PZP `MPs`/`Allies` subfolders are ground truth for the role. FanZ personalities show small
  lettered Trait badges just above the text box (e.g. E = Earthling, S = Saiyan, M = Majin).
  The printed card number carries a rarity letter (C19, U23, R127, S44, P10). Some images
  have a "(CRD)" stamp below the card: the owner's annotation, not card text. PanZ images
  for Sets 1-6 are mostly ~465 px wide; still readable by eye, so OCR upscales them 3x.
- Filename oddities to report in QA: duplicate numbers `S02 06` (Raditz / Tenshinhan),
  `S10 54` (two cards), `PZP P43` (two Piccolos); typos such as `S01_Vegeta - Price of Saiyans`.
