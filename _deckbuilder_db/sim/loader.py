"""Turn a deck code (or a decks/*.txt file) into an engine Spec, using scripts/deckcode.py for the decoding."""
import sys
from pathlib import Path
from .engine import Spec
from .cardmodel import records_by_id

SCRIPTS = Path(__file__).resolve().parent.parent / 'scripts'


def _deckcode():
    sys.path.insert(0, str(SCRIPTS))
    try:
        import deckcode
    except ImportError as e:
        raise SystemExit('scripts/deckcode.py is needed to read deck codes (it lives on the deck-code branch until merged): ' + str(e))
    return deckcode


def read_code(arg):
    p = Path(arg)
    if arg.endswith('.txt') or (len(arg) < 300 and p.exists()):
        return p.read_text(encoding='utf-8').strip().splitlines()[0].strip()
    return arg.strip()


def default_levels(dc, group):
    """Earliest legal printing of each level (Sets 1-7, no promos / Restored), like the app's default."""
    out = []
    for lv in '1234':
        cands = [p for p in group['levels'][lv] if p['set_number'] and p['set_number'] <= 7
                 and not p['card_id'].startswith('PZP') and '_RST' not in p['card_id']]
        if not cands:
            raise ValueError(f"{group['name']} has no Sets 1-7 printing for Level {lv}")
        out.append(min(cands, key=lambda p: (p['set_number'], dc._ORDER.get(p['collection'], 3), p['card_id']))['card_id'])
    return out


def load(arg, no_mppv=False):
    dc = _deckcode()
    d = dc.decode(read_code(arg))
    g = dc.mp_group(d)
    if g is None:
        raise ValueError(f"cannot identify the MP for {d['mp_name']!r}; give an explicit printings field in the code")
    levels = d['mp_levels'] or default_levels(dc, g)
    recs = records_by_id()
    ids = []
    for cid, n in d['cards'].items():
        ids += [cid] * n
    return Spec(d['name'], g['name'], levels, recs[d['mastery']]['card_name'], ids, no_mppv)
