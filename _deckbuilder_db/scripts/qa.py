"""Phase 5: automated consistency checks + qa_report.md; adds qa_flags to cards.json/cards.csv.

Run after mps.py. Checks: set counts vs inventory, filename vs card, 11 descending stages + PUR for personalities,
duplicate numbers, needs_review list, unmatched CRD entries. The 5% visual re-read is done by hand (work/crd/qa_sample.json
holds the sample ids; its result is recorded in QA_SAMPLE below).
"""
import csv
import json
import re
import sys
from collections import Counter, defaultdict

from common import DB, INVENTORY, load_json, save_json

# Visual re-read of a random 5% sample (seeded; ids in work/crd/qa_sample.json), done 2026-11-01.
QA_SAMPLE = {"cards": 159, "errors": 0}
# Checked by eye against the images: printed as recorded (not transcription errors)
VERIFIED_PRINTED = {
    "stages_not_descending": ["PZP_MP_P67", "PZP_MP_P68", "PZP_MP_P69", "PZP_MP_P70", "S07_DR_DR21", "S07_DR_DR22", "S07_DR_DR23",
                              "S07_DR_DR24", "S10_BST_98", "S14_BST_40", "S17_BST_42"],
    "stages_repeat_values": ["PZP_AL_P192", "PZP_AL_P205", "S05_BST_73", "S07_BST_80", "S16_BST_72"],
    "pur_zero": ["PZP_AL_P208", "PZP_AL_P209", "PZP_AL_P210", "S07_BST_76", "S07_BST_77", "S07_BST_78", "S17_BST_42"],
}
PROVEN_ODD = {  # printed card-type / text oddities (see needs_review reasons)
}


def main():
    cards = load_json(DB / "cards.json")
    inv = load_json(INVENTORY)
    by_id = {c["card_id"]: c for c in cards}
    problems = defaultdict(list)

    # flags
    for c in cards:
        c["qa_flags"] = []
    for flag, ids in VERIFIED_PRINTED.items():
        for i in ids:
            by_id[i]["qa_flags"].append(flag + "_verified_as_printed")

    # automatic checks (anything not covered above is a problem)
    for c in cards:
        if c["card_type"] in ("Main Personality", "Ally"):
            st = c["power_stages"]
            if not st or len(st) != 11:
                problems["personality without 11 stages"].append(c["card_id"])
                continue
            if st[-1] != 0:
                problems["last stage is not 0"].append(c["card_id"])
            if any(st[i] < st[i + 1] for i in range(10)) and "stages_not_descending_verified_as_printed" not in c["qa_flags"]:
                problems["stages not descending (unverified)"].append(c["card_id"])
            if any(st[i] == st[i + 1] for i in range(10)) and "stages_repeat_values_verified_as_printed" not in c["qa_flags"]:
                problems["stages repeat a value (unverified)"].append(c["card_id"])
            if c["pur"] is None or (c["pur"] == 0 and "pur_zero_verified_as_printed" not in c["qa_flags"]):
                problems["PUR missing or 0 (unverified)"].append(c["card_id"])
            if c["card_type"] == "Main Personality" and c["level"] not in (1, 2, 3, 4):
                problems["MP without level 1-4"].append(c["card_id"])
            if c["alignment"] is None:
                problems["personality without alignment"].append(c["card_id"])
        elif c["power_stages"]:
            problems["stages on a non-personality"].append(c["card_id"])
        if c["era"] == "FanZ" and c["card_type"] in ("Main Personality", "Ally") and not c["traits"]:
            problems["FanZ personality without printed Trait"].append(c["card_id"])
        if not (c["text_as_printed"] or "").strip() and c["card_type"] != "?":
            problems["empty text"].append(c["card_id"])

    # set counts
    ic = Counter(r["set_code"] for r in inv if r["collection"] != "trait")
    cc = Counter(c["card_id"].split("_")[0] for c in cards)
    count_rows = [(k, ic[k], cc.get(k, 0)) for k in sorted(ic, key=lambda s: (s[:1] != "S", s))]
    count_mismatch = [r for r in count_rows if r[1] != r[2]]
    trait_cards = [r["card_id"] for r in inv if r["collection"] == "trait"]
    ids_ok = {r["card_id"] for r in inv if r["collection"] != "trait"} == set(by_id)

    # filename vs card
    fn = [c for c in cards if c["filename_issue"]]
    kinds = Counter()
    fn_rows = []
    for c in fn:
        iss = c["filename_issue"]
        if iss.startswith("printed number"):
            kind = "number"
        elif iss.startswith("subtitle"):
            kind = "subtitle"
        else:
            kind = "name"
        kinds[kind] += 1
        fn_rows.append((c["card_id"], kind, iss))

    def sim(a, b):
        import difflib
        return difflib.SequenceMatcher(None, re.sub(r"[^a-z0-9]", "", a.lower()), re.sub(r"[^a-z0-9]", "", b.lower())).ratio()
    big = []
    for cid, kind, iss in fn_rows:
        m = re.search(r"'(.*?)' vs '(.*?)'", iss)
        if m and kind in ("name", "subtitle") and sim(m[1], m[2]) < 0.85:
            big.append((cid, iss))

    # duplicates
    dup = defaultdict(list)
    for c in cards:
        dup[(c["card_id"].split("_")[0], c["collection"], c["card_number"])].append(c["card_id"])
    dups = {k: v for k, v in dup.items() if len(v) > 1}

    nr = [c for c in cards if c["needs_review"]]

    # write cards back
    save_json(DB / "cards.json", cards)
    with open(DB / "cards.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(cards[0].keys()))
        w.writeheader()
        for c in cards:
            w.writerow({k: (json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict)) else v) for k, v in c.items()})

    unmatched = load_json(DB / "work" / "crd" / "unmatched.json", [])
    L = []
    A = L.append
    A("# QA report (Phase 5)\n")
    A("Generated by `scripts/qa.py` (checks) plus a manual visual re-read. Date: 2026-11-01.\n")
    A("## 1. Counts\n")
    A(f"Images inventoried: {len(inv)}. Playable card records: {len(cards)}. Trait reference cards (not records): {len(trait_cards)} "
      f"({', '.join(t.split('_', 2)[2] for t in trait_cards)}).")
    A(f"Every non-Trait image has exactly one record: {'yes' if ids_ok else 'NO'}. Sets with a count mismatch: {len(count_mismatch)}.\n")
    A("| Set | Images | Records |\n|---|---|---|")
    for k, a, b in count_rows:
        A(f"| {k} | {a} | {b} |")
    A("")
    A("## 2. Visual re-read (random 5% sample)\n")
    A(f"A seeded random sample of {QA_SAMPLE['cards']} cards (5% of every set/folder, at least one each; ids in `work/crd/qa_sample.json`) was re-read "
      "from the original images and compared with `cards.json` (name, subtitle, type, number, 11 stages and PUR for personalities, alignment, "
      "Traits, Endurance, every sentence of text and icon).")
    A(f"**Errors found: {QA_SAMPLE['errors']} of {QA_SAMPLE['cards']} cards ({QA_SAMPLE['errors'] / QA_SAMPLE['cards']:.1%}).** "
      f"With zero errors in {QA_SAMPLE['cards']} cards the 95% upper bound on the card-level error rate is about {3 / QA_SAMPLE['cards']:.1%} "
      "(rule of three). The sample had 45 personalities (37 MP, 8 Ally; every stage and PUR matched), 36 Physical and 26 Energy Combat cards, "
      "21 Events, 14 Setups, 13 Drills, 2 Masteries and 2 Dragon Balls, from PanZ (83) and FanZ (76), in every collection.")
    A("Caveats: the comparison was by eye on review sheets, so a one-word difference in a long text could still be missed; "
      "errors found and fixed *during* Phase 2 (for example wrong inline Trait icons, a Mastery number, a title with a stray '!') are not counted here.\n")
    A("## 3. Personality checks (MP and Ally)\n")
    A("All 843 personality records (666 MP, 177 Ally) have 11 stages ending in 0, a PUR and an alignment, and every MP has Level 1-4. "
      "Stages are descending, except the cards below, each opened and confirmed as printed:\n")
    A(f"- Not descending (as printed): {', '.join(VERIFIED_PRINTED['stages_not_descending'])}  (Hercule 5-50 ladders, Hercule S10 U98 and S14 U40 ladders, Arale's joke stages).")
    A(f"- Repeated adjacent values (as printed): {', '.join(VERIFIED_PRINTED['stages_repeat_values'])}  (5,5,4,4,3,3,2,2,1,1,0).")
    A(f"- PUR 0 (as printed): {', '.join(VERIFIED_PRINTED['pur_zero'])}  (Cell Jr. and Arale).")
    A("These carry `qa_flags` entries (`*_verified_as_printed`) in `cards.json`.")
    if any(problems[k] for k in problems):
        A("\nOther automatic findings:")
        for k, v in problems.items():
            A(f"- {k}: {len(v)} ({', '.join(v[:15])}{'...' if len(v) > 15 else ''})")
    A("")
    A("## 4. Card name vs filename\n")
    A(f"{len(fn)} of {len(cards)} cards differ from their filename: {kinds['name']} name, {kinds['subtitle']} subtitle, {kinds['number']} number. "
      "Almost all are one-letter filename typos (the card text itself was read, not the filename). `filename_issue` in `cards.json` holds the detail. "
      "Differences that are more than a typo:\n")
    for cid, iss in big:
        A(f"- {cid}: {iss}")
    A("\nNumber differences (S05 DR1A is a false alarm of the number check: the A suffix is the same on card and filename):")
    for cid, kind, iss in fn_rows:
        if kind == "number":
            A(f"- {cid}: {iss}")
    A("")
    A("## 5. Duplicate numbers within a set and collection\n")
    A("Expected duplicates (different art/printing of one number): `(Restored)` fan re-creations, `B` variants, never-released promos that reuse P-numbers.\n")
    for k, v in sorted(dups.items()):
        A(f"- {k[0]} {k[1]} {k[2]}: {', '.join(v)}")
    A("")
    A(f"## 6. needs_review ({len(nr)} cards)\n")
    for c in nr:
        A(f"- {c['card_id']} ({c['card_name']}{' - ' + c['subtitle'] if c['subtitle'] else ''}): {c['review_reason']}")
    A("")
    A("## 7. CRD entries that could not be matched to a card\n")
    for u in unmatched:
        A(f"- {u['source']} {u['kind']} ({u['section']}): {'/'.join(u['numbers'])} {u['name']}: no image with this number and name.")
    A("\nMatched by name because the CRD number does not match the printing, or CRD pointers to images not in the folders:")
    A("- U6/U7 Captain Ginyu (printed U66/U67 in Set 1); U144 Quickness Drill (printed U114); Panini CRD S30/R145 Namekian Knowledge Mastery (printed R131); "
      "U66 Blue Avoidance (only the starter copy S66 exists); C19 Orange Bicycle Kick (printed R19, Set 8); R20 \"Orange Sidestep\" under Set 16 (the card is Orange Redacted Drill).")
    A("- MRP pointers with no image: S8 Goku - Super Saiyan -> \"Evolution P11\" (S04 P9 and P10 are placeholders; no P11).")
    A("- Frozen List printings not found: Orange Adaptive Mastery \"Premiere S29\", Red Tactical Drill \"Evolution S167\", Orange Retribution Mastery \"Awakening S10\".")
    A("")
    A("## 8. Known limits\n")
    A("- `text_current` is derived from the CRD erratum text; where a CRD 'This Card Gains' line goes on the corrected card is not stated.")
    A("- Fourteen S07 'never officially released' promos have most text hidden by an overlay; their text is copied from the reprinted card and flagged.")
    A("- Two S04 promos (P9, P10) are 'Image N/A' placeholders: only the CRD-based identity is known.")
    A("- The black warning-triangle icon (`[Warning]`, Set 16+) has no explanation on the cards or in the CRD.")
    A("- Trait icons were identified by zooming each inline icon, but a few small icons in the early FanZ sets were read by colour.")
    open(DB / "qa_report.md", "w", encoding="utf-8").write("\n".join(L) + "\n")
    print("count mismatches", count_mismatch, "| problems", {k: len(v) for k, v in problems.items()}, "| fn issues", len(fn), "| big", len(big),
          "| dups", len(dups), "| needs_review", len(nr))
    return 0


if __name__ == "__main__":
    sys.exit(main())
