# Reprint audit: cards that share a name (Sets 1-7)

Written 2026-11-02 after the owner's app answered "Unknown card EV-S60" for Tenshinhan. Reproduce with `python scripts/audit_reprints.py` (the raw output is at the end); `friends/tests/test_reprints.py` keeps the findings true.

## What was wrong
The app knows each card by its **first printing** (see `DECKBUILDING_NOTES.md`, "Deck code format"). `deckcode.app_printing` has to map every printing of the SAME card to one code and keep DIFFERENT cards that share a name apart.
It did the first part by name alone, except for Allies, where it also compared the printed text (because Vegeta and Cell Jr. are several different cards). Tenshinhan's Set 1 card C9 starts with "(Heroes only.)"; the Set 4 reprint EV-S60 has a
redesigned layout without that line, so the two looked like different cards and `EV-S60` was treated as a first printing. The checker therefore did not warn, and three Goku decks carried a code the app rejected.
**Fix:** Allies are now told apart by **subtitle**, which is what the CRD says ("some Ally characters have multiple cards with the same name, but different subtitles; your Life Deck may only contain one copy of an Ally by name").
Tenshinhan C9 and EV-S60 are both "Returned", so they are one card and its app code is `C9`.

## Findings (1,065 names in Sets 1-7, 283 with more than one printing, 378 later printings compared with the first printing of the same card)
1. **Only Tenshinhan was affected** by the grouping bug. After the fix the only names that map to more than one code are the genuinely different cards: **Vegeta** (Villains-only Impatient `HV-U72`, Hero Unrelenting `EV-U93`) and
   **Cell Jr.** (Trapped `AW-U76`, Escaping `AW-U77`, Unrelenting `AW-U78`). Both Vegetas share a name, so a deck may hold only one of them (one Ally per name). No deck or `sim/decks` file uses a reprint the app may not know (tested).
2. **No renamed reprints:** no two cards with different names share identical type, style and rules text.
3. **Text comparison, first printing vs later printings:** 347 are identical word for word (layout only: the Set 4+ layout moves "DAMAGE:" and "HIT:" lines, adds "/" breaks, moves "(Banish after use.)"),
   12 differ only by the Set 7 gender-neutral wording ("his" -> "his or her") or an icon label, 19 have a larger wording difference. Of those 19, **13 already read identically in `text_current`** (errata and later promos are resolved by the pipeline): Black Command, Black Corruption (two reprints),
   Black Punishment, Black Scout Maneuver, Combination Drill, Orange Crashing Drill, Orange Palm Blasts, Orange Uppercut, Quickness Drill, Namekian Knowledge Mastery, Blue Guard, Namekian Flinch. The other six are item 4.
4. **Text the deck builder reads that still differs between printings of one card** (the code in a deck resolves to the first printing's record, so that is the wording the checker and simulator read):
   - Gender-neutral wording only, no effect change (Black Entanglement's HIT now says "in it" instead of "in his hand"): Black Entanglement, Black Radiating Drill, Black Speedy Dodge, Black Strike, Blue Draining Blast, Blue Mental Drill, Confrontation, Saiyan Drive By, Villainous Energy Sphere.
   - Typographic only: Blue Terror ("into" / "in"), Namekian Right Throw ("raise your anger 2 levels" / "2", "AT +3" / "AT + 3").
   - **Saiyan Rescue** (HV-U94 vs AW-S115): "[Continuous]: Once per turn as an action, choose a card..." became "While attached, once per turn as an action you may choose a card...". Same effect; the label and wording moved.
   - **Visiting the Past** (U107 vs promo PF-P4): the promo drops "(Banish after use.)" and is stamped FROZEN (recorded in `cards.json`). The Frozen list is ignored by default and the promo is a Set 5 promo, so the deck builder reads U107 (banish after use).
     **Open question for the owner:** if the promo is the card you want to play, it is *not* banished after use. (Unverified which one is current under PanZ rulings.)
   - **Tenshinhan**: C9 has "(Heroes only.)", the reprint does not. The first printing's restriction applies (matches the app, which only knows C9).
5. **Type disagreement:** Namekian Double Strike: C30 is an Energy Combat card, the promo PF-P6 is typed Physical Combat (owner ruling "stays as printed"). The app knows C30, so a deck always plays the Energy Combat one.
6. **`text_current` coverage:** in five groups only some printings carry `text_current` (Namek Dragon Ball 6, Namekian Elbow Drop, Orange Left Punch, Orange Stare Down, Red City Destruction). The words are identical, so nothing changes; it only means
   "look at `text_current` of the first printing" is not enough proof that a reprint was checked.
7. **Fields that agree across every group:** style, alignment (except the two Vegetas), is_named / named_character, limit per deck, frozen flag. So a limit printed only on a later printing cannot hide a limit from the checker.

## What I did not verify
- That the app really keys every card on its first printing: the evidence is the owner's codes (S25 not R145, R152 not P8, and the rejections of AW-S77, EV-S159, EV-S165, AW-S118, AW-S122 and now EV-S60).
  Two Vegetas and three Cell Jr. share a name and the app accepted `EV-U93` (and Cell Jr. codes were not tested yet), so it does not key on name alone; a card the app rejects should be added to the evidence list.
- Whether any same-name pair is really two different non-Ally cards: the audit found none (every non-Ally name has the same type, style and text meaning in all printings), but the app's own identity rule is unknown.
- Main Personality levels are excluded (they are chosen per printing and carry subtitles).

## Raw audit output
```
1065 card names in Sets 1-7 (excluding Main Personalities); 283 have more than one printing.

## 1. How deckcode groups same-name cards
- Cell Jr. (Ally): 3 separate cards, app codes ['AW-U76', 'AW-U77', 'AW-U78']; subtitles ['Escaping', 'Trapped', 'Unrelenting']
- Vegeta (Ally): 2 separate cards, app codes ['EV-U93', 'HV-U72']; subtitles ['Impatient', 'Unrelenting']
  Allies are separated by SUBTITLE (CRD: "same name, but different subtitles"); every other card is one card per name.

## 2. Later printings whose text differs from the first printing
  layout only: 347, TEXT CHANGE: 19, wording (his -> his or her / icon label): 12
- Black Command: first S45 vs AW-S124 (starter): TEXT CHANGE
- Black Corruption: first C15 vs EV-P3 (promo): TEXT CHANGE
- Black Corruption: first C15 vs AW-S125 (starter): TEXT CHANGE
- Black Entanglement: first S72 vs AW-S147 (starter): TEXT CHANGE
- Black Punishment: first C19 vs EV-P2 (promo): TEXT CHANGE
- Black Radiating Drill: first HV-C15 vs AW-S142 (starter): wording (his -> his or her / icon label)
- Black Scout Maneuver: first R126 vs EV-P7 (promo): TEXT CHANGE
- Black Speedy Dodge: first S123 vs AW-S145 (starter): wording (his -> his or her / icon label)
- Black Strike: first S134 vs AW-S143 (starter): wording (his -> his or her / icon label)
- Blue Draining Blast: first C26 vs AW-S38 (starter): wording (his -> his or her / icon label)
- Blue Guard: first S65 vs AW-S50 (starter): TEXT CHANGE
- Blue Mental Drill: first S38 vs AW-S37 (starter): wording (his -> his or her / icon label)
- Blue Terror: first R129 vs P18 (promo): TEXT CHANGE
- Combination Drill: first HV-C60 vs EV-P8 (promo): TEXT CHANGE
- Confrontation: first R150 vs AW-S31 (starter): wording (his -> his or her / icon label)
- Devastating Blow: first U110 vs MC-P8 (promo): wording (his -> his or her / icon label)
- Namekian Elbow Drop: first EV-C24 vs AW-S88 (starter): wording (his -> his or her / icon label)
- Namekian Flinch: first U86 vs AW-S87 (starter): TEXT CHANGE
- Namekian Knowledge Mastery: first S30 vs EV-P1 (promo): TEXT CHANGE
- Namekian Right Throw: first C35 vs AW-S86 (starter): TEXT CHANGE
- Orange Crashing Drill: first HV-C40 vs EV-P5 (promo): TEXT CHANGE
- Orange Left Punch: first EV-C35 vs AW-S66 (starter): wording (his -> his or her / icon label)
- Orange Palm Blasts: first S57 vs EV-S119 (starter): TEXT CHANGE
- Orange Stare Down: first S117 vs MC-P9 (promo): wording (his -> his or her / icon label)
- Orange Uppercut: first R139 vs PF-P14 (promo): TEXT CHANGE
- Quickness Drill: first U114 vs EV-P6 (promo): TEXT CHANGE
- Saiyan Drive By: first HV-C53 vs AW-S114 (starter): wording (his -> his or her / icon label)
- Saiyan Rescue: first HV-U94 vs AW-S115 (starter): TEXT CHANGE
- Tenshinhan: first C9 vs EV-S60 (starter): TEXT CHANGE
- Villainous Energy Sphere: first UR164 vs AW-UR146 (booster): wording (his -> his or her / icon label)
- Visiting the Past: first U107 vs PF-P4 (promo): TEXT CHANGE

## 3. Fields that disagree between printings of one card
- type: Namekian Double Strike: {'Energy Combat': ['C30'], 'Physical Combat': ['PF-P6']}
- restrictions: Tenshinhan: {('Heroes',): ['C9'], (): ['EV-S60']}

## 4. Text the deck builder reads (text_current if present) that differs between printings of one card
- Black Entanglement: text differs: S72[printed], AW-S147[printed]
- Black Radiating Drill: text differs: HV-C15[printed], EV-S34[printed], AW-S142[printed]
- Black Speedy Dodge: text differs: S123[printed], EV-S56[printed], AW-S145[printed]
- Black Strike: text differs: S134[printed], EV-S58[printed], AW-S143[printed]
- Blue Draining Blast: text differs: C26[printed], AW-S38[printed]
- Blue Mental Drill: text differs: S38[printed], EV-S65[printed], AW-S37[printed]
- Blue Terror: text differs: R129[cur], P18[cur]
- Confrontation: text differs: R150[printed], P10[printed], EV-S32[printed], AW-S31[printed]
- Namek Dragon Ball 6: only some printings carry text_current (same words): U63[printed], EV-S81[cur]
- Namekian Elbow Drop: only some printings carry text_current (same words): EV-C24[cur], AW-S88[printed]
- Namekian Right Throw: text differs: C35[cur], EV-S98[cur], AW-S86[cur]
- Orange Left Punch: only some printings carry text_current (same words): EV-C35[cur], AW-S66[printed]
- Orange Stare Down: only some printings carry text_current (same words): S117[cur], MC-P9[cur], EV-S127[printed], AW-S70[cur]
- Red City Destruction: only some printings carry text_current (same words): HV-U89[printed], PF-P13[cur]
- Saiyan Drive By: text differs: HV-C53[printed], AW-S114[printed]
- Saiyan Rescue: text differs: HV-U94[printed], AW-S115[printed]
- Tenshinhan: text differs: C9[printed], EV-S60[printed]
- Villainous Energy Sphere: text differs: UR164[printed], MC-P15[printed], AW-UR146[printed]
- Visiting the Past: text differs: U107[printed], PF-P4[printed]
```
