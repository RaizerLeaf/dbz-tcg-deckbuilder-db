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
6. `python derive.py --sets S01,...,S19,PZP,OP1,...,OP6 --out work/full`: brief-schema records plus
   derived fields (style, named, icons, keywords, limits, restrictions, filename checks) and an
   OCR-vs-vision comparison -> `work/full/cards.json`, `cards.csv`, `ocr_compare.json`
7. `python crd_parse.py` then `python crd.py` (Phase 3): parses the CRD text (`work/crd/fanz.txt`, `panz.txt`
   from `pdftotext -layout`) and writes the final `cards.json` / `cards.csv` with errata, rulings, MRP, Frozen List and
   Gold Title Reprint data (`work/crd/PHASE3_REPORT.md`, manual resolutions in `work/crd/overrides.json`). Two rules decide the current text (2026-11-02):
   (a) where an entry has both a Panini/Updated wording and a later "FanZ Updated Text", the FanZ wording is used only if a Set 1-7 printing shows it,
   otherwise the PanZ-era wording is used (Blue Guard); (b) a real Set 1-7 image that prints "(Most Recent Printing)" is the MRP (`is_mrp` true), and its wording
   becomes `text_current` of the older printings of the same card, even when the CRD does not list the card (Black Command, Orange Palm Blasts)
8. `python owner.py`: applies the owner's answers to the flagged cards (`work/owner_rulings.json`): type/icon rulings, copies for the two placeholder
   images, and removal of the 14 'NEVER OFFICIALLY RELEASED' S07 promos (listed in `excluded_cards.json`). Run after `crd.py`, before `mps.py`.
9. `python mps.py` (Phase 4): adds `traits_effective` / `traits_source` to MP and Ally records and writes `mps.json` and
   `masteries.json` (`work/crd/PHASE4_REPORT.md`)

10. `python qa.py` (Phase 5): consistency checks, adds `qa_flags` to the records and writes `qa_report.md`

Deck codes: `scripts/deckcode.py` encodes, decodes and legality-checks the owner's web-app deck codes (format in `DECKBUILDING_NOTES.md`).

## Output files (current)
- `cards.json`, `cards.csv`: one record per image except the 14 excluded overlay promos (3,092 records; see `excluded_cards.json`). Fields are those in BRIEF.md plus: `stage_cost`,
  `vision_confidence`, `filename_issue`, `notes`, `limit_per_deck_printed`, `errata_status`
  (null / printing_current / text_current_derived), `card_type_current`, `crd_entries` (structured CRD entries; `kind` is ERRATUM, RULING, or MRP_LABEL for text taken from a card image that prints "(Most Recent Printing)"),
  `frozen_listed_printing`, `frozen_filename_flag`, `gold_title_note`, `traits_effective`, `traits_source`, `owner_ruling`, `qa_flags`. `errata_status` can also be `owner_correction`.
  `card_type_current`, when set, overrides `card_type` (e.g. S04 BST_110 prints Event but is an Energy Combat).
  `text_as_printed` is what the image shows; `text_current` is the text after errata (null when the card has no erratum). The latest print wins: use `text_current`, never an
  older printing's printed text. `is_mrp` true = the most recent printing. `S04_PRO_P9` / `P10` have no image (placeholders): their text is copied from the Set 1 card, so do not treat them as a source.
  `traits` = Traits printed on the card; `traits_effective` adds the CRD's retroactive Traits for PanZ printings.
- `mps.json`: MP groups (name + alignment) with every printing of Levels 1-4 and Trait availability per level.
- `masteries.json`: every Mastery printing grouped by name, with the cards restricted to it.
- `qa_report.md`: counts per set, sample re-read result, checks, needs_review list, unmatched CRD entries.
- `crd_general.md`: the CRD's core rules and general rulings (text).

Vision text conventions: icons are written `[Attack] [Defense] [Continuous] [Instant]
[Desperation]`; inline Trait icons as `[Trait:Earthling]`; FanZ Endurance badges as a leading
`ENDURANCE N.` line; FanZ line breaks as `\n`. `rarity` is the printed letter code (C, U, R,
UR, S, P, DR); S means a starter-deck card, DR an alternate-art card.

Set codes: `S01`..`S19`, `OP1`..`OP6`, `PZP` (PanZ MP & Ally Promos).

## Status (2026-11-01)
- Phase 0 done: 3,113 images inventoried.
- Phase 1 pilot done and approved (`work/pilot/PILOT_REPORT.md`).
- Phase 2 done: all 3,106 playable images read, ingested and derived. Draft `cards.json` /
  `cards.csv` in this folder; report in `work/full/PHASE2_REPORT.md` (28 cards needed review; all resolved by the owner on 2026-11-02, so `needs_review` is now false everywhere).
- Phase 3 done: errata, rulings, MRP, Frozen List and Gold Title Reprints attached (`work/crd/PHASE3_REPORT.md`, `crd_general.md`).
- Phase 4 done: `mps.json`, `masteries.json`.
- Phase 5 done: `qa_report.md` (checks, 5% visual re-read: 0 errors in 159 cards, owner decisions, unmatched CRD entries).

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
   `T_` Trait cards (7 files) are not playable cards: no records in `cards.json`. Their
   character lists are transcribed only to cross-check Trait data (Phase 4/5).
5. PZP and OP folders: `era = FanZ`.
6. Printed rarity S = starter-deck card. Cards with a printed S number that are filed in a
   booster folder (S14 S43-S52) get `collection = starter`; the card_id is unchanged.
7. "(SDCC)" stays in the subtitle when it is printed on the card (PZP P19).
8. Piccolo - Fused is a normal Piccolo for MP grouping (not a fused MP).
9. Named = possessive title ("Goku's ...", "Trunks' ...") or text saying the card is
   "considered Named". Exceptions (possessive but not a character): "It's Over 9,000!" and
   "Time Is A Warrior's Tool" (usable in any deck), listed in `NOT_NAMES` in `derive.py`.
10. Style = first word of the title if it is Black/Blue/Namekian/Orange/Red/Saiyan, else
    Freestyle ("Namek Dragon Ball" is Freestyle); personalities have no style.
11. PanZ Ally alignment comes from the text box: "(Heroes only.)" = Hero,
    "(Villains only.)" = Villain.
