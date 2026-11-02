"""Build and verify the Dr. Wheelo comparison decks (Sets 1-7 only). Run from _deckbuilder_db/scripts:
    python build_wheelo_decks.py [key ...]     # writes ../decks/wheelo_<key>.txt and prints a verification report

Dr. Wheelo (Villain): only the Set 3 printings are legal (MC-U61..U64); the promo copies are FanZ-era.
Named cards for Wheelo: Dr. Wheelo's History and Dr. Wheelo's Revival.
Every deck: Time Is A Warrior's Tool x1, Stare Down x2 (Villain), Villainous Visage x1.
"""
import collections
import re
import sys

import deckcode as dc
from build_cell_jr_decks import find, mastery_id, anger_points   # same helpers (find = Sets 1-7 record, app's first printing)

DECKS_DIR = dc.DB / 'decks'
MP_NAME = 'Dr. Wheelo'
MP_LEVELS = ['S03_BST_61', 'S03_BST_62', 'S03_BST_63', 'S03_BST_64']   # Big Brain, Scheming, Confined, Robotic (Set 3)

CORE = {"Time Is A Warrior's Tool": 1, 'Stare Down': 2, 'Villainous Visage': 1}
WHEELO = {"Dr. Wheelo's History": 3, "Dr. Wheelo's Revival": 3}

DECKS = {
    'black_perceptive': dict(
        title='Wheelo Black Perceptive', mastery='Black Perceptive Mastery',
        cards={**CORE, **WHEELO, 'Villainous Energy Sphere': 1,
               'Black Confinement': 3, 'Black Taunt': 2, 'Black Invitation': 2, 'Black Wilt': 2, 'Black Chomp': 2,
               'Black Choke': 2, 'Black Discovery': 1,
               'Black Duck': 3, 'Black Running Guard': 3,
               'Black Energy Web': 2, 'Black Lightning Storm': 2, 'Black Blinding Burst': 2,
               'Black Knee Catch': 3, 'Black Resistance': 3, 'Black Finger Block': 2, 'Black Impediment': 2,
               'Black Corruption': 2, 'Black Easy Block': 2,
               'Black Drain': 2, 'Black Overhead Burst': 2, 'Black Lunge': 3, 'Black Hug Maneuver': 2}),
}

_BLACK = DECKS['black_perceptive']['cards']
DECKS['black_conflict'] = dict(title='Wheelo Black Conflict', mastery='Black Conflict Mastery', cards=dict(_BLACK))

_RED = {**CORE, **WHEELO, 'Villainous Energy Sphere': 1, 'Visiting the Past': 1,
        'Red Static Shot': 3, 'Red Frenzied Blasts': 2, 'Red Surrounded Beams': 2, 'Red Hurl': 3,
        'Red Blocking Hand': 3, 'Red Repel': 2, 'Red Energy Defensive Stance': 2, 'Red Sacrifice': 2,
        'Red Furious Lunge': 2, 'Red Driving Knee': 2, 'Red Jab': 2, 'Red Knee Lift': 2, 'Red Blaze': 2,
        'Red Relaxation': 1, 'Red Burning Rage': 1, 'Red Destiny': 1, 'Red Duck': 2,
        'Red Combined Blast': 2, 'Red Departing Shot': 2, 'Red Energy Outburst': 1, 'Red Counter Kick': 2,
        'Red Chop': 2, 'Red Escape': 1, 'Red Vault': 1, 'Red Scanning Drill': 2, 'Red Takeover': 1}
DECKS['red_ascension_v1'] = dict(title='Wheelo Red Ascension v1', mastery='Red Ascension Mastery', cards=dict(_RED))
# v2: simulator-guided swaps (Energy Sphere, Visiting the Past, Red Escape out; Red Chop, Red Driving Knee, Wall Breaker in)
_RED2 = dict(_RED)
for _n, _d in (('Villainous Energy Sphere', -1), ('Visiting the Past', -1), ('Red Escape', -1),
               ('Red Chop', 1), ('Red Driving Knee', 1), ('Wall Breaker', 1)):
    _RED2[_n] = _RED2.get(_n, 0) + _d
    if _RED2[_n] <= 0:
        del _RED2[_n]
DECKS['red_ascension'] = dict(title='Wheelo Red Ascension', mastery='Red Ascension Mastery', cards=_RED2)
DECKS['red_enraged'] = dict(title='Wheelo Red Enraged', mastery='Red Enraged Mastery', cards=dict(_RED))


def build(key):
    spec = DECKS[key]
    mid = mastery_id(spec['mastery'])
    mstyle = dc.BY_ID[mid]['style']
    cards = collections.Counter()
    for name, n in spec['cards'].items():
        cards[find(name, mstyle)['card_id']] += n
    code = dc.encode(spec['title'], MP_NAME, mid, cards, MP_LEVELS)
    return spec, mid, mstyle, code


def verify(code, mstyle, expect_total=60):
    problems = []
    d = dc.decode(code)
    again = dc.encode(d['name'], d['mp_name'], d['mastery'], d['cards'], d['mp_levels'])
    if again != code:
        problems.append('code does not round-trip')
    err, warn = dc.check(d)
    problems += ['check(): ' + e for e in err] + ['warning: ' + w for w in warn]
    for i, n in d['cards'].items():
        c = dc.BY_ID[i]
        if c['style'] not in (mstyle, 'Freestyle', None) and dc.ctype(c) != 'Dragon Ball':
            problems.append(f"{c['card_name']}: style {c['style']} does not match {mstyle}")
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
    keys = sys.argv[1:] or list(DECKS)
    bad = False
    for key in keys:
        code, problems = report(key)
        (DECKS_DIR / f'wheelo_{key}.txt').write_text(code + '\n', encoding='utf-8')
        bad |= bool(problems)
    sys.exit(1 if bad else 0)
