"""Build and verify the three Cell Jr. decks (Sets 1-7 only). Run from _deckbuilder_db/scripts:
    python build_cell_jr_decks.py          # writes ../decks/cell_jr_<style>.txt and prints a verification report

Cell Jr. (Villain) Level 1 says "Your Life Deck may include up to 3 copies of each Ally with "Cell Jr." in the title",
which overrides the usual one-copy-per-Ally limit and the "no Ally with your MP's name" rule. deckcode.check() does not know
that exception, so the three known false positives it raises for the Cell Jr. Allies are filtered here and replaced by explicit checks.
"""
import collections
import re
import sys
from pathlib import Path

import deckcode as dc

DECKS_DIR = dc.DB / 'decks'
MP_NAME = 'Cell Jr.'
MP_LEVELS = ['S07_BST_68', 'S07_BST_69', 'S07_BST_70', 'S07_BST_71']
CELL_JR_ALLIES = {'S07_BST_76': 3, 'S07_BST_77': 3, 'S07_BST_78': 3}   # Trapped, Escaping, Unrelenting

CORE = {  # in every deck (the Allies are added separately)
    "Time Is A Warrior's Tool": 1, 'Stare Down': 2, 'Villainous Visage': 1,
}

DECKS = {
    'blue_tag_team': dict(
        title='Cell Jr. Blue Tag Team', mastery='Blue Tag Team Mastery',
        cards={**CORE, "Cell Jr.'s Swarm": 2, "Cell Jr.'s Surround": 2, 'Visiting the Past': 2,
               'Blue Waiting Drill': 3, 'Blue Arrest': 3, 'Blue Slash': 3, 'Blue Challenging Strike': 2,
               'Blue Restraint': 1, 'Blue Discharge': 2,
               'Blue Blockade': 3, 'Blue Deterrence': 2, 'Blue Defensive Stance': 2, 'Blue Fist Catch': 2,
               'Blue Concentrated Blast': 2, 'Blue Stretch Kick': 2, 'Blue Ki Build Up': 3, 'Blue Double Blast': 2,
               'Blue Biting Drill': 2, 'Blue Lunge': 1, 'Blue Overcharge': 2, 'Blue Dominance': 1,
               'Blue Head Knock': 1, 'Blue Rest': 1, 'Blue Back Break': 1}),
    'red_ascension': dict(
        title='Cell Jr. Red Ascension', mastery='Red Ascension Mastery',
        cards={**CORE, "Cell Jr.'s Surround": 1, 'Visiting the Past': 1,
               'Red Static Shot': 3, 'Red Frenzied Blasts': 2, 'Red Surrounded Beams': 2, 'Red Hurl': 2,
               'Red Blocking Hand': 3, 'Red Repel': 2, 'Red Energy Defensive Stance': 2, 'Red Sacrifice': 2,
               'Red Furious Lunge': 2, 'Red Driving Knee': 2, 'Red Jab': 2, 'Red Knee Lift': 2, 'Red Blaze': 2,
               'Red Relaxation': 1, 'Red Burning Rage': 1, 'Red Destiny': 1, 'Red Vault': 1,
               'Red Combined Blast': 2, 'Red Departing Shot': 2, 'Red Energy Outburst': 1, 'Red Counter Kick': 2,
               'Red Chop': 2, 'Red Escape': 1, 'Red Scanning Drill': 2, 'Red Takeover': 1}),
    'black_perceptive': dict(
        title='Cell Jr. Black Perceptive', mastery='Black Perceptive Mastery',
        cards={**CORE, "Cell Jr.'s Swarm": 2, "Cell Jr.'s Surround": 1, 'Villainous Energy Sphere': 1, 'Visiting the Past': 1,
               'Black Chomp': 2, 'Black Choke': 2, 'Black Wilt': 2, 'Black Taunt': 2, 'Black Command': 2,
               'Black Confinement': 2, 'Black Pop-Up': 2, 'Black Viewing Drill': 2, 'Black Running Guard': 2,
               'Black Duck': 2, 'Black Foreshadowing': 1, 'Black Invitation': 1,
               'Black Lunge': 2, 'Black Hug Maneuver': 2, 'Black Knee Catch': 2, 'Black Blinding Burst': 2,
               'Black Overhead Burst': 2, 'Black Drain': 1, 'Black Corruption': 2,
               'Black Dash': 1, 'Black Impediment': 2, 'Black Resistance': 2, 'Black Easy Block': 2}),
}


def find(name, style):
    """The Sets 1-7 record named `name` (non-Restored, not a Main Personality), the app's first printing."""
    hits = [c for c in dc.CARDS if c['card_name'] == name and c['set_number'] and c['set_number'] <= 7
            and '_RST' not in c['card_id'] and dc.ctype(c) not in ('Main Personality', 'Mastery')]
    if not hits:
        raise SystemExit(f'no Sets 1-7 card named {name!r}')
    ids = {dc.app_printing(c['card_id']) for c in hits}
    if len(ids) > 1:
        raise SystemExit(f'{name!r} is ambiguous: {sorted(ids)}')
    return dc.BY_ID[ids.pop()]


def mastery_id(name):
    hits = [c for c in dc.CARDS if c['card_name'] == name and dc.ctype(c) == 'Mastery'
            and c['set_number'] and c['set_number'] <= 7 and '_RST' not in c['card_id']]
    ids = {dc.app_printing(c['card_id']) for c in hits}
    assert len(ids) == 1, (name, ids)
    return ids.pop()


def anger_points(t):
    pts = 0
    for m in re.finditer(r"raise (?:or lower )?(?:your|a player's)\s+anger\s+(\d)?\s*level", t, re.I):
        pts += int(m.group(1) or 1)
    for m in re.finditer(r"raise or lower a player's anger (\d) level", t, re.I):
        pts += int(m.group(1))
    return pts


def build(key):
    spec = DECKS[key]
    mid = mastery_id(spec['mastery'])
    mstyle = dc.BY_ID[mid]['style']
    cards = collections.Counter(CELL_JR_ALLIES)
    for name, n in spec['cards'].items():
        cards[find(name, mstyle)['card_id']] += n
    code = dc.encode(spec['title'], MP_NAME, mid, cards, MP_LEVELS)
    return spec, mid, mstyle, code


def verify(code, mstyle, expect_total=60):
    """Round trip + deckcode.check with the Cell Jr. exception handled explicitly. Returns a list of problems."""
    problems = []
    d = dc.decode(code)
    again = dc.encode(d['name'], d['mp_name'], d['mastery'], d['cards'], d['mp_levels'])
    if again != code:
        problems.append('code does not round-trip')
    err, warn = dc.check(d)
    expected = [r'^Cell Jr\.: Ally with the MP name$', r'^Cell Jr\. x9, limit 1$']
    for e in err:
        if not any(re.match(p, e) for p in expected):
            problems.append('check(): ' + e)
    for w in warn:
        problems.append('warning: ' + w)
    # Cell Jr. exception: exactly 3 copies of each of the three Cell Jr. Allies, none of any other Ally above 1
    cj = {i: n for i, n in d['cards'].items() if 'Cell Jr.' in dc.BY_ID[i]['card_name'] and dc.ctype(dc.BY_ID[i]) == 'Ally'}
    if cj != CELL_JR_ALLIES:
        problems.append(f'Cell Jr. Allies are {cj}')
    l1 = dc.BY_ID[d['mp_levels'][0]]
    if 'up to 3 copies of each Ally with "Cell Jr." in the title' not in dc.text(l1):
        problems.append('Level 1 text no longer has the 3-copy rule')
    # Styled cards must match the Mastery's style
    for i, n in d['cards'].items():
        c = dc.BY_ID[i]
        if c['style'] not in (mstyle, 'Freestyle', None) and dc.ctype(c) != 'Dragon Ball':
            problems.append(f"{c['card_name']}: style {c['style']} does not match {mstyle}")
        if dc.ctype(c) == 'Ally' and c['card_name'] != 'Cell Jr.' and n > 1:
            problems.append(f"{c['card_name']} x{n}")
    if sum(d['cards'].values()) != expect_total:
        problems.append(f"{sum(d['cards'].values())} cards")
    return problems, d


def report(key):
    spec, mid, mstyle, code = build(key)
    problems, d = verify(code, mstyle)
    pts = sum(anger_points(dc.text(dc.BY_ID[i])) * n for i, n in d['cards'].items())
    print(f"== {spec['title']} | {spec['mastery']} | {sum(d['cards'].values())} cards | anger points {pts} ({pts / 60:.2f}/card)")
    print('problems:', problems or 'none')
    return code, problems


if __name__ == '__main__':
    bad = False
    for key in DECKS:
        code, problems = report(key)
        (DECKS_DIR / f'cell_jr_{key}.txt').write_text(code + '\n', encoding='utf-8')
        bad |= bool(problems)
    sys.exit(1 if bad else 0)
