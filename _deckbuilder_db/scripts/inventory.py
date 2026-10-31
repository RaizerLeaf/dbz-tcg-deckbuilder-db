"""Phase 0/1: list every card image with parsed filename and folder metadata.

Writes work/inventory.json. Safe to re-run; it never touches the images.
"""
import hashlib
import sys
from collections import Counter

from PIL import Image

from common import (COLL_CODES, IMG_EXT, INVENTORY, ROOT, classify_folder,
                    parse_filename, save_json)


def main():
    rows = []
    for p in sorted(ROOT.rglob("*")):
        if not p.is_file() or p.suffix.lower() not in IMG_EXT:
            continue
        rel = p.relative_to(ROOT)
        if rel.parts[0].startswith("_"):
            continue                       # _deckbuilder_db, _rules
        folder = classify_folder(rel.parts[:-1])
        fn = parse_filename(p.stem)
        coll = folder["collection"]
        if fn["prefix"] == "DR":
            coll = "dr"
        num_token = fn["card_number"] or "X"
        if coll == "trait":
            num_token = "T-" + fn["file_name"].replace(" Trait", "").replace(" ", "")
        card_id = f"{folder['set_code']}_{COLL_CODES.get(coll, 'UNK')}_{num_token}"
        if "Restored" in fn["filename_flags"]:
            card_id += "_RST"              # restored image sits beside the original printing
        with Image.open(p) as im:
            w, h = im.size
        rows.append({
            "card_id": card_id,
            **folder,
            "collection": coll,
            "source_folder": str(rel.parent).replace("\\", "/"),
            "filename": p.name,
            "rel_path": str(rel).replace("\\", "/"),
            **fn,
            "width": w, "height": h,
            "orientation": "landscape" if w > h else "portrait",
            "sha1": hashlib.sha1(p.read_bytes()).hexdigest(),
        })

    ids = Counter(r["card_id"] for r in rows)
    for r in rows:                         # disambiguate rare collisions, never drop a file
        if ids[r["card_id"]] > 1:
            r["card_id"] += "_" + r["sha1"][:6]
    assert len({r["card_id"] for r in rows}) == len(rows)
    save_json(INVENTORY, rows)

    print(f"images: {len(rows)}")
    print("collisions resolved:", sum(1 for v in ids.values() if v > 1))
    dup = Counter(r["sha1"] for r in rows)
    print("byte-identical duplicate images:", sum(v - 1 for v in dup.values() if v > 1))
    print("unparsed filenames:", [r["rel_path"] for r in rows if not r["parse_ok"]])
    print("unknown parentheticals:", [(r["rel_path"], r["unparsed_parens"]) for r in rows if r["unparsed_parens"]])
    print("collections:", Counter(r["collection"] for r in rows))
    return 0


if __name__ == "__main__":
    sys.exit(main())
