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
   ("S04_STR_S22", 6, "Attack destroys an Ally; hit refetches the Van from discard or Banished Zone"),
   ("S04_STR_S23", 8, "6-life-card energy attack, unpreventable if Van is in play"),
   ("S04_STR_S24", 6, "Physical attacks scale with Allies in opp's Banished Zone (the Van banishes Allies); refetches the Van from Banished every combat")]),
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
 ("Frieza", "Villain", 2, "S03_PRO_P16", 7, "Golden (Set 3 promo): AT-life-card attack, +3 stages, Rejuvenate a Frieza Named card for a critical effect"),
 ("Gohan", "Hero", 1, "S06_BST_73", 5, "Fetch an Ally and play it; with 3+ Allies advance you (no MPPV)"),
 ("Goku", "Hero", 1, "S01_PRO_P5", 4, "Super Saiyan God (Set 1 promo): destroy the top card of your deck to draw a card"),
 ("Krillin", "Hero", 2, "S06_BST_74", 4, "Quick: pay 2 stages for +2 stages on an attack; 4-stage unmodifiable attack"),
 ("Master Roshi", "Hero", 1, "S06_BST_75", 4, "Restrained: fetch the Turtle Ally; banishing from opp's discard mills"),
 ("Trunks", "Hero", 1, "S06_BST_76", 6, "Protective: Sword plays Rejuvenate 1; free non-Styled Drill fetch each combat; Drills kept when advancing"),
]

# ---------------------------------------------------------------------------------------------
# What each stack is built around (read from the text; the Nappa / Raditz / Slug / Van notes also carry the owner's reading)
ROLES = {
 "S06_BST_61": "Android-title package (Androids 14/15 banished at L2); tempo: opp loses stages and skips actions",
 "S05_BST_69": "Life-card racer: every attack +1/+2 life cards, punishes a player who does not declare combat",
 "S04_STR_S21": "Android 17's Van loop (Van banishes 2 Allies, fetches an Android Ally if you have none; L1 fetches it, L2/L4 refetch it); Ally removal; L3 unpreventable with Van in play",
 "S04_STR_S26": "Anti-physical control (opp's physical attacks cannot be modified / cost more); 0-damage energy attacks cycle cards; L4 hit sets opp's MP to 0",
 "S04_BST_85": "Counter-puncher: gains stages when hit; wants a card attached to opp's MP at L4",
 "S04_BST_89": "Non-Styled Drill engine; mill; repeatable energy-attack defense at L4",
 "S06_BST_65": "Anti-levelling: opp loses 5/7/7 stages each time it advances; L4 no Endurance and board wipe",
 "S01_BST_06": "Ally swarm: Allies fetched and always able to act; life-card damage scales with Allies",
 "S05_DR_DR1": "Styled-card tutor; Level 3 is a one-shot 7-life-card unpreventable attack",
 "S07_DR_DR11": "Cell Jr./Saiyan Ally fetcher with Ally-shuffle mill",
 "S07_BST_68": "Cell Jr. Ally hand-engine: Allies are your stop / mill currency",
 "S06_BST_69": "Rejuvenate-sustain with large life-card attacks",
 "S03_BST_61": "Mill: every destroy effect grows (+1 then +2) and Rejuvenates; +2 life cards at L2",
 "S01_STR_S17": "Anger from stopping, copies opp's attack, then +3 stages; Frieza Named support",
 "S03_BST_65": "Defensive anger engine: opp's attacks shrink, levelling is cheaper, Dragon Ball capture; L4 flips into a drawback",
 "S01_STR_S09": "Life-card burst: pays your own deck or anger for extra life cards on Styled attacks",
 "S07_DR_DR16": "Everything counts as Styled; tutors; L4 makes the next attack free and unpreventable",
 "S01_STR_S05": "Drill engine: Drills fetched every combat, up to 5 at once at L4",
 "S04_STR_S06": "Ally engine: Allies fetched, always acting, +4 life cards on Ally attacks at L4",
 "S07_DR_DR1": "Generalist: flat +/- life-card bonuses plus draw and tutor, no setup needed",
 "S07_DR_DR21": "Gag MP: L1's +100 stages is cancelled by its next sentence (owner ruling); L2 shrinks opp's attacks; Named-card theme",
 "S01_STR_S13": "Hand-size attacker: discards trigger critical effects (L1); damage scales with a small opposing hand (L3)",
 "S03_BST_69": "Dragon Ball engine with Rejuvenate; cannot MPPV at L4 (owner: gives non-Namekian styles Rejuvenate; Dragon Ball victory plan)",
 "S05_BST_61": "Setups/Drills as a shield: spend board cards to prevent all damage; L3 reveals opp's hand, L4 steals tutors",
 "S07_BST_72": "Mill / banish pressure on every attack",
 "S02_BST_01": "Stage damage plus Dragon Ball tricks; mills when opp stops you",
 "S02_BST_03": "Stage pressure and Ally/Drill removal (owner: stage-lock deck; see notes)",
 "S01_STR_S21": "Rejuvenate plus cheap life-card energy attacks; critical-damage payoffs; Dragon Ball tutor",
 "S04_STR_S11": "Anger from gaining stages / Rejuvenating; Dragon Ball capture (L3); strips opp's ball effects (L4)",
 "S02_BST_05": "Setup/Drill trigger engine; random hand discard (owner: strong when a deck's Setups/Drills are strong; see notes)",
 "S02_BST_07": "Critical-effect and recursion; L3 pays 8 discards for 6 anger; L4 uses the first attack twice",
 "S01_BST_04": "Library control: reorders the top of decks, almost no damage text",
 "S04_STR_S01": "Sword package: bulk stage damage (+5 at L4)",
 "S07_DR_DR26": "Anger-doubling plus Named and Sword engine",
 "S03_BST_73": "Unpreventable stage damage; L4 hits for X stages and X life cards",
 "S01_STR_S01": "Anger-on-hit engine: every attack raises anger, later levels turn anger-raising attacks into extra stages and life cards",
 "S04_STR_S16": "Converts life-card damage to stages (and back): niche; L4 first Styled physical attack unstoppable",
 "S07_DR_DR6": "Non-Styled attack pressure (+1 to +3 life cards, unpreventable, unstoppable); opp must pass when you arrive",
 "S05_BST_65": "Anger denial and cheap attacks; L4 attacks cost -3 and +3 life cards",
}

OUTLIERS_EXTRA = [
 # (character, alignment, level, card_id, score, short name, why it is listed)
 ("Krillin", "Hero", 1, "S01_PRO_P4", 7, "SDCC promo wording", "Same attack as the starter's Ready but without 'raise your anger 2 levels'"),
]
TIERS = [("S", 7.75), ("A", 7.0), ("B", 6.25), ("C", 5.5), ("D", 0)]
NAMES = {1: "Premiere", 2: "Heroes & Villains", 3: "Movie Collection", 4: "Evolution", 5: "Perfection", 6: "Vengeance", 7: "Awakening"}


# Owner's review (2026-11-02): an MP level with an active Power is stronger than one that is purely passive. The hand-scored base values
# above are kept; every level whose printed text has a Power (an [Attack], [Defense] or POWER: line, reminder text in brackets ignored)
# gets ACTIVE_BONUS added, capped at 10. Set ACTIVE_BONUS = 0 to switch it off.
ACTIVE_BONUS = 0.5
BASE = {}


def has_power(cid):
    t = CARDS[cid]["text_current"] or CARDS[cid]["text_as_printed"] or ""
    t = re.sub(r"\([^)]*\)", "", t)
    return bool(re.search(r"POWER:|\[Attack\]|\[Defense\]", t))


def _eff(cid, sc):
    BASE[cid] = sc
    return min(10, sc + ACTIVE_BONUS) if has_power(cid) else sc


STACKS = [(ch, label, al, st, [(cid, _eff(cid, sc), note) for cid, sc, note in lv]) for ch, label, al, st, lv in STACKS]
ALTS = [(ch, al, lvl, cid, _eff(cid, sc), why) for ch, al, lvl, cid, sc, why in ALTS]
OUTLIERS_EXTRA = [(ch, al, lvl, cid, _eff(cid, sc), nm, why) for ch, al, lvl, cid, sc, nm, why in OUTLIERS_EXTRA]


def check():
    errs = []
    for ch, label, al, st, lv in STACKS:
        for i, (cid, sc, _) in enumerate(lv, 1):
            r = CARDS.get(cid)
            if not r: errs.append(f"missing {cid}"); continue
            if r["card_name"] != ch or r["level"] != i or r["alignment"] != al or r["set_number"] != st:
                errs.append(f"mismatch {cid}: {r['card_name']} L{r['level']} {r['alignment']} S{r['set_number']} vs {ch} L{i} {al} S{st}")
        if lv[0][0] not in ROLES: errs.append(f"no role for {lv[0][0]}")
    for ch, al, i, cid, sc, _ in ALTS:
        r = CARDS.get(cid)
        if not r or r["card_name"] != ch or r["level"] != i or r["alignment"] != al:
            errs.append(f"bad alt {cid}")
    for ch, al, i, cid, sc, nm, _ in OUTLIERS_EXTRA:
        r = CARDS.get(cid)
        if not r or r["card_name"] != ch or r["level"] != i or r["alignment"] != al:
            errs.append(f"bad outlier {cid}")
    return errs


def tier_of(x):
    for t, lo in TIERS:
        if x >= lo: return t


def char_score(ch, use_alts=True):
    stacks = [s for s in STACKS if s[0] == ch]
    best = None
    for al in sorted({s[2] for s in stacks}):
        picks = {}
        for lvl in range(1, 5):
            cands = [(s[4][lvl-1][1], s[4][lvl-1][0], s[1]) for s in stacks if s[2] == al]
            if use_alts:
                cands += [(a[4], a[3], "outlier") for a in ALTS if a[0] == ch and a[1] == al and a[2] == lvl]
            picks[lvl] = max(cands)
        mean = sum(p[0] for p in picks.values()) / 4
        if best is None or mean > best[0]:
            best = (mean, al, picks)
    return best


def short(label):
    for a, b in ((" Deck Reveal", " deck reveal"), (" starter", " starter"), (" booster", " booster")):
        label = label.replace(a, b)
    return label


def main():
    errs = check()
    if errs:
        print("\n".join(errs)); sys.exit(1)
    stack_rows = []
    for ch, label, al, st, lv in STACKS:
        stack_rows.append(dict(ch=ch, label=label, al=al, st=st, lv=lv, mean=sum(x[1] for x in lv) / 4, role=ROLES[lv[0][0]]))
    stack_rows.sort(key=lambda d: (-d["mean"], d["ch"], d["st"]))
    chars = collections.OrderedDict()
    for s in STACKS:
        chars.setdefault(s[0], []).append(s)
    char_rows = []
    for ch in chars:
        m, al, picks = char_score(ch)
        m0, _, _ = char_score(ch, use_alts=False)
        char_rows.append(dict(ch=ch, mean=m, al=al, picks=picks, without=m0,
                              beststack=max(sum(x[1] for x in s[4]) / 4 for s in chars[ch])))
    char_rows.sort(key=lambda d: (-d["mean"], -d["beststack"], d["ch"]))

    by_set = collections.defaultdict(list)
    lvl_by_set = collections.defaultdict(list)
    for ch, label, al, st, lv in STACKS:
        by_set[st].append(sum(x[1] for x in lv) / 4)
        for i, x in enumerate(lv, 1): lvl_by_set[(st, i)].append(x[1])
    pats = {
        "flat +life-card damage": re.compile(r"\+\s?(?:\d+|X)\s+(?:life cards?|Life Cards?)", re.I),
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

    w_ = []
    w = w_.append
    w("# Main Personality tier list, Sets 1-7 (PanZ), by stack, ranked on printed abilities only")
    w("")
    w("Generated by `scripts/mp_tier_list.py` (scores and notes live in that file; edit there and re-run). Card text is `text_current` when present, otherwise `text_as_printed`.")
    w("")
    w("## How to read this")
    w("- **Scope:** every Main Personality in Sets 1-7. A **stack** is one set's printed Levels 1-4 (Goku Premiere, Goku Evolution and Goku Awakening are three stacks). 39 stacks, 30 characters. Single odd levels from boosters and promos are listed separately as **outliers** (Part 2).")
    w("- **Ranked on abilities only.** Power stages, PUR and rarity are ignored (e.g. Goku Super Saiyan God and Golden Frieza have enormous printed power stages; none of that is counted). Deck support is not counted either; see Part 5.")
    w("- **Scoring:** each level gets a hand-assigned 1-10 score from its text. 10 = changes the game each turn; 7-8 = clearly strong (big flat life-card bonus, unstoppable / unpreventable, repeatable defense or tutor); 5-6 = solid but conditional; 1-4 = filler, a drawback, or needs outside support. These are my judgements, not a simulation, so treat gaps under about 0.5 as ties.")
    w("- **Stack score** = mean of its four level scores. **Tiers:** S = 7.75+, A = 7.0-7.74, B = 6.25-6.99, C = 5.5-6.24, D = under 5.5.")
    w("- **Active Power consideration:** from the owner's review, an MP level with an active Power (an Attack, a Defense, or a POWER you choose to use) is stronger than a purely passive [Continuous] one. I kept the hand-scored base values and add " + f"{ACTIVE_BONUS:g}" + " to every level whose text has a Power ('base' and the bonus are shown in Part 6). That is a small nudge, not a rebuild; Piccolo Premiere Level 1 (an attack with Rejuvenate) beating Piccolo Evolution Level 1 (a passive anger trigger) was the model case. It lifts mixed and active-heavy stacks by up to " + f"{ACTIVE_BONUS:g}" + " and leaves passive-only stacks (Trunks Premiere, most of Garlic Jr., Hercule's passives) where they were; the tier cut-offs moved up 0.25 to match. The Mastery list is not adjusted.")
    w("- **Characters** (Part 3): the rules let you mix printings of the same name and alignment level by level, so a character's score is the mean of the best printing at each level, outliers included. Hero and Villain Vegeta cannot mix.")
    w("- **Not in scope:** Set 8+ (FanZ); the OP series (OP1-OP6 are FanZ-era: Nail Warrior, Goku Confident, the Raditz OP4 stack, Dende); and the 'PanZ MP & Ally Promos' (`PZP_*`) reprints, which the repo skips by default. Some PZP cards carry rewritten text (Android 16 L1-3, Captain Ginyu L1-2, Cell Jr. L3, Dr. Wheelo L3, Turles L3, Mercenary Tao L1 differ the most from the Set 1-7 printings); those are not rated.")
    w("")
    w("## Part 1: Stack tier list")
    w("")
    cur = None
    n = 0
    for d in stack_rows:
        t = tier_of(d["mean"])
        if t != cur:
            if cur is not None: w("")
            cur = t; n = 0
            w(f"### Tier {t}")
            w("")
            w("| # | Stack | Alignment | Score | L1 | L2 | L3 | L4 | Built around |")
            w("|---|---|---|---|---|---|---|---|---|")
        n += 1
        sc = " | ".join(str(x[1]) for x in d["lv"])
        w(f"| {n} | **{d['ch']}**, {short(d['label'])} | {d['al']} | **{d['mean']:.2f}** | {sc} | {d['role']} |")
    w("")
    w("## Part 2: Single-level outliers (booster and promo cards that can replace one level)")
    w("")
    w("These are not a full stack, so they are not tiered. Each is scored like any other level, then placed among every Level-N card in the 39 stacks (rank 1 = best). 'Replaces' is the best stack card at that level for the same character and alignment. 'Effect' is the change to the character's Part 3 score from allowing the outlier.")
    w("")
    w("| Character | Level | Card | Where it is from | Score | Rank among all L-N cards | Replaces | Effect on character | What it does |")
    w("|---|---|---|---|---|---|---|---|---|")
    outs = [(a[0], a[1], a[2], a[3], a[4], None, a[5]) for a in ALTS] + [(a[0], a[1], a[2], a[3], a[4], a[5], a[6]) for a in OUTLIERS_EXTRA]
    for ch, al, lvl, cid, sc, nm, why in sorted(outs, key=lambda o: (o[0], o[2])):
        r = CARDS[cid]
        field = [s[4][lvl-1][1] for s in STACKS]
        rank = 1 + sum(1 for x in field if x > sc); tie = sum(1 for x in field if x == sc)
        own = [(s[4][lvl-1][1], s[4][lvl-1][0], s[1]) for s in STACKS if s[0] == ch and s[2] == al]
        bs, bid, blab = max(own)
        with_m = char_score(ch)[0]; wo = char_score(ch, use_alts=False)[0]
        eff = f"{wo:.2f} -> {with_m:.2f}" if abs(with_m - wo) > 1e-9 else "none (a stack card is better or equal)"
        src = f"{r['source_folder'].split('/')[-1]}, {r['card_number']} ({r['collection']})"
        w(f"| {ch} | L{lvl} | {r['subtitle']}{' - ' + nm if nm else ''} `{cid}` | {src} | **{sc}** | {rank} of {len(field)}{' (tied with ' + str(tie) + ')' if tie else ''} | {blab.split(' (')[0]} {bs} | {eff} | {why} |")
    w("")
    w("The four Set 6 outliers (Gohan To the Rescue, Krillin Quick, Master Roshi Restrained, Trunks Protective) are the only Set 6 cards for those characters. Goku Super Saiyan God is in the Set 1 promo folder and Golden Frieza in the Set 3 promo folder (not the OP series), so they are PanZ-era and included.")
    w("")
    w("## Part 3: By character (all stacks and outliers mixed)")
    w("")
    cur = None
    n = 0
    for d in char_rows:
        t = tier_of(d["mean"])
        if t != cur:
            if cur is not None: w("")
            cur = t; n = 0
            w(f"### Tier {t}")
            w("")
            w("| # | Character | Score | Without outliers | Best single stack | Best pick per level (L1 / L2 / L3 / L4) |")
            w("|---|---|---|---|---|---|")
        n += 1
        pk = " / ".join(f"{d['picks'][i][0]} ({d['picks'][i][2].replace(' Deck Reveal','').replace(' starter','').replace(' booster','').split(' (')[0].split(' ')[1] if d['picks'][i][2] != 'outlier' else 'outlier'})" for i in range(1, 5))
        w(f"| {n} | **{d['ch']}** ({d['al']}) | **{d['mean']:.2f}** | {d['without']:.2f} | {d['beststack']:.2f} | {pk} |")
    w("")
    w("In the last column the bracket is the set the pick comes from.")
    w("")
    w("## Part 4: Power creep, Set 1 to Set 7")
    w("")
    w("| Set | Stacks | Mean stack score | L1 | L2 | L3 | L4 | Weakest stack | Strongest stack |")
    w("|---|---|---|---|---|---|---|---|---|")
    for st in range(1, 8):
        v = by_set[st]
        lv = [sum(lvl_by_set[(st, i)]) / len(lvl_by_set[(st, i)]) for i in range(1, 5)]
        ss = sorted([(sum(x[1] for x in s[4]) / 4, s[0]) for s in STACKS if s[3] == st])
        w(f"| {st} {NAMES[st]} | {len(v)} | {sum(v)/len(v):.2f} | " + " | ".join(f"{x:.1f}" for x in lv) + f" | {ss[0][1]} {ss[0][0]:.2f} | {ss[-1][1]} {ss[-1][0]:.2f} |")
    w("")
    w("Objective text counts (levels in the stacks above whose text matches a pattern; approximate, e.g. the first pattern also catches per-attack bonuses):")
    w("")
    w("| Set | Levels | Mentions `+N life cards` | Unstoppable / unpreventable text | Cuts opponent's life-card damage |")
    w("|---|---|---|---|---|")
    ks = list(pats)
    for st in range(1, 8):
        w(f"| {st} {NAMES[st]} | {tot[st]} | {cnt[ks[0]][st]} | {cnt[ks[1]][st]} | {cnt[ks[2]][st]} |")
    w("")
    w("Same character, later set (stack means):")
    w("")
    for ch, stacks in chars.items():
        for al in sorted({s[2] for s in stacks}):
            ss = sorted([s for s in stacks if s[2] == al], key=lambda s: s[3])
            if len(ss) > 1:
                w(f"- **{ch}**: " + " -> ".join(f"Set {s[3]} {sum(x[1] for x in s[4]) / 4:.2f}" for s in ss))
    w("")
    s1 = sum(by_set[1]) / len(by_set[1]); s7 = sum(by_set[7]) / len(by_set[7])
    w("**What this shows (judgement, small sample, hand-scored):**")
    w(f"- Power creep is real but modest and uneven: mean stack score {s1:.2f} (Set 1) to {s7:.2f} (Set 7), with dips at Sets 2 and 4. Set 1 already had 4-7 life-card attacks (Piccolo, Krillin, Captain Ginyu).")
    top2 = stack_rows[:2]
    pre5 = max(sum(x[1] for x in s_[4]) / 4 for s_ in STACKS if s_[3] < 5)
    mins = {st: min((sum(x[1] for x in s_[4]) / 4, s_[0]) for s_ in STACKS if s_[3] == st) for st in range(1, 8)}
    w(f"- The top moved up most: the two best stacks are {top2[0]['ch']} ({short(top2[0]['label'])}, {top2[0]['mean']:.2f}) and {top2[1]['ch']} ({short(top2[1]['label'])}, {top2[1]['mean']:.2f}), built on flat +2/+3 life-card bonuses to every attack; Vegeta's bonuses only apply to non-Styled attacks and add 'cannot be stopped'. The best stack printed before Set 5 scores {pre5:.2f}.")
    w("- The floor: the weakest stack in each set is " + "; ".join(f"Set {st} {mins[st][1]} {mins[st][0]:.2f}" for st in range(1, 8)) + ".")
    w("- Same-character comparisons are mixed: Goku, Trunks and Hero Vegeta improve a lot by Set 7; Piccolo and Gohan were at their best in Set 1.")
    w("- In the text: life-card bonuses and unstoppable wording become common in Set 7, and the Level 4 average goes from " + f"{sum(lvl_by_set[(1, 4)]) / len(lvl_by_set[(1, 4)]):.1f} (Set 1) to {sum(lvl_by_set[(7, 4)]) / len(lvl_by_set[(7, 4)]):.1f} (Set 7).")
    w("")
    sm = {d["ch"]: d["mean"] for d in stack_rows}
    w("## Part 5: What these scores do not capture")
    w("")
    w("The scores judge each card's text on its own. Several low-scoring MPs are built around something outside the MP card (a deck package, or a matchup). The notes below are the owner's reading, checked against the card text where possible. They are **hypotheses, not tested, and they are not in the scores**.")
    w("")
    w("- **Nappa (Set 2, NAPPA).** Owner: designed to stage-lock an opponent and deal with Allies, e.g. against Ginyu remove the Allies and drain stages (possibly to mill), and energy decks have a hard time against him. Text check: L1 destroys an opposing Ally, L2 makes opp's personalities lose 1-2 stages whenever you attack, L3's hit banishes a Drill or Ally, L4 makes damage unpreventable once the opponent is at 0. Many Set 1-7 energy attacks print a stage cost (Goku L1 and L3 cost 2, Piccolo L1 costs 1, Krillin costs 2-3, Turles L2 costs 2), so draining stages should hurt energy decks. That is consistent with the text but untested. Owner also sees **Broly** (opp loses 5/7/7 stages on every advance; L4 banishes Setups, Drills and Allies) and **Android 17** (destroys an Ally at L2, unpreventable energy attack with the Van at L3) as better versions of the same job. The scores agree on the order: Broly BROLY, Android 17 A17, Nappa NAPPA.".replace("BROLY", f"{sm['Broly']:.2f}").replace("A17", f"{sm['Android 17']:.2f}").replace("NAPPA", f"{sm['Nappa']:.2f}"))
    w("- **Android 17's Van (Set 4, stack score A17).** Literal text of the Setup: 'POWER: Banish 2 Allies. If you control no Allies, you may search your Life Deck, discard pile, or Banished Zone for an Ally with \"Android\" in the title and place it into play. (Banish after use.)' The MP is built around it: L1 fetches the Van, L2's hit refetches it from the discard pile or Banished Zone, L3 makes the energy attack unpreventable while it is in play, and L4 scales with Allies in the opponent's Banished Zone and refetches the Van from the Banished Zone every combat. After reading it I raised the base scores of L2 and L4 from 5 to 6. I did **not** verify how it resolves if you control fewer than two Allies, or whether it can banish the opponent's Allies (the text does not say whose), so the loop itself is not scored higher.")
    w("- **Raditz (Set 2, RADITZ).** Owner: Setups and Drills are very strong depending on deck design, so a Raditz built around them could beat another MP using the same cards, though newer MPs may simply hit too hard for it to matter. Text check: L2 mills a card (and raises anger in combat) whenever a Setup or Drill enters play, L4 Rejuvenates a card on each one and fetches a Setup/Drill after a critical effect. The payoff depends on the Setup/Drill package, which is not scored.")
    w("- **Lord Slug (Set 3, SLUG).** Owner: gives non-Namekian styles Rejuvenate access; Red Slug could win by Dragon Ball victory off Red's critical effects, or Rejuvenate strongly. Text check: L1 raises anger and refetches a ball, L2 Rejuvenates 2 on hit, L4 fetches a ball. Also untested; the repo notes already say the Red Enraged Dragon Ball deck for him is good.")
    w("- Owner's conclusion: because the list scores isolated cards and MP abilities, Nappa, Raditz and Slug staying in Tier D (as characters) makes sense. A 'with deck support' score would need deck data or simulation, not card reading.")
    w("")
    w("## Part 6: Level-by-level notes per stack")
    w("")
    for d in sorted(stack_rows, key=lambda d: (d["ch"], d["st"], d["al"])):
        w(f"### {d['ch']}, {short(d['label'])} ({d['mean']:.2f}, Tier {tier_of(d['mean'])})")
        for i, (cid, sc, note) in enumerate(d["lv"], 1):
            w(f"- L{i} `{cid}` **{sc:g}** (base {BASE[cid]:g}, " + ("+" + f"{ACTIVE_BONUS:g}" + " Power" if has_power(cid) else "passive only") + f"): {note}")
        w("")
    w("### Outlier cards")
    for ch, al, lvl, cid, sc, nm, why in sorted(outs, key=lambda o: (o[0], o[2])):
        r = CARDS[cid]
        w(f"- {ch} L{lvl} `{cid}` ({r['subtitle']}) **{sc:g}** (base {BASE[cid]:g}{', +' + format(ACTIVE_BONUS, 'g') + ' Power' if has_power(cid) else ', passive only'}): {why}")
    w("")
    w("## Notes and caveats")
    w("- **Hercule** (owner ruling 2026-11-02): L1 prints '+100 stages of damage' then 'Your attacks cannot have their damage modified by your effects'. In that order the second sentence cancels the first, so the +100 is gag text and L1 has a base score of 3 (3.5 with the Power bonus). See `DECKBUILDING_NOTES.md`.")
    w("- **Krillin L1** has two printings: the Set 1 starter adds 'raise your anger 2 levels', the Set 1 promo (the SDCC-style promo, `S01_PRO_P4`) does not. Both are legal to mix; the starter has a base score of 8, the promo 7.")
    w("- **Frieza Golden** damage is `AT life cards`, which depends on the Attack Table result; base-scored 7 for that reason.")
    w("- **Garlic Jr. Level 4** has a printed drawback (opp's attacks +3 life cards) and is scored for the whole text.")
    w("- **Krillin Level 3** (9 minus cards in opp's hand) is strongest with hand disruption, since the defender draws 3 when combat is declared.")
    w("- Set 7 deck-reveal Goku, Vegeta and Trunks scores assume the deck can use the Styled / non-Styled split those cards care about.")
    text = "\n".join(w_) + "\n"
    for tok, key in (("RADITZ", "Raditz"), ("SLUG", "Lord Slug"), ("A17", "Android 17"), ("NAPPA", "Nappa")):
        text = text.replace(tok, f"{sm[key]:.2f}")
    open(ROOT / "MP_TIER_LIST.md", "w").write(text)
    print("wrote MP_TIER_LIST.md", len(w_), "lines; stacks", len(STACKS), "characters", len(char_rows))
    for d in stack_rows:
        print(f"{d['mean']:.2f} {tier_of(d['mean'])} {d['ch']} {d['label']}")
    for d in char_rows:
        print(f"CHAR {d['mean']:.2f} (without {d['without']:.2f}) {tier_of(d['mean'])} {d['ch']}")


main()
