# Goku (Awakening levels + Evolution Ally search): three styles compared

Built 2026-11-02 in a cloud session for the owner's request: "Goku deck using the Awakening Goku that can search for allies and also put the Vegeta hero ally into the deck;
pick the style and mastery that works best (assumed Blue Tag Team); give 3 styles with Masteries, best to worst." Sets 1-7 only, default assumptions from `CLAUDE.md`.
All three codes are in `decks/`, were written by `scripts/deckcode.py`, decode and re-encode exactly, and pass `deckcode.py check` with no errors or warnings.
**All three were playtested in the simulator** (Goku's four levels, Blue Tag Team and the Ally rules were added to `sim/` for this). **None has been imported into the app.**

## Reading of the request (please correct if wrong)
- No Set 7 (Awakening) Goku level searches for Allies. Set 7: L1 Training (+1 life card, draw when entering combat), L2 Determined (+1 life card for you, -1 for the opponent, draw the
  bottom card of the discard pile, discard a card for a critical effect), L3 Courageous (+2), L4 Selfless (+2 / opponent -2, fetches a **Styled** card). The Ally search is on the **Set 4
  (Evolution)** levels: L1 Relaxed (end of combat, Ally to the top of the Life Deck), **L3 Calm** (6-life-card energy attack that searches Life Deck or discard pile for an Ally and plays it;
  that Ally can act whatever the MP's power stage is; if the next attack is the Ally's it cannot be stopped), **L4 Dashing** (searches Life Deck, discard pile or Banished Zone for an Ally,
  places it at its highest stage; one Ally acts regardless of MP stage and its attacks deal +4 life cards).
- Levels from different sets can be mixed, so every deck uses **L1 Training (AW-S1), L2 Determined (AW-S2), L3 Calm (EV-S8), L4 Dashing (EV-S9)**: Awakening for the low levels, Evolution for the Ally search.
  The MP name is the plain `Goku` with the printings field (plain names are confirmed for Nappa and Dr. Wheelo). **(unverified)** whether the app wants `Goku (Awakening)`.
- "The Vegeta hero ally" = Set 4 `EV-U93` Vegeta (no alignment; "If your MP is Goku, once per combat you may place this card into play from your hand at 2 power stages above 0 to stop a physical
  or energy attack"; his Power is an energy attack costing 1 stage dealing AT life cards). The other Vegeta Ally (`HV-U72`) is Villains only. All three decks run EV-U93.
- Ally pool used (max 1 each, none named Goku): Vegeta, Chaozu (7-life-card energy attack, shuffles itself back into the Life Deck so it can be fetched again), Tenshinhan, Yamcha, Chichi
  (stops a physical attack; usable at any MP stage for Goku). **Piccolo was dropped after the first version**: his "regardless of MP stage" exception is for Gohan, so for Goku he can only act when Goku is at most 1 stage above 0. Left out: Ox King (damage could then only be modified by Physical/Energy Combat cards, which would
  switch off Goku's Continuous +life cards), Master Roshi (players cannot search Life Decks), Krillin Ally (destroys Drills), Bulma, Oolong, Yajirobe.

## Ranking (best to worst) - after the simulator playtest
The first version of this note ranked Blue first from card counts alone. The playtest (50 games against each of the 22 other roster decks, 1,100 games per deck, alternating who goes first; numbers re-run after merging the Vegeta, Raditz, Lord Slug and Cell Jr. work, which grew the roster to 23 decks) ranks them differently:
| # | Style | Mastery | Playtest | Round robin (roster) | How it plays |
|---|---|---|---|---|---|
| 1 | Saiyan | Saiyan Rampaging (`EV-S5`) | **64%** | 63.8% (rank 6 of 23) | Reaches Level 3 in 66% of games, Level 4 in 20%. Wins almost always by Survival; loses to the two fast Trunks decks. Saiyan Overhead Kick fetches Vegeta. |
| 2 | Red | Red Enraged (`S27`) | **57%** | 59.0% (rank 8) | Fastest levelling: Level 3 in 96% of games, Level 4 in 69%, so Calm and Dashing really fire; wins by MPPV in about half its wins. |
| 3 | Blue | Blue Tag Team (`EV-S10`) | **59%** | 54.7% (rank 10) | Most Ally-centred (5 Allies, Goku's Search x2, Heroic Plan, Overpowering Attack, Battle Readiness x2, Blue Arrest x2, Discharge x2) but reaches Level 3 in only about 15% of games, so Calm/Dashing almost never fire. Its Allies attack about 4.9 times a game, mostly because Goku sits at stage 0 after taking stage damage (that is what switches them on). |
The playtest percentage and the round-robin rank disagree about Red vs Blue (Blue 59% vs Red 57% in the playtest; Red 59.0% vs Blue 54.7% in the round robin), so **treat Red and Blue as tied**; the order above follows the round robin. Saiyan's lead (5-7 points) is outside the noise (about +/-3 points over 1,100 games). Head to head (50 games): Saiyan beat Blue 33-16 and Red 29-10; Blue beat Red 30-23. Controls (same lists with the Allies and Ally searchers swapped for style cards): Red 58% instead of 65%, Saiyan 65% instead of 70%,
so the Ally package helped in the model in both cases (Blue was not controlled cleanly). Blue Protective with the Blue list scored 57% (Tag Team 60% at that point, on the 10-deck roster), so Tag Team is not the weak link.
By Ally theme alone Blue Tag Team is still the right fit (the free Ally and the 32 Blue Ally cards); if the goal is the best result in the simulator, play Saiyan, and Red if Calm/Dashing firing matters to you.
Not chosen: Black (Black Conflict would turn Goku's +life-card attacks into critical damage, but Black has almost no Ally support: Black Dash only fetches an Ally from the opponent's deck), Orange (rewards Drills, and its Ally cards remove Allies rather than support them), Namekian (Goku is not on the Namekian list).

## Deck changes the playtest caused
- Piccolo out of all three (see above). Blue: Concentrated Blast x3 instead; Taming Technique, Blue Kiss, Blue Waiting Drill and Energy Focus x2 out for Hand Blast, Stretch Kick, Slash, Back Break x2, Eye Lasers (62.6% vs 59.8%: noise-level, kept because it also removes cards the sim only half models).
- Red: Red Hurl for Piccolo (65.2% vs 63.0%). Saiyan: Saiyan Cheap Shot for Piccolo (69.6% vs 64.0%).

## What the simulator does not cover (from `coverage`)
- Coverage: Blue 93% of card sentences modelled, Red 89%, Saiyan 87% ("hand-coded" means custom code, not every sentence). Unmodelled examples: Blue Guard's banish-instead-of-discard, Blue Overcharge, Blue Slash's mill, Red Double Strike and Shattering Leap second uses,
  Saiyan Triangle Beams' two critical effects, Saiyan Rampaging's Power, Saiyan Analysis Drill, Saiyan Hand Swipe.
- Added to the simulator for this: Allies (see `sim/README.md`, "Allies"), Goku Training / Determined / Calm / Dashing, Blue Tag Team, Ally search cards, Blue Lifting / Waiting / Transportation Drills, Blue Discharge, Blue Defensive Stance, Blue Arm Blast / Round Throw as stops, Saiyan Overhead Kick.
  Goku's other levels (Relaxed, Motivated, Courageous, Selfless, Set 1) are not modelled, so an all-Set-7 or Selfless-at-Level-4 version could not be tested.

## What is not verified
- **(unverified)** Do Goku's Continuous "your attacks deal +X life cards" apply to attacks an Ally performs? The simulator assumes yes.
- **(unverified)** Timing of Chaozu shuffling himself back into the Life Deck (modelled as right after his attack); which Allies count as "Saiyan Ally" for Overhead Kick (modelled: Vegeta only); the AI's target choice for Yamcha's HIT.
- **(unverified)** Whether the app's code for this MP must carry `(Awakening)`.
- Not modelled: damage redirected to Allies, so Allies are never used as shields; Ally Continuous powers other than the ones coded.
- The simulator is a toy model with one simple AI for both sides: these are comparisons between lists, not predictions of real games.

## Update: Tenshinhan code fixed (the app rejected `EV-S60`)
The owner's app answered "Unknown card EV-S60" (Tenshinhan, Set 4 starter). It is a reprint of Set 1 `C9`, and the app only knows a card by its first printing, so all three decks now use `C9`
(same card for the simulator and the rules: "Heroes only" is fine for Goku). `deckcode.py check` did not catch it because it groups Allies by printed text and `C9` and `EV-S60` differ only by the
"(Heroes only.)" line. Vegeta `EV-U93` is a different card from the Villains-only `HV-U72` and loaded fine. Re-run after the roster grew to 25 decks (round robin, after the final rebuild): Saiyan Rampaging 59.0%, Red Enraged 58.9%,
Blue Tag Team 52.2%, so Red and Saiyan are a tie within the noise; Blue stays third.
