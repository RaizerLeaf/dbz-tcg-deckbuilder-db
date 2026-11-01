"""Parse the FanZ Combined CRD (v1.15) and the Panini CRD (v6.0) text into entries.

Input : work/crd/fanz.txt, work/crd/panz.txt (pdftotext -layout output of the PDFs in _rules/)
Output: work/crd/entries.json  (individual card erratum/ruling entries, both documents)
        work/crd/frozen.json   (Frozen list: name + listed printings)
        work/crd/gold.json     (Gold Title Reprints with crossed-out status; strike-through was read
                                from the rendered PDF page by eye, see GOLD_CROSSED)
Nothing here touches card records; crd.py does the matching.
"""
import json
import re
import sys

from common import DB, save_json

CRD = DB / "work" / "crd"

SECTION_SET = {  # section heading in the CRD -> set number (None = organized play)
    "Premiere Set": 1, "Heroes & Villains": 2, "The Movie Collection": 3, "Evolution": 4,
    "Perfection": 5, "Vengeance": 6, "Awakening": 7, "Celestial Tournament": 8, "Legends": 9,
    "Revelation": 10, "Escalation": 11, "Movie Collection 2": 12, "Fusion": 13, "Showdown": 14,
    "Premier: Dragon Ball Super": 16, "Universal Clash: Dragon Ball Super": 17,
    "Organized Play Promos": "OP",
    # Panini CRD spellings
    "Premiere": 1, "Movie Collection": 3,
}
# names that can appear inside MRP / NOTE references
REF_SET = [
    ("Heroes & Villains", 2), ("Movie Collection 2", 12), ("Movie Collection 3", 15),
    ("The Movie Collection", 3), ("Movie Collection", 3), ("Premiere", 1), ("Evolution", 4),
    ("Perfection", 5), ("Vengeance", 6), ("Awakening", 7), ("Celestial Tournament", 8),
    ("Legends", 9), ("Revelation", 10), ("Escalation", 11), ("Fusion", 13), ("Showdown", 14),
    ("Super Premier", 16), ("Premier: Dragon Ball Super", 16), ("Universal Clash: Dragon Ball Super", 17),
    ("Universal Clash", 17),
]
NUM = r"[A-Z]{1,2}\d+"

# Read by eye from the rendered PDF page 24 (strike-through is not in the text layer).
GOLD_CROSSED = {
    "Black Side Thrust", "Black Energy Web", "Blue Arm Blast", "Orange Power Point",
    "Red Energy Defensive Stance", "Saiyan Energy Toss", "Saiyan Wrist Block",
    "Saiyan Energy Rupture", "Saiyan Focus", "Saiyan Surprise",
}


def clean_quotes(s):
    return (s.replace("“", '"').replace("”", '"').replace("‘", "'")
            .replace("’", "'").replace("–", "-").replace("—", "-"))


def split_header(first):
    """'S25/R145 Saiyan Empowered Mastery' -> [(['S25','R145'], 'Saiyan Empowered Mastery')]"""
    first = clean_quotes(first).strip()
    parts = re.split(rf"\s+and\s+(?={NUM}\b)", first)
    out = []
    for p in parts:
        m = re.match(rf"^({NUM}(?:/{NUM}|/DR\d+)*)\s*[-–]?\s*(.+)$", p.strip())
        if not m:
            out.append(([], p.strip()))
            continue
        out.append((re.split(r"/", m[1]), m[2].strip().rstrip(".")))
    return out


LABELS = ["Original Text", "Panini Updated Text", "FanZ Updated Text", "Updated Text",
          "This Card Gains", "This Card Loses"]


def parse_fanz(path):
    lines = open(path, encoding="utf-8").read().split("\n")
    start = next(i for i, l in enumerate(lines) if "III. Individual Card Rulings" in l)
    end = next(i for i, l in enumerate(lines) if "IV. Card Legality" in l)
    lines = lines[start:end]
    section, entries, cur = None, [], None

    def flush():
        nonlocal cur
        if cur:
            entries.append(cur)
        cur = None

    for raw in lines:
        s = raw.strip()
        if s in SECTION_SET:
            flush()
            section = s
            continue
        m = re.match(r"^\[(ERRATUM|RULING)\]\s*(.*)$", s)
        if m:
            flush()
            cur = {"kind": m[1], "section": section, "head": m[2], "body": []}
            continue
        if cur is not None and s:
            cur["body"].append(s)
    flush()
    out = []
    for e in entries:
        e = dict(e)
        body = clean_quotes(" ".join(e["body"]))
        head = e["head"]
        raw_all = clean_quotes(head + " " + " ".join(e["body"])).strip()
        ruling_text = None
        if e["kind"] == "RULING":
            # header and text share the first line: "S2 Vegeta - Villainous ...: These Powers ..."
            full = clean_quotes(head + " " + " ".join(e["body"]))
            m = re.match(r"^(.*?):\s+(.*)$", full)
            head, ruling_text = m[1], m[2]
            body = ""
        e["cards"] = [{"numbers": n, "name": nm} for n, nm in split_header(head)]
        e["section_set"] = SECTION_SET[e["section"]]
        e["raw"] = raw_all
        if ruling_text is not None:
            e["ruling_text"] = ruling_text
        else:
            fields = {}
            labs = "|".join(re.escape(x) for x in LABELS)
            pat = re.compile(rf"({labs}):\s*")
            pos = [(m.start(), m.end(), m[1]) for m in pat.finditer(body)]
            # trailing (MRP: ...) and (NOTE: ...) groups
            tail_pos = [m.start() for m in re.finditer(r"\((?:MRP|NOTE):", body)]
            cuts = sorted([p[0] for p in pos] + tail_pos + [len(body)])
            for st, en, lab in pos:
                nxt = min(c for c in cuts if c > st)
                txt = body[en:nxt].strip().strip('"').strip()
                fields[lab] = re.sub(r'^"+|"+$', "", txt).strip()
            e["mrp_raw"] = None
            m = re.search(r"\(MRP:\s*(.*?)\)\s*(?=\(NOTE:|$)", body)
            if m:
                e["mrp_raw"] = m[1].strip()
            notes = re.findall(r"\(NOTE:\s*(.*?)\)\s*(?=\(MRP:|\(NOTE:|$)", body)
            e["note_raw"] = " ".join(notes) or None
            e["original_text"] = fields.get("Original Text")
            e["panini_updated_text"] = fields.get("Panini Updated Text")
            e["fanz_updated_text"] = fields.get("FanZ Updated Text")
            e["updated_text"] = fields.get("Updated Text")
            e["gains"] = fields.get("This Card Gains")
            e["loses"] = fields.get("This Card Loses")
        e["source"] = "FanZ CRD v1.15"
        del e["body"], e["head"]
        out.append(e)
    return out


def parse_panz(path):
    lines = open(path, encoding="utf-8").read().split("\n")
    start = next(i for i, l in enumerate(lines) if "Individual Card Rulings" in l)
    gold = next(i for i, l in enumerate(lines) if "Gold Title Reprint" in l and i > start)
    section, entries, cur = None, [], None
    for raw in lines[start + 1:gold]:
        s = raw.strip()
        if s in SECTION_SET:
            if cur:
                entries.append(cur)
            cur, section = None, s
            continue
        if re.match(rf"^{NUM}(?:/{NUM})*\s+.+?:\s", s) and not s.startswith("Example"):
            if cur:
                entries.append(cur)
            cur = {"section": section, "text": s}
        elif cur is not None and s:
            cur["text"] += " " + s
    if cur:
        entries.append(cur)
    out = []
    for e in entries:
        full = clean_quotes(e["text"])
        m = re.match(r"^(.*?):\s+(.*)$", full)
        head, body = m[1], m[2]
        out.append({"kind": "PANINI", "section": e["section"], "section_set": SECTION_SET[e["section"]],
                    "cards": [{"numbers": n, "name": nm} for n, nm in split_header(head)],
                    "ruling_text": body.strip(), "raw": full, "source": "Panini CRD v6.0"})
    return out


def parse_frozen(path):
    lines = open(path, encoding="utf-8").read().split("\n")
    a = next(i for i, l in enumerate(lines) if "Current Frozen List" in l)
    b = next(i for i, l in enumerate(lines) if "DEFUNCT RULE" in l and i > a)
    out = []
    for s in (l.strip() for l in lines[a + 1:b]):
        m = re.match(r"^(.+?)\s*\((.+?)\)?$", clean_quotes(s))
        if not m or "Cards on this list" in s:
            continue
        name = m[1].strip()
        prints = []
        for p in m[2].split(","):
            p = p.strip().rstrip(")")
            mm = re.match(rf"^(.*?)\s+({NUM})$", p)
            if mm:
                prints.append({"set": mm[1], "number": mm[2]})
        out.append({"name": name, "printings": prints})
    return out


def parse_gold(path):
    lines = open(path, encoding="utf-8").read().split("\n")
    a = next(i for i, l in enumerate(lines) if l.strip() == "Gold Title Reprints")
    out, sec = [], None
    for l in lines[a + 3:]:
        s = l.strip()
        if s in ("Premiere Set", "Heroes & Villains"):
            sec = s
            continue
        if not s or sec is None:
            continue
        for nm in re.split(r"\s{2,}", s):
            nm = nm.strip()
            if nm:
                out.append({"name": nm, "set": 1 if sec == "Premiere Set" else 2,
                            "crossed_out": nm in GOLD_CROSSED})
    return out


def main():
    entries = parse_fanz(CRD / "fanz.txt") + parse_panz(CRD / "panz.txt")
    save_json(CRD / "entries.json", entries)
    save_json(CRD / "frozen.json", parse_frozen(CRD / "fanz.txt"))
    save_json(CRD / "gold.json", parse_gold(CRD / "fanz.txt"))
    f = sum(e["source"].startswith("FanZ") for e in entries)
    print(f"FanZ entries {f}, Panini entries {len(entries) - f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
