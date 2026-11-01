# Phase 1 pilot report (S01, S14, PZP: 652 images)

Files: `cards.json` / `cards.csv` (all 652 records), `sample_records.json` (10 samples),
`ocr_compare.json` (per-card OCR agreement). Vision source: `work/vision/{S01,S14,PZP}.jsonl`.

## Coverage
| Set | Images | Read |
|---|---|---|
| S01 Premiere (booster 164, starter 150, promo 21) | 335 | 335 |
| S14 Showdown (booster 52, promo 49) | 101 | 101 |
| PZP PanZ MP & Ally Promos (MPs 159, Allies 57) | 216 | 216 |

By type: 225 Main Personality, 72 Ally, 104 Energy Combat, 102 Physical Combat, 50 Event,
42 Drill, 28 Setup, 22 Mastery, 7 Dragon Ball. Every card was read from the image, with the
original opened whenever a sheet was not clear.

## Accuracy checks
- OCR text vs my reading: mean word agreement 0.989 (median 1.0; 632 of 652 cards >= 0.90).
  I checked every word-level difference. All were OCR noise (Endurance badges, disclaimer
  text, words cut off by the OCR crop). Three that looked like real gaps ("less" on S14 R16,
  "may" on S14 P28, "+1" on S14 P42) were confirmed as printed by zooming into the original.
- Reverse check (OCR words missing from my text): 0 cases, so no dropped sentences found.
- Power stages: 297 personalities; 231 matched OCR exactly. 13 values differed (mostly 5 vs
  9). I re-checked all 13 against close-ups and every one was an OCR misread.
- Names, subtitles and card numbers vs filenames: all match apart from 8 filename issues
  (below).
- Traits: consistent per character and with the CRD Trait list.
- Blind re-read of a random 12-card sample (icons, Traits, PUR, level, type, alignment,
  text): 12 of 12 exact.

## Problem cards
Printed oddities (transcribed as printed, worth knowing):
1. S14 U40 Hercule - Best Buddy: power stages printed ascending (137 ... 182, then 0).
2. PZP P67-P70 Hercule MPs: power stages printed ascending (5 ... 50, then 0).
3. PZP P212 Trunks - Resolved: second stage 555,000; S01 C5 (same card) prints 550,000. Both
   checked.
4. PZP P104 Garlic Jr. - Transformed: "Your opponent's attacks deal +3 life cards", a
   drawback where L1-L3 reduce damage. Check against the CRD in Phase 3.
5. S01 U113 Overpowering Attack (Errata): "(Limit 1 per deck.)" sits at the end of the text
   box instead of the start; the image looks edited to show the erratum.
6. Same card name, different text between printings: S01 P4 vs S13 Krillin - Ready (the
   promo lacks "and raise your anger 2 levels"; PZP P15 matches the starter, PZP P19 (SDCC)
   matches the promo); S01 P3 vs S9 Gohan - Resilient Child (minor wording); S01 P18 vs R129
   Blue Terror ("in" vs "into"); S14 P39 vs S01 R144 Red Observation and S14 P48 vs S01 U110
   Devastating Blow (modernised wording).
7. Spelling differs between printings: S01 U72 "JIECE" vs PZP P162 "JEICE"; S01 U69 prints
   "CHICHI" (filename "Chi Chi"); PZP P206 text says "Chi-Chi".
8. Printed typos/grammar kept as printed: S01 R126/P16 Black Scout Maneuver ("your
   opponent's his Life Deck ... banishes them"), S01 U77 "Chose", S01 U82 "it's", S01 S126
   "opponents", S01 S19 subtitle "CONQUERER".
9. Number oddities: PZP "P121A" prints "BONUS P121" and "P121B" prints "P121" (two
   different Android 16 levels share P121); PZP "P166B" prints "P166" (alternate art of
   P166); S14 R5, U18, R31, R37 print "PREVIEW" with the number; S14 boosters use "S"
   rarity for S43-S52.
10. PZP P19 Krillin: "(SDCC)" is printed on the card as part of the subtitle, not only in the
   filename.
11. PZP P206 Ox King: a "(FROZEN)" stamp is below the image but the filename has no
   (Frozen) flag.

Filename issues (card is clear; the file name is wrong):
- PZP "P43_Piccolo - Ferocious" prints **P42** (resolves the duplicate P43).
- Typos: S01 S1 and PZP P24 "Price of Saiyans"; S01 S4 "Vegata"; PZP P22 "Unleshed ";
  PZP P33 "Andrid 18"; S14 S48 "Cultiating Mass"; PZP P121A has no " - " before "Focused".

Nothing in the pilot is `needs_review`: no card was unreadable.

## Open questions
1. MP vs Ally: I used the printed edge label (`ALLY` vs `HERO`/`VILLAIN`). OK to use this
   for every set?
2. `T_` Trait cards and the `DR` prefix (not in the pilot): what are they, and should they
   be records?
3. Era for the PZP and OP folders: they are printed by FanZ. Keep `era = FanZ`?
4. The S rarity letter appears on booster cards in S14 (S43-S52), so it isn't only
   "Starter". I store the printed code without interpreting it. Do you want a meaning?
5. Should "(SDCC)" stay in the subtitle of PZP P19, given it is printed?
6. Piccolo - Fused (S01 S24, PZP P23) has no Fusion Trait printed. Treat as a normal
   Piccolo for Phase 4 (not a fused MP)?
7. Named cards: I mark titles with a possessive ("Goku's Kamehameha", "Trunks' Sword
   Slash") plus cards whose text says they are "considered Named" (Bee, Overwhelming Power).
   Is that your definition?
8. Style: "Namek Dragon Ball N" is Freestyle (first word "Namek", not "Namekian").
   Personalities get no style. OK?
9. PanZ Allies print no alignment; I leave `alignment` null and record "(Heroes only.)" in
   `restrictions`. OK?
