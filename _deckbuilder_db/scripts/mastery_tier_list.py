#!/usr/bin/env python3
"""Build MASTERY_TIER_LIST.md: tier list of the 18 PanZ (Sets 1, 4, 7) Mastery cards, ranked on printed abilities only.

Scores (1-10, half points allowed) are HAND-ASSIGNED judgements from the card text (text_current when present).
The script checks every card_id, reads the Frozen flag and the FanZ counts from cards.json / masteries.json, and writes the markdown.
Run from _deckbuilder_db/scripts:  python mastery_tier_list.py
"""
import json, collections, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
CARDS = {r["card_id"]: r for r in json.load(open(ROOT / "cards.json"))}
MASTERIES = {m["name"]: m for m in json.load(open(ROOT / "masteries.json"))["masteries"]}

# (card_id, score, what the text does / why the score)
M = [
 ("S01_BST_122", 9, "ALL attacks +1 stage and +1 life card with no condition; discard a card to banish 2 from opp's discard (+ opp discards if Styled)"),
 ("S01_BST_127", 8, "Opp needs 6 anger to advance; repeatable cross-type stop (Physical stops energy, Energy stops physical); Blue discard moves anger"),
 ("S01_BST_131", 6, "Anger when your combat effects Rejuvenate/shuffle; Namek ball mills; one ball safe from critical capture. Narrow, Namekian-specific"),
 ("S01_BST_136", 7.5, "Drills survive levelling; energy attacks +1 life card; critical effect refetches a Styled Drill. Great for Drill decks, little otherwise"),
 ("S01_BST_140", 9, "Every critical effect raises anger 1; loot when you advance, draw when you lower. A full anger engine with a built-in speed-up"),
 ("S01_BST_145", 6, "Saiyan attacks raise anger and gain 3 stages on hit, but you cannot win by MPPV"),
 ("S04_STR_S05", 7, "Level up for 1 less anger (min 4); Styled hits may raise anger; discard an Endurance card for a stage attack"),
 ("S04_STR_S10", 6, "Free Ally at the start of opp's first turn; Ally safe from critical discard; Rejuvenate a banished Ally each combat"),
 ("S04_STR_S15", 7.5, "End-of-turn bottom-card pick-up; raise anger 2 by discarding a ball/Styled card to shuffle and draw. Fast but card-hungry"),
 ("S04_STR_S20", 6, "Attacks +1 stage; Rejuvenate a Drill after advancing; fetch a Styled [Continuous] Drill on a hit when you hold 2 or fewer"),
 ("S04_STR_S25", 6, "Banish a Styled card off your discard pile for +2 stages and anger denial; replay an attack from the discard pile"),
 ("S04_STR_S30", 6, "Styled hits destroy opp's Setup/Drill; mill-for-mill trade that gains stages or moves anger"),
 ("S07_DR_DR10", 7.5, "Drill deck: free Drill at opp's first turn, next Styled attack costs 0, raise anger up to 2, fetch a Drill after levelling"),
 ("S07_DR_DR15", 7, "Earth ball in combat raises anger; with 3+ Earth balls ALL attacks +2 life cards; tutors a ball. Needs the ball package"),
 ("S07_DR_DR20", 6, "Start on Level 2 but need 6 anger; attacks without 'anger' raise anger 1"),
 ("S07_DR_DR25", 7, "Any attack of 4+ life cards counts as critical damage; discard Styled for stages or anger"),
 ("S07_DR_DR30", 8, "Critical effects give stages; free anger 1 at the end of every combat; banish a card for another anger and maybe an opp skip"),
 ("S07_DR_DR5", 8.5, "ALL attacks +1 life card; discard a Styled card to draw and prevent 4 stages and 4 life cards of the next attack"),
]

# (what it does in plain words, why it earned its tier)
DESC = {
 "S01_BST_122": ("Every attack you make gets +1 stage and +1 life card of damage, always. Its Power: discard a card to banish the bottom 2 cards of your opponent's discard pile, and if the discarded card was Styled your opponent also discards a card from hand.",
   "Unconditional. It works on every attack from the first turn, in any deck, with nothing to set up, and a flat life-card bonus is the same kind of effect that puts the Set 7 Goku and Vegeta MPs at the top of the MP list. The Power adds hand and discard-pile pressure on top. It is not a 10 because it does nothing for levelling speed or defense."),
 "S01_BST_140": ("Every time you use a critical damage effect you raise your anger 1 level. When you advance you draw a card then discard a card; when you lower you may draw a card.",
   "It turns the critical effects Red already produces into levelling progress (a level costs 5 anger), and the draw/discard on level changes smooths your hand every time you move. It has no other conditions. Not a 10 because it only pays off when you get critical effects, so it is a speed engine rather than a flat bonus."),
 "S07_DR_DR5": ("Every attack you make deals +1 life card. Its Power: discard a Styled card from your hand to draw a card and prevent 4 stages and 4 life cards of damage from your opponent's next attack this combat.",
   "It is the only Mastery that has an always-on damage bonus and a real defense in the same card. The bonus is smaller than Devious (life card only, no stage) and the defense costs a card and covers one attack, which is why it sits just under the two Premiere cards at 8.5."),
 "S01_BST_127": ("Your opponent needs 6 anger to advance a personality level. Defense Power: discard a Physical Combat card to stop an energy attack, or an Energy Combat card to stop a physical attack; if the discarded card was Blue you may raise or lower a player's anger 1 level.",
   "Two defensive jobs in one card: it slows the opponent's levelling by an anger point, and it gives a repeatable stop that works with cards a deck would not normally use for that attack type. It adds no damage, so it ranks below the damage Masteries. It only affects levelling: per the owner's ruling, MPPV at Level 4 is still 5 anger."),
 "S07_DR_DR30": ("When you use a critical damage effect you gain 2 stages. At the end of every combat you may raise your anger 1 level. Power: banish the top card of your Life Deck to raise your anger 1 level; if it was Styled your opponent skips their next action this combat.",
   "Free anger at the end of each combat plus a second anger power, with or without critical hits, so it levels you steadily without needing anything to go right. It is the non-frozen alternative to Red Enraged. It sits below Enraged because Enraged's +1 per critical effect is bigger in a deck full of them, and below the damage Masteries because it adds no damage or defense; the Power also costs a Life Deck card."),
 "S04_STR_S15": ("Instant at the end of the turn: reveal the bottom card of your Life Deck and if it is Styled or a Dragon Ball you may take it (then put a card from hand on the top or bottom). Power: raise your anger 2 levels; you may discard a Dragon Ball or Styled card to shuffle your Life Deck and draw a card.",
   "Anger 2 from a single Power is the biggest single anger raise among the Sets 1-7 Masteries (only Orange Retribution matches it), and the end-of-turn pick-up adds card selection. It is held at 7.5 because it adds no damage or defense and leans on Styled cards and Dragon Balls in your hand."),
 "S01_BST_136": ("Your Drills are not discarded when you advance or lower. Your energy attacks deal +1 life card. At the end of any combat in which you used a critical damage effect, search your discard pile for a Styled Drill and place it into play.",
   "It removes the main cost of an Orange Drill deck (Drills are discarded when you advance), and gives energy attacks a flat life-card bonus. The bonus is energy attacks only and the Drill recovery needs a critical effect, and the whole card is only great in a Drill deck, so it stays at 7.5."),
 "S07_DR_DR10": ("You may not activate two Drills with the same name in a turn. At the start of your opponent's first turn you fetch a Styled non-[Continuous] Drill into play. Whenever your MP changes levels you may shuffle all your Drills back. Power: your next Styled attack costs 0 stages, raise your anger up to 2 levels, and if your MP changed levels this combat fetch a Styled Drill into play.",
   "A complete Drill engine: a free Drill, a free attack, up to 2 anger and a refetch after levelling. It has the same score as Adaptive because the power is offset by the narrowness: it only helps a Drill deck, has the same-name restriction, and does nothing for plain damage."),
 "S07_DR_DR25": ("Any of your attacks that deals at least 4 life cards of damage is considered to deal critical damage. Power: discard a card; if it was Styled you gain 6 stages or may raise or lower a player's anger 1 level.",
   "Big attacks become critical hits, which gives you the always-available critical effects (capture a Dragon Ball, discard an Ally, lower anger) for free. It adds no damage itself and needs 4+ life-card attackers, so it is a solid B rather than an A."),
 "S07_DR_DR15": ("When an Earth Dragon Ball you own enters play during combat you raise your anger 1 level. While 3 or more Earth Dragon Balls you own are in play, all your attacks deal +2 life cards. Power: if fewer than 3 of your Dragon Balls are in play, fetch one.",
   "The +2 life-card bonus is as big as anything in the S tier, and the Power fetches the balls to turn it on. The catch is the condition: it needs 3 Earth balls in play, so it takes setup and can be undone by capture or destruction. That risk keeps it at 7."),
 "S04_STR_S05": ("You need 1 less anger to advance a personality level (minimum 4). Your Styled attacks gain 'HIT: you may raise your anger 1 level'. Power: discard a Styled card with Endurance to make a non-Styled physical attack for 1 + X stages (X = the card's Endurance).",
   "Cheaper levels and anger on hits make it a levelling Mastery, in the same family as Restored and Ascension but a bit weaker: the anger on hit requires your attack to land and the Power is niche. It gives no damage or defense."),
 "S04_STR_S30": ("Your Styled attacks gain 'HIT: destroy an opponent's Setup or Drill'. Power: destroy the top card of your Life Deck to destroy the top card of your opponent's; if the opponent's was a Physical or Energy Combat card you gain 4 stages, otherwise raise a player's anger 1 level.",
   "Board disruption and a symmetric mill. The payoff depends on what happens to be on top of their deck and it spends your own Life Deck, and there is no damage, defense or levelling boost, so it is C."),
 "S04_STR_S10": ("At the start of your opponent's first turn you fetch an Ally into play at 3 stages above 0. While you control 1 Ally it cannot be discarded by critical damage effects. At the end of combat you Rejuvenate an Ally from your Banished Zone.",
   "A free Ally and some protection for it. Everything depends on how good the Allies in the deck are; the Mastery does nothing for your MP, so it is C."),
 "S01_BST_131": ("Whenever your effects during combat Rejuvenate or shuffle cards into your Life Deck, raise your anger 1 level. After a Namek Dragon Ball enters play under your control, destroy the top card of your opponent's Life Deck. While you control 1 Dragon Ball it cannot be captured by a critical damage effect.",
   "Narrow: it only pays out if you have Rejuvenate or shuffle effects and Namek Dragon Balls, and it adds no damage or defense. It is frozen, but on its own text it is a C."),
 "S04_STR_S20": ("Your attacks deal +1 stage. After your MP advances you search your discard pile for a Drill and Rejuvenate it. Power after a successful Styled attack: that attack gains 'HIT: if you control 2 or fewer Drills, fetch a Styled [Continuous] Drill into play'.",
   "+1 stage is a small bonus, the Drill recovery only happens when you advance, and the fetch needs a hit and 2 or fewer Drills. It is the weakest of the three Orange Masteries. It is not frozen."),
 "S04_STR_S25": ("When entering combat you banish the top card of your discard pile; if it was Styled, your Styled physical attacks this combat deal +2 stages and gain 'HIT: lower your opponent's anger 1 level'. Power: reveal a Styled card from hand and put it at the bottom of your Life Deck; if the top of your discard pile is an attack you may play it.",
   "Everything depends on what is on top of your discard pile, and the bonuses are small (+2 stages, 1 anger of denial). Useful tricks, but unreliable, so C."),
 "S07_DR_DR20": ("You may start the game on Level 2. You need 6 anger to advance. Your Styled attacks without 'anger' printed in the text box gain 'raise your anger 1 level'.",
   "It trades a slower level cost (6 anger) for anger on most attacks and a Level 2 start, which roughly cancel out. There is no damage, defense or Power, so it adds little over the MP itself."),
 "S01_BST_145": ("You cannot win by MPPV. Your Saiyan Style attacks gain 'Raise your anger 1 level. HIT: gain 3 stages'. Whenever you Rejuvenate a Saiyan Style card you raise your anger 1 level.",
   "Anger and stages on every Saiyan attack, but giving up MPPV removes one of the main ways to win, and it only helps Saiyan Style cards. The drawback outweighs the speed, so it is a C even though it is frozen."),
}

# On the FanZ CRD v1.15 Frozen List page, only these two entries carry the light-blue "Panini additions" highlight (checked by looking at the PDF page image;
# the text extraction cannot see it). The other frozen Masteries are unhighlighted, i.e. on the list through the fan-run continuation.
PANINI_HIGHLIGHT = {"Black Devious Mastery", "Red Enraged Mastery"}
TIERS = [("S", 8.5), ("A", 7.5), ("B", 7.0), ("C", 0)]


def tier_of(x):
    for t, lo in TIERS:
        if x >= lo: return t


def main():
    rows = []
    for cid, sc, note in M:
        r = CARDS.get(cid)
        if not r: print("missing", cid); sys.exit(1)
        if (r["card_type_current"] or r["card_type"]) != "Mastery" or not (r["set_number"] and r["set_number"] <= 7):
            print("bad", cid); sys.exit(1)
        m = MASTERIES[r["card_name"]]
        rows.append(dict(id=cid, name=r["card_name"], style=r["style"], st=r["set_number"], score=sc, note=note, frozen=m["frozen"],
                         reprint_sets=sorted({p["set_number"] for p in m["printings"] if p["set_number"] and p["set_number"] >= 8})))
    # every PanZ mastery name must be covered
    panz_names = {r["card_name"] for r in CARDS.values() if (r["card_type_current"] or r["card_type"]) == "Mastery" and r["set_number"] and r["set_number"] <= 7}
    assert panz_names == {x["name"] for x in rows}, panz_names ^ {x["name"] for x in rows}
    rows.sort(key=lambda d: (-d["score"], d["name"]))

    # FanZ counts
    fz_all = [r for r in CARDS.values() if (r["card_type_current"] or r["card_type"]) == "Mastery" and not (r["set_number"] and r["set_number"] <= 7)]
    fz_new = sorted({r["card_name"] for r in fz_all} - panz_names)
    new_by_set = collections.defaultdict(list)
    for r in fz_all:
        if r["card_name"] in fz_new and r["collection"] == "booster":
            new_by_set[r["set_number"]].append(r["card_name"])
    reprint_sets = collections.defaultdict(list)
    for r in fz_all:
        if r["card_name"] in panz_names: reprint_sets[r["set_number"]].append(r["card_name"])
    fz_frozen = [n for n in fz_new if MASTERIES[n]["frozen"]]
    never = [x["name"] for x in rows if not x["reprint_sets"]]

    def mean(v): return sum(v) / len(v)
    frozen = [x for x in rows if x["frozen"]]
    unfrozen = [x for x in rows if not x["frozen"]]

    out = []
    w = out.append
    w("# Mastery tier list, Sets 1-7 (PanZ), ranked on printed abilities only")
    w("")
    w("Generated by `scripts/mastery_tier_list.py` (scores and notes live in that file; edit there and re-run). Text is `text_current` when present, otherwise `text_as_printed`.")
    w("")
    w("## How to read this")
    w("- **18 Masteries in 3 stacks:** Set 1 Premiere, Set 4 Evolution and Set 7 Awakening each print six, one per Style (Black, Blue, Namekian, Orange, Red, Saiyan).")
    w("- **Ranked on abilities only,** the same way as the MP list: a hand-assigned 1-10 score from the printed text (half points allowed). 9-10 = changes every turn with no real condition; 7-8 = clearly strong; 6 = solid but narrow or needs a specific package; 1-5 = weak. My judgement, not a simulation, so treat gaps under about 0.5 as ties.")
    w("- **Tiers:** S = 8.5+, A = 7.5-8.49, B = 7.0-7.49, C = under 7.0. A Mastery is judged on its own text; whether it fits a deck (Drills, Dragon Balls, Allies) is noted but not scored.")
    w("- **Frozen** = on the Frozen List in the FanZ CRD v1.15 ('Cards on this list may not be used in any official FanZ tournament'). Frozen is shown for information; it is not used in the score. A frozen card is not dead: it is only illegal in that tournament format. This repo's default deck rules ignore the Frozen list.")
    w("")
    w("## Tier list")
    w("")
    cur = None
    n = 0
    for d in rows:
        t = tier_of(d["score"])
        if t != cur:
            if cur is not None: w("")
            cur = t; n = 0
            w(f"### Tier {t}")
            w("")
            w("| # | Mastery | Style | Set | Score | Frozen | What it does |")
            w("|---|---|---|---|---|---|---|")
        n += 1
        w(f"| {n} | **{d['name'].replace(' Mastery','')}** `{d['id']}` | {d['style']} | {d['st']} | **{d['score']:g}** | {('**Frozen** (Panini-marked)' if d['name'] in PANINI_HIGHLIGHT else '**Frozen** (FanZ-added)') if d['frozen'] else 'no'} | {d['note']} |")
    w("")
    w("## Why each Mastery earned its spot")
    w("")
    w("What puts a Mastery in a tier: **S** = a flat, unconditional damage bonus (or an anger engine with no setup) that works in any deck; **A** = strong effects that either need a specific kind of deck (Drills) or only help levelling or defense; **B** = good but conditional (a condition to meet or a smaller bonus); **C** = narrow, situational, or carries a real drawback.")
    w("")
    tdesc = {r["id"]: r for r in rows}
    cur = None
    for d in rows:
        t = tier_of(d["score"])
        if t != cur:
            cur = t
            w(f"### Tier {t}")
            w("")
        what, why = DESC[d["id"]]
        fr = ("frozen, Panini-marked" if d["name"] in PANINI_HIGHLIGHT else "frozen, FanZ-added") if d["frozen"] else "not frozen"
        w(f"**{d['name']}** (Set {d['st']}, score {d['score']:g}, {fr})")
        w(f"- *What it does:* {what}")
        w(f"- *Why it is here:* {why}")
        w("")
    w("## By stack")
    w("")
    w("| Stack | Mean | Masteries (score) | Frozen |")
    w("|---|---|---|---|")
    for st, nm in ((1, "Set 1 Premiere"), (4, "Set 4 Evolution"), (7, "Set 7 Awakening")):
        v = [x for x in rows if x["st"] == st]
        w(f"| {nm} | **{mean([x['score'] for x in v]):.2f}** | " + ", ".join(f"{x['name'].replace(' Mastery','')} {x['score']:g}" for x in v) + f" | {sum(x['frozen'] for x in v)} of {len(v)} |")
    w("")
    w("By Style (three Masteries each):")
    w("")
    for sty in ("Black", "Blue", "Namekian", "Orange", "Red", "Saiyan"):
        v = sorted([x for x in rows if x["style"] == sty], key=lambda d: d["st"])
        w(f"- **{sty}** (mean {mean([x['score'] for x in v]):.2f}): " + " -> ".join(f"{x['name'].replace(' Mastery','').split(' ',1)[1]} (Set {x['st']}) {x['score']:g}{' [frozen]' if x['frozen'] else ''}" for x in v))
    w("")
    w("## Are the frozen Masteries the best ones?")
    w("")
    w(f"Mostly, but not entirely. {len(frozen)} of the 18 are frozen: all six from Set 1 (only Devious and Enraged were Panini's own freezes, see below), Namekian Restored (Set 4) and Orange Retribution (Set 7). None of the {len(fz_new)} Masteries FanZ added is frozen.")
    w("")
    w(f"- **Average score:** frozen {mean([x['score'] for x in frozen]):.2f} vs not frozen {mean([x['score'] for x in unfrozen]):.2f}.")
    sa = [x for x in rows if tier_of(x['score']) in ('S', 'A')]
    w(f"- **Top of the list:** the two best-scoring (Black Devious, Red Enraged) are both frozen. Of the {len(sa)} Masteries in Tiers S and A, {sum(x['frozen'] for x in sa)} are frozen; the two that are not are " + " and ".join(x['name'].replace(' Mastery','') for x in sa if not x['frozen']) + ".")
    w("- **Frozen but only mid-ranked:** " + ", ".join(f"{x['name'].replace(' Mastery','')} ({x['score']:g})" for x in frozen if tier_of(x['score']) == 'C') + ". On their own text these are narrow (Namekian Rejuvenation anger; a Saiyan Mastery that gives up MPPV). By the highlighting, those two were added to the list by FanZ, not Panini; the CRD gives no reason for any entry.")
    w("- **Strong and not frozen:** " + ", ".join(f"{x['name'].replace(' Mastery','')} ({x['score']:g})" for x in unfrozen if tier_of(x['score']) in ('S','A')) + " (the notes call Red Ascension the non-frozen alternative to Red Enraged).")
    w(f"- **FanZ reprints:** {len(rows) - len(never)} of the 18 got a FanZ promo reprint. The {len(never)} that never did are " + ", ".join(x['name'].replace(' Mastery','') for x in rows if not x['reprint_sets']) + (", all frozen." if all(x['frozen'] for x in rows if not x['reprint_sets']) else ".") + " Blue Protective, Namekian Knowledge and Orange Adaptive were reprinted as Set 13 promos; the Frozen List names only their Premiere printings (by card number), and the CRD does not say whether the promo printings are legal, so that is unverified.")
    pan = [x for x in rows if x["name"] in PANINI_HIGHLIGHT]
    fzf = [x for x in frozen if x["name"] not in PANINI_HIGHLIGHT]
    w(f"- **Who froze them:** on the CRD's Frozen List page, Panini's own entries are marked in light blue, and only Black Devious and Red Enraged are marked. The other six frozen Masteries are unmarked, which I read as FanZ additions. The two Panini-marked ones are the two top-scoring Masteries ({mean([x['score'] for x in pan]):.1f}); the six FanZ-added average {mean([x['score'] for x in fzf]):.2f}. (From the highlighting on the PDF page; the Panini Final CRD itself prints no Frozen List, only the Legacy Thawing Bonus below.)")
    w("- **Orange:** the list names Orange Adaptive and Orange Retribution only. Orange Adept (Set 4) is not on it, and neither are the four new FanZ Orange Masteries, so on these sources not every Orange Mastery is frozen. If you know of a PanZ-era source that freezes Orange Adept, I have not seen it and have not changed anything.")
    w("- **Legacy Thawing Bonus:** the CRD's (defunct for FanZ) rule lets listed MPs use frozen Black Devious or Red Enraged in non-FanZ events; it names only those two Masteries.")
    w("")
    w("## FanZ Masteries")
    w("")
    w(f"**FanZ added {len(fz_new)} new Masteries** (not rated here), in four sets, one per Style each time:")
    w("")
    for st in sorted(new_by_set):
        w(f"- **Set {st}** ({len(new_by_set[st])}): " + ", ".join(sorted(x.replace(' Mastery', '') for x in new_by_set[st])))
    w("")
    reps = sum(len(v) for v in reprint_sets.values())
    w(f"FanZ also reprinted {len(rows) - len(never)} of the 18 PanZ Masteries as promos ({reps} cards: " + ", ".join(f"Set {s} x{len(v)}" for s, v in sorted(reprint_sets.items())) + "). Counting is by distinct Mastery name, from `cards.json`; the FanZ new Masteries total across all printings is " + f"{sum(1 for r in fz_all if r['card_name'] in fz_new)} cards (each also reprinted once as a promo in Set 15 or 17, except Set 16 and Set 19's, which have no reprint).")
    w("")
    open(ROOT / "MASTERY_TIER_LIST.md", "w").write("\n".join(out) + "\n")
    print("\n".join(out))


main()
