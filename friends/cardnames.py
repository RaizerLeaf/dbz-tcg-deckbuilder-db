"""One spelling per card for the pack and for the list checker.

Names are the card names. The few names that belong to more than one distinct card (some Allies: Vegeta, Tenshinhan, Cell Jr.)
are written `Name [code]` where code is the deck-code number (e.g. `Vegeta [HV-U72]`)."""
import collections
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / '_deckbuilder_db' / 'scripts'))
import deckcode as dc  # noqa: E402


def norm(s):
    s = s.replace('’', "'").replace('‘', "'").replace('“', '"').replace('”', '"')
    return re.sub(r'\s+', ' ', s).strip().lower()


def _build():
    by = collections.defaultdict(list)
    for cid in sorted(set(dc.CANONICAL.values())):
        c = dc.BY_ID[cid]
        if dc.ctype(c) != 'Main Personality':
            by[c['card_name']].append(cid)
    display, index = {}, collections.defaultdict(set)
    for name, ids in by.items():
        for cid in ids:
            d = name if len(ids) == 1 else f"{name} [{dc.card_code(dc.BY_ID[cid])}]"
            display[cid] = d
            index[norm(d)].add(cid)
            index[norm(name)].add(cid)      # the bare name still finds it (reported as ambiguous when there are several)
    return display, index


DISPLAY, INDEX = _build()
