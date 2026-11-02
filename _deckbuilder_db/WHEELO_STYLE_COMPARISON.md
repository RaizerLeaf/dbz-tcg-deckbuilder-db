# Dr. Wheelo: style comparison and the Red Ascension deck (2026-11-02)

Owner request: build a new Wheelo deck, pick the best style from the card pool and the Masteries available, 60 cards, simulated as the notes require.
Everything here is from the toy simulator (`sim/README.md`): a rough model, not a prediction. Builder: `scripts/build_wheelo_decks.py`.

## What Wheelo has to work with
- **Only one legal level stack** (Set 3: Big Brain MC-U61, Scheming MC-U62, Confined MC-U63, Robotic MC-U64; the promo copies are FanZ-era).
  L1 Power: destroy your top card to destroy the opponent's top 2 and **set your anger to 3**. L2: +2 life cards on every attack, each stop makes the opponent destroy 1.
  L3 (PUR 4): +1 to every "destroy the top cards of the opponent's Life Deck"; Instant Power after a successful attack: destroy 2, Rejuvenate 2. L4 (PUR 5): +2 to those destroys and Rejuvenate 2 per destroy effect.
- Not Saiyan or Namekian (`panz_heritage` both false), so those Masteries are out. Heroes-only cards are out. Named cards for him: Dr. Wheelo's History and Dr. Wheelo's Revival.
- Legal Masteries with a Set 1-7 printing: Black Conflict / Devious / Perceptive, Blue Protective / Resolute / Tag Team, Orange Adaptive / Adept / Retribution, Red Ascension / Enraged / Ruthless.
- Wheelo has MPPV available (anger 5 on Level 4). Earlier notes said a faster MPPV build was "not recommended"; the simulator says the opposite (below).
  The reason is L1: its Power sets anger to 3 every turn, so the first level costs only 2 more anger, and L2's +2 life cards turns every 3-life-card Red attack into critical damage.

## Styles compared (same simulator, 50 games against each of the 25 roster decks = 1,250 games unless noted; +-3 points)
| Style / Mastery | Deck | Win rate | How it plays |
|---|---|---|---|
| **Red, Red Ascension** | `decks/wheelo_red_ascension.txt` | **74%** (first draft 67%) | anger 0.98 points/card; reaches Level 3 by about turn 2 and Level 4 by turn 3-4; wins by MPPV about turn 5 |
| Red, Red Enraged (same 60 cards as the first Ascension draft) | `decks/wheelo_red_enraged.txt` | 47% | Enraged only pays when a critical effect is used, Ascension pays +1 anger at the end of every combat |
| Black, Black Perceptive | `decks/wheelo_black_perceptive.txt` | 45% | mill/Survival deck; Perceptive's Power (destroy 1 of each Life Deck) is excellent with L3/L4 but games end before it matters |
| Blue, Blue Protective (existing `decks/wheelo_blue_lockdown.txt`) | | 46% (20 games each) | anti-anger lock (opponents need 6 anger to level); the Red deck only splits with it (Red wins 25/50) |
| Black, Black Devious (existing `sim/decks/wheelo_black_v2.txt`) | | 21% (roster) | slow mill, loses to every MPPV deck |
| Black, Black Conflict (Perceptive's card list) | `decks/wheelo_black_conflict.txt` | 12% | **suspect**: the simulator's Conflict Power discards a card every turn with no plan, so the model undersells it |
| Orange (Adaptive / Adept / Retribution), Blue Resolute / Tag Team, Red Ruthless | not built | - | not simulated: Orange has only 25 anger cards, Resolute / Adept / Ruthless are not modelled |

Ranked options: 1. Red Ascension (built). 2. Blue Protective (existing, the answer to fast anger decks). 3. Black Perceptive (the "real" mill deck, kept on file).

## The deck
`decks/wheelo_red_ascension.txt`: Dr. Wheelo (all four Set 3 levels), Red Ascension Mastery, 60 cards, `deckcode.py check`: no errors, no warnings, round-trips.
- 6 Wheelo cards: Dr. Wheelo's Revival x3 (Setup; when it is destroyed from your own deck it destroys 3 opposing cards, more at L3/L4), Dr. Wheelo's History x3.
- Defaults: Time Is A Warrior's Tool x1, Stare Down x2 (Villain), Villainous Visage x1.
- Red engine: Static Shot x3, Hurl x3, Chop x3, Driving Knee x3, Blocking Hand x3 (anger 2 when it stops), Frenzied Blasts, Surrounded Beams, Combined Blast, Energy Outburst, Sacrifice, Departing Shot, Counter Kick, Furious Lunge, Jab, Knee Lift, Duck, Repel, Energy Defensive Stance, Vault, Blaze x2, Relaxation, Burning Rage, Destiny, Takeover, Scanning Drill x2, one Wall Breaker.
- No Dragon Balls, no Allies.

## What the tuning showed
- Ablation (remove one card at a time, 59 cards): the cards whose removal hurt most were Red Chop, Driving Knee, Counter Kick, Sacrifice, Repel, Hurl, Vault; removing Energy Sphere, Visiting the Past, Red Escape, Burning Rage or Visage did not hurt.
  Swapping Sphere / Visiting the Past / Escape for a third Chop, Driving Knee and one Wall Breaker moved 67% -> 74%. Dragon Balls (Namek 1/3/5/6/7) gave 65-68%, so they were left out. Red Despair Drill made no difference.
- The Wheelo mill cards (History, Revival) are neutral to slightly negative in this model because the deck wins by MPPV, not by Survival; they stay because they are his identity and Revival is a free 3-card destroy when it is hit from the deck.
  Cutting them for Red cards is worth +1-2 points if the owner wants a purer Red deck.
- Weak matchups (wins out of 50): Orange Trunks 18, Red Trunks 18, Vegeta Pinnacle Red 19, Goku Red Enraged 19, Wheelo Blue Lockdown 25, Goku Saiyan 26. Against Orange Trunks it mostly dies to Survival (31 of 32 losses): it takes a lot of life-card damage while chasing anger.
  It is a race deck: when the opponent reaches Level 4 first it loses.

## Not modelled / unverified (from `python -m sim coverage decks/wheelo_red_ascension.txt`: 87% of card sentences modelled)
- Red Combined Blast's "lower anger 3 to stop Events", Departing Shot's destroy on a Drill leaving, Furious Lunge's "cannot be stopped by a non-Styled card", Jab's pay-3 unpreventable, Knee Lift's anger-lowering HIT, Relaxation's draw, Scanning Drill's discard / anger-lowered triggers, Surrounded Beams' unstoppable-on-advance. All text-only.
- Wheelo's Revival and the L1 Power are modelled; "raise a player's anger" choices follow the simulator's own-anger assumption.
- **(unverified)** that Wheelo's L1 Power (set your anger to 3) can be used every turn at Level 1 alongside Ascension's Power; the simulator allows it. If the owner rules otherwise, the deck is slower.
- **(unverified)** the roster win rate is the model's opinion under identical simple AI, no calibration against real games.
