# Goku (Awakening levels + Evolution Ally search): three styles compared

Built 2026-11-02 in a cloud session for the owner's request: "Goku deck using the Awakening Goku that can search for allies and also put the Vegeta hero ally into the deck;
pick the style and mastery that works best (assumed Blue Tag Team); give 3 styles with Masteries, best to worst." Sets 1-7 only, default assumptions from `CLAUDE.md`.
All three codes are in `decks/`, were written by `scripts/deckcode.py`, decode and re-encode exactly, and pass `deckcode.py check` with no errors or warnings.
**None has been imported into the app, and none was simulated** (see "What is not verified").

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
  (stops a physical attack; usable at any MP stage for Goku), Piccolo (stops an energy attack). Left out: Ox King (damage could then only be modified by Physical/Energy Combat cards, which would
  switch off Goku's Continuous +life cards), Master Roshi (players cannot search Life Decks), Krillin Ally (destroys Drills), Bulma, Oolong, Yajirobe.

## Ranking (best to worst)
| # | Style | Mastery | Why |
|---|---|---|---|
| 1 | Blue | Blue Tag Team (`EV-S10`) | Only style built around Allies: 32 Blue cards mention Allies (Battle Readiness, Taming Technique, Arrest, Discharge, Kiss, Waiting Drill, Transportation Drill...). Tag Team puts an Ally into play for free at the start of the opponent's first turn (target: Vegeta), protects a lone Ally from critical discards and Rejuvenates a banished Ally at the end of combat. Weakness: Blue has the fewest anger cards (about 10 in this build), so it reaches Calm/Dashing slowly; the Ally engine therefore has to work from Level 1-2 on card searches. |
| 2 | Red | Red Enraged (`S27`) | Fast anger: about 39 anger-raising cards in 60, a deck core copied from the friend's Red Piccolo (non-Piccolo cards only; Dragon Balls and Piccolo cards removed). Goku L2 Determined turns any discard into a critical effect, which Red Enraged converts into +1 anger every turn, so Calm (L3) and Dashing (L4) arrive early and Goku himself does the Ally fetching; MPPV is also available. Weakness: only 6 Allies and 4 search cards, and Red has no Ally support (several Red cards banish or destroy Allies; those were left out). |
| 3 | Saiyan | Saiyan Rampaging (`EV-S5`) | Goku is on the Saiyan heritage list; Rampaging needs 1 less anger to advance (minimum 4) and Styled attacks may raise anger 1. Saiyan Overhead Kick x2 fetches a Saiyan Ally (Vegeta is on the Rulebook 3.0 Saiyan list) and the style has 18 anger cards in this build. Weakest because it has neither Blue's Ally package nor Red's speed, and Rampaging's Power is not modelled anywhere. |
Not chosen: Black (Black Conflict would turn Goku's +life-card attacks into critical damage, but Black has almost no Ally support: Black Dash only fetches an Ally from the opponent's deck), Orange (rewards Drills, and its Ally cards remove Allies rather than support them), Namekian (Goku is not on the Namekian list).
Blue Resolute (`AW-S5`, +1 life card; discard a Styled card to draw and prevent 4 stages and 4 life cards) is the one Blue alternative if the free Ally is not wanted.

## What is not verified
- The simulator (`sim/`) does not model Goku's levels or Allies (`python -m sim coverage` says so), so **there is no win-rate evidence**; the ranking is reasoning from card text and counts.
- **(unverified)** Do Goku's Continuous "your attacks deal +X life cards" apply to attacks an Ally performs? The decks work either way, but Dashing's +4 on top of them is the plan's peak.
- **(unverified)** How the Attack Table `AT` is read for an Ally's attack (Vegeta's damage is "AT life cards").
- **(unverified)** Whether the app's code for this MP must carry `(Awakening)`.
- Allies can act only when the MP is at most 1 stage above 0 (Rulebook 3.0), except via Calm, Dashing, Blue Kiss, Tag Team's placement, or a card that says so. In Blue/Tag Team the early Allies mostly serve as stops (Vegeta from hand, Chichi, Piccolo) until Calm/Dashing.
- Card counts of "anger cards" come from a text search ("raise your anger", "raise a player", "raise or lower") and are approximate.
