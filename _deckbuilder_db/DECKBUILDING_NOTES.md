# Deck-building notes

Lessons from deck-building sessions with the owner. They sit on top of `cards.json`, `mps.json` and
`masteries.json`. Anything marked **(unverified)** is my inference and has not been confirmed by the owner or the app.

## Working assumptions (unless the owner says otherwise)
- Card pool: Sets 1-7 only (PanZ). No PZP / OP promos, no `_RST` Restored copies, no FanZ sets.
- Rulings: PanZ-era text (Panini CRD only). The Frozen list is ignored.
- No Traits. Saiyan / Namekian Masteries use the Rulebook 3.0 heritage lists (`mps.json` -> `panz_heritage`).
- 60-card Life Deck plus 1 Mastery. Max 3 copies of a card name. A card's printed `limit_per_deck` is lower and wins
  (e.g. Orange Uppercut is Limit 1). Max 1 copy of each Ally and each Dragon Ball. One Dragon Ball set per deck.
- **Card text is literal.** "A Dragon Ball in play" means anyone's. "Your effects destroy" does not include banishing.
  Card effects resolve before damage or blocks are calculated.

## Legality checklist (run before giving any deck)
1. 60 cards, copy limits, printed limits.
2. **Named cards must match the MP name** ("Goku's Search" cannot go in a Nail deck). Use `is_named` /
   `named_character`. Cards that are only "considered Named for your effects" (Pesky Barrage, Black Back Strike) are fine in any
   deck. "Time Is A Warrior's Tool" and "It's Over 9,000!" are not Named (`NOT_NAMES` in `derive.py`).
3. "(Heroes only)" / "(Villains only)" must match the MP's alignment. Hero decks use Confrontation, Villain decks use Stare Down.
4. No Ally with the MP's name (and, for fused MPs, none of the characters it fuses).
5. The MP must have all four levels. A deck may mix printings from different sets.

## Defaults the owner wants in (nearly) every deck
- **Time Is A Warrior's Tool** x1 (Limit 1, Freestyle, no alignment restriction, `R152`).
- **At least 2** of Confrontation (`R150`, Heroes only) or Stare Down (`R151`, Villains only).

## How to compare styles for an MP
1. What does each level reward, and what does the MP **punish** the opponent for (Nail: stopping or Enduring his attacks)?
2. Is there a level worth sitting on all game instead of climbing to Level 4? Examples: Blue Turles on Level 1 (Styled AT +5 attacks,
   stage-lock); Blue Piccolo on Level 2 (Combat Stance, using Blue Dominance to get there). Check how the deck gets there and stays there.
3. Which win condition does the deck reach from that level? MPPV needs Level 4, Survival (empty Life Deck), Dragon Ball Victory
   (all seven of one set). Lord Slug cannot win by MPPV.
4. Compare the best individual cards in each style, not just counts. Count what stacks with the MP's passives.
5. List cards that cancel the MP's passives and leave them out ("cannot be stopped", "Endurance cannot be used",
   Remembrance Drill for a destroy-based mill MP).
6. Check Mastery effects on the opponent as well as on you (Blue Protective makes opponents need 6 anger).
7. Mention costs: your own anger raisers force a level-up at 5 anger, Drills are discarded when you change level (unless a card says
   otherwise), the number of turns before the engine is online.
8. Give 2-3 options ranked most to least recommended, each with style, Mastery and reasons.

## Mechanics confirmed by the owner
- A critical damage effect can only discard an **opponent's** Ally. A card effect saying "destroy an Ally" may target your own.
- A card effect printed before the DAMAGE line (e.g. "Use a critical damage effect") happens immediately, before the block or the damage.
- Dragon Ball Victory is possible with your own Dragon Balls of one set.
- You draw 3 at the start of your turn and the defender draws 3 when combat is declared. Hand size is 1 or 0 after the Discard Step.

## MP-specific notes
- **Lord Slug**: Red Enraged works (guaranteed critical effects raise anger, so Levels 3-4 arrive fast). Named: Lord Slug's Fist Slam,
  Lord Slug's Regeneration (Limit 2). Win with Dragon Ball Victory.
- **Turles**: Blue stage-lock on Level 1 (AT +5 and +2 from Turles, damage cannot be prevented) is a top option. Saiyan, Red and Black are the levelling options.
- **Nail** (only one legal printing set, Set 2): Protector punishes stops. Nail's Dashing Attack (an Energy Combat card by owner ruling, physical attack in
  text) always gives a critical effect. Combat Ready's HIT can use any player's Dragon Ball. Black mill and Namekian ball plans are the top two.
- **Dr. Wheelo**: destroy effects get +1 at Level 3 and +2 and Rejuvenate 2 at Level 4. Banish effects do not count. Black Perceptive Mastery
  (Set 4 only) is likely a better fit than Devious. Revival triggers when discarded or destroyed from your Life Deck.
- **Trunks**: owner's Orange Drill deck uses Orange Retribution Mastery (changing levels shuffles Drills back, its Power refetches Drills). Frenzied (Level 2)
  gives a critical effect per Named card.

- **Piccolo (friend's Red deck, all Premiere levels: Stoic, Combat Stance, Unleashed, Fused)**: about 1 anger point per card. Combat Stance gives a critical effect every turn, Unleashed
  (+2 life cards, ball search on critical damage) turns 4-life-card attacks into critical hits, and Piccolo's Weighted Clothing (banish from discard: raise anger 2) is an
  uncounterable MPPV finisher. Composed (L1) and Stoic (L1) cannot both be used, and Composed needs real Rejuvenate/stage-gain support.
- **Garlic Jr.** (Villain, only Set 3 printings are legal): L1 needs 2 less anger to advance and its Power raises anger 1. L3 can capture a Dragon Ball whenever you raise your anger.
  L4 gives the opponent's attacks +3 life cards, so reach it and win the same turn. Counter Blast doubles Continuous modifiers, so do not play it at L4.

- **Krillin** (Hero, legal Set 1-7 levels: Ready, Energetic or Quick, Ready For Battle, Enraged): an energy-attack MP that rewards shrinking the opponent's hand. L3 deals 9 minus the cards in their hand.
  L1 gives a critical effect and 2 anger the next time any card is discarded from a hand this combat. Named: Krillin's Solar Flare, Krillin's Destructo Disk (cannot be stopped or prevented).
  Black has 14 hand-disruption cards; Black Devious Mastery makes the opponent discard each turn and turns 4-life-card attacks into critical hits.

## Deck code format (from the owner's web app)
`D1.<name>.<MP name>.<Mastery>[.<MP printings>].<card>.<card>...`
- Names are URL-encoded (`%20`). Cards are `<set prefix>-<card number>`, `*N` for N copies, sorted as plain text.
- Set prefixes: none = Set 1, `HV` 2, `MC` 3, `EV` 4, `PF` 5, `VG` 6, `AW` 7.
- Optional MP printings field: `_<L1>_<L2>_<L3>_<L4>`, one printing per level.
- **(unverified)** Set 7 deck-reveal cards appear as `S<n>` where `cards.json` numbers them `DR<n>` (e.g. `AW-S10` = `DR10`).
- A name containing a period (Dr. Wheelo) written as `Dr%2E%20Wheelo` imported correctly: all 60 cards, MP Dr. Wheelo and Black Devious Mastery (owner-confirmed).
