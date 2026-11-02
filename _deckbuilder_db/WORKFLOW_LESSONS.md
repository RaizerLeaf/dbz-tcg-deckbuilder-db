# Workflow lessons (how to work with the owner and this repository)

Written at the end of a very long session that built the deck-building notes, the simulator (`sim/`) and the friends' page (`friends/`, `docs/`). Strategy and rules are in
`STRATEGY_KNOWLEDGE.md` and `DECKBUILDING_NOTES.md`; this file is about **process**: what the owner likes, mistakes that happened and the check that now prevents each one,
tool and sandbox gotchas, and how the generated files stay correct.

## What the owner likes
- **Settled rulings are written down at once** (`DECKBUILDING_NOTES.md`, "Mechanics confirmed by the owner") and never asked again. This session: Protective only affects levelling, "your opponent destroys" counts as "your effect destroys",
  critical *damage* is not a critical damage *effect*, errata applies and the **latest print wins**, Frozen list ignored, Sets 1-7 only, Evolution P9/P10 never came out. Write the owner's own words into `work/owner_rulings.json` when it is a data ruling.
- **2-3 ranked options with reasons** (style, Mastery, why), most to least recommended, not a single answer. Teach-by-example: when they correct you ("card text is literal", "Named cards must
  match the MP"), the correction is a rule: write it into the notes so it is not asked twice.
- **Straightforward, plain wording.** They asked for the friends' page to be one linear set of steps and for jargon ("pack") to go. Test a page the way a first-time friend would read it.
- **Verified before presented.** A deck is decoded, re-encoded and checked by script before they see it. Say what you could not verify and what the model leaves out.
- **Branches for big pieces of work** (simulator, friends' page), then they say "merge it". Small notes and fixes go straight to `main`. Commit and push after each batch.
- **Other chats work in this repository at the same time.** Always `git fetch` and look at `origin/main` before editing shared files, put new knowledge in new files when possible
  (the shared notes get edited by several chats), and run the tests again after every merge: another chat's database change can make generated files stale.
- **Outward-facing or irreversible actions need their say-so** (making the repo public, publishing). They gave it explicitly; the session still could not do it (see sandbox limits).
- The brief's rule is to write only inside `_deckbuilder_db/`. The single exception, agreed with the owner, is generated `docs/` at the repo root (GitHub Pages only serves the root or `/docs`).
  One slip happened (a `friends/` folder at the root); it was moved. Ask before adding anything else outside `_deckbuilder_db/` (for example a `.github/` workflow).

## Mistakes that happened, and what prevents them now
| Mistake | Prevention |
|---|---|
| Put Goku's Search (a Named card) in a Nail deck | `deckcode.py check` flags Named cards; never hand-pick cards without `is_named` / `named_character` |
| Orange Uppercut x2 although "Limit 1" | printed limits come from `limit_per_deck`; the checker enforces them |
| "Time Is A Warrior's Tool" flagged as Named (possessive title) | `NOT_NAMES` in `derive.py`; regression note in STRATEGY_KNOWLEDGE |
| Hand-retyped a deck code and lost a card (59 cards), or added one (61 cards: an extra `PF-R129` crept in) | never retype codes; write them to a file with the script and paste from it |
| Assumed the friend's Piccolo used Composed/Revitalized, then Stoic, from memory | ask the owner or read the exported code's printings field; the owner confirmed Stoic |
| Dismissed Red for Lord Slug, missed Blue Level-1 stage-lock for Turles | compare styles by what the MP rewards and punishes, and consider sitting on one level (method in the notes) |
| Wrote a deck code from guesses: the Mastery as a name, no rarity letters, later reprints (`AW-S77`, `EV-S165`) the app did not know | the format and the first-printing rule are in `DECKBUILDING_NOTES.md`; `deckcode.py` implements them and its test round-trips the owner's codes. When a format is unknown, ask for 2-3 real exported codes and decode them before encoding anything |
| Told the owner Blue Guard's text was "the corrected wording" when it was the FanZ-era wording (the PanZ one is on the Awakening S50 image and in the Panini CRD) | check which CRD a wording comes from (`STRATEGY_KNOWLEDGE.md` section 3); `crd.py` now uses the FanZ wording only if a Set 1-7 image shows it |
| Built a card pool from the first printing and read a stale wording (Black Command, Orange Palm Blasts, Black Scout Maneuver) | the latest print wins: `text_current` carries it; a real image that prints "(Most Recent Printing)" is the MRP even when the CRD is silent |
| The cloud session was set to push to a branch while `CLAUDE.md` says push to `main`; the owner learned this late and was surprised | when the session's branch rule and `CLAUDE.md` disagree, say so in the first reply and ask which to follow; do not quietly pick one |
| Offered changes to a deck the owner said was for a friend | leave a friend's deck as it is unless asked; describe the change and let the owner decide |
| Believed "skip their next action" stops defenses | responding to an attack is not an Action (Rulebook 3.0) |
| Wrote simulator output paths with `../work/full` and created a stray `work/` outside `_deckbuilder_db/` | pass `--out work/full` exactly; check `git status` for untracked top-level folders |
| Generated `docs/` went stale after another chat changed card text | `friends/tests` has a freshness test that fails until `python friends/build_site.py` is re-run |
| Told the owner to enable GitHub Pages although the repo was private | Pages is not available for private repos on the free plan; check visibility first |

## Tool, git and sandbox gotchas
- `pkill -f "<text>"` run from the same shell command kills that shell (the command line contains the text). Find the PID with `ss -ltnp` and `kill` it.
- `git show REF:path > file` leaves an **empty file** if `git show` fails. Check the file size, and `git fetch origin <branch>:refs/remotes/origin/<branch>` first.
- `git reset -q -- $(empty list)` resets the whole index. `git add -A -- path ':(exclude)**/__pycache__/**'` can add nothing; `__pycache__/` is already in `.gitignore`, so a plain `git add -A path` is fine.
- The stop hook may say a branch has unpushed commits when only the **remote-tracking ref is missing locally** (a push of a new branch can leave none). Fix:
  `git fetch origin <branch>:refs/remotes/origin/<branch>` then `git push -u origin <branch>`.
- A merge conflict in `CLAUDE.md` is common (several chats edit it). Keep both sides' lines; re-run all tests afterwards.
- `| head` on a script that prints a lot can raise `BrokenPipeError`; harmless.
- The Claude Code session's GitHub proxy **blocks repository settings writes, the Pages API, GraphQL and `*.github.io`**. The owner must change repo visibility and Pages settings in the web UI,
  and the live page cannot be fetched from the session. Say so and give exact click-by-click steps.
- Chromium and Playwright are preinstalled: `NODE_PATH=$(npm root -g) node script.js`; `<option>` elements need `waitForSelector(..., {state:'attached'})`; look at screenshots (they show real layout problems).
  Node 22 is available for tests of browser code. Do not `pip`/`npm install` without asking.
- Serve `docs/` locally with `python3 -m http.server`; the multi-file page needs a server (it fetches JSON), `docs/deck-helper.html` works from disk.

## Generated files: keep them honest
- `docs/` and `friends/dist/` are generated. Regenerate with `python friends/build_site.py` and `python friends/build_pack.py` (from `_deckbuilder_db/`), commit them, never edit by hand.
- `python -m unittest discover -s friends/tests -t .` and `python -m unittest discover -s sim/tests -t .` (from `_deckbuilder_db/`) must pass before a push. The Python checker and the browser checker
  (`docs/core.js`) are compared by a Node test; change one and the test shows the other is out of step.
- GitHub Pages and its CDN can serve an old page for up to about 10 minutes after a push. `build_site.py` puts a version tag on script, style and data URLs; the HTML itself can still lag.

## Building something for friends who only have a free chat AI
- Web chats do not read `AGENTS.md`, `CLAUDE.md` or `GEMINI.md` (those are for coding agents that work in a repository). The equivalent is a **prompt plus data files** the friend uploads or pastes.
- The chat AI cannot run scripts or count to 60, so rule checking happens **outside** the chat (the page's "Check the deck" step / `friends/list_to_code.py`).
- Free plans limit file size and context: offer a light file (one character plus 2-3 styles, about 30,000 tokens) as well as the full one (about 70,000). Token counts are estimates (characters / 4).
- Hosting: private repos cannot use Pages on the free plan. The owner made the repo public (images and all) and serves `/docs` from `main`. `docs/deck-helper.html` is a one-file fallback.

## Simulator: how to use it honestly
- `python -m sim run A B -n 1000` for win rates, `bo3`/`game` for the play log, `coverage` for what is **not** modelled. Quote the coverage warnings with any result.
- It reproduces the earlier numbers (Wheelo V2 vs the friend's Red Piccolo about 16% for Wheelo; Red Trunks vs Orange Trunks V4 about 61% for Red). A change that moves them needs an explanation.
- A win rate here is the model's opinion under identical simple play, not a prediction of how a person would do. A loss in a matchup the model calls lopsided is not evidence of a play mistake.

## Still to do (as of this session)
- Ask the owner whether the final Nappa code (`decks/nappa_saiyan_clench.txt`) imports, and which MP name / printings the app wants; record the answer in `DECKBUILDING_NOTES.md` ("Decks on file").
- Nappa options 2 and 3 (Saiyan Dynamic, Black Devious) and the Black-based anti-anger Wheelo option are described but not built. Simulate the Wheelo Blue deck against the friend's Red Piccolo once Allies and Blue Protective are modelled.
- FanZ-era support in the simulator, the pack builder and the page (rulings, keywords, Traits, Frozen list). Everything built here is PanZ (Sets 1-7) only.
- Simulator: Allies, second-use attacks, more MPs and Masteries (Red Ascension, Blue Protective, Black Perceptive/Conflict, Saiyan Masteries), a smarter AI, calibration against real games.
- Optional: a GitHub Action that rebuilds `docs/` automatically (needs the owner's OK: it lives in `.github/`); a browser version of the simulator (Pyodide).
- Open rules questions are listed at the end of `STRATEGY_KNOWLEDGE.md` and marked **(unverified)** in the notes. Ask the owner before relying on them.
