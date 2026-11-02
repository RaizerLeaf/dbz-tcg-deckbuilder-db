# Dragon Ball Z TCG deck-builder database

This repo holds card images (the numbered `0X_Set ...` folders, `z_OP Series`, `zz_PanZ MP & Ally Promos`) and the
database built from them in `_deckbuilder_db/`. The goal is an accurate, searchable card database for helping the owner (and later
other people) build decks.

## Read first
- `_deckbuilder_db/BRIEF.md` - the original rules for this project.
- `_deckbuilder_db/DECKBUILDING_NOTES.md` - **deck-building rules, legality checklist, method for comparing styles, deck code format, lessons
  from past decks.** Read it before suggesting or editing any deck.
- `_deckbuilder_db/README.md` - how the database was built, field meanings, pipeline order.
- **Starting a deck: follow "Start here: workflow for a new deck" at the top of `DECKBUILDING_NOTES.md`.**
- `_deckbuilder_db/STRATEGY_KNOWLEDGE.md` - **verified rules (anger, damage, Dragon Balls, "play" vs "place into play"), what makes a fast MPPV deck, the anger
  numbers by style, simulation results, deck-code review, mistakes to avoid and open questions.**
- `_deckbuilder_db/WORKFLOW_LESSONS.md` - **how the owner likes to work, mistakes already made and the checks that prevent them, git/sandbox/tool gotchas, how the generated
  `docs/` page stays correct, and what is still to do.** Read it before starting any larger piece of work.
- Simulating matchups: use `_deckbuilder_db/sim/` (`python -m sim run|bo3|game|coverage`, see `sim/README.md`). PanZ (Sets 1-7) only; FanZ simulation is a later TODO.
  Always run `coverage` and quote its limits with any result.
- Friends without Claude Code: `_deckbuilder_db/friends/` (pack builder, list checker, static page source). `docs/` at the repo root is the generated page, rebuilt with
  `python friends/build_site.py`; never edit it by hand. See `friends/README.md`. The repo is public and Pages serves `main` /docs; the page is expected at
  `https://raizerleaf.github.io/dbz-tcg-deckbuilder-db/` (the owner confirmed it works; this exact address was not fetched from the session, which cannot reach github.io).
- Deck codes: use `scripts/deckcode.py` (encode / decode / check). It is on `main`.
  Never retype a deck code by hand: generate it with the script and write it to a file.

## Hard rules
- Never guess card text or rules. If something is unclear or unverified, say so.
- Never modify, rename or move the original images. Write only inside `_deckbuilder_db/`.
- Ask before installing software or changing anything outside `_deckbuilder_db/`.
- Card text is literal ("a Dragon Ball in play" means anyone's; "destroy" is not "banish"; "play" is not "place into play").
- Commit and push to `main` after each batch of database changes. Other chats work here too: `git fetch` first, re-run the tests after every merge, and regenerate `docs/` if card text changed.

## Data
- `_deckbuilder_db/cards.json` (3,090 records, 5 MB; query it with Python, do not read it whole), `mps.json` (MP groups by level),
  `masteries.json`, `excluded_cards.json`.
- Use `text_current` when present (errata applied, latest print wins, PanZ-era wording), otherwise `text_as_printed`. `card_type_current` overrides `card_type`.
- Owner rulings are in `work/owner_rulings.json` and applied by `scripts/owner.py`. Do not re-ask settled rulings.
- `is_named` / `named_character` mark Named cards (possessive titles); see `NOT_NAMES` in `scripts/derive.py` for the exceptions.

## Default deck-building assumptions (unless the owner says otherwise)
Sets 1-7 only (PanZ), no PZP/OP promos, no `_RST` copies, PanZ-era rulings, Frozen list ignored, no Traits, 60-card Life Deck,
max 3 copies (printed limit wins), one Dragon Ball set per deck, Named cards must match the MP name.
Every deck should include Time Is A Warrior's Tool x1 and at least 2 Confrontation (Hero MP) or Stare Down (Villain MP).

Before giving a deck: decode and re-encode its code, then check copy counts, printed limits, Named cards, Heroes/Villains-only text, and the
60-card count with a script. **Then playtest it in the simulator** (`DECKBUILDING_NOTES.md`, "Playtesting a deck in the simulator": coverage first, add any missing MP/Mastery/card behaviors,
`python -m sim playtest <deck>` against the 10-deck roster, read a few play logs, no big batches), then `python -m sim roster add <deck>` so it can be tested against. Do not present a deck you have not checked and playtested.

## Re-running the pipeline
Run from `_deckbuilder_db/scripts` in this order: `derive.py --sets S01,...,S19,PZP,OP1,...,OP6 --out work/full`, `crd_parse.py`,
`crd.py`, `owner.py`, `mps.py`, `qa.py`. Pass `--out work/full` exactly (a path like `../work/full` writes outside `_deckbuilder_db/`).
Diff `cards.json` before and after, and commit only intended changes.
