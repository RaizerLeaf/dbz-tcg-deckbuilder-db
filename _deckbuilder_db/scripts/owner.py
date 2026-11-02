"""Apply the owner's answers (work/owner_rulings.json) to cards.json. Run after crd.py, before mps.py.

- stays_as_printed_type: clear needs_review, record the ruling (card type stays as printed).
- type_error: card_type_current set (card_type stays what the image prints).
- icon_error: text_current gets the corrected icon; text_as_printed stays as printed.
- placeholder_copy_from_original: the image is 'Image N/A'; text/type etc. are copied from the named original printing.
- restored_is_newer_ruling: clear needs_review, record the ruling.
- exclude_never_released: promos that never came out (S04 P9 Blue Guard, S04 P10 Namekian Mouth Beam; the image is an 'Image N/A'
  placeholder). They are removed from cards.json/csv and listed in excluded_cards.json with the printing to use instead.
- exclude_use_restored_instead: the 'NEVER OFFICIALLY RELEASED' overlay cards are removed from cards.json/csv and listed
  in excluded_cards.json (their '(Restored)' copy is the record to use).
New fields: owner_ruling (text), errata_status 'owner_correction' for icon/type fixes.
"""
import csv
import json
import re
import sys

from common import DB, load_json, save_json
from derive import ICONS


def icons_of(t):
    return sorted({i for i in ICONS if f"[{i}]" in t}) + [f"Trait:{t2}" for t2 in sorted(set(re.findall(r"\[Trait:([^\]]+)\]", t)))]


def main():
    R = load_json(DB / "work" / "owner_rulings.json")
    cards = load_json(DB / "cards.json")
    by = {c["card_id"]: c for c in cards}
    for c in cards:
        c.setdefault("owner_ruling", None)

    def clear(c, msg):
        c["needs_review"], c["review_reason"] = False, None
        c["owner_ruling"] = msg

    for cid, words in R["stays_as_printed_type"].items():
        c = by[cid]
        clear(c, f"Owner ruling 2026-11-02: \"{words}\" (printed type kept although the text/icons do not match it).")

    for cid, r in R["type_error"].items():
        c = by[cid]
        clear(c, f"Owner ruling 2026-11-02: \"{r['owner_words']}\". Printed type is {c['card_type']}; treated as {r['card_type_current']} "
                 f"({r['basis']}).")
        c["card_type_current"] = r["card_type_current"]
        c["errata_status"] = "owner_correction"
        c["errata_note"] = c["owner_ruling"]
        c["text_current"] = c["text_as_printed"]

    for cid, r in R["icon_error"].items():
        c = by[cid]
        assert r["from"] in c["text_as_printed"], cid
        c["text_current"] = c["text_as_printed"].replace(r["from"], r["to"], 1)
        clear(c, f"Owner ruling 2026-11-02: \"{r['owner_words']}\". The printed icon is wrong; text_current shows the corrected icon "
                 f"('{r['from']}' -> '{r['to']}').")
        c["errata_status"] = "owner_correction"
        c["errata_note"] = c["owner_ruling"]
        c["icons"] = icons_of(c["text_current"])

    for cid, r in R["placeholder_copy_from_original"].items():
        c, s = by[cid], by[r["source"]]
        for k in ("card_type", "text_as_printed", "text_current", "stage_cost", "limit_per_deck", "limit_per_deck_printed", "restrictions",
                  "deck_rules", "icons", "keywords", "errata_status", "ruling_note", "crd_entries", "is_mrp"):
            c[k] = json.loads(json.dumps(s[k]))
        c["is_mrp"] = True  # the CRD names Evolution P9 / P10 as the most recent printings
        c["errata_note"] = ("Image is an 'Image N/A' placeholder. Text copied from " + s["card_id"] + " (" + s["filename"] + ") on the owner's "
                            "instruction. " + (s["errata_note"] or ""))
        c["vision_confidence"] = "copied"
        clear(c, f"Owner ruling 2026-11-02: \"{r['owner_words']}\". text_as_printed, card type and rules fields are copied from {s['card_id']}; "
                 "the CRD names this promo as a most recent printing (MRP) of the card, so the real card may print the CRD's corrected wording.")
        c["notes"] = ((c.get("notes") or "") + " | text copied from " + s["card_id"]).strip(" |")

    for cid, msg in R["restored_is_newer_ruling"].items():
        clear(by[cid], f"Owner ruling 2026-11-02: \"{msg}\"")

    ex = []
    for cid, rep in R["exclude_use_restored_instead"].items():
        if cid.startswith("_"):
            continue
        c = by.pop(cid)
        assert rep in by, rep
        ex.append({"card_id": cid, "filename": c["filename"], "source_folder": c["source_folder"], "use_instead": rep,
                   "reason": "Image is overlaid with 'NEVER OFFICIALLY RELEASED' and most text is hidden. Owner (2026-11-02): ignore these "
                             "and use the Restored versions instead."})
    for cid, rep in R.get("exclude_never_released", {}).items():
        if cid.startswith("_"):
            continue
        c = by.pop(cid)
        assert rep in by, rep
        ex.append({"card_id": cid, "filename": c["filename"], "source_folder": c["source_folder"], "use_instead": rep,
                   "reason": "Never released: the CRD names this promo as a most recent printing, but the owner (2026-11-02) says it never came "
                             "out. The image is an 'Image N/A' placeholder. Use the original printing instead."})
    out = [c for c in cards if c["card_id"] in by]
    save_json(DB / "excluded_cards.json", ex)
    save_json(DB / "cards.json", out)
    with open(DB / "cards.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0].keys()))
        w.writeheader()
        for c in out:
            w.writerow({k: (json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict)) else v) for k, v in c.items()})
    print(f"{len(out)} cards ({len(ex)} excluded); needs_review now {sum(c['needs_review'] for c in out)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
