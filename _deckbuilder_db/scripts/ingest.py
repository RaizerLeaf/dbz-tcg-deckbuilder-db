"""Merge vision transcriptions + OCR + inventory into cache/<card_id>.json (one per image).

Vision transcriptions live in work/vision/*.jsonl, one JSON object per line, written while
reading the review sheets. Short keys keep them compact:
  id      card_id (required)
  name    card title / personality name as printed
  sub     subtitle (personalities)
  type    printed card type: Main Personality, Ally, Personality, Mastery, Physical Combat,
          Energy Combat, Event, Setup, Drill, Dragon Ball, Trait, or "?" if unsure
  num     card number as printed incl. rarity letter, e.g. "C19", "S44", "P10"
  lvl, stages (list of 11 ints, top to bottom), pur, align ("Hero"/"Villain"/null)
  traits  list of Trait names shown as icons
  text    text box as printed; icons written as [Attack] [Defense] [Continuous] [Instant]
          [Desperation]; paragraph breaks as \n
  conf    "high" | "medium" | "low"   (my confidence in the transcription)
  review  null, or a reason string -> needs_review=true
  note    free-form observation (layout oddities, printed stamps, etc.)
Later lines for the same id replace earlier ones, so corrections are appended, not edited.

Usage: python ingest.py
"""
import difflib
import json
import re
import sys

from common import CACHE, INVENTORY, OCR_CACHE, VISION_DIR, load_json, save_json


def norm(s):
    s = (s or "").lower().replace("’", "'").replace("“", '"').replace("”", '"')
    s = re.sub(r"\[(attack|defense|continuous|instant|desperation)\]", " ", s)
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def ocr_agreement(vision_text, ocr_lower):
    """Share of the vision text's words that OCR also found, in order (0-1)."""
    v, o = norm(vision_text).split(), norm(ocr_lower).split()
    if not v:
        return None
    sm = difflib.SequenceMatcher(None, v, o, autojunk=False)
    return round(sum(b.size for b in sm.get_matching_blocks()) / len(v), 3)


def load_vision():
    out = {}
    for f in sorted(VISION_DIR.glob("*.jsonl")):
        for ln, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError as e:
                raise SystemExit(f"{f.name}:{ln}: bad JSON: {e}")
            rec["_src"] = f"{f.name}:{ln}"
            out[rec["id"]] = rec
    return out


def main():
    inv = {r["card_id"]: r for r in load_json(INVENTORY)}
    vision = load_vision()
    unknown = [k for k in vision if k not in inv]
    if unknown:
        print("vision ids not in inventory:", unknown)
    n = 0
    for cid, v in vision.items():
        if cid not in inv:
            continue
        o = load_json(OCR_CACHE / f"{cid}.json", {}) or {}
        reg = o.get("regions", {})
        agree = ocr_agreement(v.get("text"), reg.get("lower", {}).get("text"))
        rec = {"inventory": inv[cid], "vision": v,
               "ocr": {"agreement": agree,
                       "lower_conf": reg.get("lower", {}).get("conf"),
                       "header_text": reg.get("header", {}).get("text"),
                       "stages_text": reg.get("stages", {}).get("text"),
                       "error": o.get("error")}}
        save_json(CACHE / f"{cid}.json", rec)
        n += 1
    print(f"ingested {n} vision records; cache now holds {len(list(CACHE.glob('*.json')))} cards")
    return 0


if __name__ == "__main__":
    sys.exit(main())
