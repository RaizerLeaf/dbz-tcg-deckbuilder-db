# Phase 2 report (2026-11-01)

All 3,106 playable card images were read from review sheets, transcribed to `work/vision/*.jsonl`,
merged with Tesseract OCR and the inventory (`ingest.py`), and converted to brief-schema records
(`derive.py`). The 7 `T_` Trait reference cards are not records (see `work/traits_reference.json`).

Outputs: `cards.json` / `cards.csv` (draft, one record per image, 3,106 rows; `text_current`,
`errata_note`, `ruling_note`, `gold_title_reprint`, `is_mrp` are still null until Phases 3-4),
`work/full/cards.json`, `cards.csv`, `ocr_compare.json`. `cache/<card_id>.json` holds one JSON per image.

## Counts
| Type | Cards |
|---|---|
| Physical Combat | 729 |
| Main Personality | 666 |
| Energy Combat | 620 |
| Event | 321 |
| Drill | 268 |
| Setup | 220 |
| Ally | 177 |
| Mastery | 74 |
| Dragon Ball | 29 |
| Placeholder image (type unknown) | 2 |

Per set: S1 335, S2 159, S3 158, S4 328, S5 163, S6 156, S7 352, S8 76, S9 68, S10 132, S11 93,
S12 81, S13 106, S14 101, S15 103, S16 152, S17 93, S18 87, S19 81, OP1-OP6 66, PZP 216.
Collections: booster 1,607, starter 670, promo 511, promo_mp 159, op 66, promo_ally 57, dr 36.
Era: PanZ 1,651, FanZ 1,455.

## Quality signals
- Vision confidence: 3,084 high, 6 medium, 16 low.
- OCR text agreement (share of vision words OCR also found): mean 0.969 over 3,104 cards.
  20 cards are below 0.6: 14 are the "never officially released" S07 promos (text hidden by an overlay;
  OCR sees only the overlay), the rest are very short Drill/attack texts where OCR misses the infinity
  symbol. Samples checked by eye (S14 BST_32, S07 STR_S123) match the vision text.
- OCR stage agreement (843 personalities where OCR read the stage column): mean 0.959. The 41 cards below
  0.8 are nearly all full-art promos where OCR cannot read the stage column; their stages were compared
  by eye against the booster printing.
- 28 cards are flagged `needs_review` (list below). 59 cards have a filename issue (almost all one-letter
  filename typos; the card itself was read, not the filename).

## needs_review (28)
- Printed card-type oddities (check against the CRD): S02 BST_136, S03 BST_116, S04 BST_22, BST_24, BST_35,
  BST_110, S05 PRO_P6, S08 BST_19, S10 BST_46, S12 PRO_P21, S19 BST_54.
- (Restored) fan re-creation: S06 PRO_P1_RST.
- Placeholder images ("Image N/A", no card to read): S04 PRO_P9, S04 PRO_P10.
- "Never officially released" overlay, text copied from the reprinted card: S07 PRO_P1, P3, P7-P12, P14,
  P15, P17-P20.
- Cleared during this run after zooming: S10 BST_39 (Earthling), S11 BST_32 (God).

## Notes for later phases
- New in FanZ Sets 13+: F badge = Fusion (T_Fusion trait card), black warning-triangle icon `[Warning]`
  (Set 16+, meaning not stated on the cards), Foresee/Remain keywords, "Stops an attack" wording, and a
  stage cost printed as `2:` instead of `costing 2 stages`.
- Mastery-restricted cards (e.g. "Blue Unity Mastery only") appear from Set 17 on; the restriction text is
  kept in `restrictions` but not yet linked to a Mastery record.
- Wording differences between a promo and its booster printing are recorded in each record's `notes`.
- Filename mismatches worth a look in QA: S16 BST_40 (file "Majin Instability", card "Majin Denial"),
  S16 BST_67 (file subtitle "Entertained", card "Guide Angel"), S17 BST_36 (file "Furious Charge", card
  "Furious Strike"), S09 BST_35 (file "Chilled Prescience", card "Chilled's Prescience"), PZP P43 number.
