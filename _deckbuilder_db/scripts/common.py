"""Shared paths and filename/folder parsing for the DBZ TCG deckbuilder database.

Original card images are only ever read, never written.
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]          # ...\Master PanZ & FanZ Sets
DB = ROOT / "_deckbuilder_db"
CACHE = DB / "cache"                                 # one JSON per image: <card_id>.json
OCR_CACHE = CACHE / "ocr"
VISION_DIR = DB / "work" / "vision"                  # vision transcriptions (JSONL batches)
SHEETS = DB / "work" / "sheets"                      # review sheets for the vision pass
INVENTORY = DB / "work" / "inventory.json"

IMG_EXT = {".jpg", ".jpeg", ".png"}
KNOWN_FLAGS = {"CRD", "Errata", "Frozen", "Restored", "SDCC"}

# Spelling as printed by the publisher; folder spelling is kept in source_folder.
SET_NAMES = {
    1: "Premiere", 2: "Heroes & Villains", 3: "Movie Collection", 4: "Evolution",
    5: "Perfection", 6: "Vengeance", 7: "Awakening", 8: "Celestial Tournament",
    9: "Legends", 10: "Revelation", 11: "Escalation", 12: "Movie Collection 2",
    13: "Fusion", 14: "Showdown", 15: "Movie Collection 3", 16: "Super Premier",
    17: "Universal Clash", 18: "Incursion", 19: "Judgement",
}

COLL_CODES = {"booster": "BST", "starter": "STR", "promo": "PRO", "trait": "TRT",
              "op": "OP", "promo_mp": "MP", "promo_ally": "AL", "dr": "DR"}

FILE_RE = re.compile(r"^(?P<pre>[A-Za-z]*)(?P<num>\d+)?(?P<suf>[A-Z])?_(?P<rest>.+)$")


def parse_filename(stem):
    """Split 'S08_Goku - Super Saiyan (CRD)' into number, name, subtitle and flags."""
    m = FILE_RE.match(stem)
    if not m:
        return {"prefix": None, "number": None, "card_number": None, "name_part": stem,
                "file_name": stem, "file_subtitle": None, "filename_flags": [],
                "unparsed_parens": [], "parse_ok": False}
    pre, num, rest = m["pre"], m["num"], m["rest"].strip()
    if num and m["suf"]:
        num_suffix = m["suf"]            # e.g. 42B, P121A: variant letter on the number
    else:
        num_suffix = ""
    flags, unknown = [], []
    while True:
        pm = re.search(r"\s*\(([^)]*)\)\s*$", rest)
        if not pm:
            break
        if pm[1].strip() in KNOWN_FLAGS:
            flags.insert(0, pm[1].strip())
            rest = rest[: pm.start()].rstrip()
        else:
            unknown.insert(0, pm[1].strip())
            break
    name, sub = (rest.split(" - ", 1) + [None])[:2] if " - " in rest else (rest, None)
    return {"prefix": pre or None, "number": int(num) if num else None,
            "card_number": f"{pre}{num}{num_suffix}" if num else pre,
            "name_part": rest, "file_name": name.strip(),
            "file_subtitle": sub.strip() if sub else None,
            "filename_flags": flags, "unparsed_parens": unknown, "parse_ok": True}


def classify_folder(rel_parts):
    """rel_parts: path parts relative to ROOT, excluding the filename."""
    top = rel_parts[0]
    sub = rel_parts[1] if len(rel_parts) > 1 else ""
    m = re.match(r"^(\d+)_Set (\d+)", top)
    if m:
        n = int(m[2])
        if "(Booster)" in sub:
            coll = "booster"
        elif "(Starter" in sub:
            coll = "starter"
        elif "(Promos)" in sub:
            coll = "promo"
        elif "(Traits)" in sub:
            coll = "trait"
        elif "(" not in sub:
            coll = "booster"          # Sets 8+ name the main set folder without "(Booster)"
        else:
            coll = "unknown"
        return {"set_number": n, "set_name": SET_NAMES.get(n), "set_code": f"S{n:02d}",
                "era": "PanZ" if n <= 7 else "FanZ", "collection": coll}
    if top.startswith("z_OP Series"):
        return {"set_number": None, "set_name": sub, "set_code": sub,
                "era": "FanZ", "collection": "op"}
    if top.startswith("zz_PanZ MP & Ally Promos"):
        return {"set_number": None, "set_name": "PanZ MP & Ally Promos", "set_code": "PZP",
                "era": "FanZ", "collection": "promo_mp" if sub == "MPs" else "promo_ally"}
    return {"set_number": None, "set_name": None, "set_code": "UNK", "era": None,
            "collection": "unknown"}


def load_json(p, default=None):
    p = Path(p)
    if not p.exists():
        return default
    return json.loads(p.read_text(encoding="utf-8"))


def save_json(p, obj):
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(p)
