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
2. **Red + Red Enraged Mastery.** Built as a draft: `sim/decks/lord_slug_red_namek.txt` (the earlier `lord_slug_red_v3.txt` with the seven Earth balls swapped for the Namek set, as the notes advise).
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
- Ball access: Dragon Radar, Namekian Dragon Clan, Namekian Disturbance, Namekian Planned Attack x2, Namekian Dash x2, Namekian Growth, Namekian Ending.
- Rejuvenate attacks: Chin Grab x3, Onslaught x3, Dragon Blast x3, Focused Beams x2, Overhead Blast x2, Sudden Blast, Airborne Attack x2, High Knee x2; finishers Optic Blast, Villainous Energy Beam.
- Defence / recovery: Forceful Block x3, Hybrid Defense x2, Buffer, Protective Posture, Namekian Regeneration x2, Namekian Fusion, Namekian Concentration, Namekian Overtime x2.
- Tech: Wall Breaker x2 (opponent cannot gain anger), Korin (Rejuvenate 1 after taking life-card damage).

## Simulator result (rough signal only)
`sim/behaviors.py` got an **approximate** Namekian Knowledge Mastery (anger +1 per in-combat `rejuv`, Namek ball entering mills 1, a single ball is protected). It does **not** model Knowledge's "shuffles into your Life Deck" trigger, ball-search cards (Dragon Radar, Dragon Clan, Planned Attack, Dash, Disturbance, Ending), Wall Breaker, Dragon Blast's Rejuvenate, Korin or the Regeneration level change; coverage is 71% for the Namekian deck and 77% for the Red one. Win % for the Slug deck, 500 games each:

| vs | Namekian Knowledge | Red Enraged (Namek balls) |
|---|---|---|
| friend's Red Piccolo | 1.8 | 11.2 |
| Wheelo (Black mill) | 19.8 | 10.8 |
| Nail (Black mill) | 21.0 | 10.6 |
| Garlic Jr. (Red) | 3.2 | 4.6 |

Reading: in the model both Slug decks are slow and lose to fast MPPV decks (Piccolo wins on turn 3 of its own turns); Namekian does better against slow decks. The numbers understate Namekian because its ball search and anger denial are not modelled. Treat the ranking as card-based reasoning, not a simulated result.

## Unverified / open
- Does Knowledge's anger trigger once per effect or once per card? (Assumed once per effect; Slug L3's doubling changes the amount, not the number of triggers.)
- Does the Namek ball "cannot be captured" clause of Knowledge apply when a second ball arrives? (Text: "While you control 1 Dragon Ball".)
- Which Namek Dragon Ball 6 text is current (two wordings exist; the deck uses `U63` either way).
- The app has not loaded this code yet; the explicit MP printings field and the plain MP name are confirmed by earlier imports (Nappa, Wheelo).
