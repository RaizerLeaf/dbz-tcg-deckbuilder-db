# Real game: Orange Trunks V6 vs the friend's Red Piccolo (owner's log, 2026-11-02)

Source: `2026-11-02_orange_trunks_v6_vs_friend_red_piccolo.txt` (the app's own log, played online against the friend). **Result: defeat by MPPV on turn 9** (the friend's 5th turn).
This is **one game**. It is evidence about how the friend plays and about what the simulator assumes; it is not a win rate.

## What the log shows (facts)
- **The friend's Level 1 is Piccolo - Composed** (EV-S11), not Stoic: "Whenever you gain stages from a card effect, raise your anger 1 level. Whenever you Rejuvenate during combat, raise your anger 1 level."
  Path: Composed (turn 3-8) -> Combat Stance (turn 8) -> Unleashed (turn 8) -> Fused (turn 8) -> MPPV turn 9. The simulator's copy of his deck (`sim/decks/piccolo_red_friend.txt`, no printings field) plays Stoic.
  (Whether his saved deck always plays Composed is not confirmed; this game says it did.)
- **He did not declare combat on his own turns 1, 3, 5, 7.** He built: six Namek Dragon Balls (2, 1, 4, 5, 7, 6; one short of Dragon Ball Victory), Setups (Red Blaze, Red Relaxation x2, Visiting The Past, Red Destiny,
  Red Burning Rage), powered up, and Rejuvenated each non-combat turn. His first and only declared combat was turn 9, to activate Red Burning Rage (+1 anger) at Level 4 with 4 anger: instant MPPV.
- **Most of the combat happened in combats the owner declared** (turns 6 and 8). Declaring combat made the friend draw 3 and let his "use when entering combat" Setups fire (Red Blaze on turn 6; Red Relaxation twice on turn 8).
- **Anger engine seen:** 9 critical damage effects, every one chosen as "lower Trunks' anger 1"; Red Enraged triggered 12 times (+1 anger each). Red Relaxation gave a critical effect AND 2 stages (Composed +1), so about +2 anger for him and -1 for the owner per use.
  Red Right Cross (pays 4 stages, +2 anger) was used three times; Weighted Clothing, Shattering Leap (used twice) and Shoulder Grab (the rest of the attacks count as critical) fed the rest.
- **Owner side:** stayed on Level 1 all game (anger peaked at 3). Combat only on turns 6 and 8; Orange Retribution Power used twice (+2 each). The MP was often at 0 stages (Right Cross costs the owner stages, he lost 4, 3, 5...).
- **Aggressive Sword Drill:** turn 6, Protective's Power put it into play (a search), so its own "if you have not searched your Life Deck this turn" search could not be used. The simulator applies the same rule, so this is modelled.
  Protective only fetches non-Styled Drills; V6 runs one (Aggressive Sword Drill), V5 ran two.
- At 3:46 the log says "You raise Piccolo's anger 1 (now 5)" via Composed's stage-gain trigger, which moved him to Level 2. The log does not show which effect gained stages, so the cause is unclear.

## What it means for the simulator
| Simulator assumption | Real game |
|---|---|
| Friend's L1 = Stoic (default first printing) | Composed. With Composed in the sim, V6 wins 85.3% instead of 90.5% (3,000 games, seed 777); V6 lite 81.7% vs 85.5%; V5 79.0% vs 81.7%. |
| The AI declares combat whenever it has an affordable attack, a Setup or a usable Power (`Game.wants_combat`); games end around turn 4-5 | The friend waits and builds; the real game lasted 9 turns. In 3,000 sim games V6 won only once on turn 9. |
| (experiment, repository unchanged) A "patient" Composed Piccolo that declares combat only on Level 4 with 4+ anger | V6 wins **58.4%** (not 85.3%); games average 7.3 turns; Piccolo wins by MPPV 1,192 of 3,000. This policy is my rough guess at his play, not a calibrated one. |
Both the Stoic default and the always-attack AI flatter decks that win by pressure. Roster rankings were built on both, so the whole roster is affected the same way; a change to the shared AI moves every rank and needs the owner's OK.

## Ideas (not done)
- Re-point the roster's friend deck at an explicit Composed code (`_EV-S11_S22_S23_S24`), and/or add an optional "patient" policy for decks the owner names.
- Re-tune V6 against the patient Composed Piccolo (more realistic), keeping the roster as the second check.
- Trunks' Knee Bash banishes a Setup: the friend's Setups (Relaxation, Blaze, Burning Rage) are his engine and only work in combat.
