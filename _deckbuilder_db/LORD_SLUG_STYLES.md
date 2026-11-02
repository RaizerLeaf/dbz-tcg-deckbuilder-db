# Lord Slug: style comparison (Sets 1-7, PanZ rulings, errata applied)

Written 2026-11-02. Lord Slug is a **Villain** with **Namekian heritage** (`mps.json`), so Namekian Masteries are legal and Saiyan Masteries are not. One legal printing per level (all Set 3):
L1 Aged (PUR 3) / L2 Successful (PUR 4) / L3 Renewed (PUR 5) / L4 Huge (PUR 6, top power 400,000).

## What each level rewards
- **L1**: every Dragon Ball that enters play raises anger 1; if you control no ball at the end of combat, search for one and place it into play.
- **L2**: Power is an attack (AT +3 stages, HIT Rejuvenate 2): a Rejuvenate trigger every turn.
- **L3**: attacks deal +2 stages; the first time each combat one of your effects shuffles or Rejuvenates cards into your Life Deck, the amount is doubled (Lord Slug's Regeneration 4 -> 8).
- **L4**: cannot win by MPPV; Instant Power: lower 1 level **or** search for a ball and play it. Rulebook 3.0: a deck that cannot MPPV and would advance at Level 4 resets anger to 0 and goes to the MP's highest stage, so anger at L4 is a full heal.
- **Named**: Lord Slug's Fist Slam (L2 or lower: anger +2; L3+: Rejuvenate 1 and capture a ball), Lord Slug's Regeneration (Limit 2, Rejuvenate 4, may advance or lower).
- **Wins**: Dragon Ball Victory, or emptying the opponent's Life Deck (damage and destroy effects). MPPV is impossible, so the anger economy only has to buy three level-ups.

## Ranking (best to worst)
1. **Namekian + Namekian Knowledge Mastery, Namek Dragon Balls.** Built: `decks/lord_slug_namekian_knowledge.txt`.
   - Knowledge raises anger 1 for every in-combat Rejuvenate or shuffle into the Life Deck. Slug's own L2 HIT, Fist Slam (L3+) and Regeneration all Rejuvenate, and Namekian has the most Rejuvenate cards (Chin Grab triggers twice, Onslaught, Focused Beams, Dragon Blast, Forceful Block, Hybrid Defense, Regeneration, ...).
   - Every Namek ball that enters play destroys the top card of the opponent's Life Deck (a free mill on top of L1's anger), and with exactly one ball in play it cannot be captured. Namek Dragon Ball 1 also protects the others and gives +1 life card to your attacks.
   - Namekian has about 15 ball-search cards (Dragon Radar, Dragon Clan, Disturbance, Planned Attack, Dash, Ending, Growth, ...), so L1's "ball enters" anger and a Dragon Ball Victory attempt are both live.
   - Namekian also has the anger-denial cards a slow deck needs against MPPV (Airborne Attack, Downward Blast, Counter Blast, Side Kick) and Freestyle Villain tools (Wall Breaker, Villainous Energy Beam / Power Ball).
2. **Red + Red Enraged Mastery.** Built by another chat as `decks/lord_slug_red_namek.txt` (Red Slug V4 Namek: the earlier `sim/decks/lord_slug_red_v3.txt` with the Earth balls swapped for the Namek set). In the roster playtest below, the Namekian deck beats it 47 games out of 50.
   - Red has the rejuvenation-adjacent cards the owner pointed out: Red Right Blast (draws on the next Rejuvenate; from the discard pile it lowers anger 2), Red Hurl (anger +1, HIT Rejuvenate 2), Red Blaze (anger +1, Rejuvenate 2, critical effect), Red Duck (Rejuvenate X = anger), Red Emergency.
   - Red has by far the most anger (54 cards) and critical-effect cards (18), and Enraged turns each critical effect into anger +1. Slug only needs 15 anger to reach L4, so most of that engine is wasted, except that anger at L4 resets the MP to its highest stage. Critical effects can capture balls.
   - Weakness: almost no ball search (Radar and Fist Slam only), no anger denial, and Knowledge's mill and ball protection are missing.
3. **Namekian + Namekian Radiant Mastery, Earth Dragon Balls (not built).** Radiant: an Earth ball you own entering during combat raises anger 1 (stacks with L1); with 3 or more Earth balls you own in play your attacks deal +2 life cards; its Power fetches a ball while you control fewer than 3. Strong if three balls stay in play, but Earth balls are not protected (Earth 1 gives *all* attacks +1 life card, including the opponent's), the Namek protection and mill are lost. Worth a test as a variant of #1.

Not recommended: Black, Orange and Blue have 6-10 Rejuvenate cards each and no ball support; Saiyan Masteries are illegal for Slug.

## Deck on file: Lord Slug Namekian Knowledge (60 cards)
Code in `decks/lord_slug_namekian_knowledge.txt` (generated with `deckcode.py`, explicit MP printings `_MC-U69_MC-U70_MC-U71_MC-U72`). `deckcode.py check`: no errors or warnings; decode/re-encode identical.
- Defaults: Time Is A Warrior's Tool x1, Stare Down x2 (Villain MP).
- Named: Lord Slug's Fist Slam x3, Lord Slug's Regeneration x2.
- Dragon Balls: the seven Namek Dragon Balls.
- Ball access: Dragon Radar, Namekian Dragon Clan, Namekian Disturbance, Namekian Planned Attack x2, Namekian Dash x2, Namekian Growth.
- Rejuvenate attacks: Chin Grab x3, Onslaught x3, Dragon Blast x3, Focused Beams x2, Overhead Blast x2, Sudden Blast, Airborne Attack x2, High Knee x2; finishers Optic Blast, Villainous Energy Beam.
- Defence / recovery: Forceful Block x3, Hybrid Defense x2, Buffer, Protective Posture, Namekian Regeneration x2, Namekian Fusion, Namekian Overtime x2; Namekian Downward Blast x3 (lowers the opponent's anger 2).
- Tech: Wall Breaker x2 (opponent cannot gain anger). Korin, Namekian Ending and Namekian Concentration were cut after the first draft. **Korin was an error: he is a Hero Ally and cannot be played with Lord Slug (Villain)**; the first code posted in the chat contained him, the code in `decks/` does not. Ending (its end-of-combat shuffle was not worth modelling) and Concentration (only works on turns without combat) were cut for playtest reasons.

## Simulator playtest (rough signal only; `python -m sim playtest decks/lord_slug_namekian_knowledge.txt -n 50`, 50 games per opponent)
Coverage: **97% modelled**. Not modelled: Namek Dragon Ball 2's optional level lowering, Downward Blast's "place this card on the top or bottom of your Life Deck", Focused Beams' "if stopped, banish the bottom 2 cards", Villainous Energy Beam's "damage is banished" (the cards still leave the Life Deck), Lord Slug's Regeneration's "use after taking damage / advance or lower" (the AI plays it proactively for the Rejuvenate 4), Dash's "reveal a ball to look at the hand", Growth's Level 3+ Styled-card search, Allies. "Hand-coded" in `coverage` means custom code exists, not that every sentence is handled.

| Opponent (roster) | Slug wins / 50 | How games ended |
|---|---|---|
| Orange Trunks V5 | 6 | lost to MPPV 11, to Survival 33; won DBV 3, Survival 3 |
| Red Trunks draft | 6 | lost to MPPV 39, Survival 5; won DBV 1, Survival 5 |
| Vegeta Pinnacle Red Ascension | 8 | lost to MPPV 36, Survival 6; won DBV 6, Survival 2 |
| Vegeta Awakening Saiyan Dynamic | 29 | lost to Survival 21; won DBV 5, Survival 24 |
| Nappa Saiyan Clench | 24 | lost to Survival 26; won DBV 7, Survival 17 |
| friend's Red Piccolo | 21 | lost to MPPV 29; won DBV 4, Survival 17 |
| Red Garlic Jr. | 23 | lost to MPPV 27; won DBV 4, Survival 19 |
| Nail Black | 47 | lost to Survival 3; won DBV 4, Survival 43 |
| Wheelo Black mill | 41 | lost to Survival 9; won DBV 7, Survival 34 |
| Wheelo Blue lockdown | 46 | lost to Survival 4; won DBV 4, Survival 42 |
| Black Krillin | 40 | lost to Survival 10; won DBV 6, Survival 34 |
| Red Slug V4 Namek | 46 | lost DBV 3, Survival 1; won DBV 21, Survival 25 |

Overall 56% over 600 games (+/- about 14 points per opponent at 50 games; table after merging the Vegeta decks that another chat added to the roster). It joined the roster at rank 3 of 11 (61.7%); after other chats added the Vegeta and Raditz decks and `roster rebuild` it is rank 6 of 17 (49.7%). The per-opponent table above does not include the Raditz decks.
Reading: the deck is a slow grinder. It beats the mill and slower decks, trades evenly with Nappa, Piccolo and Garlic (Wall Breaker, Downward Blast and the Survival route let it race), and loses to the fastest decks (both Trunks decks, which MPPV or out-damage it by turn 4-5). Dragon Ball Victory fires in 4-7 games per opponent; most wins are Survival. Logs read: Wall Breaker holds Piccolo on Level 1 for several turns; Knowledge takes Slug to Level 3 by turn 4-5 (Nappa log); Dragon Blast hits for 9 life cards with three balls out; Optic Blast captured a ball for a Dragon Ball Victory.

What was added to the simulator for this deck (`sim/behaviors.py`, `cardmodel.py`, `engine.py`, covered by `SlugNamekian` tests in `sim/tests/test_rules.py`):
- Namekian Knowledge Mastery (anger on in-combat Rejuvenate, Namek ball entering mills 1, one ball cannot be captured).
- Lord Slug Level 3: the first in-combat Rejuvenate each combat is doubled (new hook `rejuv_amount`). Previously Level 3 only gave +2 stages.
- **Engine/parser fixes that affect every deck:** "HIT: Rejuvenate N" is now applied (it was ignored, so Slug's own Level 2 Power and many cards never Rejuvenated); in-combat Rejuvenate triggers fire only if a card actually moved; "AT +1 stage" (singular) and "4 + X life cards" are parsed (Wall Breaker and Namekian Dragon Blast dealt no damage before).
- Cards: Dragon Radar, Dragon Clan, Disturbance, Planned Attack, Dash, Growth (ball search/play; "play" uses the ball's immediate effects, "place into play" does not; no second ball of the same name), Dragon Blast, Overhead Blast, Hybrid Defense, Regeneration, Airborne Attack, Protective Posture, Sudden Blast (shuffle counted as one Knowledge trigger), Onslaught (second use at once with 2+ balls), Fusion, Overtime, Namek Dragon Ball 4, Optic Blast, Wall Breaker.
- Regression decks before/after: Wheelo V2 vs Piccolo 15.9% -> 15.9%; Red Trunks vs Orange V4 (Orange MPPV off) 59.1% -> 60.4%; Red Slug V4 vs Piccolo 10.2% -> 11.8% (HIT Rejuvenate now applies).

## Unverified / open
- Does Knowledge's anger trigger once per effect or once per card? (Assumed once per effect; Slug L3's doubling changes the amount, not the number of triggers.)
- Does the Namek ball "cannot be captured" clause of Knowledge apply when a second ball arrives? (Text: "While you control 1 Dragon Ball".)
- Which Namek Dragon Ball 6 text is current (two wordings exist; the deck uses `U63` either way).
- Unverified simulator assumptions (marked in the code): Slug L3 doubling also applies to card-by-card Rejuvenate (Airborne Attack) but not to Sudden Blast's shuffle; Onslaught's second use is taken immediately; a second Wall Breaker adds nothing.
- The app has not loaded this code yet; the explicit MP printings field and the plain MP name are confirmed by earlier imports (Nappa, Wheelo).
