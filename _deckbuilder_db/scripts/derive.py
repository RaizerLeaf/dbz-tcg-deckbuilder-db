"""Build card records (brief schema) from cache/<card_id>.json and compare OCR with vision.

Reads the merged cache written by ingest.py. Derives style, named, icons, keywords, limits,
restrictions and sanity checks; never invents card text (text_current / errata / rulings stay
null until Phase 3).

Usage: python derive.py [--sets S01,S14,PZP] [--out work/pilot]
Writes <out>/cards.json, <out>/cards.csv, <out>/ocr_compare.json
"""
import argparse
import csv
import difflib
import json
import re
import sys
from pathlib import Path

from common import CACHE, DB, load_json, save_json

STYLES = ("Black", "Blue", "Namekian", "Orange", "Red", "Saiyan")
PERSONALITY = ("Main Personality", "Ally", "Personality")
ICONS = ("Attack", "Defense", "Continuous", "Instant", "Desperation")
KEYWORDS = ("Focused", "Unstoppable", "Unpreventable", "Unmodifiable")
NOT_NAMES = {"It"}                      # "It's Over 9,000!" is not a Named card

FIELDS = ["card_id", "set_number", "set_name", "era", "source_folder", "collection",
          "card_number", "filename", "filename_flags", "card_name", "subtitle", "card_type",
          "style", "is_named", "named_character", "alignment", "rarity", "level",
          "power_stages", "pur", "traits", "icons", "keywords", "limit_per_deck",
          "restrictions", "deck_rules", "text_as_printed", "text_current", "errata_note",
          "ruling_note", "frozen", "gold_title_reprint", "is_mrp", "ocr_confidence",
          "ocr_agreement", "filename_issue", "needs_review", "review_reason", "notes"]


def norm_name(s):
    s = (s or "").lower().replace("’", "'").replace("-", " ")
    return re.sub(r"[^a-z0-9]+", "", s)


def parentheticals(text):
    return re.findall(r"\(([^()]*)\)", text or "")


def derive_restrictions(text):
    """Deck-building restrictions stated as '(X only.)' sentences inside parentheses."""
    out, deck_rules = [], []
    for par in parentheticals(text):
        for sent in re.split(r"(?<=\.)\s+", par.strip()):
            s = sent.strip().rstrip(".")
            m = re.match(r"^(.+?) only$", s)
            if m and not s.lower().startswith("use only"):
                out.append(m[1])
            if re.search(r"Life Deck (cannot|may) include", s):
                deck_rules.append(s + ".")
    return out, deck_rules


def derive(rec):
    inv, v, o = rec["inventory"], rec["vision"], rec["ocr"]
    text = v.get("text") or ""
    name = v.get("name") or ""
    ctype = v.get("type")
    reasons = [v["review"]] if v.get("review") else []

    first = name.split(" ")[0] if name else ""
    if ctype in PERSONALITY:
        style = None
    else:
        style = first if first in STYLES else "Freestyle"

    m = re.match(r"^(.+?)['’]s?\s", name)
    named = m[1] if m and m[1] not in NOT_NAMES else None
    is_named = bool(named) or bool(re.search(r"considered (a )?(Styled and )?Named", text))

    icons = sorted({i for i in ICONS if f"[{i}]" in text})
    traits_inline = sorted(set(re.findall(r"\[Trait:([^\]]+)\]", text)))
    kw = [k for k in KEYWORDS if re.search(rf"\b{k}\b", text)]
    for k in ("Remain", "Foresee"):
        kw += [f"{k} {n}" for n in re.findall(rf"\b{k} (\d+)", text)]
    end = re.search(r"\bENDURANCE (\d+)", text)
    if end:
        kw.append(f"Endurance {end[1]}")
    if re.search(r"Banish after use", text):
        kw.append("Banish after use")
    cost = re.search(r"\[Attack\] (\d+): ", text) or re.search(r"costing (\d+) stages?", text)
    lim = re.search(r"Limit (\d+) per deck", text)
    restrictions, deck_rules = derive_restrictions(text)

    num = v.get("num") or ""
    rm = re.match(r"^(?:BONUS |PREVIEW )?(UR|DR|C|U|R|S|P)\d", num)
    rarity = rm[1] if rm else None          # printed code; S = starter deck, DR = alternate-art tier

    # --- checks against the filename and the layout rules ---------------------------
    fname_issues = []
    if norm_name(name) != norm_name(inv["file_name"]):
        fname_issues.append(f"name differs from filename: '{name}' vs '{inv['file_name']}'")
    if ctype in PERSONALITY and inv.get("file_subtitle") is not None:
        sub = v.get("sub") or ""
        for fl in inv["filename_flags"]:
            sub = sub.replace(f"({fl})", "")
        if norm_name(sub) != norm_name(inv["file_subtitle"]):
            fname_issues.append(f"subtitle differs from filename: '{v.get('sub')}' vs "
                           f"'{inv['file_subtitle']}'")
    fnum = re.sub(r"^[A-Z]*?(?=\d)", "", inv.get("card_number") or "")
    fnum = re.sub(r"[AB]$", "", fnum).lstrip("0")
    pnum = re.sub(r"^\D*", "", num.split()[-1] if num else "").lstrip("0")
    if fnum and pnum and fnum != pnum:
        fname_issues.append(f"printed number {num} differs from filename number "
                       f"{inv['card_number']}")
    st = v.get("stages")
    notes = [v["note"]] if v.get("note") else []

    # PanZ Allies print no alignment on the edge; it is in the text box (owner, 2026-11-01).
    align = v.get("align")
    if align is None and ctype == "Ally":
        found = {"Heroes": "Hero", "Villains": "Villain"}
        hits = [found[r] for r in restrictions if r in found]
        if len(hits) == 1:
            align = hits[0]
            notes.append("alignment taken from the text box")
        else:
            reasons.append("Ally without a printed alignment")

    # Printed S = starter deck card (owner, 2026-11-01), even when filed with the boosters.
    collection = inv["collection"]
    if rarity == "S" and collection == "booster":
        collection = "starter"
        notes.append("printed S number but filed in the booster folder; collection set to "
                     "starter")
    if ctype in PERSONALITY:
        if not st or len(st) != 11 or v.get("pur") is None:
            reasons.append("personality without 11 stages or PUR")
        elif any(st[i] < st[i + 1] for i in range(10)):
            notes.append("power stages are not descending (printed that way)")

    return {
        "card_id": inv["card_id"], "set_number": inv["set_number"],
        "set_name": inv["set_name"], "era": inv["era"],
        "source_folder": inv["source_folder"], "collection": collection,
        "card_number": num, "filename": inv["filename"],
        "filename_flags": inv["filename_flags"], "card_name": name,
        "subtitle": v.get("sub"), "card_type": ctype, "style": style,
        "is_named": is_named, "named_character": named,
        "alignment": align, "rarity": rarity,
        "level": v.get("lvl"), "power_stages": st, "pur": v.get("pur"),
        "traits": v.get("traits") or [], "icons": icons + [f"Trait:{t}" for t in traits_inline],
        "keywords": kw, "stage_cost": int(cost[1]) if cost else None,
        "limit_per_deck": int(lim[1]) if lim else None,
        "restrictions": restrictions, "deck_rules": deck_rules,
        "text_as_printed": text, "text_current": None, "errata_note": None,
        "ruling_note": None, "frozen": "Frozen" in inv["filename_flags"] or None,
        "gold_title_reprint": None, "is_mrp": None,
        "ocr_confidence": o.get("lower_conf"), "ocr_agreement": o.get("agreement"),
        "vision_confidence": v.get("conf"),
        "filename_issue": "; ".join(fname_issues) or None,
        "needs_review": bool(reasons), "review_reason": "; ".join(reasons) or None,
        "notes": " | ".join(notes) or None,
    }


def stage_ocr_match(stages, ocr_text):
    """Share of the 11 printed stages that OCR also read, in order (0-1)."""
    if not stages or not ocr_text:
        return None
    got = [int(x.replace(",", "")) for x in re.findall(r"\d[\d,]*", ocr_text)
           if x.replace(",", "").isdigit()]
    sm = difflib.SequenceMatcher(None, stages, got, autojunk=False)
    return round(sum(b.size for b in sm.get_matching_blocks()) / len(stages), 3)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sets", default="S01,S14,PZP")
    ap.add_argument("--out", default="work/pilot")
    a = ap.parse_args()
    sets = set(a.sets.split(","))
    out = DB / a.out
    cards, cmp_rows = [], []
    for p in sorted(CACHE.glob("*.json")):
        rec = load_json(p)
        if rec["inventory"]["set_code"] not in sets:
            continue
        c = derive(rec)
        cards.append(c)
        cmp_rows.append({
            "card_id": c["card_id"], "type": c["card_type"],
            "text_agreement": c["ocr_agreement"], "ocr_conf": c["ocr_confidence"],
            "stage_agreement": stage_ocr_match(c["power_stages"], rec["ocr"]["stages_text"]),
            "title_in_header": (norm_name(c["card_name"])[:12] in
                                norm_name(rec["ocr"]["header_text"]))})
    save_json(out / "cards.json", cards)
    with open(out / "cards.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(cards[0].keys()))
        w.writeheader()
        for c in cards:
            w.writerow({k: (json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict))
                            else v) for k, v in c.items()})
    save_json(out / "ocr_compare.json", cmp_rows)
    nr = sum(c["needs_review"] for c in cards)
    print(f"{len(cards)} cards -> {out}; needs_review={nr}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
