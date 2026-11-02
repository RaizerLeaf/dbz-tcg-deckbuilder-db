"""Encode, decode and check deck codes for the owner's deck-builder web app.

Format (worked out from three codes the owner exported, see SAMPLE_CODES):
    D1.<deck name>.<MP name>.<Mastery>[._<L1>_<L2>_<L3>_<L4>].<card>.<card>...
- Names are URL-encoded, with '.' written as %2E ("redder%20Pic%201%2E0", "Trunks%20%28Awakening%29").
- Every card (Mastery and MP printings included) is <set prefix>-<printed number>, with the rarity letter kept:
  C58 (Set 1), HV-C137, MC-R125, EV-S11, PF-C54, VG-U83, AW-C54, UR162, P8.
  Set 1 has no prefix. Set 7 DR cards use S (DR10 -> AW-S10).
- The MP printings field is optional (one printing per level).
- Cards are written <code>*N for N copies and sorted as plain text.

Usage (from _deckbuilder_db/scripts):
    python deckcode.py decode "<code>"     list the cards in a code
    python deckcode.py check "<code>"      decode and run the legality checklist
    python deckcode.py test                round-trip the sample codes
"""
import collections
import json
import re
import sys
import urllib.parse
from pathlib import Path

DB = Path(__file__).resolve().parent.parent
PREFIX = {1: '', 2: 'HV', 3: 'MC', 4: 'EV', 5: 'PF', 6: 'VG', 7: 'AW'}

SAMPLE_CODES = [  # exported by the owner's app; their decoded lists matched the owner's screenshots
    'D1.Broly.Broly.S25.AW-C54*2.C58*2.EV-C47*3.EV-R119*2.HV-R128*3.HV-U94.HV-U95*2.MC-R125*3.PF-C54*2.PF-C55*3.'
    'R146*2.R147*3.R148*2.S130*3.S149*3.S83*3.S95*3.UR162.UR164.VG-C51*2.VG-C53*3.VG-R128.VG-R137*3.VG-R138*3.'
    'VG-U83.VG-U97*2.VG-U98',
    'D1.redder%20Pic%201%2E0.Piccolo.S27._EV-S11_S22_S23_S24.C1.C2.C3.C46*3.C49*3.C50*3.HV-C44*2.HV-C47*3.HV-C48*3.'
    'MC-R118*2.R121.R152.S119*3.S120*3.S139*3.S148*3.S35*2.S49*3.S60*3.S69*3.S80*3.S94*2.U107*2.U119*3.U61.U62.U63',
    'D1.Orange%20Trunks%20V2.Trunks%20%28Awakening%29.AW-S10._VG-U76_EV-S2_U64_EV-S4.AW-C32.AW-C37.AW-R119*3.'
    'AW-R139*3.AW-U93.C36.C41*2.C42*2.MC-C37*2.MC-R115*3.MC-U90.PF-C39*2.PF-C42.PF-R110.PF-R111*2.PF-R113*3.'
    'PF-R128*2.PF-U93.R139.R150*2.R152.R159*3.S101.S107*3.S128.S138*2.S42.S78*2.S99.U95.UR163.VG-C39*2.VG-R115.'
    'VG-R118*2.VG-R119*3',
]

CARDS = json.loads((DB / 'cards.json').read_text(encoding='utf-8'))
MPS = json.loads((DB / 'mps.json').read_text(encoding='utf-8'))['mps']
BY_ID = {c['card_id']: c for c in CARDS}


def text(c):
    return c.get('text_current') or c['text_as_printed'] or ''


def ctype(c):
    return c.get('card_type_current') or c['card_type']


def card_code(c):
    s = c['set_number']
    if not s or s > 7:
        raise ValueError(f"{c['card_id']}: only Sets 1-7 have app codes")
    n = c['card_number']
    if n.startswith('DR'):
        n = 'S' + n[2:]
    return f'{PREFIX[s]}-{n}' if PREFIX[s] else n


def _index():
    idx = {}
    for c in sorted(CARDS, key=lambda c: '_RST' in c['card_id']):  # prefer the non-Restored record
        if c['set_number'] and c['set_number'] <= 7:
            k = card_code(c)
            if k in idx and BY_ID[idx[k]]['card_name'] != c['card_name']:
                raise ValueError(f'code {k} is ambiguous: {idx[k]} / {c["card_id"]}')
            idx.setdefault(k, c['card_id'])
    return idx


INDEX = _index()


def quote(s):
    return urllib.parse.quote(s, safe='').replace('.', '%2E')


def encode(name, mp_name, mastery_id, cards, mp_levels=None):
    """cards: {card_id: copies}; mp_levels: optional [L1, L2, L3, L4] card_ids."""
    parts = ['D1', quote(name), quote(mp_name), card_code(BY_ID[mastery_id])]
    if mp_levels:
        parts.append('_' + '_'.join(card_code(BY_ID[i]) for i in mp_levels))
    toks = [card_code(BY_ID[i]) + (f'*{n}' if n > 1 else '') for i, n in cards.items()]
    return '.'.join(parts + sorted(toks))


def decode(code):
    p = code.strip().split('.')
    if p[0] != 'D1' or len(p) < 5:
        raise ValueError('not a D1 deck code')
    deck = {'name': urllib.parse.unquote(p[1]), 'mp_name': urllib.parse.unquote(p[2]),
            'mastery': INDEX[p[3]], 'mp_levels': None, 'cards': collections.Counter()}
    rest = p[4:]
    if rest and rest[0].startswith('_'):
        deck['mp_levels'] = [INDEX[k] for k in rest.pop(0)[1:].split('_')]
    for t in rest:
        k, _, n = t.partition('*')
        if k not in INDEX:
            raise ValueError(f'unknown card code {k}')
        deck['cards'][INDEX[k]] += int(n or 1)
    return deck


def mp_group(deck):
    if deck['mp_levels']:
        ids = set(deck['mp_levels'])
        for g in MPS:
            if ids <= {p['card_id'] for lv in g['levels'].values() for p in lv}:
                return g
    base = re.sub(r'\s*\(.*\)$', '', deck['mp_name'])  # "Trunks (Awakening)" -> "Trunks"
    hits = [g for g in MPS if g['name'] == base]
    return hits[0] if len(hits) == 1 else None


def check(deck):
    """Returns (errors, warnings) for CLAUDE.md's default assumptions."""
    err, warn = [], []
    g = mp_group(deck)
    if not g:
        return [f"cannot find the MP group for {deck['mp_name']!r}"], warn
    mp, align = g['name'], g['alignment']
    mastery = BY_ID[deck['mastery']]
    if ctype(mastery) != 'Mastery':
        err.append(f"{mastery['card_name']} is not a Mastery")
    if mastery['style'] in ('Saiyan', 'Namekian') and not g['panz_heritage'].get(mastery['style']):
        err.append(f"{mp} is not on the {mastery['style']} heritage list")
    if deck['mp_levels']:
        for lv, i in zip('1234', deck['mp_levels']):
            if i not in [p['card_id'] for p in g['levels'][lv]]:
                err.append(f'MP printing {card_code(BY_ID[i])} is not {mp} Level {lv}')
    total = sum(deck['cards'].values())
    if total != 60:
        err.append(f'{total} cards, not 60')
    names = collections.Counter()
    other_align = 'Heroes' if align == 'Villain' else 'Villains'
    for i, n in deck['cards'].items():
        c = BY_ID[i]
        nm = c['card_name']
        names[nm] += n
        if '_RST' in i:
            err.append(f'{nm}: Restored copy')
        if ctype(c) in ('Main Personality', 'Mastery'):
            err.append(f'{nm}: {ctype(c)} in the Life Deck')
        if other_align in c['restrictions']:
            err.append(f'{nm}: {other_align} only')
        for r in c['restrictions']:
            if r.endswith('Mastery') and r != mastery['card_name']:
                err.append(f'{nm}: {r} only')
        if c['is_named'] and c['named_character'] and c['named_character'] != mp:  # 'considered Named' cards have none
            err.append(f"{nm}: Named {c['named_character']}, MP is {mp}")
        if ctype(c) == 'Ally' and nm in (g['cannot_include_allies_named'] or []):
            err.append(f'{nm}: Ally with the MP name')
    for nm, n in names.items():
        c = BY_ID[next(i for i in deck['cards'] if BY_ID[i]['card_name'] == nm)]
        lim = 1 if ctype(c) in ('Ally', 'Dragon Ball') else 3
        m = re.search(r'limit (\d+) per deck', text(c), re.I)
        for v in (c['limit_per_deck'], int(m.group(1)) if m else None):
            if v:
                lim = min(lim, v)
        if n > lim:
            err.append(f'{nm} x{n}, limit {lim}')
    dbsets = {nm.split(' Dragon Ball')[0] for nm in names if ' Dragon Ball ' in nm}
    if len(dbsets) > 1:
        err.append(f'more than one Dragon Ball set: {sorted(dbsets)}')
    if names["Time Is A Warrior's Tool"] != 1:
        warn.append("Time Is A Warrior's Tool is not x1")
    want = 'Confrontation' if align == 'Hero' else 'Stare Down'
    if names[want] < 2:
        warn.append(f'fewer than 2 {want}')
    return err, warn


def show(deck):
    print(f"{deck['name']} | MP {deck['mp_name']} | Mastery {BY_ID[deck['mastery']]['card_name']}")
    if deck['mp_levels']:
        for i in deck['mp_levels']:
            c = BY_ID[i]
            print(f"  L{c['level']} {card_code(c):8} {c['card_name']} - {c['subtitle']}")
    for i, n in sorted(deck['cards'].items(), key=lambda kv: (ctype(BY_ID[kv[0]]), BY_ID[kv[0]]['card_name'])):
        c = BY_ID[i]
        print(f"  {n}x {card_code(c):9} {ctype(c):16} {c['card_name']}")
    print(f"  total {sum(deck['cards'].values())}")


def test():
    for code in SAMPLE_CODES:
        d = decode(code)
        again = encode(d['name'], d['mp_name'], d['mastery'], d['cards'], d['mp_levels'])
        assert again == code, f'round trip failed:\n{code}\n{again}'
        err, warn = check(d)
        print(f"ok  {d['name']}: {sum(d['cards'].values())} cards, errors {err or 'none'}, warnings {warn or 'none'}")


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'test'
    if cmd == 'test':
        test()
    else:
        d = decode(sys.argv[2])
        show(d)
        if cmd == 'check':
            e, w = check(d)
            print('ERRORS:', e or 'none')
            print('WARNINGS:', w or 'none')
