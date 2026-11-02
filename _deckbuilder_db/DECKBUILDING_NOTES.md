# Deck-building notes

Lessons from deck-building sessions with the owner. They sit on top of `cards.json`, `mps.json` and
`masteries.json`. Anything marked **(unverified)** is my inference and has not been confirmed by the owner or the app.

## Start here: workflow for a new deck
1. Read `CLAUDE.md` (hard rules and defaults), this file, and `STRATEGY_KNOWLEDGE.md` (verified rules, mistakes to avoid). Settled owner rulings are not re-asked.
2. Pin down the request: the MP (name + alignment), any Mastery or style the owner wants, and the matchup it must beat. Assume the working assumptions below unless told otherwise.
3. Look the MP up in `mps.json` (`mp_key` is `name|alignment`): the legal Set 1-7 printings per level, `panz_heritage` (Saiyan/Namekian Masteries), `cannot_include_allies_named`.
   A level with one printing has no choice. Use `work/crd/panz.txt` / `rulebook.txt` / `crd_general.md` for rules; never guess card text.
4. Build the legal pool from `cards.json` with Python (do not read it whole): `set_number` 1-7, no `_RST` ids, not the other alignment (`restrictions`), no other character's Named cards,
   text from `text_current` (via `deckcode.text`). There is one record per printing, so group by `card_name`. Search the text for what the MP rewards, e.g.
   `cd _deckbuilder_db/scripts && python3 -c "import deckcode as dc, re; [print(dc.card_code(c), c['card_name'], '|', dc.text(c)) for c in dc.CARDS if c['set_number'] and c['set_number']<=7 and '_RST' not in c['card_id'] and re.search(r'destroy.*Life Deck', dc.text(c))]"`.
5. Compare styles with "How to compare styles" below and give 2-3 ranked options, unless the owner asked for one style.
6. Build to the defaults (60 cards, limits, Time Is A Warrior's Tool x1, Confrontation/Stare Down x2).
7. Encode with `scripts/deckcode.py` (`encode`), write the code to `decks/<name>.txt`, then `python deckcode.py check "$(cat ../decks/<name>.txt)"`. Never retype a code by hand.
8. **Playtest it in the simulator before finalizing (required).** Reading card text is not enough: the simulator shows whether the plan actually runs (does the engine come online, do the key
   cards fire, how many turns to Level 3/4, does the deck run out of cards first). See "Playtesting a deck in the simulator" below. Adjust the list from what it shows, then re-check legality (step 7).
9. Present the deck by role, the code in a fenced block, and every unverified assumption; ask the owner to import it. Record new owner rulings and lessons here, then commit and push to `main`.

## Playtesting a deck in the simulator (required before finalizing)
Run everything from `_deckbuilder_db/`. The simulator is a toy model (`sim/README.md`), but it is the only thing that executes the cards, so every deck gets played before it is presented.
1. **Coverage first:** `python -m sim coverage decks/<name>.txt` (or `sim/decks/`). It lists the MP levels and the Mastery that are **NOT MODELLED** and the card sentences it ignores.
2. **"The simulator does not have this character" is not a reason to skip.** Add the missing MP levels, the Mastery and the cards your plan depends on to `sim/behaviors.py` from the card text
   (recipe: `sim/README.md`, "Adding things"; usually one small class per MP level), run `python -m unittest discover -s sim/tests -t .`, and commit the new behaviors so the next deck
   starts with them. Model what the deck's plan relies on; ignoring cosmetic text is fine. If a rule is unclear, write the behavior the literal text implies, mark it **(unverified)** in the
   code and in your answer, and do not invent card text. Only skip a piece with the owner's OK; otherwise say exactly which parts are unmodelled and that those parts are text-only.
3. **Play it, a little:** `python -m sim game <your deck> <opponent> --seed N` and read 2-3 play logs against a benchmark opponent (for example `sim/decks/piccolo_red_friend.txt` as a fast MPPV deck
   and one slower deck or the matchup the owner named). Look for: which levels it reaches and when, whether the key cards and combos fire, cards that sit in hand unused, how it loses.
   A `python -m sim run` of **20-50 games** is fine as a sanity check. **Do not run hundreds or thousands of games for deck building**: large `run` batches are for matchup testing when the owner asks.
4. **Use what you see:** cut cards that never matter, add support for the step that stalled, re-encode and re-check. Then, when you present the deck, say what you simulated, which parts were
   unmodelled (from `coverage`), what the logs showed, and that the simulator is a rough model, not a prediction.

## Working assumptions (unless the owner says otherwise)
- Card pool: Sets 1-7 only (PanZ). No PZP / OP promos, no `_RST` Restored copies, no FanZ sets.
- Rulings: PanZ-era text (Panini CRD only). The Frozen list is ignored.
- **Errata applies, and the latest print wins** (owner-confirmed): play every card with its current text (`text_current` when present, e.g. Namekian Knowledge Mastery, Blue Guard,
  Namek Dragon Ball 7, Black Command), not the printed text. The most recent printing is often a later set or a promo (Evolution P1, P3, P7), and a card image that prints
  "(Most Recent Printing)" shows the current wording even where the CRD is silent. PanZ-era wording is used: Blue Guard is "would be discarded ... by a card effect", not the FanZ wording.
  Only Sets 1-7 are used; the repo also holds FanZ (Set 8+), OP and PZP cards, which are out of scope unless the owner says otherwise.
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
9. **Choose the level printings deliberately.** Levels may come from different sets and can change a deck completely (Trunks has four sets of levels). Ask which levels the deck will really
   spend time on: games last about 3 turns per player, so a Level 3/4 payoff only counts if the deck reaches it. Drills vanish when you advance (only a few levels keep them), so levels
   3-4 must work without them.
10. **MPPV decks: count anger.** Anger points per card, cards that raise anger or give a critical effect without attacking (they cannot be stopped), anger gained when defending, and cards
   that trigger when discarded by an effect. Red has by far the most (numbers in `STRATEGY_KNOWLEDGE.md`, section 5). **Skip-the-levels decks** (no MPPV) need a reliable level-skip
   (Orange Devouring Drill) instead of anger. Do not rely on "name a card" gambles (Trunks' Sword Stance is only about 19-28% even with a top-of-deck setup).

## Mechanics confirmed by the owner
- A critical damage effect can only discard an **opponent's** Ally. A card effect saying "destroy an Ally" may target your own.
- A card effect printed before the DAMAGE line (e.g. "Use a critical damage effect") happens immediately, before the block or the damage.
- Dragon Ball Victory is possible with your own Dragon Balls of one set.
- You draw 3 at the start of your turn and the defender draws 3 when combat is declared. Hand size is 1 or 0 after the Discard Step.
- Evolution promos P9 (Blue Guard) and P10 (Namekian Mouth Beam) never came out. The CRD's MRP pointers to them are stale; Blue Guard's real MRP is Awakening S50, and Namekian Mouth Beam has no Set 1-7 MRP image (the Set 3 C28 card prints "Styled block"; the Panini CRD C28 ruling, which is PanZ-era, says to treat it as "Styled card with a shield icon", so that is its `text_current`; owner showed the card 2026-11-02).
- Blue Protective Mastery ("needs 6 anger to advance a personality level") only affects levelling. MPPV is still 5 anger on Level 4.
- "Your opponent destroys the top X cards of his Life Deck" from your card counts as "one of your effects destroys cards from the top of your
  opponent's Life Deck" (Wheelo L3/L4, Cell Jr. AW-U76, Blue Challenging Strike). Read literally; some early-set wording is odd, check those case by case.
- "Deals critical damage" is not the same as "uses a critical damage effect". Wall Breaker (and similar "banish when ... deals critical damage") only
  leaves when the opponent actually deals critical damage, not when a card just lets them use a critical damage effect.

## MP-specific notes
- **Lord Slug**: Red Enraged works (guaranteed critical effects raise anger, so Levels 3-4 arrive fast). Named: Lord Slug's Fist Slam,
  Lord Slug's Regeneration (Limit 2). Win with Dragon Ball Victory.
  Lord Slug **cannot win by MPPV**, so Dragon Ball Victory (or Survival) is his only route, and an opponent's critical effects can capture his balls. Use the **Namek** set with
  Namek Dragon Ball 1 ("your other Dragon Balls cannot be captured", +1 life card on your attacks), not Earth (Earth Dragon Ball 1 has no protection). A Red critical-effect shell fits
  Piccolo better than Slug (Combat Stance and Unleashed feed critical effects and balls; Piccolo can also MPPV).
- **Turles**: Blue stage-lock on Level 1 (AT +5 and +2 from Turles, damage cannot be prevented) is a top option. Saiyan, Red and Black are the levelling options.
  The Blue plan: stay on Level 1, play only Styled cards, use AT +5 Setups/physicals (Blue Stretch Kick, Round Throw, Lunge, Face Crunch; AT 0 still hits for 7 stages with Turles' +2),
  Blue Biting Drill (+2 stages), Blue Hush, and Blue Protective Mastery (opponents need 6 anger so they level slowly). Caveats: Blue Stretch Kick and Back Break raise **your own** anger (at 5 you advance
  whether you want to or not), "cannot be prevented" does not beat Stops, and stage damage drains the MP first (the lock works because the opponent cannot pay for energy attacks or use Allies at 0).
- **Nail** (only one legal printing set, Set 2): Protector punishes stops. Nail's Dashing Attack (an Energy Combat card by owner ruling, physical attack in
  text) always gives a critical effect. Combat Ready's HIT can use any player's Dragon Ball. Black mill and Namekian ball plans are the top two.
- **Dr. Wheelo**: destroy effects get +1 at Level 3 and +2 and Rejuvenate 2 at Level 4. Banish effects do not count. Black Perceptive Mastery
  (Set 4 only) is likely a better fit than Devious. Revival triggers when discarded or destroyed from your Life Deck.
- **Dr. Wheelo vs anger/MPPV decks**: Blue Protective (opponent needs 6 anger to advance) turns Wheelo into an anti-anger mill deck: Blue Biting Drill
  (lowering anger already at 0 makes them destroy their top card), Blue Slash (HIT: they destroy 6 minus their anger), Blue Head Knock (anger to 0), and
  Wheelo L2 mills 1 per stop, which Protective's Power and Blue's stops feed. Black keeps its mill and can add anti-anger cards instead (Black Choke, Impediment,
  Easy Block, Corruption, Extreme Blast). Wheelo has no MPPV engine past L1 (L1 sets anger to 3; L2-L4 give none) and tiny power levels, so a "faster MPPV"
  build is not recommended. Protective, "your opponent destroys" and Wall Breaker rulings: see Mechanics confirmed by the owner.
  Mill numbers with the confirmed "your opponent destroys" ruling, at Level 4 (+2): Blue Slash 6 -> 8 (9 with Cell Jr. AW-U76, 10 with Blue Challenging Strike up), Blue Biting Drill 1 -> 3,
  Dr. Wheelo's History 3 -> 5. Option 2 (keep Black's mill and add Black Choke / Impediment / Easy Block / Extreme Blast and Villainous Energy Beam / Power Ball) was described but **not built**.
- **Trunks** (Hero; four sets of levels, mix freely): Premiere Inquisitive/Resolved/Energy Charged/Young Super Saiyan (reorder the top of a Life Deck on entering combat, Energy Charged draws);
  Evolution Returned/**Swordmaster** (free 8-stage physical attack if you have not attacked from hand)/**Defiant** (fetch a Styled or Sword attack from your discard pile, opponent skips an action)/**Overpowering** (+5 stages on every attack);
  Set 6 **Protective** (Level 1 only; Drills are not discarded when you advance from it, Sword cards Rejuvenate 1, fetches a non-Styled Drill);
  Awakening deck-reveal **Dashing** (doubles anger you raise in combat)/**Frenzied** (critical effect per Named card, free stop of a physical attack)/Bold/**Overwhelming** (Sword attacks cannot be stopped and raise anger 1; Power +2 anger).
  Named: Trunks' Sword Slash, Knee Bash (counts as "Sword"), Slam (considered Styled), Sword Stance (cannot MPPV); Aggressive Sword Drill and Dashing Sword Attack are Freestyle "Sword" cards.
  Owner's Orange Drill deck uses Orange Retribution Mastery (changing levels shuffles Drills back, its Power refetches Drills, Power also raises anger up to 2 a turn).
  Two worked answers: **Orange, no MPPV, with level-skips (Orange Devouring Drill)**: Protective, Swordmaster, Defiant, Overpowering. **Red, MPPV**: Dashing, Frenzied, Energy Charged (or Defiant), Overwhelming;
  at Level 4 one turn can reach 5 anger (Retribution/Enraged raises, Overwhelming Power +2, one Sword attack +1) and Red Enraged turns every critical effect into +1 anger. Orange has 25 anger cards
  (33 points) to Red's 54 (77), so Orange is the weaker MPPV style for this stack.

- **Piccolo (friend's Red deck, all Premiere levels: Stoic, Combat Stance, Unleashed, Fused)**: about 1 anger point per card. Combat Stance gives a critical effect every turn, Unleashed
  (+2 life cards, ball search on critical damage) turns 4-life-card attacks into critical hits, and Piccolo's Weighted Clothing (banish from discard: raise anger 2) is an
  uncounterable MPPV finisher. Composed (L1) and Stoic (L1) cannot both be used, and Composed needs real Rejuvenate/stage-gain support.
- **Garlic Jr.** (Villain, only Set 3 printings are legal): L1 needs 2 less anger to advance and its Power raises anger 1. L3 can capture a Dragon Ball whenever you raise your anger.
  L4 gives the opponent's attacks +3 life cards, so reach it and win the same turn. Counter Blast doubles Continuous modifiers, so do not play it at L4.

- **Krillin** (Hero, legal Set 1-7 levels: Ready, Energetic or Quick, Ready For Battle, Enraged): an energy-attack MP that rewards shrinking the opponent's hand. L3 deals 9 minus the cards in their hand.
  L1 gives a critical effect and 2 anger the next time any card is discarded from a hand this combat. Named: Krillin's Solar Flare, Krillin's Destructo Disk (cannot be stopped or prevented).
  Black has 14 hand-disruption cards; Black Devious Mastery makes the opponent discard each turn and turns 4-life-card attacks into critical hits.

- **Nappa** (Villain, Saiyan heritage, only Set 2 printings are legal: Rested, Smirking, Overconfident, Enraged): a stage-damage MP. Stages lost or taken at
  power level 0 come off the Life Deck (Rulebook 3.0), and L4 makes your attacks unpreventable while the opponent's MP is at 0, so drive their MP to 0
  first. L2 drains 1 stage per attack you perform (2, from all their personalities, if you changed levels this combat). The opponent picks which personality
  loses the stages and can redirect damage to Allies, so L1/L3 Ally removal matters. Named: Nappa's Energized Charge (opponent's MP changes levels -> power 0),
  Nappa's Confidence. Vegeta Ally (Set 2) gives physical attacks +2 stages with Nappa. Saiyan Clench (Limit 2, Villains only) doubles power stage damage of
  non-AT attacks, and Nappa's L4 top power (24,000) meets its 500,000 cap. First deck: Saiyan Rampaging (4 anger to level; its Power turns an Endurance card
  into a 1+X stage attack). **(unverified)** Saiyan Dive's "Endurance considered 10" counts for Rampaging's X; Clench doubles before or after +stage modifiers;
  Overpowering Aura Drill / Body Blow can fetch Clench; how many "Saiyans in play" Turles Ally counts under PanZ rulings.
  Options not built: **Saiyan Dynamic** (start on Level 2 so the drain runs from turn 1; 6 anger to level, so MPPV is slower) and **Black Devious** (+1 stage and +1 life card on every attack;
  Black pool not surveyed for Nappa). The deck on file is `decks/nappa_saiyan_clench.txt`.

## Decks on file (codes are in the files; decode with `deckcode.py`)
`decks/` holds owner-exported decks; `sim/decks/` holds decks built in sessions for simulation. Only codes the owner imported are confirmed to load in the app.
| File | MP / style / Mastery | Status |
|---|---|---|
| `sim/decks/wheelo_black_v2.txt` | Dr. Wheelo, Black, Black Devious | imported by the owner (60 cards, MP and Mastery correct); plays a destroy/mill plan, loses to fast MPPV decks in the simulator |
| `sim/decks/piccolo_red_friend.txt` | Piccolo, Red, Red Enraged (the friend's "redder Pic 1.0") | owner's friend's deck; used as the speed benchmark for MPPV |
| `sim/decks/trunks_orange_v3.txt`, `trunks_orange_v4.txt` | Trunks, Orange, Orange Retribution | built from the owner's Orange Trunks; V4 = skip-levels plan (Devouring Drill x3, Evolution levels); not confirmed in the app |
| `decks/trunks_orange_v5.txt` | Trunks, Orange, Orange Retribution (Protective / Swordmaster / Defiant / Overpowering) | V4 plus six simulator-guided swaps; see `TRUNKS_STYLE_COMPARISON.md`; **imported by the owner (2026-11-02): loaded with no issues**. How it plays is not yet reported |
| `sim/decks/trunks_red_draft.txt` | Trunks, Red, Red Enraged | draft anger/MPPV build; not confirmed in the app |
| `sim/decks/lord_slug_red_v3.txt` | Lord Slug, Red, Red Enraged | Earth balls (see the Namek-set advice above); not confirmed in the app |
| `sim/decks/nail_black_v2.txt` | Nail, Black, Black Devious | black mill build with Time Is A Warrior's Tool and Confrontation; not confirmed in the app |
| `sim/decks/garlic_red.txt`, `krillin_black.txt` | Garlic Jr., Red, Red Enraged / Krillin, Black, Black Devious | built this session; not confirmed in the app |
`decks/` (built in a cloud session, deck codes written by `deckcode.py`):
| File | MP / style / Mastery | Status |
|---|---|---|
| `decks/nappa_saiyan_clench.txt` | Nappa, Saiyan, Saiyan Rampaging | stage-drain plan around Saiyan Clench; **imported by the owner (2026-11-02): 60 cards, no errors**; the first two attempts failed (see Deck code format) |
| `decks/wheelo_blue_lockdown.txt` | Dr. Wheelo, Blue, Blue Protective | anti-anger mill build for the owner's friend, who is still trying to make Wheelo work. Not imported or simulated; **the owner will report back on how it plays later** (record the result here). Owner said to leave it as is; a possible swap (Blue Smug Punch -> a third Wall Breaker) was offered and not made |

## Deck code format (from the owner's web app)
**Use `scripts/deckcode.py`** to encode, decode and check codes (`python deckcode.py check "<code>"`; `python deckcode.py test` round-trips the
owner's three sample codes, Broly / Piccolo / Trunks, whose decoded lists matched the app's screenshots).
`D1.<name>.<MP name>.<Mastery>[._<L1>_<L2>_<L3>_<L4>].<card>.<card>...`
- Names are URL-encoded (`%20`, `.` as `%2E`, `(` `)` as `%28` `%29`). Cards are `*N` for N copies, sorted as plain text.
- Every card, the Mastery and the MP printings included, is `<set prefix>-<printed number>` **with the rarity letter**: `C58`, `HV-C137`,
  `MC-R125`, `EV-S11`, `UR162`. Set prefixes: none = Set 1, `HV` 2, `MC` 3, `EV` 4, `PF` 5, `VG` 6, `AW` 7.
- The Mastery is a card number, not a name (`S25` = Saiyan Empowered, `S27` = Red Enraged).
- Set 7 DR cards are `S<n>` (`AW-S10` = Orange Retribution Mastery DR10, confirmed by the owner's Trunks code).
- The MP printings field is optional (the Broly code and the friend's second Piccolo code have none). **(unverified)** With no field the app probably uses each level's first printing (Piccolo: Stoic `S21` at Level 1; `EV-S11` is Composed).
- The app's MP name can carry a qualifier (`Trunks (Awakening)`); what it means is not known yet.
- **Confirmed by the Nappa import (2026-11-02):** the plain MP name `Nappa` and an explicit MP printings field (`_HV-C3_HV-C4_HV-U63_HV-U64`) are accepted.
- **The app knows each non-MP card by one printing only: its first** (earliest set; within a set starter/DR, then booster, then promo).
  The owner's codes always use it (`S25` not `R145`, `R152` not `P8`, `S149` not `AW-S122`), and later reprints (`AW-S77` Stare Down,
  `EV-S159`, `EV-S165`, `AW-S118`, `AW-S122`) came back "Unknown card". `deckcode.py` encodes this automatically (`app_printing`).
  MP levels can be any printing.
- Never retype a code by hand: write it to `decks/<name>.txt` with the script and paste from there. (The second Nappa code got an extra
  `PF-R129`, Orange Ki Ball, from hand-copying.)
- A name containing a period (Dr. Wheelo) written as `Dr%2E%20Wheelo` imported correctly: all 60 cards, MP Dr. Wheelo and Black Devious Mastery (owner-confirmed).
