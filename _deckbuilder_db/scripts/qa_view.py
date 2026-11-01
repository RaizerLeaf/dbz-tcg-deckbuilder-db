"""qa_view.py OUTDIR id1 id2 ... : review sheets for just these cards (same tile layouts as sheets.py), grouped by tile kind.
Prints the sheet files and which ids are on each."""
import sys
from pathlib import Path
from common import INVENTORY, load_json
import sheets

out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
inv = {r["card_id"]: r for r in load_json(INVENTORY)}
by = {}
for cid in sys.argv[2:]:
    kind, tile = sheets.tile_for(inv[cid])
    by.setdefault(kind, []).append((cid, tile))
n = 0
for kind, items in by.items():
    per, cols = sheets.PLAN[kind]
    for i in range(0, len(items), per):
        chunk = items[i:i + per]
        n += 1
        f = out / f"q{n:02d}_{kind}.png"
        sheets.grid([t for _, t in chunk], cols).save(f)
        print(f.name, [c for c, _ in chunk])
