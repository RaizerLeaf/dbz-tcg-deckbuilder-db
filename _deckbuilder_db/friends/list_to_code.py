"""Turn the plain-text deck list a chat AI produced into a deck code for the owner's web app, and check it.

    python friends/list_to_code.py deck.txt          (or: python friends/list_to_code.py - < deck.txt)

Input format (see friends/INSTRUCTIONS.md):
    Name: My deck
    MP: Piccolo                       ("Vegeta (Villain)" if the name exists for both alignments; keep an app qualifier such as "Trunks (Awakening)" as the app shows it)
    Levels: Stoic, Combat Stance, Unleashed, Fused     (optional)
    Mastery: Red Enraged Mastery
    3 Red Hurl                         ("3x Red Hurl" also works)
    ...
Output: the deck code, then the legality check from scripts/deckcode.py (errors, warnings) and the card count.
Unknown names are listed with close matches. Exit status is 1 if there are errors.
"""
import collections
import difflib
import re
import sys
from pathlib import Path

DB = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(DB / 'scripts'))
import deckcode as dc  # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parent))
import cardnames  # noqa: E402


def norm(s):
    s = s.replace('’', "'").replace('‘', "'").replace('“', '"').replace('”', '"')
    return re.sub(r'\s+', ' ', s).strip().lower()


def name_index():
    idx = collections.defaultdict(set)
    for cid in set(dc.CANONICAL.values()):
        c = dc.BY_ID[cid]
        if dc.ctype(c) != 'Main Personality':
            idx[norm(c['card_name'])].add(cid)
    return idx


def parse(textblock):
    d = {'name': 'Deck', 'mp': None, 'levels': None, 'mastery': None, 'cards': collections.Counter(), 'unknown': [], 'ambiguous': []}
    idx = cardnames.INDEX
    for raw in textblock.splitlines():
        line = raw.strip().strip('`')
        if not line or line.lower().startswith(('total', '```', '#')):
            continue
        m = re.match(r'^(name|mp|levels|mastery)\s*:\s*(.+)$', line, re.I)
        if m:
            k, v = m[1].lower(), m[2].strip()
            if k == 'name': d['name'] = v
            elif k == 'mp':
                q = re.match(r'^(.*?)\s*\(([^)]*)\)\s*$', v)
                if q and q[2].strip().lower() in ('hero', 'villain'):
                    d['mp'] = (q[1].strip(), q[2].strip(), None)
                elif q:                       # an app qualifier such as "Trunks (Awakening)": keep it in the code, look up the base name
                    d['mp'] = (q[1].strip(), None, v)
                else:
                    d['mp'] = (v, None, None)
            elif k == 'levels': d['levels'] = [x.strip() for x in re.split(r'[,;/]', v) if x.strip()]
            else: d['mastery'] = v
            continue
        m = re.match(r'^(\d+)\s*x?\s+(.+?)\s*$', line, re.I)
        if not m:
            d['unknown'].append((line, []))
            continue
        n, nm = int(m[1]), m[2]
        hits = idx.get(norm(nm))
        if not hits:
            close = difflib.get_close_matches(norm(nm), list(idx), n=3, cutoff=0.6)
            d['unknown'].append((line, close))
        elif len(hits) > 1:
            d['ambiguous'].append((line, sorted(hits)))
        else:
            d['cards'][next(iter(hits))] += n
    return d


def find_group(mp, align):
    base = norm(mp)
    hits = [g for g in dc.MPS if norm(g['name']) == base and (not align or g['alignment'].lower() == align.lower())]
    return hits


def resolve_levels(group, subs):
    out = []
    for lv, sub in zip('1234', subs):
        cands = [p for p in group['levels'][lv] if norm(p['subtitle'] or '') == norm(sub) and p['set_number'] and p['set_number'] <= 7
                 and not p['card_id'].startswith('PZP') and '_RST' not in p['card_id']]
        if not cands:
            raise ValueError(f"{group['name']} has no Level {lv} called {sub!r} in Sets 1-7")
        out.append(min(cands, key=lambda p: (p['set_number'], dc._ORDER.get(p['collection'], 3), p['card_id']))['card_id'])
    return out


def convert(textblock):
    d = parse(textblock)
    problems = []
    if not d['mp']:
        return None, ['no "MP:" line']
    mp, align, app_name = d['mp']
    groups = find_group(mp, align)
    if len(groups) != 1:
        return None, [f'MP {mp!r}: ' + ('not found' if not groups else 'exists as Hero and Villain, write "MP: %s (Hero)" or "(Villain)"' % mp)]
    g = groups[0]
    mastery = [i for i in set(dc.CANONICAL.values()) if dc.ctype(dc.BY_ID[i]) == 'Mastery' and norm(dc.BY_ID[i]['card_name']) == norm(d['mastery'] or '')]
    if not mastery:
        close = difflib.get_close_matches(norm(d['mastery'] or ''), [norm(dc.BY_ID[i]['card_name']) for i in set(dc.CANONICAL.values()) if dc.ctype(dc.BY_ID[i]) == 'Mastery'], n=3)
        return None, [f"Mastery {d['mastery']!r} not found" + (f'; close: {close}' if close else '')]
    levels = None
    if d['levels']:
        if len(d['levels']) != 4:
            return None, ['"Levels:" needs exactly 4 names']
        try:
            levels = resolve_levels(g, d['levels'])
        except ValueError as e:
            return None, [str(e)]
    for line, close in d['unknown']:
        problems.append(f'unknown card line {line!r}' + (f' (close: {close})' if close else ''))
    for line, ids in d['ambiguous']:
        problems.append(f'ambiguous name {line!r}: {ids}')
    code = dc.encode(d['name'], app_name or g['name'], mastery[0], d['cards'], levels)
    return (code, g, d), problems


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else '-'
    block = sys.stdin.read() if src == '-' else Path(src).read_text(encoding='utf-8')
    res, problems = convert(block)
    if res is None:
        print('ERRORS:', *problems, sep='\n  ')
        sys.exit(1)
    code, g, d = res
    deck = dc.decode(code)
    err, warn = dc.check(deck)
    print(code)
    print(f"\n{d['name']}: MP {g['name']} ({g['alignment']}), Mastery {dc.BY_ID[deck['mastery']]['card_name']}, {sum(deck['cards'].values())} cards")
    print('ERRORS:', *(problems + err or ['none']), sep='\n  ')
    print('WARNINGS:', *(warn or ['none']), sep='\n  ')
    sys.exit(1 if (problems or err) else 0)


if __name__ == '__main__':
    main()
