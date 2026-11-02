"""Build the static page (GitHub Pages) from the card database.

    python friends/build_site.py          (run from _deckbuilder_db/)  ->  ../docs/

Sources: friends/site/{index.html,app.js,core.js,style.css}; data comes from cards.json / mps.json / masteries.json through scripts/deckcode.py,
so the page uses exactly the cards, codes and rules of the Python tools. `docs/` is generated output; never edit it by hand.
GitHub Pages can only publish the repository root or /docs, which is why this one folder sits outside _deckbuilder_db/.
"""
import json
import re
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
DB = HERE.parent
sys.path.insert(0, str(DB / 'scripts'))
sys.path.insert(0, str(HERE))
import deckcode as dc        # noqa: E402
import build_pack as bp      # noqa: E402
import cardnames             # noqa: E402

GLOBAL_OUT = DB.parent / 'docs'


def card_limit(c):
    lim = 1 if dc.ctype(c) in ('Ally', 'Dragon Ball') else 3
    m = re.search(r'limit (\d+) per deck', dc.text(c), re.I)
    for v in (c.get('limit_per_deck'), int(m.group(1)) if m else None):
        if v:
            lim = min(lim, v)
    return lim


def build_data():
    cards, masteries = [], []
    for cid in sorted(set(dc.CANONICAL.values())):
        c = dc.BY_ID[cid]
        t = dc.ctype(c)
        if t == 'Main Personality':
            continue
        rec = {'id': cid, 'name': c['card_name'], 'disp': cardnames.DISPLAY.get(cid, c['card_name']), 'type': t, 'style': c['style'] or 'Freestyle',
               'text': re.sub(r'\s+', ' ', dc.text(c)).strip(), 'restr': list(c['restrictions']), 'code': dc.card_code(c), 'set': c['set_number']}
        if t == 'Mastery':
            rec['style'] = c['style']
            masteries.append(rec)
        else:
            rec['lim'] = card_limit(c)
            rec['named'] = c['named_character'] if (c.get('is_named') and c.get('named_character')) else None
            cards.append(rec)
    mps = []
    for g in dc.MPS:
        levels = {}
        for lv in '1234':
            levels[lv] = []
            for p in g['levels'][lv]:
                if not p['set_number'] or p['set_number'] > 7 or p['card_id'].startswith('PZP') or '_RST' in p['card_id']:
                    continue
                levels[lv].append({'id': p['card_id'], 'code': dc.card_code(dc.BY_ID[p['card_id']]), 'sub': p['subtitle'], 'set': p['set_number'],
                                   'order': dc._ORDER.get(p['collection'], 3), 'pur': p['pur'],
                                   'top': (p.get('power_stages') or [None])[0], 'text': re.sub(r'\s+', ' ', p['power_text'] or '').strip()})
        if all(levels[lv] for lv in '1234'):
            mps.append({'name': g['name'], 'alignment': g['alignment'], 'heritage': g['panz_heritage'], 'noAlly': g['cannot_include_allies_named'] or [],
                        'fused': g.get('fused_from'), 'levels': levels})
    alias = {}
    for code, k in dc.INDEX.items():
        c = dc.BY_ID[k]
        if dc.ctype(c) == 'Main Personality':
            continue
        canon = dc.CANONICAL.get(k)
        if canon and canon != k:
            alias[code] = canon
    return {'cards': cards, 'masteries': masteries, 'mps': mps, 'alias': alias}


def build_parts():
    cards = bp.pool_cards()
    by = bp.cards_by_style(cards)
    mps_all, _ = bp.mps_file(None)
    names = sorted({g['name'] for g in dc.MPS})
    by_name = {}
    for n in names:
        txt, count = bp.mps_file(n)
        if count:
            by_name[n] = txt
    mast, _ = bp.masteries_file()
    header = bp.mps_file('__none__')[0]
    return {'instructions': (HERE / 'INSTRUCTIONS.md').read_text(encoding='utf-8'), 'mpsAll': mps_all, 'mpsByName': by_name, 'mpsHeader': header,
            'masteries': mast, 'cards': {s: bp.style_file(s, by[s]) for s in bp.STYLES}}


def single_file(data, parts):
    """One self-contained HTML file (no server, works from disk): css, js and data inlined."""
    def safe(js):
        return js.replace('</', '<\\/')
    html = (HERE / 'site' / 'index.html').read_text(encoding='utf-8')
    css = (HERE / 'site' / 'style.css').read_text(encoding='utf-8')
    core = (HERE / 'site' / 'core.js').read_text(encoding='utf-8')
    app = (HERE / 'site' / 'app.js').read_text(encoding='utf-8')
    inline = 'window.DBZ_INLINE = ' + safe(json.dumps({'cards': data, 'parts': parts}, ensure_ascii=False, separators=(',', ':'))) + ';'
    html = html.replace('<link rel="stylesheet" href="style.css">', '<style>\n' + css + '</style>')
    html = html.replace('<script src="core.js"></script>', '<script>\n' + inline + '\n</script>\n<script>\n' + safe(core) + '\n</script>')
    html = html.replace('<script src="app.js"></script>', '<script>\n' + safe(app) + '\n</script>')
    return html


def main(out=None):
    OUT = Path(out) if out else GLOBAL_OUT
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'data').mkdir(exist_ok=True)
    (OUT / 'packs').mkdir(exist_ok=True)
    data = build_data()
    parts = build_parts()
    (OUT / 'data' / 'cards.json').write_text(json.dumps(data, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    (OUT / 'data' / 'pack_parts.json').write_text(json.dumps(parts, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    for f in ('index.html', 'app.js', 'core.js', 'style.css'):
        shutil.copyfile(HERE / 'site' / f, OUT / f)
    (OUT / '.nojekyll').write_text('', encoding='utf-8')
    (OUT / 'deck-helper.html').write_text(single_file(data, parts), encoding='utf-8')
    with tempfile.TemporaryDirectory() as t:
        bp.build(outdir=t)
        shutil.copyfile(Path(t) / 'deckbuilder_pack.md', OUT / 'packs' / 'deckbuilder_pack_full.md')
    sizes = {p.name: p.stat().st_size for p in sorted(OUT.rglob('*')) if p.is_file()}
    print(json.dumps({'cards': len(data['cards']), 'masteries': len(data['masteries']), 'mps': len(data['mps']), 'files(bytes)': sizes}, indent=1))


if __name__ == '__main__':
    main()
