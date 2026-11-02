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
9. Present the deck by role, the code in a fenced block, the simulator playtest (what you ran, what was unmodelled, what you saw) and every unverified assumption; ask the owner to import it.
   Save the code in `decks/`, run `python -m sim roster add decks/<name>.txt` (step 5 of the playtest section), record new owner rulings and lessons here, then commit and push to `main`.

## Playtesting a deck in the simulator (required before finalizing)
Run everything from `_deckbuilder_db/`. The simulator is a toy model (`sim/README.md`), but it is the only thing that executes the cards, so every deck gets played before it is presented.
1. **Coverage first:** `python -m sim coverage decks/<name>.txt` (or `sim/decks/`). It lists the MP levels and the Mastery that are **NOT MODELLED** and the card sentences it ignores.
2. **"The simulator does not have this character" is not a reason to skip.** Add the missing MP levels, the Mastery and the cards your plan depends on to `sim/behaviors.py` from the card text
   (**step-by-step guide for someone who has never opened the simulator: `sim/MODELLING_GUIDE.md`**; short recipe: `sim/README.md`, "Adding things"; usually one small class per MP level), run `python -m unittest discover -s sim/tests -t .`, and commit the new behaviors so the next deck
   starts with them. Model what the deck's plan relies on; ignoring cosmetic text is fine. If a rule is unclear, write the behavior the literal text implies, mark it **(unverified)** in the
   code and in your answer, and do not invent card text. Only skip a piece with the owner's OK; otherwise say exactly which parts are unmodelled and that those parts are text-only.
3. **Play it against the test-deck roster:** `python -m sim playtest decks/<name>.txt`. It plays your deck against every deck on the roster (**up to 25 decks, one version per MP + Mastery**, 20 games each by default; a game takes about 10 ms, so a full playtest takes about 3 seconds and the 50-game cap about 6;
   the command refuses more than 50 games per opponent). It prints a win rate per opponent and how each game ended, and the command to read a play log of your worst matchup (`python -m sim game A B --seed 1`):
   read 2-3 logs. Look for: which levels it reaches and when, whether the key cards and combos fire, cards that sit in hand unused, how it loses. For a specific matchup the owner named, also
   `python -m sim game <your deck> <their deck>`. **Do not run hundreds or thousands of games for deck building**: large `python -m sim run A B -n 1000` batches are for matchup testing when the owner asks.
   The roster is a spread of the decks built so far (see "The test-deck roster" below), so never rely on the friend's Piccolo deck alone: it is a very fast, niche MPPV deck.
4. **Use what you see:** cut cards that never matter, add support for the step that stalled, re-encode and re-check. Then, when you present the deck, say what you simulated, which parts were
   unmodelled (from `coverage`), what the logs showed, and that the simulator is a rough model, not a prediction.
5. **Add the finished deck to the roster:** save its code to `decks/<name>.txt`, then `python -m sim roster add decks/<name>.txt` and commit `decks/<name>.txt` and `sim/roster.json`. The command
   ranks the deck against the current roster (round robin, fixed seeds): if it is in the top 25 by win rate it joins and, once the roster is full, the lowest-ranked deck is retired; if it does not make the top 25 it is not added. If an older version of the same deck (same MP + Mastery) is on the roster, the better of the two stays and the other is listed as superseded. It only plays the new deck against the roster (pair results are cached), so it takes well under a second.
   It refuses a deck whose MP levels or Mastery are NOT MODELLED (do step 2 first). Say in your answer whether the deck joined the roster.

### The test-deck roster
`sim/roster.json` holds **at most 25 decks** (the cap is `MAX_ROSTER` in `sim/roster.py`; games are fast enough to test against many decks); `python -m sim roster` shows it. Rule: a new finished deck is played against the roster in a round robin (30 games per pair, fixed seeds, first player
alternating); decks are ranked by win rate, the top 25 stay and the rest are retired. **Only one version of a deck counts**: a deck's family is its MP + Mastery (Orange Trunks V3/V4/V5 are one deck); only the best-ranked version of each family stays, the older ones are listed as `superseded` in the file, and versions of one family do not play each other in the ranking. A new version replaces its predecessor only if it ranks higher (`retired` in the file; the deck files stay in the repository and can still be used with `sim game`/`sim run`).
`python -m sim roster rebuild` re-ranks every deck in `decks/` and `sim/decks/` from scratch (use it to resolve a merge conflict in `roster.json`). Decks with NOT MODELLED parts are not rankable.
Things to know:
- The ranking is the **model's** win rate, not real strength (the model may overrate the Orange Trunks decks), and it measures decks against each other only. A win rate is relative to the decks on the
  roster at that moment, so the numbers shift a little whenever the roster changes.
- Because the roster keeps the highest winners it drifts toward strong, fast decks. Once the roster is full, slow decks get retired first. Two truly different strategies with the same MP and Mastery
  count as versions of one deck (the roster keeps the better one); use `sim game` / `sim run` to test against the other directly. If you need a slow or specific opponent, use it directly with `sim game` / `sim run`.
- Snapshot when it was created (10 decks): Orange Trunks V5 (89%; V3 and V4 superseded), Red Trunks draft (79%), Nappa Saiyan Clench (58%), the friend's Red Piccolo (52%), Nail Black (37%),
  Garlic Jr. (37%), Krillin (31%), Wheelo Black (30%), Wheelo Blue (29%), Lord Slug (8%). Check `python -m sim roster` for the current list.
- Every deck on the roster must be fully modelled: `roster add` refuses a deck with NOT MODELLED MP levels or Mastery. The first roster build skipped Nappa for that reason, so Nappa's four levels,
  the stage-drain effects ("your opponent loses N stages", including "to a minimum of 0") and Saiyan Clench were added to the simulator; the remaining gaps for that deck are listed by `coverage`
  (Allies, second-use attacks, Saiyan Dive's banish).

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
1b. **Every Styled card must match the Mastery's style** (Rulebook 3.0: "All of your Styled cards must match the Style of your Mastery"; Freestyle cards are free). `deckcode.py check` and the page checker enforce it.
   A Raditz draft mixed Red, Orange and Saiyan cards under Red Enraged and passed the old checker; never pick cards across styles.
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
  **Simulator test (Earth V3 vs Namek V4, same 60 cards apart from the seven balls, 450 games against the 9 other roster decks, 500 head-to-head):** Namek 9.8% vs Earth 10.0% overall (a tie within noise); head-to-head Namek 59% / Earth 41%.
  Namek's edge is almost all Namek 6 (+3 PUR, opponent's attacks -2 stages) and Namek 1 (+1 life card), i.e. it helps Slug *survive and hit*, not win by Dragon Balls: in 180 games each, Slug had 7 or more balls in play in only 1 game (Earth) / 13 games (Namek) and won by Dragon Ball Victory only 11 times in 500 (Namek) -
  games last about 7 turns and crit decks capture the balls. Both versions score 0/50 against Orange Trunks and Red Trunks (Garlic Jr.: Earth 5/50, Namek 0/50); Slug's real wins come from Survival against slower decks (Wheelo Blue 26-36%).
  **Model gaps that may undersell Slug:** Namek 2 (lower a personality) and Namek 4 (destroy 2 Setups/Drills) are not modelled; Earth 6 (re-Rejuvenate banished balls) and Earth 7 (play a ball from hand as an action) are not modelled and would help Earth; the Dragon Radar "search and play" and Lord Slug's Regeneration advance/lower are not modelled; the AI never protects balls on purpose. Treat Slug as the weakest roster deck against fast decks, and as a deck you play for a slow Dragon Ball plan against slower decks.
- **Goku** (Hero; Set 7 Training/Determined/Courageous/Selfless, Set 4 Relaxed/Motivated/Calm/Dashing, Set 1 levels; mix freely): only the Set 4 levels search for Allies (Calm L3, Dashing L4, Relaxed L1 to the top of the deck). Allies act only while the MP is at most 1 stage above 0
  unless a card frees them, so Goku taking stage damage (stage 0) turns his Allies on; Chichi works regardless for Goku, Piccolo does not (his exception is for Gohan). Three decks and the ranking are in `GOKU_STYLE_COMPARISON.md`. The sim models Training, Determined, Calm and Dashing only.
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
- **Raditz** (Villain, Saiyan heritage, only Set 2 printings are legal: True Saiyan, Confident, Angered, Triumphant): Setups and Drills are played in the Planning Step, Setups are used in combat.
  L1 Power: physical attack (1 life card), look at your top 2 (one to hand, one banished from your own Life Deck), raise anger 1. **L2: every Setup or Drill entering play destroys the top card of the opponent's Life Deck, and +1 anger if it enters during combat** (searched or "placed into play"; Planning-step plays give the destroy only).
  L3: opponent discards a random card when entering combat (Instant). L4: Setup/Drill entering play Rejuvenates a card; the first critical damage effect each combat searches Life Deck or discard pile for a Setup/Drill and places it into play. Named: Raditz's Offensive Guard
  (attach: once per combat place a Setup/Drill from hand into play), Raditz's Dirty Tactics (Limit 2, not used). The Set 2 Nappa Ally ("Setups cannot be used") is a trap in a Setup deck. Many "Events" in the Red/Saiyan pool are really Setups (Red Blaze, Red Destiny, Saiyan Enraged), so they also trigger L2 when played.
  **Styled cards must match the Mastery** (Rulebook 3.0): Orange Celebration/Encouragement ("a Styled Drill") only find Drills of the Mastery's style, so the Drill engine is Orange only with an Orange Mastery.
  Simulated styles (50 games per roster deck): **Orange Retribution 82%** (80% after the Vegeta deck joined the roster) (anger 2 a turn from its Power plus Drills entering play; reaches Level 4 by its second turn and wins by MPPV about turn 5), Red Enraged 51%, Saiyan Rampaging 48%, Orange Adaptive 44%
  (the last three are within noise of each other; against the 12-deck roster that now contains Raditz Orange they measure 46% / 42% / 38%). Decks on file: `decks/raditz_orange.txt` (on the roster), `raditz_red.txt`, `raditz_saiyan.txt`, `raditz_adaptive.txt`. Not modelled: Offensive Guard's "banish from hand to stop an attack", Orange Retribution's
  shuffle-Drills-on-level-change, Rampaging's Power, Red Slide keeping Drills. **(unverified)** Saiyan Analysis Drill copies do not stack and do not lower Level 4 MPPV; Level 3's discard also fires when defending; Level 1's reveal/anger happen even if its attack is stopped.

- **Vegeta (Hero)** (Saiyan heritage; Hero levels from Evolution = Styled, Awakening = non-Styled): Awakening *Experienced / Imposing / Energized / Pinnacle of Power* give non-Styled (Freestyle) attacks
  +2 / +1 (and no prevention) / +3 (and a second use of the first stopped one) / +3 and **cannot be stopped**. Evolution *Calculating / On the Move / Super Saiyan / Elite* reward Styled attacks (life cards <-> stage damage;
  Elite: first Styled physical cannot be stopped). Named: Vegeta's Galick Gun (x3, 6 life cards for 2 stages, unpreventable, two critical effects), Destruction Blast, Final Flash, Vegeta's Anger. Experienced's
  parenthesis says non-Styled damage can only be modified by Experienced itself (Level 1 only; the simulator ignores this).
  Style comparison (an early one-off run, before the roster existed: 800 games per opponent against 8 reference decks, average win rate; the Awakening/Red Ascension deck was later improved and playtested against the roster, see the deck table): **Awakening Freestyle + Red Ascension 71.5%** (`decks/vegeta_pinnacle_red_ascension.txt`),
  Evolution Styled Red + Red Ascension 64.0%, Awakening Freestyle + Saiyan Dynamic 51.3%; also tried: Evolution Saiyan Dynamic 47.2%, Awakening + Red Enraged 46% (300 games), Evolution Saiyan Rampaging 40.7%,
  Awakening + Black Conflict 24% (400 games, too slow to level). Red Ascension beat Red Enraged because its free +1 anger a turn (end of combat) plus Power levels the MP faster. The model does not count the
  Evolution stage-conversion, so the Evolution Red result is a floor.
  **(unverified)** Whether "+N life cards" applies to a stage-only attack (Devastating Blow, "AT +1 stage"); the deck does not depend on it. Overpowering Attack finds no Ally in this deck (no Allies in it).
  Weak spots seen in the playtest: stage-damage decks (Orange Trunks) drain its Life Deck while it sits at 0-4 stages after paying stage costs (loses by Survival), and Blue Protective / Wall Breaker slow its anger. Untested idea: Wall Breaker (opponent cannot gain anger) against MPPV decks.
  Quick Blast, Surprise Attack, Blinding Energy Move and Point-Blank Volley were left out on purpose (Blinding Energy Move ends combat and Point-Blank Volley's anger is double-counted by the parser) (Quick Blast banishes your own Defense cards while attached; Surprise Attack lets the opponent banish 2 of your non-Styled cards).

## Decks on file (codes are in the files; decode with `deckcode.py`)
`decks/` holds owner-exported decks; `sim/decks/` holds decks built in sessions for simulation. Only codes the owner imported are confirmed to load in the app.
| File | MP / style / Mastery | Status |
|---|---|---|
| `sim/decks/wheelo_black_v2.txt` | Dr. Wheelo, Black, Black Devious | imported by the owner (60 cards, MP and Mastery correct); plays a destroy/mill plan, loses to fast MPPV decks in the simulator |
| `sim/decks/piccolo_red_friend.txt` | Piccolo, Red, Red Enraged (the friend's "redder Pic 1.0") | owner's friend's deck; a very fast, niche MPPV deck: one stress test among several, not the general benchmark |
| `sim/decks/trunks_orange_v3.txt`, `trunks_orange_v4.txt` | Trunks, Orange, Orange Retribution | built from the owner's Orange Trunks; V4 = skip-levels plan (Devouring Drill x3, Evolution levels); not confirmed in the app |
| `decks/trunks_orange_v5.txt` | Trunks, Orange, Orange Retribution (Protective / Swordmaster / Defiant / Overpowering) | V4 plus six simulator-guided swaps; see `TRUNKS_STYLE_COMPARISON.md`; **imported by the owner (2026-11-02): loaded with no issues**. How it plays is not yet reported |
| `sim/decks/trunks_red_draft.txt` | Trunks, Red, Red Enraged | draft anger/MPPV build; not confirmed in the app |
| `decks/lord_slug_red_namek.txt` | Lord Slug, Red, Red Enraged | **V4, Namek balls** (the roster version; 15% over 500 playtest games); not confirmed in the app |
| `sim/decks/lord_slug_red_v3.txt` | Lord Slug, Red, Red Enraged | V3, Earth balls (older version, same family; superseded on the roster); not confirmed in the app |
| `sim/decks/nail_black_v2.txt` | Nail, Black, Black Devious | black mill build with Time Is A Warrior's Tool and Confrontation; not confirmed in the app |
| `sim/decks/garlic_red.txt`, `krillin_black.txt` | Garlic Jr., Red, Red Enraged / Krillin, Black, Black Devious | built this session; not confirmed in the app |
`decks/` (built in a cloud session, deck codes written by `deckcode.py`):
| File | MP / style / Mastery | Status |
|---|---|---|
| `decks/nappa_saiyan_clench.txt` | Nappa, Saiyan, Saiyan Rampaging | stage-drain plan around Saiyan Clench; **imported by the owner (2026-11-02): 60 cards, no errors**; the first two attempts failed (see Deck code format) |
| `decks/wheelo_blue_lockdown.txt` | Dr. Wheelo, Blue, Blue Protective | anti-anger mill build for the owner's friend, who is still trying to make Wheelo work. Not imported or simulated; **the owner will report back on how it plays later** (record the result here). Owner said to leave it as is; a possible swap (Blue Smug Punch -> a third Wall Breaker) was offered and not made |
| `decks/lord_slug_namekian_knowledge.txt` | Lord Slug, Namekian, Namekian Knowledge (Namek balls) | built 2026-11-02; style comparison and playtest in `LORD_SLUG_STYLES.md`; 56% over 600 roster games (50 per opponent), roster rank 6 of 17 after the later Vegeta and Raditz decks joined; **not imported into the app yet** |
| `decks/raditz_orange.txt` | Raditz, Orange, Orange Retribution | Drill/Setup engine plus anger 2 a turn; **simulated 82% vs the roster, joined it at rank 2**; check clean (60 cards); not imported by the owner |
| `decks/raditz_red.txt`, `raditz_saiyan.txt`, `raditz_adaptive.txt` | Raditz, Red Enraged / Saiyan Rampaging / Orange Adaptive | comparison builds (51% / 48% / 44% in the simulator); check clean; not on the roster, not imported |
| `decks/vegeta_pinnacle_red_ascension.txt` | Vegeta (Hero), Awakening levels, Red, Red Ascension | built 2026-11-02, checked with `deckcode.py check` (60 cards, no errors); playtested against the roster (72% over 200 games; 69% over 500 at 50 games each, see roster); coverage 86% modelled; **on the roster (rank 3 of 11)**; **not imported in the app yet** |
| `decks/vegeta_evolution_red_ascension.txt` | Vegeta (Hero), Evolution levels, Red, Red Ascension | ranked 2nd, same checks, not imported |
| `decks/vegeta_awakening_saiyan_dynamic.txt` | Vegeta (Hero), Awakening levels, Saiyan, Saiyan Dynamic (start on Level 2) | ranked 3rd, same checks, not imported |
| `decks/goku_blue_tag_team.txt` | Goku, Blue, Blue Tag Team (L1 Training, L2 Determined, L3 Calm, L4 Dashing) | Ally-search Goku; 57% over 950 playtest games (roster rank 7 of 20); not imported |
| `decks/goku_red_enraged.txt` | Goku, Red, Red Enraged (same levels) | 61% over 950 playtest games (roster rank 6); Red core from the friend's Piccolo deck minus Piccolo cards; not imported |
| `decks/goku_saiyan_rampaging.txt` | Goku, Saiyan, Saiyan Rampaging (same levels) | 69% over 950 playtest games (roster rank 5); Rampaging's Power not modelled; not imported |

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
