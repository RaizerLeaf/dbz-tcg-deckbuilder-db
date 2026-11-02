# How to model something new in the simulator (a guide for someone who has never opened `sim/`)

You are building a deck and `python -m sim coverage <deck>` (or `playtest` / `roster add`) says a Main Personality level, a Mastery or a card is **NOT MODELLED**.
That is not a reason to skip the simulator: you add the missing piece yourself. This guide takes you from "never seen this code" to a tested addition.
Allow 10-30 minutes per MP level or Mastery, a few minutes per card.

Rules that apply the whole time:
- **Never guess card text or rules.** Model what the card says, literally ("destroy" is not "banish", "play" is not "place into play"). If the text is ambiguous or the rulebook (`work/crd/rulebook.txt`) does not settle it, model the
  most literal reading, put a comment `# UNVERIFIED: ...` on the line, and tell the owner.
- **Do not leave out part of a text silently.** If you cannot model a sentence (Allies, a second use of an attack, a choice the simple AI cannot make), write it in a comment above the class and name it when you report results.
- **Never change `engine.py` rules to make one card work.** If the engine truly lacks a mechanic, add a small general hook (see "When the hooks are not enough") and a rule test.
- Everything lives in `_deckbuilder_db/sim/`. Run all commands from `_deckbuilder_db/`.

## 1. The 10-minute tour

| File | What it is |
|---|---|
| `cardmodel.py` | Turns a card's text into numbers: damage, cost, anger, stops, Endurance, Rejuvenate, stage gain, critical effects, "loses N stages". `synthetic(name, text)` builds a card out of bare text (for MP power attacks). `coverage()` says which sentences are understood. |
| `engine.py` | The rules: `Player` (hand, deck = Life Deck, discard, stage, anger, level, balls, drills, setups), `Game` (turn order, combat, Attack Table, critical damage, anger, advancing, MPPV, Dragon Ball Victory). It calls **hooks** on every active behaviour. |
| `behaviors.py` | **Where you work.** One `Behavior` class per MP level / Mastery, a table of per-card extras, passives, and the simple AI that decides what to play. |
| `loader.py` | Deck code -> `Spec` (MP, level cards, Mastery, 60 card ids). |
| `roster.py` | The test-deck roster used by `playtest` and `roster add`. |
| `tests/` | `test_rules.py` (engine rules and modelled behaviours), `test_roster.py`. |

How a turn works in the engine, in one line: planning (play Dragon Balls, Drills, Setups) -> maybe declare combat -> attack (cards from hand, MP power) -> defender responds (stops, Endurance, defend powers) -> damage (stages first, overflow comes off the Life Deck) -> critical damage effects -> anger/advance checks -> end of combat -> discard to 1 card.
A **behaviour** is just an object with optional methods. The engine asks every *active* behaviour (current MP level, the Mastery, Dragon Balls/Drills/Setups in play with a `@passive`) the same question and combines the answers.

## 2. Step by step

### Step 1 - Find out what is missing
```bash
python -m sim coverage decks/my_deck.txt
```
Look for `NOT MODELLED` lines (an MP level or Mastery) and the list under `unmodelled card text`. Cards are reported per sentence:
- *parsed* - `cardmodel.py` understood it (damage, cost, stops, ...). Nothing to do.
- *hand-coded* - the card has an entry in `behaviors.py` (`CARD_EXTRA` / `CARD_PASSIVE`).
- *unmodelled* - ignored. Decide whether it matters (an Ally, a trigger that rarely happens) or model it.

### Step 2 - Read the exact text
```bash
python - <<'EOF'
import json
for g in json.load(open('mps.json'))['mps']:
    if g['name'] == 'Nappa':            # change the name
        print(json.dumps(g, indent=1)[:3000])
EOF
```
(`mps.json` groups the levels of one MP; `cards.json` has every card. For a card use `text_current` if present, else `text_as_printed`.) Note the **exact subtitle** of each level - the registry key is `(MP name, subtitle)`.
For a Mastery, find its record in `masteries.json`; the key is the full Mastery name, e.g. `'Red Enraged Mastery'`.

Write each sentence on its own line and decide for each: *when* does it happen, *whose* state changes, *how often* (once per turn, once per combat, always).

### Step 3 - Pick the tool for each sentence
| The text says | Use | Example in `behaviors.py` |
|---|---|---|
| "POWER: [Attack] ... DAMAGE: N" (an attack the MP makes) | `synthetic(...)` + `has_power` / `power` calling `p.attack(opp, power=...)` | `NAPPA_L1`, `SLUG_ATK`, `KR_L1` |
| "POWER: draw / Rejuvenate / raise anger / destroy" | `has_power` + `power` doing it with `p.draw`, `p.rejuv`, `p.raise_anger`, `p.destroy_opp` | `WheeloL1` |
| "Your attacks deal +N stages / +N life cards" | `stage_bonus` / `life_bonus` | `SlugL3`, `NappaL4`, `BlackDevious` |
| "Whenever you use a critical damage effect ..." | `on_crit_effect` | `RedEnraged` |
| "Whenever you advance ..." | `on_advance` | `RedEnraged` |
| "Whenever you perform an attack / play a card ..." | `on_play` | `NappaL2` |
| "When this attack is stopped / when you stop" | `on_stopped` / `on_stop_made` | search the file for `def on_stopped` |
| "Damage cannot be prevented / cannot be stopped" | `unprevented` / `unstoppable` | `NappaL4` |
| "You cannot do MPPV" | `can_mppv` returns False | `SlugL4` |
| "When a Dragon Ball enters play ..." | `on_ball_entered` | `SlugL1` |
| "At the start of combat you may search your deck" | `entering_combat` (argument `defender` is True when you are being attacked) | `SlugL4` |
| "At the end of combat ..." | `end_of_combat` | `SlugL1` |
| "HIT: ..." on an MP attack | `after_hit(p, opp, card, removed)` | `NappaL3` |
| A card whose single effect the parser cannot read | `_x('Card Name', immediate=/hit=/use=/defend=/on_damaged=/enters=/base_stage=/can_use=...)` | `_namek3`, Saiyan cards |
| A card that stays in play and gives a continuous effect | `@passive('Card Name')` class with hooks | Namek Dragon Ball 1 and 6, `_Clench` |

If the sentence matches a primitive the parser already reads (see the regexes in `cardmodel.py`), nothing is needed: `coverage` shows it as parsed.

### Step 4 - Write the class
Registry decorators (all in `behaviors.py`):
```python
@mp('Nappa', 'Smirking')                       # (MP name, level subtitle) exactly as printed
class NappaL2(Behavior):
    def on_play(self, p, opp, card):           # p = the player this behaviour belongs to, opp = the other player
        opp.lose_stages(2 if p.cb['changed'] else 1)

@mastery('Red Enraged Mastery')
class RedEnraged(Behavior):
    def on_crit_effect(self, p): p.raise_anger(1)

_x('Namek Dragon Ball 5', immediate=_namek5)   # the function is called when the card enters play / is used
```
A level's behaviour is active only while that level is the current one. Masteries are always active. Behaviours the engine does not ask about simply do nothing (all hooks default to "no effect").

Helpers you will use (all in `behaviors.py` / `engine.py`):
- **Once-per rules:** `once_turn(p, 'key')` is True only the first time per turn; `once(p, 'key')` the first time per combat. Use a unique key per effect. Powers are once per turn, so almost every `power` starts `if once_turn(p, 'x'):`.
- **State bags:** `p.tf` (flags reset every turn) and `p.cb` (flags reset every combat; the list of keys is in `Player.reset_combat`). Add a key there if you need a new per-combat flag.
- **Doing things:** `p.draw(n)`, `p.rejuv(n)`, `p.raise_anger(n)`, `p.lower_anger(n)`, `p.gain_stages(n)`, `opp.lose_stages(n)`, `p.mill(n)` (destroy top of own Life Deck), `p.destroy_opp(n)`, `p.lose_card(card, 'destroy'|'banish'|...)`, `p.attack(opp, power=SYNTHETIC)`, `fetch_from_deck(p, predicate, 'hand'|'drill'|'ball')`, `find_in(zone, predicate)`.
- **Reading state:** `p.stage`, `p.anger`, `p.level`, `p.hand`, `p.deck`, `p.discard`, `p.balls`, `p.drills`, `p.setups`, `p.power()` (power level), `p.opp`.

### Step 5 - Hook reference (when each is called, what it should return)
Every hook has `p` = the player the behaviour belongs to. "Combined" says how the engine merges several answers.

| Hook | Called when | Returns / combined |
|---|---|---|
| `on_game_start(p)` | before turn 1 | nothing |
| `anger_modify(p, n, in_combat)` | anger is about to go up by `n` | new `n` (chained) |
| `anger_needed(p)` | the anger needed to advance is computed | a number or `None` (lowest wins) |
| `adv_anger_delta(p)` | same, Levels 1-3 | change to the amount needed |
| `opp_adv_anger_min(p)` | same, asked of the *opponent's* behaviours | a minimum for the other player |
| `on_anger_raised(p)` | after your anger rose | nothing |
| `on_crit_effect(p)` | you used a critical damage effect | nothing |
| `on_crit_damage(p, opp)` | you dealt critical damage (5+ life cards) | nothing |
| `crit_threshold(p)` / `own_crit_threshold(p)` | the life-card count that counts as critical (against you / for your attacks) | number or `None` |
| `on_advance(p)` | you advanced a level | nothing |
| `on_rejuvenate(p)` | after you Rejuvenate | nothing |
| `on_gain_stages(p, n)` | you gained `n` stages | nothing |
| `on_card_discarded(p)` | one of your cards was discarded | nothing |
| `on_play(p, opp, card)` | you perform an attack with `card` | nothing |
| `on_drill_played(p, opp, card)` | you played a Drill | nothing |
| `on_stopped(p, opp, card)` | your attack `card` was stopped | nothing |
| `on_stop_made(p, opp, card)` | you stopped `card` | nothing |
| `stage_bonus(p, card, opp)` / `life_bonus(p, card, opp)` | damage of your attack is computed | added |
| `stage_scale(p, card, opp)` | after the above | multiplier (default 1) |
| `incoming_life(p, card, atk)` / `incoming_stage(p, card, atk)` | damage against you is computed (`atk` = attacker) | added (negative reduces) |
| `unstoppable(p, card)` | the defender tries to stop your attack | True = cannot be stopped |
| `unprevented(p, card, opp)` | damage prevention is checked | True = damage cannot be prevented |
| `protect_balls(p)` | the opponent's critical effect wants to capture your Dragon Ball | True = they cannot |
| `on_ball_entered(p)` | a Dragon Ball entered play for you | nothing |
| `pur_bonus(p)` | the power level is computed | added |
| `can_mppv(p)` | MPPV is checked | all must be True |
| `keep_drills(p, old_level)` | you change level | True = Drills stay |
| `destroy_amount(p, n)` / `after_destroy(p, got)` | before / after your destroy effect | new amount / nothing |
| `entering_combat(p, opp, defender)` | combat is declared (`defender` True when you are attacked) | nothing |
| `end_of_combat(p, opp)` | combat ends | nothing |
| `has_power(p)` / `power(p, opp)` | the AI decides whether to declare combat to use a POWER / uses it | bool / True if used |
| `defend_power(p, atk, card, kind)` | you respond to an attack | True = your power handled it |
| `after_hit(p, opp, card, removed)` | your attack hit (`removed` = life cards removed) | nothing |

If the table says "nothing" the return value is ignored. Search `engine.py` for the hook name to see the exact call site - 2-3 lines of context make the semantics clear.

### Step 6 - Make the AI use it (only if the effect is a choice)
The simple AI (`choose_action`, `use_card` in `behaviors.py`) plays attacks, Setups, Drills and MP powers. If your effect is a POWER, `has_power` returning True is what makes the AI declare combat to use it, and `power` returning True tells it the power was used.
Do not write a clever AI. The same simple AI plays both decks so comparisons stay fair; a card whose value depends on a decision (which card to discard, when to hold) should use the cheap rule the neighbouring cards use (`p.value`).

### Step 7 - Check coverage and watch it happen
```bash
python -m sim coverage decks/my_deck.txt        # the level / Mastery / card should now say "modelled"
python -m sim game decks/my_deck.txt decks/nappa_saiyan_clench.txt --seed 1 | less
```
Read the log: does your effect fire at the moment the text says, the right number of times, with the right numbers? A log line is cheap evidence; a win rate is not. Try 2-3 seeds. Things to watch for:
- the effect never fires (wrong subtitle spelling in `@mp(...)`, `has_power` False, hook name typo) - `coverage` will still say "modelled" if the registry key matches, so the log check matters;
- the effect fires every action instead of once (missing `once_turn` / `once`);
- the player does something illegal-looking, like a Level 4 attack from Level 1.

### Step 8 - Add a rule test
Open `tests/test_rules.py`, find a neighbouring test (e.g. the `StageDrain` or Nappa tests) and copy its set-up: build two `Player`s from small decks, force the situation, call the hook or `attack`, assert the numbers. One test per behaviour is enough: "Smirking makes the opponent lose 1 stage, 2 after a level change".
```bash
python -m unittest discover -s sim/tests -t .
```
All tests must pass. If the numbers of an old regression change (`README.md`, "Regression decks"), find out why before moving on.

### Step 9 - Playtest and report
```bash
python -m sim playtest decks/my_deck.txt            # 20 games per roster deck
python -m sim roster add decks/my_deck.txt
```
In your report to the owner always say: what you added to the simulator, what you left out (and why), what was `UNVERIFIED`, and the coverage percentage.

### Step 10 - Commit
`git fetch`, merge, re-run the tests (another chat may have edited `behaviors.py`, and `roster.json` can conflict: resolve with `python -m sim roster rebuild`), then commit `sim/` changes and `decks/` + `sim/roster.json` and push to `main`.

## 3. Worked example: Nappa (four MP levels + stage-drain cards)
Texts (paraphrased; read the originals in `mps.json`): L1 *Rested*: POWER attack for 3 stages. L2 *Smirking*: whenever you attack, the opponent's personalities lose stages. L3 *Overconfident*: POWER attack for 7 stages, HIT banishes a Drill. L4 *Enraged*: +4 stages; damage cannot be prevented while the opponent's MP is at power level 0.

1. `coverage` showed all four as NOT MODELLED, plus cards with "loses N stages" the parser did not read.
2. Level 1 and 3 are POWER attacks -> `synthetic('Rested', 'POWER: [Attack] Physical attack. DAMAGE: 3 stages.')` and a small shared base class `_NappaAttack` (`has_power` True; `power` = `once_turn` then `p.attack(opp, power=self.card)`).
3. Level 3's HIT is not a number -> `after_hit` banishes a Drill (`opp.drills.pop()` into `opp.banished`).
4. Level 2 is "whenever you perform an attack" -> `on_play` -> `opp.lose_stages(...)`; the "if you changed levels this combat" condition is `p.cb['changed']`.
5. Level 4: `stage_bonus` returns 4; `unprevented` returns `opp.power() == 0`.
6. Cards: "loses N stages" got a parser primitive (`opp_lose`) because many cards use it; the odd ones (Saiyan Uppercut's variable damage, Clench's doubling) went into `_x(...)` / `@passive`.
7. Tests for the parser, overflow vs floor 0, Smirking, Enraged, Clench. Then playtest and `roster add`.
Part of Nappa's text was not modelled (an Ally destroyed by L1; Turles/Vegeta Allies) - the code has a comment, and the report said so.

## 4. When the hooks are not enough
Sometimes the engine has no place to hook (a new kind of trigger). Then:
1. Search `engine.py` for the nearest event and add **one small general hook** to `Behavior` in `behaviors.py` (default: do nothing) and call it in the engine for all `behaviors()`.
2. Add it to the table in this guide - `tests/test_docs.py` fails if a hook in `Behavior` is missing from this file.
3. Add a rule test, run all tests, and check that the regression numbers did not move (a new hook that defaults to "no effect" must not change any old result).

## 5. Common mistakes
| Mistake | Fix |
|---|---|
| `@mp('Lord Slug', 'Huge Slug')` - subtitle not exactly as printed | copy the subtitle from `mps.json`; a mismatch leaves the level NOT MODELLED |
| Modelling a Mastery under a short name | the key is the full Mastery name (`'Black Devious Mastery'`) |
| Effect repeats every time the AI asks | wrap in `once_turn` (per turn) or `once` (per combat) |
| Changing `p` when you meant `opp` | hooks get both; read the table above and say who changes in the comment |
| Counting an effect as "your" effect when the text says "your opponent chooses" | owner rulings in `DECKBUILDING_NOTES.md` ("Mechanics confirmed by the owner"); ask if not covered |
| Cached roster results look unchanged | they are keyed by a hash of the simulator, so any edit in `sim/` re-ranks everything on the next `roster add` (about a minute) |
| `python script.py` in another folder says "sim is not a package" | keep the script anywhere, but run it as `python - < script.py` from `_deckbuilder_db/` |
| Reporting a win rate without limits | always quote `coverage` and the sample size; 50 games per opponent is about +/-14 points |
