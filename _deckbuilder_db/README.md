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
6. `python derive.py --sets S01,S14,PZP --out work/pilot`: brief-schema records plus derived
   fields (style, named, icons, keywords, limits, restrictions, filename checks) and an
   OCR-vs-vision comparison -> `<out>/cards.json`, `cards.csv`, `ocr_compare.json`

Vision text conventions: icons are written `[Attack] [Defense] [Continuous] [Instant]
[Desperation]`; inline Trait icons as `[Trait:Earthling]`; FanZ Endurance badges as a leading
`ENDURANCE N.` line; FanZ line breaks as `\n`. `rarity` is the printed letter code (C, U, R,
UR, S, P, DR); S means a starter-deck card, DR an alternate-art card.

Set codes: `S01`..`S19`, `OP1`..`OP6`, `PZP` (PanZ MP & Ally Promos).

## Status (2026-11-01)
- Phase 0 done: 3,113 images inventoried.
- Phase 1 pilot (S01, S14, PZP = 652 images): OCR, vision pass, ingest and derive done.
  Results and problem cards: `work/pilot/PILOT_REPORT.md`. Waiting for the owner's OK
  before Phase 2.

## Layout findings
- PanZ Personalities print `ALLY` on the right edge for Allies and `HERO`/`VILLAIN` for MPs;
  FanZ prints `HERO ALLY`, `VILLAIN ALLY` or `HERO/VILLAIN ALLY`. That edge label is used to
  tell MPs from Allies (owner to confirm).
- PanZ Masteries are landscape. FanZ Masteries (S14 P18-P27) are portrait, and FanZ
  Setups/Drills are landscape, so orientation alone does not identify a Mastery.
- FanZ Trait badges (letter in the corner): A Alien, R Android (Red Ribbon logo), E Earthling
  (Capsule Corp logo), G God, M Majin, N Namekian, S Saiyan. R = Android was deduced from
  the CRD Trait list (Android 19 shows only R).
- The printed card number carries a rarity letter (C19, U23, R127, UR161, S44, P10); some
  FanZ numbers also carry `PREVIEW` or `BONUS`.
- Some images have a "(CRD)" or "(FROZEN)" stamp below the card: the owner's annotation,
  not card text.
- Filename oddities for the QA report: duplicate numbers `S02 06` (Raditz / Tenshinhan) and
  `S10 54` (two cards); `PZP P43` is resolved (the "Ferocious" file prints P42). Pilot
  filename typos are listed in the pilot report.
- PanZ images for Sets 1-6 are ~465 px wide; still readable by eye, so OCR upscales them 3x.

## Fixes to make before Phase 2
- `ocr.py`: the landscape `lower` crop (x 0.15-0.85) cuts off the right edge of FanZ
  landscape Setups/Drills, and OCR cannot read the Endurance badge. OCR is a cross-check
  only, so this lowers OCR agreement but does not affect the vision records.
- `sheets.py`: the personality heuristic depends on OCR and missed one full-art promo
  (S14 P14 Buu) and FanZ portrait Masteries; full-card 2-up sheets worked better for
  high-res FanZ cards.

## Owner decisions (2026-11-01, answers to the pilot questions)
1. MP vs Ally: decided by the printed edge label (`ALLY` = Ally; `HERO`/`VILLAIN` = MP).
2. FanZ Masteries are portrait and FanZ Setups/Drills landscape: expected.
3. Trait badge R = Android: confirmed.
4. `DR` cards are normal cards: DR is a rarity tier for alternate artwork (`rarity = DR`,
   card_id and `collection = dr` unchanged; their folders mix DR with starter cards).
   `T_` Trait cards (reference cards listing who has each Trait): decision pending.
5. PZP and OP folders: `era = FanZ`.
6. Printed rarity S = starter-deck card. Cards with a printed S number that are filed in a
   booster folder (S14 S43-S52) get `collection = starter`; the card_id is unchanged.
7. "(SDCC)" stays in the subtitle when it is printed on the card (PZP P19).
8. Piccolo - Fused is a normal Piccolo for MP grouping (not a fused MP).
9. Named = possessive title ("Goku's ...", "Trunks' ...") or text saying the card is
   "considered Named".
10. Style = first word of the title if it is Black/Blue/Namekian/Orange/Red/Saiyan, else
    Freestyle ("Namek Dragon Ball" is Freestyle); personalities have no style.
11. PanZ Ally alignment comes from the text box: "(Heroes only.)" = Hero,
    "(Villains only.)" = Villain.
