#!/usr/bin/env python3
"""Build MP_TIER_LIST.md: a tier list of every PanZ (Sets 1-7) Main Personality, by character.

The 1-10 level scores below are HAND-ASSIGNED judgements made from the printed ability text
(text_current when present, else text_as_printed). Power stages and PUR are deliberately ignored.
This script only (a) checks every card_id exists and is the stated level, (b) does the arithmetic,
(c) computes a few objective text counts for the power-creep section, (d) writes the markdown.

Run from _deckbuilder_db/scripts:  python mp_tier_list.py
"""
import json, re, collections, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
CARDS = {r["card_id"]: r for r in json.load(open(ROOT / "cards.json"))}

# (character, stack label, alignment, set, [(card_id, score, short note) for L1..L4])
STACKS = [
 ("Android 13", "Set 6 Vengeance", "Villain", 6, [
   ("S06_BST_61", 4, "Android plays raise anger; 4-stage attack fetches an Android Ally"),
   ("S06_BST_62", 5, "Banish Androids 14+15 to advance; attack makes opp skip an action"),
   ("S06_BST_63", 7, "Opp loses 4 stages and skips first action; 7-stage attack shuts off opp [Continuous]"),
   ("S06_BST_64", 6, "Non-Styled attacks make opp skip an action; scales with Androids in discard")]),
 ("Android 16", "Set 5 Perfection", "Villain", 5, [
   ("S05_BST_69", 6, "Mills non-attackers; ALL attacks (both players) +1 life card"),
   ("S05_BST_70", 5, "Your attacks +1 life card; every Life Deck gets Endurance 1 (symmetric)"),
   ("S05_BST_71", 7, "Your attacks +1 life card; only your deck gets Endurance 1; tutor alignment card"),
   ("S05_BST_72", 8, "Your attacks +2 life cards; Rejuvenate 2 / banish 2 off alignment-restricted plays")]),
 ("Android 17", "Set 4 Evolution starter", "Villain", 4, [
   ("S04_STR_S21", 4, "Attack + fetch Android 17's Van"),
   ("S04_STR_S22", 5, "Attack destroys an Ally; hit refetches the Van"),
   ("S04_STR_S23", 8, "6-life-card energy attack, unpreventable if Van is in play"),
   ("S04_STR_S24", 5, "Physical attacks scale with Allies in opp's Banished Zone; fetch Van")]),
 ("Android 18", "Set 4 Evolution starter", "Villain", 4, [
   ("S04_STR_S26", 4, "Locks opp's first physical attack from modification; 0-damage attack cycles hand"),
   ("S04_STR_S27", 6, "Opp's physical attacks cannot be modified; your attacks +1 life card"),
   ("S04_STR_S28", 5, "Same lock at any power; 0-damage attack reorders top 6 and draws"),
   ("S04_STR_S29", 9, "Opp's physical attacks cost +2; a hit sets opp's MP to 0 power")]),
 ("Android 19", "Set 4 Evolution booster", "Villain", 4, [
   ("S04_BST_85", 6, "Gain stages after taking life-card damage; next Styled attack counts as critical"),
   ("S04_BST_86", 5, "Gain stages after damage; cheap 4-stage energy attack taxes opp"),
   ("S04_BST_87", 5, "Gain 2 stages after damage; fetch an MP-attachment card after a stop"),
   ("S04_BST_88", 7, "Gain 10 stages; with your card on opp's MP: +4 life cards and unpreventable")]),
 ("Android 20", "Set 4 Evolution booster", "Villain", 4, [
   ("S04_BST_89", 4, "Reveal opp hand; pay 3 stages to shrink opp and fetch a Drill"),
   ("S04_BST_90", 6, "Free Drill fetch each combat; Rejuvenate 3 at end of combat with a Drill"),
   ("S04_BST_91", 6, "Fetch a Drill from anywhere each combat; mills by Drill count"),
   ("S04_BST_92", 7, "Repeatable full prevention of energy attacks (costs 2 of your deck); Drill-mill")]),
 ("Broly", "Set 6 Vengeance", "Villain", 6, [
   ("S06_BST_65", 6, "Opp loses 5 stages when it advances; attack banishes with 2 attack cards"),
   ("S06_BST_66", 6, "Opp loses 7 stages when it advances; physical +2 stages; banish a Setup/Drill"),
   ("S06_BST_67", 6, "All opp personalities lose 7 stages on advance; physical +3 stages"),
   ("S06_BST_68", 8, "No Endurance for opp; physical +4 stages banished; banish up to everything on board")]),
 ("Captain Ginyu", "Set 1 Premiere", "Villain", 1, [
   ("S01_BST_06", 6, "4-life-card energy attack that also fetches an Ally into play"),
   ("S01_BST_07", 7, "4-life-card energy attack, Ally from discard, anger per Ginyu Force Ally"),
   ("S01_BST_66", 8, "ALL attacks +2 life cards; Ginyu Force Allies always act and cannot be discarded"),
   ("S01_BST_67", 8, "ALL attacks +X life cards, X = your Allies in play; Allies always act")]),
 ("Cell", "Set 5 Perfection Deck Reveal", "Villain", 5, [
   ("S05_DR_DR1", 3, "Self-mill attack, +3 stages; small payoff"),
   ("S05_DR_DR2", 6, "Opp's non-Styled attacks cost +1; tutor a Styled card each combat"),
   ("S05_DR_DR3", 9, "7-life-card physical attack that cannot be prevented; can advance you after"),
   ("S05_DR_DR4", 5, "Tutor a Styled card each combat; once-per-game lower-both-MPs")]),
 ("Cell", "Set 7 Awakening Deck Reveal", "Villain", 7, [
   ("S07_DR_DR11", 6, "Fetch a Cell Jr. Ally each combat; shuffle Ally to move anger 2"),
   ("S07_DR_DR12", 6, "Fetch Cell Jr. from deck/discard/banished; destroy 3 of opp's deck"),
   ("S07_DR_DR13", 7, "Fetch a Saiyan Ally; with 2+ Allies destroy 5 of opp's deck; AT +6 stages"),
   ("S07_DR_DR14", 5, "Tutor a Styled card each combat; once-per-game lower-both-MPs")]),
 ("Cell Jr.", "Set 7 Awakening", "Villain", 7, [
   ("S07_BST_68", 5, "Attack unstoppable by discarding a Cell Jr. Ally; hit fetches a [Continuous] card"),
   ("S07_BST_69", 6, "Once per combat discard a Cell Jr. Ally to stop an attack"),
   ("S07_BST_70", 7, "Repeatable stops by Rejuvenating Cell Jr. Allies; refills them each turn"),
   ("S07_BST_71", 7, "Repeatable: banish a Cell Jr. Ally to destroy 3 of opp's deck; non-AT physical +3 stages")]),
 ("Cooler", "Set 6 Vengeance", "Villain", 6, [
   ("S06_BST_69", 5, "Setup lock on first action; loot + mill + Rejuvenate 1"),
   ("S06_BST_70", 8, "5-life-card physical attack with Rejuvenate 2; anger whenever you take damage"),
   ("S06_BST_71", 8, "6-life-card energy attack with Rejuvenate 3; Rejuvenate 1 after every damage"),
   ("S06_BST_72", 6, "Both players' anger gains Rejuvenate you; once-per-game Rejuvenate 7 and end combat")]),
 ("Dr. Wheelo", "Set 3 Movie Collection", "Villain", 3, [
   ("S03_BST_61", 6, "Trade 1 of your cards for 2 of opp's; sets anger to 3"),
   ("S03_BST_62", 8, "ALL attacks +2 life cards; opp mills whenever you stop an attack"),
   ("S03_BST_63", 7, "Mill 2 + Rejuvenate 2 after a hit; every destroy effect +1"),
   ("S03_BST_64", 6, "Every destroy effect +2 and Rejuvenate 2 (needs other mill)")]),
 ("Frieza", "Set 1 Premiere", "Villain", 1, [
   ("S01_STR_S17", 5, "Stopping an attack may raise anger"),
   ("S01_STR_S18", 5, "Discard a card to copy opp's last attack +2 stages"),
   ("S01_STR_S19", 7, "ALL attacks +3 stages; keeps Level 1 [Continuous]"),
   ("S01_STR_S20", 5, "Mill 4 + fetch a Frieza Named card; keeps Level 2 power")]),
 ("Garlic Jr.", "Set 3 Movie Collection", "Villain", 3, [
   ("S03_BST_65", 8, "Opp attacks -1 life card; 2 less anger per level; raise anger each turn"),
   ("S03_BST_66", 7, "Opp attacks -2 life cards; Dragon Ball reveals raise anger"),
   ("S03_BST_67", 8, "Opp attacks -2 life cards/-2 stages; every anger raise captures a Dragon Ball"),
   ("S03_BST_68", 4, "DRAWBACK: opp attacks +3 life cards; Dragon Balls safe, capture on anger loss")]),
 ("Gohan", "Set 1 Premiere", "Hero", 1, [
   ("S01_STR_S09", 6, "Styled attacks +up to 2 life cards by milling yourself"),
   ("S01_STR_S10", 7, "Styled attacks +2 life cards; Rejuvenate on critical"),
   ("S01_STR_S11", 7, "6-stage attack; lower anger for +2 life cards per level lowered"),
   ("S01_STR_S12", 8, "Styled attacks +3 life cards; recycles anger cards")]),
 ("Gohan", "Set 7 Awakening Deck Reveal", "Hero", 7, [
   ("S07_DR_DR16", 6, "All attacks Styled; banished Ally raises anger; AT +2 life card attack"),
   ("S07_DR_DR17", 5, "All attacks Styled; tutor Styled attack/defense; may lower instead of advance"),
   ("S07_DR_DR18", 5, "All attacks Styled +2 stages; attack that banishes Setup/Drill/Ally"),
   ("S07_DR_DR19", 8, "Attacks Styled, only stoppable by same-type cards; next attack costs 0 and is unpreventable")]),
 ("Goku", "Set 1 Premiere", "Hero", 1, [
   ("S01_STR_S05", 6, "3-life-card energy attack that fetches a Drill"),
   ("S01_STR_S06", 6, "Free Drill fetch every combat; may lower a level"),
   ("S01_STR_S07", 7, "5-life-card energy attack; Drill/Setup from discard; Rejuvenate 5 Drills"),
   ("S01_STR_S08", 6, "Search deck/discard/banished for up to 5 Drills and play them (errata)")]),
 ("Goku", "Set 4 Evolution starter", "Hero", 4, [
   ("S04_STR_S06", 5, "Physical attack; Ally swap; hit stacks top of deck with an Ally"),
   ("S04_STR_S07", 7, "ALL attacks +2 life cards; protect an Ally from leaving play"),
   ("S04_STR_S08", 8, "6-life-card energy attack that fetches an Ally that always acts"),
   ("S04_STR_S09", 7, "Ally from anywhere at top stage; its attacks +4 life cards")]),
 ("Goku", "Set 7 Awakening Deck Reveal", "Hero", 7, [
   ("S07_DR_DR1", 7, "ALL attacks +1 life card; draw a card each combat"),
   ("S07_DR_DR2", 8, "Your attacks +1 / opp's -1 life card; discard a card for a critical damage effect"),
   ("S07_DR_DR3", 8, "ALL attacks +2 life cards; attack AT +2; draw from discard"),
   ("S07_DR_DR4", 9, "Your attacks +2 / opp's -2 life cards; tutor a Styled card every turn")]),
 ("Hercule", "Set 7 Awakening Deck Reveal", "Hero", 7, [
   ("S07_DR_DR21", 3, "Owner ruling: the +100 stages is nullified by the next sentence (own attacks cannot be modified by your effects), so it is gag text; left with a 1-stage attack, +5 stages, Dynamite Kick fetch, and no energy attacks in deck"),
   ("S07_DR_DR22", 7, "Opp's attacks -3 stages and -3 life cards; no Continuous Drills"),
   ("S07_DR_DR23", 6, "Opp cannot lower you; damage modifiers doubled; Named cards raise anger on hit"),
   ("S07_DR_DR24", 6, "Your attacks +2 life cards; Named cards mill opp and lower both anger")]),
 ("Krillin", "Set 1 Premiere", "Hero", 1, [
   ("S01_STR_S13", 8, "4-life-card energy attack; next hand discard = critical effect + 2 anger"),
   ("S01_STR_S14", 6, "4-life-card energy attack; hit makes opp discard"),
   ("S01_STR_S15", 8, "Energy attack for 9 minus cards in opp's hand life cards"),
   ("S01_STR_S16", 6, "Your first Styled attack each turn cannot be stopped")]),
 ("Lord Slug", "Set 3 Movie Collection", "Villain", 3, [
   ("S03_BST_69", 6, "Dragon Ball engine: anger per ball, refetches a ball each combat"),
   ("S03_BST_70", 4, "Plain AT +3 stage attack, Rejuvenate 2"),
   ("S03_BST_71", 4, "All attacks +2 stages; doubles discard-shuffle effects"),
   ("S03_BST_72", 5, "No MPPV; drop a level or fetch a Dragon Ball each combat")]),
 ("Master Roshi", "Set 5 Perfection", "Hero", 5, [
   ("S05_BST_61", 8, "Put a Setup/Drill into play to prevent all damage from an attack, +2 anger"),
   ("S05_BST_62", 7, "Return a Setup/Drill to prevent all damage from an attack; anger on shuffle"),
   ("S05_BST_63", 6, "Opp plays with hand revealed; Setup/Drill recursion; mill on Rejuvenate"),
   ("S05_BST_64", 6, "Hijack opp's first tutor each turn; banish a Setup/Drill to mill 4")]),
 ("Mercenary Tao", "Set 7 Awakening", "Villain", 7, [
   ("S07_BST_72", 5, "Anger when opp Ally milled; Rejuvenate on stop; loot"),
   ("S07_BST_73", 6, "Each attack mills 1; 1-life-card attack, hit makes next attack unstoppable"),
   ("S07_BST_74", 6, "Stopped attacks banish opp's top card; next non-Styled attack unstoppable"),
   ("S07_BST_75", 7, "Each attack banishes opp's top card; hand-look and banish a card")]),
 ("Nail", "Set 2 Heroes & Villains", "Hero", 2, [
   ("S02_BST_01", 6, "Physical attack AT +2 life cards; mills if stopped"),
   ("S02_BST_02", 5, "Opp mills 2 when it stops you; Endurance use is punished"),
   ("S02_BST_61", 5, "All attacks +3 stages; Dragon Ball tricks, +1 anger"),
   ("S02_BST_62", 5, "7-stage attack, hit uses a Dragon Ball's immediate effect")]),
 ("Nappa", "Set 2 Heroes & Villains", "Villain", 2, [
   ("S02_BST_03", 5, "3-stage attack that destroys an opp Ally"),
   ("S02_BST_04", 4, "Opp loses 1-2 stages whenever you attack"),
   ("S02_BST_63", 5, "7-stage attack, hit banishes a Drill or Ally"),
   ("S02_BST_64", 6, "All attacks +4 stages; unpreventable once opp is at 0")]),
 ("Piccolo", "Set 1 Premiere", "Hero", 1, [
   ("S01_STR_S21", 7, "3-life-card energy attack for 1 stage + Rejuvenate 1"),
   ("S01_STR_S22", 8, "Discard to Rejuvenate 2 + opp mills 2; Styled discard adds draw + critical effect"),
   ("S01_STR_S23", 8, "ALL attacks +2 life cards; critical damage fetches a Dragon Ball"),
   ("S01_STR_S24", 8, "7-life-card energy attack; opp needs 7+ life cards to crit you")]),
 ("Piccolo", "Set 4 Evolution starter", "Hero", 4, [
   ("S04_STR_S11", 6, "Anger on stage gain and combat Rejuvenate"),
   ("S04_STR_S12", 5, "AT +4 stage attack, rearrange a Styled card"),
   ("S04_STR_S13", 5, "7-stage attack, hit swaps/captures a Dragon Ball"),
   ("S04_STR_S14", 6, "Opp loses ball immediates; Endurance scales with balls; replay banished ball")]),
 ("Raditz", "Set 2 Heroes & Villains", "Villain", 2, [
   ("S02_BST_05", 5, "1-life-card attack; digs 2 cards, +1 anger"),
   ("S02_BST_06_225601", 5, "Setups/Drills mill opp and raise anger in combat"),
   ("S02_BST_65", 5, "Opp discards a random card each time you enter combat"),
   ("S02_BST_66", 5, "Setups/Drills Rejuvenate a discard card; critical effect fetches a Setup/Drill")]),
 ("Tenshinhan", "Set 2 Heroes & Villains", "Hero", 2, [
   ("S02_BST_07", 4, "Banish top card to tutor a Named card"),
   ("S02_BST_06_00168a", 6, "Attacks +1 life card; Rejuvenate after a critical effect"),
   ("S02_BST_67", 7, "5-life-card energy attack; banish 8 discards to raise anger 6"),
   ("S02_BST_68", 8, "Your first attack each combat is used twice")]),
 ("Trunks", "Set 1 Premiere", "Hero", 1, [
   ("S01_BST_04", 4, "Look at/reorder top 4 each combat; banish opp discard card"),
   ("S01_BST_05", 5, "Reorder top 4 of ANY deck; banish opp discard card"),
   ("S01_BST_64", 5, "Reorder top 6 of your deck; draw"),
   ("S01_BST_65", 5, "Reorder top 6 of any deck each combat")]),
 ("Trunks", "Set 4 Evolution starter", "Hero", 4, [
   ("S04_STR_S01", 4, "AT +1 attack; opp skips action if stopped"),
   ("S04_STR_S02", 5, "8-stage sword attack (only if no attack from hand yet)"),
   ("S04_STR_S03", 6, "Tutor Styled/Sword attack from discard; opp skips an action (errata)"),
   ("S04_STR_S04", 6, "ALL attacks +5 stages")]),
 ("Trunks", "Set 7 Awakening Deck Reveal", "Hero", 7, [
   ("S07_DR_DR26", 8, "Anger raised during combat is doubled"),
   ("S07_DR_DR27", 8, "Named plays give a critical effect; defense stops physical and fuels anger"),
   ("S07_DR_DR28", 5, "All attacks +2 stages; 6-stage attack costs you an action"),
   ("S07_DR_DR29", 7, "Sword attacks unstoppable and raise anger; skip 2 actions for 2 anger")]),
 ("Turles", "Set 3 Movie Collection", "Villain", 3, [
   ("S03_BST_73", 6, "Styled attacks +2 stages and unpreventable"),
   ("S03_BST_74", 7, "5-stage unpreventable energy attack; hit taxes opp or gives anger+critical"),
   ("S03_BST_75", 6, "All attacks +3 stages and unpreventable; trims opp's discard"),
   ("S03_BST_76", 8, "Attack for X stages AND X life cards (X = opp stages above 0); no Endurance")]),
 ("Vegeta", "Set 1 Premiere (Villain)", "Villain", 1, [
   ("S01_STR_S01", 7, "Every attack gains 'HIT: raise your anger 1'"),
   ("S01_STR_S02", 6, "4-stage attack; anger-raising attacks +1 stage/+1 life card this combat"),
   ("S01_STR_S03", 8, "Anger-raising attacks +3 stages and +3 life cards"),
   ("S01_STR_S04", 5, "AT +6 stages; lower anger 1 to draw")]),
 ("Vegeta", "Set 4 Evolution starter (Hero)", "Hero", 4, [
   ("S04_STR_S16", 4, "Convert Styled life-card damage to stages; reveal instead of discard"),
   ("S04_STR_S17", 5, "Same conversion permanently; 4-life-card attack"),
   ("S04_STR_S18", 4, "Convert either direction; reveal instead of discard"),
   ("S04_STR_S19", 6, "First Styled physical attack unstoppable; first energy attack fetches a physical")]),
 ("Vegeta", "Set 7 Awakening Deck Reveal (Hero)", "Hero", 7, [
   ("S07_DR_DR6", 7, "Non-Styled attacks +2 life cards; cheap 1-life-card attack"),
   ("S07_DR_DR7", 7, "Non-Styled +1 life card and unpreventable; anger + stages on demand"),
   ("S07_DR_DR8", 9, "Non-Styled +3 life cards; first stopped one is used twice; opp passes on arrival"),
   ("S07_DR_DR9", 10, "Non-Styled attacks cannot be stopped and +3 life cards; opp passes on arrival")]),
 ("Yamcha", "Set 5 Perfection", "Hero", 5, [
   ("S05_BST_65", 5, "2-life-card energy attack; lowers opp anger; hit stops next physical attack"),
   ("S05_BST_66", 5, "Attacks cost -1; lower opp anger 1 each combat; recur energy attack"),
   ("S05_BST_67", 7, "Energy attacks -1 cost and unpreventable; draw + lower opp anger 2"),
   ("S05_BST_68", 9, "Attacks cost -3 and +3 life cards; 4-life-card energy attack")]),
]

# single alternate printings of one level that can be mixed into the character's stacks (same alignment)
ALTS = [
 ("Frieza", "Villain", 2, "S03_PRO_P16", 7, "Set 3 promo Golden: AT-life-card attack, +3 stages, Frieza Named -> critical effect"),
 ("Gohan", "Hero", 1, "S06_BST_73", 5, "Set 6 To the Rescue: fetch an Ally; 3+ Allies advances you"),
 ("Goku", "Hero", 1, "S01_PRO_P5", 4, "Set 1 promo Super Saiyan God: mill 1 to draw 1"),
 ("Krillin", "Hero", 2, "S06_BST_74", 4, "Set 6 Quick: pay 2 stages for +2 stages; 4-stage unmodifiable attack"),
 ("Master Roshi", "Hero", 1, "S06_BST_75", 4, "Set 6 Restrained: Turtle Ally; Setup/Drill banish mills"),
 ("Trunks", "Hero", 1, "S06_BST_76", 6, "Set 6 Protective: Sword plays Rejuvenate; free Drill fetch; keeps Drills"),
]

TIERS = [("S", 7.5), ("A", 6.75), ("B", 6.0), ("C", 5.25), ("D", 0)]


def check():
    errs = []
    for ch, label, al, st, lv in STACKS:
        for i, (cid, sc, _) in enumerate(lv, 1):
            r = CARDS.get(cid)
            if not r: errs.append(f"missing {cid}"); continue
            if r["card_name"] != ch or r["level"] != i or r["alignment"] != al or r["set_number"] != st:
                errs.append(f"mismatch {cid}: {r['card_name']} L{r['level']} {r['alignment']} S{r['set_number']} vs {ch} L{i} {al} S{st}")
    for ch, al, i, cid, sc, _ in ALTS:
        r = CARDS.get(cid)
        if not r or r["card_name"] != ch or r["level"] != i or r["alignment"] != al:
            errs.append(f"bad alt {cid}")
    return errs


def tier_of(x):
    for t, lo in TIERS:
        if x >= lo: return t


def main():
    errs = check()
    if errs:
        print("\n".join(errs)); sys.exit(1)
    chars = collections.OrderedDict()
    for s in STACKS:
        chars.setdefault(s[0], []).append(s)
    result = []
    for ch, stacks in chars.items():
        best = None
        for al in sorted({s[2] for s in stacks}):
            per = {}
            picks = {}
            for lvl in range(1, 5):
                cands = [(s[4][lvl-1][1], s[4][lvl-1][0], s[1]) for s in stacks if s[2] == al]
                cands += [(a[4], a[3], "alt") for a in ALTS if a[0] == ch and a[1] == al and a[2] == lvl]
                sc, cid, lab = max(cands)
                per[lvl] = sc; picks[lvl] = (cid, lab, sc)
            mean = sum(per.values()) / 4
            if best is None or mean > best[0]:
                best = (mean, al, picks)
        stack_scores = [(s[1], s[2], s[3], sum(x[1] for x in s[4]) / 4) for s in stacks]
        result.append(dict(ch=ch, mean=best[0], al=best[1], picks=best[2], stacks=stack_scores,
                           beststack=max(x[3] for x in stack_scores)))
    result.sort(key=lambda d: (-d["mean"], -d["beststack"], d["ch"]))

    # ---- power creep numbers
    by_set = collections.defaultdict(list)
    for ch, label, al, st, lv in STACKS:
        by_set[st].append(sum(x[1] for x in lv) / 4)
    lvl_by_set = collections.defaultdict(list)
    for ch, label, al, st, lv in STACKS:
        for i, x in enumerate(lv, 1): lvl_by_set[(st, i)].append(x[1])
    pats = {
        "flat +life-card damage on attacks": re.compile(r"\+\s?(?:\d+|X)\s+(?:life cards?|Life Cards?)", re.I),
        "unstoppable / unpreventable": re.compile(r"cannot (?:be stopped|be prevented|have (?:its|their) damage prevented)", re.I),
        "cuts opp's life-card damage": re.compile(r"opponent's attacks deal -\d life cards?", re.I),
    }
    cnt = {k: collections.Counter() for k in pats}
    tot = collections.Counter()
    for ch, label, al, st, lv in STACKS:
        for cid, _, _ in lv:
            r = CARDS[cid]
            t = r["text_current"] or r["text_as_printed"] or ""
            tot[st] += 1
            for k, p in pats.items():
                if p.search(t): cnt[k][st] += 1

    out = []
    w = out.append
    w("# Main Personality tier list, Sets 1-7 (PanZ), ranked on printed abilities only")
    w("")
    w("Generated by `scripts/mp_tier_list.py` (the scores live in that file; edit them there and re-run). Card text is `text_current` when present, otherwise `text_as_printed`.")
    w("")
    w("## How to read this")
    w("- **Scope:** every Main Personality printed in Sets 1-7, grouped by character (Goku Premiere + Evolution + Awakening = \"Goku\"). Set 8+ (FanZ) MPs, the OP promos and Dende (OP3 only) are out of scope. 30 characters, 39 level-stacks.")
    w("- **Ranked on abilities only.** Power stages, PUR and rarity are ignored. The one place that bites: a few MPs have tiny printed power (Hercule, Captain Ginyu's Frog, Dr. Wheelo), so their real strength depends on stats this list does not look at.")
    w("- **Scoring:** each level gets a hand-assigned 1-10 score from its printed text. 10 = changes the game each turn; 7-8 = clearly strong (big flat life-card bonus, unstoppable or unpreventable, repeatable defense or tutor); 5-6 = solid but conditional or low-impact; 1-4 = filler, a drawback or needs outside support. Scores are my judgement, not a simulation, so treat gaps under about 0.5 as ties.")
    w("- **Multiple stacks:** the rules let you mix printings of the same name and alignment level by level, so a character's score is the **mean of the best available printing at each level**. A character with several stacks (Goku, Trunks, Piccolo) gets credit for the best of them, but not for more than one pick per level. Each stack's own mean is also shown so you can see which set carried the character. Hero and Villain Vegeta cannot mix, so his score is his better alignment.")
    w("- **Tiers:** S = 7.5 or more, A = 6.75-7.49, B = 6.0-6.74, C = 5.25-5.99, D = under 5.25.")
    w("- **Not modelled:** deck-building support (how many cards exist for an archetype), Mastery interactions, matchups, and the Frozen list. Conditional cards (Android 17, Cell Jr., Cell Set 7) are scored as if their support exists but are marked down for needing it.")
    w("")
    w("## Tier list")
    w("")
    cur = None
    for d in result:
        t = tier_of(d["mean"])
        if t != cur:
            cur = t
            w(f"### Tier {t}")
            w("")
            w("| Rank | Character | Score | Stacks (set: stack mean) | Best level picks (L1 / L2 / L3 / L4) |")
            w("|---|---|---|---|---|")
            rank_i = 0
        rank_i += 1
        stks = "; ".join(f"{lab.split(' (')[0].replace(' Deck Reveal','').replace(' starter','').replace(' booster','')}: {m:.2f}" for lab, al, st, m in d["stacks"] if al == d["al"] or len({x[1] for x in d['stacks']}) == 1)
        picks = " / ".join(f"{d['picks'][i][2]}" for i in range(1, 5))
        w(f"| {rank_i} | {d['ch']} ({d['al']}) | **{d['mean']:.2f}** | {stks} | {picks} |")
        # collect for later detail
        if d is result[-1] or tier_of(result[result.index(d)+1]["mean"]) != t:
            w("")
    w("")
    w("## Power creep, Set 1 to Set 7")
    w("")
    w("Average stack score by the set each stack was printed in (stack = one printed set of Levels 1-4):")
    w("")
    w("| Set | Stacks | Mean stack score | L1 | L2 | L3 | L4 |")
    w("|---|---|---|---|---|---|---|")
    names = {1: "1 Premiere", 2: "2 Heroes & Villains", 3: "3 Movie Collection", 4: "4 Evolution", 5: "5 Perfection", 6: "6 Vengeance", 7: "7 Awakening"}
    for st in range(1, 8):
        v = by_set[st]
        lv = [sum(lvl_by_set[(st, i)]) / len(lvl_by_set[(st, i)]) for i in range(1, 5)]
        w(f"| {names[st]} | {len(v)} | {sum(v)/len(v):.2f} | " + " | ".join(f"{x:.1f}" for x in lv) + " |")
    w("")
    w("Text counts (objective, from the level texts of the stacks above; a level is counted once if its text matches):")
    w("")
    w("| Set | Levels | Mentions a life-card damage bonus (`+N life cards`) | Unstoppable / unpreventable text | Cuts opponent's life-card damage |")
    w("|---|---|---|---|---|")
    for st in range(1, 8):
        k = list(pats)
        w(f"| {names[st]} | {tot[st]} | {cnt[k[0]][st]} | {cnt[k[1]][st]} | {cnt[k[2]][st]} |")
    w("")
    w("Weakest and strongest stack printed in each set:")
    w("")
    w("| Set | Weakest stack | Strongest stack |")
    w("|---|---|---|")
    for st in range(1, 8):
        ss = [(sum(x[1] for x in s[4]) / 4, s[0]) for s in STACKS if s[3] == st]
        lo, hi = min(ss), max(ss)
        w(f"| {names[st]} | {lo[1]} {lo[0]:.2f} | {hi[1]} {hi[0]:.2f} |")
    w("")
    w("Same character, later set (stack means, same alignment):")
    w("")
    for ch, stacks in chars.items():
        for al in sorted({s[2] for s in stacks}):
            ss = sorted([s for s in stacks if s[2] == al], key=lambda s: s[3])
            if len(ss) > 1:
                w(f"- **{ch}**: " + " -> ".join(f"Set {s[3]} {sum(x[1] for x in s[4]) / 4:.2f}" for s in ss))
    w("")
    s1 = sum(by_set[1]) / len(by_set[1]); s7 = sum(by_set[7]) / len(by_set[7])
    w("**What this shows (judgement, small sample, hand-scored):**")
    w(f"- Power creep exists but is modest and uneven: mean stack score goes {s1:.2f} (Set 1) to {s7:.2f} (Set 7), with dips at Set 2 and Set 4 and no steady climb. Set 1 was not weak; its text already had 4-7 life-card attacks (Piccolo, Krillin, Captain Ginyu).")
    w("- The **top** moved up the most: the two best stacks in the game are Set 7 Deck Reveal Vegeta (Hero) and Goku, built on flat bonuses to every attack (+2 to +3 life cards) plus 'cannot be stopped'; the catch is that Vegeta's bonuses only apply to non-Styled attacks and Goku's are spread across draw/tutor effects. Nothing printed before Set 5 scores above 7.75.")
    w("- The **floor** rose too: every Set 7 stack scores 6.0 or more except Hercule (5.5, a joke MP), while Sets 1, 2 and 4 contain 4.75-5.5 stacks (Trunks, Nappa, Raditz, Nail, Vegeta Hero Set 4, Frieza, the Android 17 starter).")
    w("- Same-character comparisons are mixed, not one-way: Goku, Trunks and Hero Vegeta get clearly better by Set 7 (Hero Vegeta +3.5 from Set 4, Trunks +2.25 from Set 1), but Piccolo and Gohan were already at their best in Set 1 and later stacks are weaker.")
    w("- Where it shows most in the text: life-card damage bonuses and unstoppable text become common in Set 7 (see the counts above), and the Level 4 average rises from 6.4 to 7.4.")
    w("")
    w("## Per-character detail")
    w("")
    w("Notes at the bottom explain the caveats.")
    w("")
    for d in result:
        w(f"### {d['ch']} - {tier_of(d['mean'])} ({d['mean']:.2f})")
        for s in STACKS:
            if s[0] != d["ch"] or s[2] != d["al"] and len({x[2] for x in chars[d['ch']]}) > 1:
                continue
            m = sum(x[1] for x in s[4]) / 4
            w(f"- **{s[1]}** ({s[2]}, stack mean {m:.2f})")
            for i, (cid, sc, note) in enumerate(s[4], 1):
                w(f"  - L{i} `{cid}` **{sc}**: {note}")
        for a in ALTS:
            if a[0] == d["ch"] and a[1] == d["al"]:
                w(f"- *Mix-in, Level {a[2]}* `{a[3]}` **{a[4]}**: {a[5]}")
        if len({x[2] for x in chars[d['ch']]}) > 1:
            other = [s for s in chars[d['ch']] if s[2] != d["al"]]
            for s in other:
                m = sum(x[1] for x in s[4]) / 4
                w(f"- (Other alignment, not mixable: {s[1]}, stack mean {m:.2f})")
        w("")
    w("## Notes and caveats")
    w("- **Hercule:** owner ruling (2026-11-02): Level 1 prints '+100 stages of damage' and then 'Your attacks cannot have their damage modified by your effects'. Read in that order, the second sentence cancels the first, so the +100 is gag/flavour text and does nothing. He is scored on what is left (Level 1 = 3). I first scored it as a literal +100 and had him in Tier A; that was wrong.")
    w("- **Frieza Golden (Set 3 promo)** damage is `AT life cards`, which depends on the Attack Table result and is scored 7 rather than higher for that reason.")
    w("- **Android 16, Garlic Jr. Level 4** have printed drawbacks / symmetric effects; they are scored for the whole text, not the upside.")
    w("- **Krillin Level 3** (9 minus cards in opp's hand) is strong only if the opponent's hand is small; the notes say the defender draws 3 on entering combat, so it needs hand disruption.")
    w("- Scores for Set 7 Deck Reveal stacks (Goku, Vegeta, Trunks) assume the deck can use the Styled / non-Styled split those cards care about.")
    open(ROOT / "MP_TIER_LIST.md", "w").write("\n".join(out) + "\n")
    print("wrote MP_TIER_LIST.md", len(out), "lines; stacks", len(STACKS), "characters", len(result))
    for d in result:
        print(f"{d['mean']:.2f} {tier_of(d['mean'])} {d['ch']} ({d['al']})  best stack {d['beststack']:.2f}")
    for st in range(1, 8):
        print(st, len(by_set[st]), round(sum(by_set[st]) / len(by_set[st]), 2), {k: cnt[k][st] for k in pats}, tot[st])


main()
