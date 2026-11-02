# Friends: deck building with a free chat AI

Plan and reasoning: `PLAN.md`. This folder is Phase 1 (works today, no website needed). PanZ era (Sets 1-7) only; FanZ is a later TODO.

## For a friend (any chat AI: Claude, Gemini, ChatGPT)
1. Get `dist/deckbuilder_pack.md` (full, about 70,000 tokens) or a lighter pack made for your MP (about 25,000-30,000 tokens, see below).
2. Start a new chat, upload the file (or paste it) and say: *"Follow the instructions at the top of this file. I want to build a deck for <MP>."*
3. The AI compares styles and builds a list in the format shown at the top of the pack.
4. Paste the list into the checker (below), fix whatever it reports, and copy the deck code into the deck-builder web app.
Free plans may limit file size, uploads, messages or context: if the full pack is refused, use a light pack.

## For the owner / anyone with Claude Code
```
python friends/build_pack.py                                  # full pack -> friends/dist/
python friends/build_pack.py --mp Trunks --styles Red Orange  # light pack for one MP and the styles worth comparing
python friends/list_to_code.py friends/deck.txt               # deck list from the AI -> deck code + legality check (needs scripts/deckcode.py)
python -m unittest discover -s friends/tests -t .             # tests
```
Regenerate `dist/` whenever `cards.json` changes. The checker is the same legality code the owner uses (`scripts/deckcode.py`): 60 cards, copy limits, printed limits, Named cards,
Heroes/Villains only, Mastery-only cards, Allies, Dragon Ball sets, heritage lists, plus warnings for the owner's defaults. It does **not** judge strategy.

## Pack contents
`INSTRUCTIONS.md` (rules, legality, how to compare styles, output format) + MPs with every legal level printing + Masteries + cards by style (Black, Blue, Namekian, Orange, Red, Saiyan) + Freestyle
(including Allies and Dragon Balls). Each card appears once, with its current (errata-applied) text. Card images are not included.

## Known limits
- The AI can still misjudge strategy or miscount; the checker catches rule errors, not weak decks.
- MP names with an app qualifier (for example `Trunks (Awakening)`) must be written as the app shows them on the `MP:` line.
- Phase 2 (a static page under `docs/` that does all this in the browser) and Phase 3 (simulator in the browser) are not built yet.
