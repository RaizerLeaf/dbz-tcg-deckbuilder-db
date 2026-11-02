"""Build the files a friend gives to a chat AI so it can help build a deck (PanZ Sets 1-7 only).

    python friends/build_pack.py                         full pack -> friends/dist/   (run from _deckbuilder_db/) (all MPs, all styles)
    python friends/build_pack.py --mp Trunks --styles Red Orange   lighter pack for one MP and the styles worth comparing

Outputs (in friends/dist/):
  deckbuilder_pack.md         INSTRUCTIONS.md + everything below, one file (best for a single upload or paste)
  parts/mps.md, masteries.md, cards_<style>.md   the same data split up
  pack_info.json              counts and rough token estimates

Card data is the "first printing" of each card name, using `text_current` (errata applied), as the deck-code tool does.
"""
import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DB = HERE.parent          # _deckbuilder_db/
ROOT = DB.parent
sys.path.insert(0, str(DB / 'scripts'))
import deckcode as dc  # noqa: E402
sys.path.insert(0, str(HERE))
import cardnames  # noqa: E402

STYLES = ['Black', 'Blue', 'Namekian', 'Orange', 'Red', 'Saiyan', 'Freestyle']


def tokens(s):
    return len(s) // 4          # rough estimate


def text(c):
    return re.sub(r'\s+', ' ', dc.text(c)).strip()


def pool_cards():
    """One record per card name the app knows, excluding MPs and Masteries."""
    ids = sorted(set(dc.CANONICAL.values()))
    out = []
    for i in ids:
        c = dc.BY_ID[i]
        if dc.ctype(c) in ('Main Personality', 'Mastery'):
            continue
        out.append(c)
    return out


def card_line(c, with_style=False):
    parts = [cardnames.DISPLAY.get(c['card_id'], c['card_name']), dc.ctype(c)]
    if with_style:
        parts.append(c['style'] or 'Freestyle')
    lim = c.get('limit_per_deck')
    if lim:
        parts.append(f'limit {lim}')
    if c.get('is_named') and c.get('named_character'):
        parts.append(f"Named {c['named_character']}")
    parts.append(text(c))
    return ' | '.join(parts)


def cards_by_style(cards):
    by = {s: [] for s in STYLES}
    for c in cards:
        st = c['style'] if c['style'] in STYLES else 'Freestyle'
        by[st].append(c)
    for s in by:
        by[s].sort(key=lambda c: (dc.ctype(c), c['card_name']))
    return by


def style_file(style, cards):
    head = [f'## {style} cards ({len(cards)})', 'Format: name | type | [limit] | [Named character] | text. '
            + ('Allies, Dragon Balls and Freestyle cards have no style and can go in any deck (check "Heroes only"/"Villains only").' if style == 'Freestyle'
               else f'Usable with a {style} Mastery (plus the Freestyle list).')]
    body = [card_line(c) for c in cards]
    return '\n'.join(head + body) + '\n'


def legal_printings(group, lv):
    seen, out = set(), []
    for p in group['levels'][lv]:
        if not p['set_number'] or p['set_number'] > 7 or p['card_id'].startswith('PZP') or '_RST' in p['card_id']:
            continue
        pt = re.sub(r'\s+', ' ', p['power_text'] or '').strip()
        key = (p['subtitle'], re.sub(r'\W', '', pt.lower()))
        if key in seen:
            continue
        seen.add(key)
        out.append((p, pt))
    return out


def mps_file(only=None):
    mps = json.loads((DB / 'mps.json').read_text(encoding='utf-8'))['mps']
    out = ['## Main Personalities (Sets 1-7)',
           'Each MP has 4 levels; you choose one printing per level (they may come from different sets). Format: L<level> <subtitle> (Set n): PUR, highest power level | text.', '']
    n = 0
    for g in mps:
        if only and g['name'].lower() != only.lower():
            continue
        if any(not legal_printings(g, lv) for lv in '1234'):
            continue
        n += 1
        heritage = [h for h, ok in g['panz_heritage'].items() if ok]
        extra = []
        if heritage:
            extra.append('heritage list: ' + ', '.join(heritage))
        if g.get('fused_from'):
            extra.append('fused from ' + ' + '.join(g['fused_from']))
        out.append(f"### {g['name']} ({g['alignment']})" + (' - ' + '; '.join(extra) if extra else '') + f"; no Ally named {g['name']}")
        for lv in '1234':
            for p, pt in legal_printings(g, lv):
                top = p['power_stages'][0] if p.get('power_stages') else '?'
                out.append(f"L{lv} {p['subtitle']} (Set {p['set_number']}): PUR {p['pur']}, top power {top:,} | {pt}" if isinstance(top, int)
                           else f"L{lv} {p['subtitle']} (Set {p['set_number']}): PUR {p['pur']} | {pt}")
        out.append('')
    return '\n'.join(out), n


def masteries_file():
    data = json.loads((DB / 'masteries.json').read_text(encoding='utf-8'))['masteries']
    out = ['## Masteries (Sets 1-7)', 'Saiyan / Namekian Masteries need an MP on the matching heritage list. Format: name | style | text.', '']
    n = 0
    for m in sorted(data, key=lambda m: (m['style'] or '', m['name'])):
        prints = [p for p in m['printings'] if p['set_number'] and p['set_number'] <= 7 and '_RST' not in p['card_id'] and not p['card_id'].startswith('PZP')]
        if not prints:
            continue
        p = prints[0]
        n += 1
        out.append(f"{m['name']} | {m['style']} | {re.sub(chr(10), ' ', (p['text_current'] or p['text_as_printed'] or '')).strip()}")
    return '\n'.join(out) + '\n', n


def build(mp=None, styles=None, outdir=None):
    outdir = Path(outdir or HERE / 'dist')
    parts = outdir / 'parts'
    parts.mkdir(parents=True, exist_ok=True)
    for f in parts.glob('*.md'):
        f.unlink()
    cards = pool_cards()
    by = cards_by_style(cards)
    chosen = [s for s in STYLES if s == 'Freestyle' or not styles or s in styles]
    mps_text, n_mps = mps_file(mp)
    mast_text, n_mast = masteries_file()
    if styles:
        keep = {s.title() for s in styles}
        mast_text = '\n'.join(l for l in mast_text.split('\n') if '|' not in l or l.split('|')[1].strip() in keep or l.startswith('Format')) + '\n'
    files = {'mps.md': mps_text, 'masteries.md': mast_text}
    for s in chosen:
        files[f'cards_{s.lower()}.md'] = style_file(s, by[s])
    for name, body in files.items():
        (parts / name).write_text(body, encoding='utf-8')
    scope = 'FULL pack: every MP and every style.' if not (mp or styles) else \
        f"LIGHT pack for {mp or 'all MPs'}; styles included: {', '.join(chosen)} (ask me to rebuild the pack if you want to compare another style)."
    instructions = (HERE / 'INSTRUCTIONS.md').read_text(encoding='utf-8')
    pack = instructions + f'\n{scope}\n\n' + '\n'.join(files[n] for n in files)
    (outdir / 'deckbuilder_pack.md').write_text(pack, encoding='utf-8')
    info = {'scope': scope, 'mps': n_mps, 'masteries': n_mast, 'cards': {s: len(by[s]) for s in chosen},
            'tokens_est': {'whole pack': tokens(pack), **{n: tokens(b) for n, b in files.items()}, 'instructions': tokens(instructions)}}
    (outdir / 'pack_info.json').write_text(json.dumps(info, indent=2), encoding='utf-8')
    return info


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--mp', help='only this MP name (all levels)')
    ap.add_argument('--styles', nargs='*', help='only these styles (Freestyle is always included)')
    ap.add_argument('--out', help='output folder (default friends/dist)')
    a = ap.parse_args()
    info = build(a.mp, a.styles, a.out)
    print(json.dumps(info, indent=2))


if __name__ == '__main__':
    main()
