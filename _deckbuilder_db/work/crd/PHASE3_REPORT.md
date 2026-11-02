# Phase 3 report: errata, rulings, Frozen List, Gold Title Reprints

Sources: FanZ Combined CRD v1.15 (6/4/2025, 24 pp) and Panini CRD v6.0 (6/30/2017, 10 pp), both in `_rules/`.
Regenerate: `python scripts/crd_parse.py && python scripts/crd.py` (reads `work/full/cards.json`, writes `cards.json`/`cards.csv`).

## What was parsed
- FanZ CRD: 106 [ERRATUM] + 15 [RULING] entries (section III), the Frozen List (14 names), the Gold Title Reprint list (24 names),
  and the core/general rules (kept as text in `crd_general.md`).
- Panini CRD: 62 individual card rulings (59 duplicate a FanZ entry, 3 exist only in the Panini CRD:
  C15 Blue Knee, U66 Blue Avoidance, S144 Blue Swift Block).

## Matching
Entries are keyed by set section + printed card number, then checked against the card name. 109 erratum and 18 ruling
matches were made this way (+ a few by name where the CRD number is a typo, listed below). Errata/rulings also apply to every
printing with the same card name: 78 erratum and 3 ruling records were attached to printings the CRD does not list
(`listed_for_this_printing: false`), only when the printing's own text showed the original or updated wording.

Result: 167 cards have errata attached: 120 `printing_current` (printed text already shows the corrected wording) and
47 `text_current_derived` (text_current = printed text with the CRD change applied). 70 cards carry a ruling note.
No erratum is left unresolved. 10 needed a manual resolution because the CRD "Original Text" does not match the printing
word for word; each is in `work/crd/overrides.json` with the reason (derived only from the CRD's own updated wording).

## text_current rules
- verbatim CRD replacement of a span of the printed text, or
- printed text plus the CRD's "This Card Gains" line (placed at the start, or after the Endurance line; exact position on a corrected image is not known), or
- unchanged when the printing already shows the update.
FanZ-era notation is kept (e.g. "[Sword Icon]" -> `[Attack]`, "Ϟ POWER" -> `[Instant] POWER`, "(God Trait only.)" -> `([Trait:God] only.)`).
`limit_per_deck`, `restrictions`, `deck_rules`, `icons`, `keywords` are re-derived from the current text (8 cards change their Limit).

## Update 2026-11-02: latest print wins
- **PanZ wording.** 4 CRD entries carry a Panini/Updated wording plus a later "FanZ Updated Text" (Blue Guard, Orange Uppercut, Unleashed, Orange Checkup Drill). The FanZ wording is used
  only when a Set 1-7 printing shows it (Uppercut S05 P14 and Checkup Drill S07 C32 print "Limit 1 per deck"; Unleashed is a "Gains" entry). Blue Guard is not shown anywhere in Sets 1-7 with the FanZ
  wording, and Set 7 S50 prints "would be discarded ... by a card effect", so that is its `text_current`.
- **Printed label.** Real Set 1-7 images that print "(Most Recent Printing)" (13 cards) are `is_mrp` true, and their wording is copied to the older printings' `text_current`. This fixed Black Scout Maneuver
  (CRD text has a typo; P7 prints the right wording), Black Command and Orange Palm Blasts (no CRD entry) and Namekian Flinch. Unflagged before: S04 P7, S07 S50, S04 S119, S07 S124.
- **S04 P9 (Blue Guard) and P10 (Namekian Mouth Beam) never came out** (owner, 2026-11-02). Their records were 'Image N/A' placeholders with text copied from Set 1; they are now excluded by `owner.py`
  (`exclude_never_released`, listed in `excluded_cards.json`). The CRD's MRP pointers to them are stale: Blue Guard's real MRP is Awakening S50; Namekian Mouth Beam has no Set 1-7 MRP image; its `text_current` ("Styled card with a shield icon") is the wording in both the FanZ CRD erratum and the Panini CRD C28 ruling. The Set 3 image (shown by the owner 2026-11-02) prints the original "Styled block".
- Result: 173 cards with errata (124 `printing_current`, 49 `text_current_derived`), 56 `is_mrp` true. 14 records changed, then the 2 placeholders removed (3,090 records; diffed before and after).

## is_mrp
True = this printing is named by the CRD as the most recent (corrected) printing, or the entry says "currently up to date in the X
card images", or "this change matches the printed text of ...". False = card has errata but this printing is not the MRP
(117 cards). null = no erratum (2,939 cards). 50 printings are True.

## Frozen List / Gold Title Reprints
- `frozen` is true for all printings of the 14 listed names (28 cards); `frozen_listed_printing` is true only for the exact printings the
  CRD names. `frozen_filename_flag` records the owner's "(Frozen)" filename flag. Every filename flag agrees with the CRD list.
- Gold Title Reprint: 24 names on the list; 10 are crossed out in the PDF (strike-through read by eye from the rendered page 24, since the
  text layer does not carry it), so `gold_title_reprint` = true for 14 cards (usable), false for 10 (listed but crossed out), null otherwise.

## Problems to look at (also for the QA report)
- Unmatched CRD entries (2): Evolution P4 Trunks - Bashful (FanZ and Panini CRD). No such image is in the folders; the updated
  PanZ MP & Ally promo `PZP_AL_P169` and H&V U71 show the corrected text.
- MRP pointer with no image (1): S8 Goku - Super Saiyan -> "Evolution P11" (no S04 P11 image; S04 P9/P10 never came out and were excluded, see below).
- CRD numbers that do not match the printings (matched by name instead): U6/U7 Captain Ginyu (printed U66/U67), U144 Quickness Drill
  (printed U114), S30/R145 Namekian Knowledge Mastery (Panini CRD says R145; printed R131), U66 Blue Avoidance (only the starter copy is S66),
  C19 Orange Bicycle Kick (printed R19, Set 8), R20 "Orange Sidestep" in Set 16 (the card is Orange Redacted Drill, matched by number).
- Frozen List printings that do not exist in the records: Orange Adaptive Mastery "Premiere S29" (S29 is Blue Protective; the Adaptive starter is S26),
  Red Tactical Drill "Evolution S167" (S167 is in Awakening; Evolution's is S132), Orange Retribution Mastery "Awakening S10" (only DR10 is in the folders).
- Errata cards whose printed wording differs from the CRD's "Original Text" (typos or reworded printings): see overrides.json.
- The red "latest additions" markings and the Panini light-blue shading in the CRD PDFs are not in the text layer, so `source` says "FanZ CRD" for every
  entry; whether an entry also appears in the Panini CRD is recorded by a separate Panini entry on the same card.
