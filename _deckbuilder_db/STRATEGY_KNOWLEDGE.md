# Strategy knowledge and verified rules

Written at the end of a long deck-building session (decks for Nail, Lord Slug, Turles, Piccolo, Dr. Wheelo, Trunks, Garlic Jr., Krillin) so other
chats do not have to rediscover it. Read it together with `DECKBUILDING_NOTES.md` (checklist and per-MP notes) and `CLAUDE.md` (rules for working here).
Items marked **(unverified)** are inferences. Everything else is from `work/crd/rulebook.txt`, the CRD, the card data, or something the owner said.

## 1. Rules checked in Rulebook 3.0 (`work/crd/rulebook.txt`)
- **Anger and levels.** Reaching 5 anger advances the MP, sets it to 10 stages, resets anger to 0, **discards all Drills**, and you may use the new level's Power
  this turn. Excess anger does not carry over. If an *effect* advances or lowers you, anger stays the same (lowering sets you to 5 stages). If you cannot win by MPPV and
  would advance at Level 4, anger resets to 0 and the MP goes to its highest stage. Anger cannot go below 0.
- **Start of game:** MP on Level 1 at 5 stages. Each turn: draw 3, Planning Step (play Allies, Setups, Drills, Dragon Balls, then power up by PUR), optional combat, Discard
  Step (down to 1 or 0 cards), Rejuvenation Step (only if you did **not** declare combat: Rejuvenate 1).
- **Combat:** the declarer uses "when entering combat" effects, then the defender uses theirs and **draws 3**. Players alternate Actions; combat ends when both pass in a row.
  **Using a card to respond to an attack is not an Action**, so "skips their next action" does not stop them defending.
- **Attack Table:** compare the attacker's Power Level bracket (A 0-999, B 1,000-9,999, C 10,000-99,999, D 100,000-499,999, E 500,000-1,499,999, F 1,500,000+) to the
  defender's. A low-power MP (Garlic Jr., Krillin) gets AT 0 against most opponents, so it should win with life-card damage, not "AT +x stages".
- **Damage:** stage damage first; stages lost at power level 0 come off the Life Deck. Critical damage = 5 or more Life Cards from an unstopped attack; the three
  critical effects (capture a Dragon Ball, discard an opponent's Ally, lower opponent's anger 1) are always selectable. Endurance banishes a revealed Endurance card to prevent
  that many further Life Cards. "Cannot be prevented" beats Endurance but not Stops.
- **Dragon Balls:** discarded or destroyed balls go to the bottom of the Life Deck (they do not count as damage and need a replacement discard). You cannot play a ball with the
  same name as one in play. Dragon Ball Victory = control all seven of one set.
- **"Play" vs "place into play":** playing pays costs and uses a Dragon Ball's immediate effects; placing into play does neither. So a search that "places a ball into play"
  does not trigger its effects, and a Drill placed by an effect is not "played" (matters for Orange Devouring Drill).
- **Powers** of an MP level, Ally or Mastery may be used **once per turn**, regardless of changing levels. **(unverified)** whether the defender's turn counts separately.
- Allies can act when the MP is at most 1 stage above 0.
- Survival Victory: the opponent's Life Deck has no cards left.

## 2. Mechanics the owner confirmed
- Card text is literal. "A Dragon Ball in play" means anyone's; "destroy" is not "banish"; effects printed before the DAMAGE line resolve before blocks and damage.
- A critical effect can only discard an opponent's Ally; a card effect saying "destroy an Ally" may target your own.
- Owner rulings that apply to specific cards are in `work/owner_rulings.json` (e.g. Nail's Dashing Attack stays an Energy Combat card although its text is a physical attack).

## 3. Data and tool gotchas
- `is_named` / `named_character` come from a possessive-title rule in `derive.py`; false positives go in `NOT_NAMES` ("Time Is A Warrior's Tool", "It's Over 9,000!").
  "Considered Named for your effects" cards (Pesky Barrage, Black Back Strike) have `is_named` but no `named_character` and are legal in any deck.
- `restrictions` holds `Heroes` / `Villains` / `<Mastery name>`; every "(Heroes only)" / "(Villains only)" card has one (checked: 0 missing).
- Use `text_current` if present, else `text_as_printed`. Use `card_type_current` if present.
- Re-running the pipeline: pass `--out work/full` exactly. `--out ../work/full` writes a `work/` folder outside `_deckbuilder_db/` (this happened once and was removed).
- Check `limit_per_deck` for every card: Orange Uppercut (Limit 1) was wrongly given x2 once.

## 4. Deck codes and the encoder review
- `scripts/deckcode.py` (encode / decode / check) was written by another chat and is now merged into `main` (the app only knows each card by its first printing; see `DECKBUILDING_NOTES.md`).
- Review result: its format matches what this session worked out independently (D1 header, URL-encoded names with `.` as `%2E`, Mastery as a card number, optional
  `_L1_L2_L3_L4` printings field, `*N` copies, plain-text sort, `EV` = Set 4, Set 7 deck-reveal cards written `S<n>`).
- Run on every code produced in this session (Nail, Lord Slug, Wheelo, Trunks V2/V3/V4, Red Trunks, Garlic Jr., Krillin) plus the codes the owner sent: all decode and re-encode
  **exactly**, and its checker reported no errors on any of the legal decks. It also correctly rejects the mistakes made earlier: Goku's Search in a Nail deck (Named), Stare Down in a Hero deck,
  Orange Uppercut x2 (limit 1), and two Dragon Ball sets.
- Its "first printing" rule (the app knows a non-MP card only by its earliest printing) is consistent with all codes here.
- **Never retype a code by hand**: write it to a file with the script. (A retyped copy of one Trunks code lost a card and showed 59.)
- **(unverified)** The qualifier in an MP name such as `Trunks (Awakening)` probably names the set of the MP group when a character has several MP sets (Premiere, Evolution,
  Awakening deck-reveal); the explicit printings field overrides which levels are used.
- **Resolved (owner, 2026-11-02):** `EV-S11` is Piccolo Composed (Stoic is `S21`). The friend's "redder Pic 1.0" deck plays Stoic; the owner's second export of it has no printings field (same 60 cards). The earlier code with `_EV-S11_S22_S23_S24` selected Composed explicitly. What the app plays when the field is absent is not confirmed (probably the first printing of each level, i.e. Stoic).

## 5. Strategy lessons
**How a style was chosen (use this method):** list what each level rewards and punishes, count supply of the cards that stack with the MP, list cards that cancel the MP's passives,
check the Mastery's effect on the opponent, then give 2-3 ranked options with reasons. Mistakes this corrected: Lord Slug was dismissed in Red (the owner's Red Enraged
Dragon Ball Victory deck is good), and Blue stay-on-Level-1 stage-lock was missed for Turles.

**Anger economy (Sets 1-7, usable by a Hero, unique cards):** Red 54 cards / 77 anger points / 17 critical-effect cards; Black 25 / 35 / 6; Orange 25 / 33 / 2; Saiyan 18 / 21 / 4;
Blue 11 / 17 / 2; Namekian 6 / 7 / 10. Anger points per card in decks: friend's Red Piccolo 1.00, Garlic Jr. build 0.95, Red Trunks build 0.68, Black Krillin 0.42, Orange Trunks 0.38.

**Why a Red MPPV deck is fast (friend's Piccolo):** (a) very high anger density; (b) 14 non-attack cards that raise anger or give a critical effect (cannot be stopped, cost no stages);
(c) defense cards that raise anger when they stop something; (d) cards that trigger when discarded **by a card effect** (Red Sacrifice +2, Red Restraint +1), fed by Combat Stance,
Stare Down and the opponent's discard effects; (e) Red Enraged: every critical effect is +1 anger and an opponent's -1; (f) Piccolo's Weighted Clothing banished from the discard pile is
a +2 anger action that cannot be answered by a defense; (g) Unleashed (+2 life cards) turns 4-life-card attacks into critical hits.
A level costs 5 anger and the excess is lost, so many small packets are efficient. Games last about 3 turns per player.

**Other MPs with a similar engine (all Red-based, untested):** Goku Level 2 (critical effect for any discard), Vegeta (every attack raises anger; Level 3 +3 stages and +3 life cards on
anger-raising attacks), Garlic Jr. (3 anger per level at Level 1, +1 free anger a turn, captures a ball on any anger raise at Level 3), Frieza Level 1 and Master Roshi Level 1 (stopping raises anger).
Red Ascension is a non-frozen alternative to Red Enraged.

**Dragon Ball Victory:** only works for the opponent's balls if they play any. Own balls come from Planning-step plays, Dragon Radar, Unleashed (search on critical damage), Lord Slug's
levels, Information Gathering. Namek Dragon Ball 1 protects your *other* balls from capture; Piccolo Level 4 Fused makes the opponent need 7 life cards to use a critical effect.

**Orange / Drill decks:** Drills are discarded whenever you advance (Trunks' Protective is the one Level 1 that keeps them), so Level 3 and 4 must work without Drills. Orange Devouring Drill
(advance one level when you play a Drill, no MPPV that turn) is the reliable skip-level card. Only Drills played from hand count.

**Mill (Dr. Wheelo):** only "destroy" effects trigger his Level 3/4 bonuses. Banish does not, and Black Remembrance Drill turns destroys into banishes, so avoid it.
Revival triggers when it is discarded or destroyed from your own Life Deck, including by damage.

**Krillin:** Level 3 deals 9 minus cards in the opponent's hand, so hand disruption (Black has 14 such cards) is the engine.

**Defaults the owner wants:** Time Is A Warrior's Tool x1 and at least 2 Confrontation (Hero) or Stare Down (Villain) in every deck.

## 6. Simulation results (toy model, not an official rules engine)
A small simulator was written in the session scratchpad (not in the repo). It parses damage, cost, anger, stops and Endurance from card text and hard-codes the MP/Mastery effects of the
decks being compared; both sides follow the same simple priority list; secondary effects (most searches, banishes, skips) are ignored. Treat results as a rough signal.
- Red Trunks draft vs Orange Trunks V4 (Orange MPPV off): Red won 61%; with Orange MPPV allowed, 56%. Games last about 6 turns in total.
- Dr. Wheelo V2 vs the friend's Red Piccolo (assuming Stoic at Level 1): Wheelo won about 17%. Piccolo won almost entirely by MPPV on its third turn; Wheelo rarely reached Level 3.
  Going first changed it by about 3 points. A variant with 3 Wall Breaker (it attaches to Piccolo so it cannot gain anger until it deals critical damage) only moved Wheelo to 18%.
- Lesson: against a deck that can MPPV in about 3 turns, a deck that needs 4+ turns to start its engine loses most games. A loss in such a matchup is not evidence of a play mistake.

## 7. Open questions
- Which Piccolo Level 1 the friend's deck really uses (Composed or Stoic)?
- Does "once per turn" count the defender's turn separately for Powers?
- Does a doubling effect like Trunks' Dashing apply to anger raised by a Mastery trigger (Red Enraged)? The simulator assumed yes.
- What the "(Awakening)" qualifier in an MP name means to the app.
