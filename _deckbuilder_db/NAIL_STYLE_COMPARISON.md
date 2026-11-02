# Nail: style comparison and decks (Sets 1-7, Hero, PanZ rulings)

Built 2026-11-02 at the owner's request: "a Nail deck, 3 styles ranked, Namekian is obvious but do not pass up Red (Rejuvenate / Red Right Blast)".
Decks: `decks/nail_red_enraged.txt` (the pick), `decks/nail_namekian_knowledge.txt` (the runner-up). Third option: `sim/decks/nail_black_v2.txt` (built earlier).
All codes were written by `deckcode.py`, decode and re-encode exactly, and pass `deckcode.py check` (60 cards, limits, Named, Heroes-only). Style legality
(Red or Namekian cards plus Freestyle, nothing else) was checked by script too, because `deckcode.py check` does not test it.
**Not yet imported by the owner**, so the codes are not confirmed to load in the app.

## What Nail rewards (Set 2 is the only legal printing set, so there is no level choice)
| Level | Text | What it wants |
|---|---|---|
| 1 Watchful (PUR 2) | Physical attack, AT +2 life cards; if stopped, destroy the top card of the opponent's Life Deck | being stopped costs the opponent a card |
| 2 Protector (PUR 3) | Whenever the opponent stops one of your attacks, he destroys the top 2 cards of his Life Deck; after your attack damages him he banishes X cards (X = his Endurance uses on it) | stops and Endurance are punished: a mill / Survival plan |
| 3 Unflinching (PUR 4) | Your attacks deal +3 stages. POWER: return a Dragon Ball in play to hand, or place one from your hand into play. Raise your anger 1 level | **(unverified)** the anger raise is read as unconditional (a separate sentence), so Level 3 gives anger with or without Dragon Balls |
| 4 Combat Ready (PUR 5) | Hand size +1. POWER: physical attack, 7 stages, HIT: use the immediate effects of a Dragon Ball in play | MPPV at Level 4, or a Dragon Ball engine |

Nail is a Namekian-heritage MP (Namekian Masteries are legal). His Named cards: Nail's Dashing Attacking (Freestyle, an Energy Combat card by owner ruling, always uses a critical damage effect,
HIT shuffles itself into the Life Deck) and Nail's Heritage (Limit 2). Allies named Nail are not allowed.

## Ranking (best to worst)
Simulator numbers are the toy model's opinion under identical simple play (1,000 games, first player alternates), **not** predictions. Margins under about 5 points are noise.
| | Style / Mastery | vs friend's Red Piccolo (MPPV benchmark) | vs Black Nail | vs Namekian Nail |
|---|---|---|---|---|
| **1** | **Red, Red Enraged** (`nail_red_enraged`) | **64%** | 75% | 91% |
| 2 | Namekian, Namekian Knowledge (`nail_namekian_knowledge`) | 11% | 55% | - |
| 3 | Black, Black Devious (`nail_black_v2`) | 18% | - | 45% |

### 1. Red, Red Enraged (recommended)
- Red is where the anger is (54 usable cards / 77 anger points, 17 critical-effect cards). Nail needs 15 anger to climb to Level 4 and 5 more for MPPV; Red Enraged turns every critical effect into +1 anger,
  and Nail's Level 3 Power adds 1 more each turn. In the simulator it wins mostly by MPPV on its own 3rd-4th turn.
- Nail's passives still work for it: every Red attack that gets stopped mills the opponent (1 at Level 1, 2 at Level 2), so a defender cannot just sit behind stops. Red has no "cannot be stopped" dependence.
- **Rejuvenation Red cards** (the owner asked for these): Red Hurl (raises anger 1, HIT Rejuvenate 2) x2, Red Duck (stops a physical attack, Endurance 2, Rejuvenate X = current anger) x3,
  Red Blaze (Setup: anger 1, Rejuvenate 2, critical effect) x3, Red Right Blast (draws when anyone Rejuvenates; AT life cards +4 stages) x2. The simulator does not model Red Duck's Rejuvenate X or Red Right Blast's draw,
  so those cards are undervalued there.
- Nail's Dashing Attacking x3 is a critical effect on every hit (+1 anger with Enraged) and returns to the Life Deck.
- Costs: no Dragon Balls in the list, so Level 3's ball option and Level 4's HIT are unused. A Namek-ball hybrid (Dragon Ball 3 and 5) tested at 58% against 64% for this list (within noise, slightly worse); Dragon Balls
  are a luxury for a deck that wants to be fast. Red Restraint / Sacrifice (the friend's discard-triggered cards) were left out because this deck has no discard feeders.
- Weakness (judgement, not tested): anything that stops anger gain slows it down (Wall Breaker, Red Glare, Blue Protective's 6 anger to level).

### 2. Namekian, Namekian Knowledge
- Knowledge: Rejuvenating or shuffling cards into your Life Deck during combat raises anger 1; a Namek Dragon Ball entering play destroys the opponent's top card; your Dragon Balls cannot be captured.
  This is the best fit for Nail's identity (Dragon Ball engine, Namek set, mill from balls plus stops) and it gives MPPV, Survival and Dragon Ball Victory (uncapturable balls) as routes.
- The deck: Rejuvenate engine (Forceful Block, Buffer, Chin Grab, Onslaught, Focused Beams, Hybrid Defense), anger from Namekian Chop (anger = balls), Cover, Shoulder Slam and Devastating Blow (Freestyle),
  Namek balls 1, 3, 5, 7 plus Dragon Radar and Namekian Planned Attack to find them.
- Why it is only second: its anger comes in ones. It needs about 20 anger in roughly three turns and the simulator says it usually gets there too late (11% against the Red MPPV benchmark). It beats the
  slow Black mill deck head to head (55%). Namekian cards are better at staying alive (Endurance, Rejuvenate) than at racing.
- The simulator's Knowledge is an **approximation I added** (`sim/behaviors.py`): Rejuvenate effects in combat give anger 1, a Namek ball entering play mills 1, balls cannot be captured.
  Shuffling into the Life Deck is **not** modelled (so Nail's Dashing Attacking, Energy Guard and Crushing Slam give no anger there). If those count, the real deck is somewhat faster than the 11%.
- Worth trying if the opponent is slow or defensive, or if the owner wants a Dragon Ball Victory plan (that needs Shocking Drill, Dragon Clan, Growth and Disturbance added back; v1 of this list had them and tested worse, 5%).

### 3. Black, Black Devious (the earlier mill build)
- Mill / hand-attack plan: Black Command, Corruption, Swipe and Nail's stops. Strong against slow decks, loses to anything that levels quickly (18% against Red Piccolo, 25% against the Red Nail).
- Alternatives in Black not built: Black Perceptive (destroy top card of own deck to destroy the opponent's; +4 stages when they destroy a combat card) and Black Conflict.

Not built or simulated (judgement only): Orange (Drills are discarded on every level change and Nail has no Drill payoffs), Blue (low anger supply, 11 usable anger cards), Saiyan (Nail is not on the Saiyan heritage list, so no Saiyan Masteries).

## Red Nail: card roles (60 cards, no Dragon Balls)
- **Defaults:** Time Is A Warrior's Tool x1, Confrontation x2.
- **Non-attack anger / critical effects (cannot be stopped):** Red Blaze x3, Red Relaxation x3, Red Burning Rage x2, Red Destiny x2, Red Blazing Aura x2, Red Takeover x2.
- **Defense that raises anger or Rejuvenates:** Red Energy Defensive Stance x3, Red Blocking Hand x3, Red Repel x2, Red Duck x3.
- **Attacks that raise anger or give critical effects:** Nail's Dashing Attacking x3, Red Frenzied Blasts x3, Red Static Shot x3, Red Surrounded Beams x2, Red Hurl x2, Red Right Blast x2,
  Red Driving Knee x3, Red Shoulder Grab x3, Red Double Strike x3, Red Chop x3, Red Right Cross x2, Red Jab x2, Red Mule Kick x1.

## Simulator limits to quote with these numbers (`python -m sim coverage <deck>`)
- Red Nail: 83% of card sentences modelled. Not modelled: Red Chop's X, Red Duck's Rejuvenate X, Red Right Blast's draw, Static Shot's no-Endurance rule, Double Strike's second use, Relaxation's draw, Repel's stage loss.
- Namekian Nail: Knowledge is only approximated (above); Allies and many Namekian ball searches are not modelled.
- Both sides follow one simple priority list; secondary effects are mostly ignored. A matchup the model calls lopsided is not evidence of a play mistake.

## Open questions (unverified)
- Does Nail's Level 3 anger raise happen when no Dragon Ball is returned or placed? (Read as yes.)
- Does Nail's Dashing Attacking "HIT: Shuffle this card into your Life Deck" count as "an effect that shuffles cards into your Life Deck" for Namekian Knowledge? (Likely yes; not modelled.)
- Does Nail's Heritage's "Rejuvenate it as an action" trigger Knowledge? (Not in either deck.)
