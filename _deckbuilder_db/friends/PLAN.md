# Deck builder for friends on free Claude (or any chat AI)

## The problem
The owner's deck-building help works because Claude Code can read `cards.json`, run scripts (deck-code checker, simulator) and never relies on memory.
A friend on a free chat has none of that: no repository, no scripts, no live AI that we host. What they do have is a chat window that accepts a prompt
and, usually, file uploads (limits unknown to us: check the current free-plan limits before promising anything).

## What a chat AI can and cannot do
- It can reason about card text **if the text is in the conversation**. It will otherwise guess or misremember, so the card data has to travel with the prompt.
- It cannot run `deckcode.py`, count to 60 reliably, or check Named / Limit rules with certainty. So checking must happen **outside** the chat.
- `AGENTS.md` / `CLAUDE.md` / `GEMINI.md` are read by coding agents that work in a repository (Codex, Claude Code, Gemini CLI). A web chat does not read them.
  The equivalent for a web chat is a **prompt file plus data files** that the friend uploads or pastes. The same pack works for Claude, Gemini and ChatGPT.

## Options
| Option | What the friend does | Pros | Cons |
|---|---|---|---|
| A. Pack + prompt | Downloads files, uploads them to any chat, pastes the prompt | Works today with any AI, free, no hosting | Friend must check the list; limited by upload and context limits |
| B. Static website (GitHub Pages, no backend) | Opens a page: builds a pack for their MP, searches cards, pastes the AI's list to be checked and turned into a deck code | Closes the loop (verification and code in the browser); no server cost | Needs a public repo or Pages; hosting card text publicly is the owner's decision |
| C. Hosted AI | Chats with a bot on our page | Best experience | Needs an API key, a server and a bill. Not wanted. |
| D. Simulator in the browser | Runs `sim/` through Pyodide | Matchup feedback for friends | Heavy (5 MB data + Python runtime); do last |

## Recommendation: A first, then B
1. **Phase 1 (built):** `build_pack.py` makes the pack (instructions, rules, MPs, Masteries, cards by style) and `list_to_code.py`
   turns the AI's plain-text list into a deck code with the same legality checker the owner uses. The owner (or a friend with Claude Code) can run these today.
2. **Phase 2 (built):** a static page under `docs/` (GitHub Pages serves only that folder, so the card images in the repo are not published). It builds the card info for a character and styles (called a "pack" in code), searches
   cards, and ports `list_to_code` + the legality checks to JavaScript so a friend can paste the AI's list and get a checked deck code without Python.
3. **Phase 3 (optional):** simulator through Pyodide.

## Flow for a friend
1. Pick an MP on the page (or tell the owner). Download the pack (full, or the lighter one for that MP and 2-3 candidate styles).
2. New chat: upload the pack file (or paste it), say "follow the instructions in the file".
3. The AI asks for the MP, compares 2-3 styles with Masteries, builds the list in the plain-text format, and self-checks.
4. Paste the list into the checker (Phase 1: `list_to_code.py`, Phase 2: the web page). Fix whatever it reports, copy the deck code into the deck-builder web app.

## Decisions needed from the owner
- Public hosting: the owner said fine, but the repository is private and Pages needs a public one (or a paid plan). So: single-file page, a separate public repo with only `docs/`, or a free static host (see README). The card **images** stay out of `docs/`.
- Maintenance (owner unsure): regenerate with `python friends/build_site.py`; a test fails if `docs/` is stale. An optional GitHub Action could automate it (needs OK: it lives outside `_deckbuilder_db/`).
- Is the card-pool scope PanZ (Sets 1-7) only for friends too? The builder assumes yes; FanZ is a later TODO like the simulator.
- Do friends need to know the owner's deck-building defaults (Time Is A Warrior's Tool, 2+ Confrontation / Stare Down)? They are in the prompt now.

## Known limits
- The AI's strategy quality depends on how much of `STRATEGY_KNOWLEDGE.md` fits. The prompt carries the method and the main lessons, not every note.
- Free plans may cap upload size, file count, messages, or context. The lite pack exists for that reason. Token counts below are estimates (characters / 4).
- Anything a chat AI says about card text should be checked against the pack; the checker only verifies deck legality, not strategy.
