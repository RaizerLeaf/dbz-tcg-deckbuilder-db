"""Phase 4: MP grouping index (mps.json) and Mastery index (masteries.json).

Run after crd.py. Reads cards.json, work/crd/fanz.txt (retroactive Trait lists) and writes
  cards.json / cards.csv  (adds traits_effective and traits_source for Main Personalities and Allies)
  mps.json                one group per MP name + alignment, every printing of each Level 1-4
  masteries.json          every Mastery printing grouped by name, with the cards restricted to it

Rules used (BRIEF + Rulebook 3.0 + FanZ CRD v1.15):
  - A deck's MP set is Levels 1-4, all with the same MP name AND alignment (printings may come from different sets).
  - Future Gohan is its own MP; no Future Gohan MP card exists in the images, so no group is made for it.
  - Fused MPs cannot include the Allies they are fused from.
  - FanZ: a Saiyan/Namekian Mastery (and any "([Trait] only)" card) needs the Trait on all four chosen MP levels.
    PanZ (Rulebook 3.0) used a fixed heritage list instead; both are reported.
  - Traits printed on a card are used as printed. PanZ-era printings print none, so the CRD's list of
    retroactive Traits is applied by character name (traits_source says which).
"""
import copy
import csv
import json
import re
import sys
from collections import defaultdict

from common import DB, load_json, save_json
from crd_parse import clean_quotes

TRAITS = ["Alien", "Android", "Earthling", "Fusion", "God", "Majin", "Namekian", "Saiyan"]
PANZ_HERITAGE = {  # Rulebook 3.0, pp. on Styles
    "Namekian": ["Piccolo", "Nail", "Lord Slug", "Gohan", "Cell", "Cell Jr.", "Dende", "Kami"],
    "Saiyan": ["Goku", "Vegeta", "Gohan", "Nappa", "Raditz", "Trunks", "Turles", "Cell", "Cell Jr.", "King Vegeta",
               "Bardock", "Broly", "Paragus", "Goten", "Pan", "Gotenks", "Gogeta", "Vegito"],
}
FUSED = {  # CRD section I
    "Vegito": ["Goku", "Vegeta"], "Gogeta": ["Goku", "Vegeta"], "Gotenks": ["Goten", "Kid Trunks"],
    "Kefla": ["Caulifla", "Kale"], "Fused Zamasu": ["Goku Black", "Zamasu"],
}
COLL_ORDER = {"booster": 0, "starter": 1, "dr": 2, "promo_mp": 3, "promo_ally": 3, "promo": 3, "op": 4}


def retro_traits():
    txt = open(DB / "work" / "crd" / "fanz.txt", encoding="utf-8").read()
    a = txt.index("The Traits are listed below")
    b = txt.index("New Text Changes")
    block = clean_quotes(txt[a:b])
    out = defaultdict(list)  # trait -> [(name, variant|None)]
    cur = None
    for line in block.split("\n")[1:]:
        s = line.strip()
        if not s:
            continue
        m = re.match(r"^(" + "|".join(TRAITS) + r"):\s*(.*)$", s)
        if m:
            cur, body = m[1], m[2]
        elif cur:
            body = s
        else:
            continue
        if body.startswith("("):
            continue
        for part in body.split(","):
            part = part.strip()
            if not part:
                continue
            nm, _, var = part.partition(" - ")
            out[cur].append((nm.strip(), var.strip() or None))
    return out


def norm(s):
    return re.sub(r"[^a-z0-9]", "", clean_quotes(s or "").lower())


def retro_for(card, table):
    got = []
    for trait, items in table.items():
        for nm, var in items:
            if norm(nm) != norm(card["card_name"]):
                continue
            if var is None or norm(var) == norm(card.get("subtitle")):
                got.append(trait)
                break
    return [t for t in TRAITS if t in got]


def printing(c):
    return {
        "card_id": c["card_id"], "set_number": c["set_number"], "set_name": c["set_name"], "era": c["era"],
        "collection": c["collection"], "card_number": c["card_number"], "rarity": c["rarity"],
        "subtitle": c["subtitle"], "level": c["level"], "pur": c["pur"], "power_stages": c["power_stages"],
        "power_text": c["text_current"] or c["text_as_printed"],
        "traits_printed": c["traits"], "traits": c["traits_effective"], "traits_source": c["traits_source"],
        "errata_status": c["errata_status"], "is_mrp": c["is_mrp"], "needs_review": c["needs_review"],
        "filename_flags": c["filename_flags"],
    }


def sort_key(c):
    return (c["set_number"] if isinstance(c["set_number"], int) else 99, COLL_ORDER.get(c["collection"], 5),
            int(re.sub(r"\D", "", c["card_number"] or "0") or 0), c["card_id"])


def main():
    cards = load_json(DB / "cards.json")
    table = retro_traits()

    # --- effective Traits (MPs and Allies) --------------------------------------------------------
    mismatch = []
    for c in cards:
        c["traits_effective"], c["traits_source"] = list(c["traits"]), None
        if c["card_type"] in ("Main Personality", "Ally"):
            retro = retro_for(c, table)
            if c["traits"]:
                c["traits_source"] = "printed"
                if retro and not set(retro) <= set(c["traits"]):
                    mismatch.append((c["card_id"], c["card_name"], c["subtitle"], c["traits"], retro))
            elif retro:
                c["traits_effective"], c["traits_source"] = retro, "CRD retroactive list (not printed on this card)"
            else:
                c["traits_source"] = "none printed; not on the CRD retroactive list"

    # --- MP groups ------------------------------------------------------------------------------
    mps = [c for c in cards if c["card_type"] == "Main Personality"]
    groups = defaultdict(list)
    for c in mps:
        groups[(c["card_name"], c["alignment"])].append(c)
    out = []
    for (name, align), cs in sorted(groups.items(), key=lambda kv: (norm(kv[0][0]), kv[0][1])):
        levels = {str(l): sorted([x for x in cs if x["level"] == l], key=sort_key) for l in (1, 2, 3, 4)}
        entry = {
            "mp_key": f"{norm(name)}|{align.lower()}", "name": name, "alignment": align,
            "can_mix_levels_across_sets": True,
            "fused_from": FUSED.get(name),
            "cannot_include_allies_named": sorted(set(([name] if True else []) + (FUSED.get(name) or []))),
            "panz_heritage": {s: name in names for s, names in PANZ_HERITAGE.items()},
            "levels": {l: [printing(x) for x in xs] for l, xs in levels.items()},
            "levels_missing": [l for l, xs in levels.items() if not xs],
            "printings_per_level": {l: len(xs) for l, xs in levels.items()},
        }
        tr = {}
        for t in TRAITS:
            per = {l: [x["card_id"] for x in xs if t in x["traits_effective"]] for l, xs in levels.items()}
            if any(per.values()):
                tr[t] = {"printings_with_trait_by_level": per,
                         "available_on_all_four_levels": all(per[l] for l in per),
                         "levels_without_it": [l for l in per if not per[l]]}
        entry["trait_availability"] = tr
        entry["fanz_saiyan_mastery_possible"] = bool(tr.get("Saiyan", {}).get("available_on_all_four_levels"))
        entry["fanz_namekian_mastery_possible"] = bool(tr.get("Namekian", {}).get("available_on_all_four_levels"))
        entry["note"] = ("Fused MP: its Life Deck cannot include Allies named " + " or ".join(FUSED[name]) + ".") \
            if name in FUSED else None
        out.append(entry)
    meta = {
        "generated_from": "cards.json (Phase 3) + FanZ CRD v1.15 Trait lists + Rulebook 3.0 heritage lists",
        "rules": [
            "An MP set is Levels 1-4 with the same MP name and the same alignment; printings from different sets may be mixed.",
            "Future Gohan is a separate MP that cannot be mixed with other Gohans (his Life Deck may contain Gohan Named cards). "
            "No Future Gohan MP card is present in the images, so there is no group for him.",
            "Fused MPs (Vegito, Gogeta, Gotenks, Kefla, Fused Zamasu) cannot include Allies of the characters they are fused from.",
            "FanZ: a Saiyan or Namekian Mastery, and any card marked '([Trait] only.)', needs that Trait on all four chosen MP levels. "
            "PanZ used the heritage lists in panz_heritage instead.",
            "You cannot include Allies whose name matches your MP's name (Rulebook 3.0).",
            "traits (per printing) = printed Traits if the card prints any, otherwise the CRD's retroactive Trait list by character name.",
        ],
        "groups": len(out), "mp_printings": len(mps),
        "groups_missing_a_level": [e["mp_key"] for e in out if e["levels_missing"]],
        "printed_traits_missing_a_retroactive_trait": mismatch,
    }
    save_json(DB / "mps.json", {"_meta": meta, "mps": out})

    # --- masteries ------------------------------------------------------------------------------
    ms = [c for c in cards if c["card_type"] == "Mastery"]
    mnames = {c["card_name"] for c in ms}
    restricted = defaultdict(list)
    style_wide = defaultdict(list)
    for c in cards:
        for r in c["restrictions"]:
            r2 = clean_quotes(r)
            if r2.endswith("Mastery"):
                if r2 in mnames:
                    restricted[r2].append(c["card_id"])
                else:
                    style_wide[r2].append(c["card_id"])
    g = defaultdict(list)
    for c in ms:
        g[c["card_name"]].append(c)
    mout = []
    for name, cs in sorted(g.items(), key=lambda kv: (kv[1][0]["style"] or "", kv[0])):
        style = cs[0]["style"]
        mout.append({
            "name": name, "style": style,
            "style_requirement": {
                "Saiyan": "MP needs the Saiyan Trait on all four chosen levels (FanZ); PanZ: MP on the Saiyan heritage list",
                "Namekian": "MP needs the Namekian Trait on all four chosen levels (FanZ); PanZ: MP on the Namekian heritage list",
            }.get(style),
            "frozen": any(x["frozen"] for x in cs),
            "printings": [{
                "card_id": x["card_id"], "set_number": x["set_number"], "set_name": x["set_name"], "era": x["era"],
                "collection": x["collection"], "card_number": x["card_number"], "rarity": x["rarity"],
                "text_as_printed": x["text_as_printed"], "text_current": x["text_current"],
                "errata_status": x["errata_status"], "is_mrp": x["is_mrp"], "frozen": x["frozen"],
                "frozen_listed_printing": x["frozen_listed_printing"], "limit_per_deck": x["limit_per_deck"],
                "keywords": x["keywords"], "needs_review": x["needs_review"], "filename_flags": x["filename_flags"],
            } for x in sorted(cs, key=sort_key)],
            "cards_restricted_to_this_mastery": sorted(restricted.get(name, [])),
        })
    save_json(DB / "masteries.json", {"_meta": {
        "styles": sorted({m["style"] for m in mout}),
        "note": "cards_restricted_to_this_mastery lists cards whose '(X Mastery only.)' text names this Mastery exactly; "
                "style_wide_restrictions lists cards restricted to a Mastery name that is not a card (e.g. 'Saiyan Mastery').",
        "style_wide_restrictions": {k: sorted(v) for k, v in style_wide.items()},
        "mastery_printings": len(ms), "masteries": len(mout)}, "masteries": mout})

    # --- write cards back with the new Trait fields ------------------------------------------------
    save_json(DB / "cards.json", cards)
    with open(DB / "cards.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(cards[0].keys()))
        w.writeheader()
        for c in cards:
            w.writerow({k: (json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict)) else v)
                        for k, v in c.items()})
    print(f"{len(out)} MP groups from {len(mps)} printings; {len(mout)} masteries from {len(ms)} printings")
    print("groups missing a level:", meta["groups_missing_a_level"])
    print("printed vs retro Trait mismatches:", len(mismatch))
    return 0


if __name__ == "__main__":
    sys.exit(main())
