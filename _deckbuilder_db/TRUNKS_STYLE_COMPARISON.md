# Trunks: style comparison on the owner's level stack (simulator, 2026-11-02)

Stack compared: **Protective (VG-U76) / Swordmaster (EV-S2) / Defiant (EV-S3) / Overpowering (EV-S4)**, Hero, Sets 1-7, errata applied.
Everything below is the toy simulator's opinion (`sim/README.md`): treat it as a rough signal, not a prediction. Coverage for the final deck: 84% of card text modelled.

## Method
For each style an optimizer (random single-card swaps, kept if the win rate against the friend's Red Piccolo improved, 400 iterations, 400 games per check) started from a rule-of-thumb deck
(Orange also from the owner's V4). Cards were limited to a pool without cards the simulator would exploit (cost-free "banish 4 to raise anger 6", "use only if", attach cards, Dragon Balls, ...).
Final numbers are 1,500 games per matchup on a different random seed.

| Deck (win % for the Trunks deck) | vs friend's Red Piccolo | vs Red Trunks (own levels) | vs Garlic | vs Nail | mean of 7 opponents |
|---|---|---|---|---|---|
| Orange V4 (owner) | 76.9 | 42.2 | 87.7 | 99.5 | 85.9 |
| Orange, optimized from V4 | 82.3 | 45.7 | 90.2 | 98.8 | 87.2 |
| Orange, optimized from scratch (control) | 80.9 | 25.1 | 91.4 | 99.4 | 84.4 |
| Saiyan Rampaging | 67.7 | 9.5 | 80.0 | 87.4 | 72.9 |
| Red Enraged | 59.3 | 15.3 | 72.3 | 87.7 | 70.1 |
| Blue Protective | 48.4 | 5.9 | 62.3 | 35.1 | 51.1 |
| Black Devious / Black Conflict | 16.1 / 6.0 | 1.2 / 0.2 | 39.0 / 12.7 | 24.5 / 5.8 | 23.8 / 7.8 |

Other opponents (Lord Slug, Krillin, Wheelo) are in the mean; all were beaten 94-100% by the Orange decks.

## Findings
- **On this stack Orange is best, then Saiyan, then Red.** The control (Orange from scratch) reaching V4's level shows the optimizer is not just overfitting V4.
- **Red does much better on its own levels.** The Red Trunks draft on Dashing / Frenzied / Energy Charged / Overwhelming beats the Piccolo 88.8% (2,000 games); the same Red cards on the Protective / Swordmaster / Defiant /
  Overpowering stack drop to 68.9% (untuned) and 59% (tuned). Level choice matters more than style here. (The notes' two worked answers say the same: Orange on this stack, Red on the Dashing stack.)
- **Orange's weakness is Red Trunks**, which beats it about 55-60% whatever the tuning (the Red deck MPPVs on turn 3).
- **Black result is not reliable.** The optimizer got stuck on a deck of expensive energy attacks with almost no defenses. Do not read it as "Black is bad"; a hand-built Black deck was not tried.
- **Blue Protective** (opponent needs 6 anger to level) only reached 48% against the Piccolo in the model. Its Defense Power is simplified there.
- Not simulated at all: Orange Adept / Adaptive, Red Ruthless, Saiyan Empowered, Black Perceptive, Blue Resolute / Tag Team, Saiyan Rampaging's Power. Namekian Masteries are not legal for Trunks (not on the heritage list).
- The simulator ignores cards' drawbacks it does not parse (e.g. Orange Welcoming Drill's "you must declare combat"), so such cards were kept out of the final deck.

## Orange Trunks V5 (`decks/trunks_orange_v5.txt`)
V4 with six changes: -1 Heroic Energy Sphere, -1 Orange Electricity (3 to 2), -1 Orange Enraged Bash (2 to 1); +1 Orange Right Beam (5 life cards, lowers the opponent's anger 2, cannot be stopped by non-Styled cards),
+1 Orange Upward Strike (lowers the opponent's anger, more per Drill), +1 Orange Extension (fetches a Drill after a second physical attack).
Simulator, 3,000 games each: vs Red Piccolo 83.3% (V4 77.8%); vs Red Trunks 46.3% (V4 40.4%); vs Garlic 90.3%; vs Nail 99.4%. With Orange MPPV switched off, vs Piccolo 79.6%.
Legality: `deckcode.py check` no errors or warnings, decode/re-encode identical, 60 cards. **Not imported into the app yet.**
Caveat: the changes were chosen by the simulator, which does not model Uppercut's search, Enraged Bash's Drill Rejuvenate or Heroic Energy Sphere's cancel. The owner should judge those three cuts.
