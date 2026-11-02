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
        w(f"| {n} | **{d['name'].replace(' Mastery','')}** `{d['id']}` | {d['style']} | {d['st']} | **{d['score']:g}** | {'**Frozen**' if d['frozen'] else 'no'} | {d['note']} |")
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
    w(f"Mostly, but not entirely. {len(frozen)} of the 18 are frozen: all six from Set 1, Namekian Restored (Set 4) and Orange Retribution (Set 7). None of the {len(fz_new)} Masteries FanZ added is frozen.")
    w("")
    w(f"- **Average score:** frozen {mean([x['score'] for x in frozen]):.2f} vs not frozen {mean([x['score'] for x in unfrozen]):.2f}.")
    sa = [x for x in rows if tier_of(x['score']) in ('S', 'A')]
    w(f"- **Top of the list:** the two best-scoring (Black Devious, Red Enraged) are both frozen. Of the {len(sa)} Masteries in Tiers S and A, {sum(x['frozen'] for x in sa)} are frozen; the two that are not are " + " and ".join(x['name'].replace(' Mastery','') for x in sa if not x['frozen']) + ".")
    w("- **Frozen but only mid-ranked:** " + ", ".join(f"{x['name'].replace(' Mastery','')} ({x['score']:g})" for x in frozen if tier_of(x['score']) == 'C') + ". On their own text these are narrow (Namekian Rejuvenation anger; a Saiyan Mastery that gives up MPPV). Set 1 being frozen in full looks like a set-wide decision more than a card-by-card power ranking, but that is my inference; the CRD gives no reason.")
    w("- **Strong and not frozen:** " + ", ".join(f"{x['name'].replace(' Mastery','')} ({x['score']:g})" for x in unfrozen if tier_of(x['score']) in ('S','A')) + " (the notes call Red Ascension the non-frozen alternative to Red Enraged).")
    w(f"- **FanZ reprints:** {len(rows) - len(never)} of the 18 got a FanZ promo reprint. The {len(never)} that never did are " + ", ".join(x['name'].replace(' Mastery','') for x in rows if not x['reprint_sets']) + (", all frozen." if all(x['frozen'] for x in rows if not x['reprint_sets']) else ".") + " Blue Protective, Namekian Knowledge and Orange Adaptive were reprinted as Set 13 promos; the Frozen List names only their Premiere printings (by card number), and the CRD does not say whether the promo printings are legal, so that is unverified.")
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
