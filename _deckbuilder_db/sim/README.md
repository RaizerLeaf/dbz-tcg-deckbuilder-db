# Deck simulator (toy model)

A reusable simulator for matching two decks from this repository. It replaces the throw-away scripts that were rewritten for every
matchup. **It is a coarse model, not the official rules engine.** Read "What the numbers mean" before quoting a result.

## Scope: PanZ era only (Sets 1-7)
The simulator only supports PanZ-era cards (Sets 1-7, Panini rulings, Frozen list ignored). Decks that contain FanZ cards (Sets 8+, PZP/OP promos) are rejected by
`loader.py` with an error. **TODO (later): add FanZ simulation** - FanZ rulings and CRD errata, FanZ keywords (Foresee, Remain, Focused, Warning and similar), the Trait
system, the FanZ legality rules and the Frozen list, and behaviors for FanZ MPs and Masteries. Nothing in the engine assumes FanZ rules yet.

## Quick start (run from `_deckbuilder_db/`)
```
python -m sim run  sim/decks/wheelo_black_v2.txt sim/decks/piccolo_red_friend.txt -n 1000   # win rates, alternating who goes first
python -m sim bo3  sim/decks/trunks_red_draft.txt sim/decks/trunks_orange_v4.txt --no-mppv-b   # best of 3 with the play log
python -m sim game A B --seed 7 --first b                                                     # one game with the play log
python -m sim coverage sim/decks/nail_black_v2.txt                                            # what the model does NOT cover for this deck
python -m unittest discover -s sim/tests -t .                                                 # rule tests
```
A and B are deck codes (in quotes) or paths to `.txt` files holding one code. Deck codes are decoded with `scripts/deckcode.py`
(on `main`; the simulator needs it).
`--no-mppv-a/-b` removes MPPV as a win condition for that side (the owner sometimes assumes this for Orange decks).
Always run `coverage` for both decks and quote its warnings next to the result.

## Layout
- `cardmodel.py` - reads `cards.json`, parses damage, cost, anger, stops, Endurance, Rejuvenate, stage gain, critical effects out of the card text, and
  produces the coverage report (sentences parsed / hand-coded / unmodelled).
- `engine.py` - the rules: turn order, Attack Table, stage damage overflowing into Life Cards, Endurance, critical damage, anger and levelling,
  Dragon Balls and Dragon Ball Victory, Rejuvenate, destroy vs banish, discard to one card, defender draws 3, win conditions.
  Rule sources are in `work/crd/rulebook.txt`; the rule tests in `tests/test_rules.py` pin them down.
- `behaviors.py` - everything card-specific, plus the simple AI (`choose_action`). MP levels and Masteries are `Behavior` subclasses registered with
  `@mp(name, subtitle)` / `@mastery(name)`. Drills and Dragon Balls that stay in play use `@passive(card name)`. One-off card effects go in `CARD_EXTRA`.
- `loader.py` - deck code -> `Spec` (60 card ids, MP level printings, Mastery). With no printings field it picks the earliest Sets 1-7 printing of each level.
- `decks/` - sample decks used for regression runs.

## What is modelled
- MP levels: Trunks (Dashing, Protective, Frenzied, Swordmaster, Defiant, Energy Charged, Bold, Overpowering, Overwhelming), Piccolo (Stoic, Composed, Combat Stance,
  Unleashed, Fused), Dr. Wheelo (all four), Garlic Jr. (all four), Lord Slug (all four), Krillin (all four), Nail (all four).
- Masteries: Red Enraged, Red Ascension, Black Devious, Black Conflict, Blue Protective (opponent needs 6 anger to level; its Defense Power is simplified), Saiyan Rampaging (its Power is not modelled), Saiyan Dynamic, Orange Retribution, Namekian Knowledge (approximation: in-combat Rejuvenate gives anger, a Namek ball entering play mills 1, balls cannot be captured; shuffling into the Life Deck is not modelled). New and only regression-checked, not rule-tested.
- Drills / balls: Orange Hoping, Intimidating, Hiding, Aura, Captivity, Devouring, Burning Aura, Steady; Aggressive Sword Drill; Namek Dragon Balls 1, 3, 5, 6, 7; Earth 1-5.
- About 60 cards with extra effects (see `CARD_EXTRA`), notably Wheelo's destroy package, Red anger/critical Setups and Events, Weighted Clothing, Sacrifice, Restraint.
- Any MP level or Mastery without a behavior is **ignored** (its text does nothing). `coverage` lists these as NOT MODELLED.

## What is NOT modelled (important)
- Allies (never played), "stays in play for a second use" attacks, attached cards, Focused / skip-action subtleties, most Drill powers, most Dragon Ball effects beyond those above,
  Energy attacks costing less, Saiyan/Namekian-specific text, and every sentence `coverage` prints as unmodelled.
- "Hand-coded" in `coverage` means the card has custom code, not that every sentence of it is handled.
- AI: both sides follow one fixed priority list (powers, then Events/Setups with an effect, then the highest-value attack); they defend whenever a legal defense exists and
  the attack is big enough, and declare combat whenever they have something to do. No bluffing, no holding cards, no reading the opponent's hand.
- Rules assumed but unverified: Powers are once per turn for each player's own turn and separately on the opponent's turn; "Styled" means the card's style equals the
  player's Mastery style; advancing by effect sets the MP to 10 stages (the rulebook states this only for advancing by anger).
- Searches take the first matching card and then shuffle.

## What the numbers mean
- A win rate is the model's opinion for these two lists under identical simple play. Use it to see which side is faster and why (read a few `game` logs), not as a prediction.
- Games are short (about 3 turns per player). Decks that need 4+ turns to start their engine lose most games against MPPV decks, in the model and (per the owner) in practice.
- Regression numbers when this was written: Wheelo V2 vs the friend's Red Piccolo: Wheelo 16% (1,500 games). Red Trunks draft vs Orange Trunks V4 with Orange MPPV off: Red 61%.
  They match the earlier one-off scripts, so a change that moves these needs an explanation.

## Adding things
1. Run `python -m sim coverage <deck>`; fix the NOT MODELLED lines that matter for the matchup first.
2. New MP level: add a `@mp('Name', 'Level subtitle')` class in `behaviors.py` with the hooks it needs (`power`, `stage_bonus`, `entering_combat`, ...).
   Mastery: `@mastery('Full Mastery Name')`. Card: an entry in `CARD_EXTRA` (`immediate`, `hit`, `use`, `defend`, `on_damaged`) or `@passive`.
3. Add a rule test in `tests/test_rules.py` if you add or change an engine rule. Never change engine rules without checking `work/crd/rulebook.txt`.
4. Re-run the regression decks and compare with the numbers above.

## Roadmap
FanZ-era support (explicitly deferred, see Scope); Allies; second-use attacks; Red Ascension, Blue Protective, Black Perceptive and Conflict, Saiyan Masteries; Drill powers; a smarter AI (holding cards, defending only when it
matters, using Setups before combat); an optional real-game log import to calibrate the model against the owner's results.
