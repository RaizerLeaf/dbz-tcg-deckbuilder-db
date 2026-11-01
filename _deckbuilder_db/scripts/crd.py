"""Phase 3: attach CRD errata / rulings / Frozen List / Gold Title Reprint data to the card records.

Reads : work/full/cards.json (Phase 2 base, never modified), work/crd/entries.json, frozen.json, gold.json
        (made by crd_parse.py)
Writes: cards.json, cards.csv (final records), work/crd/match_report.json, work/crd/unmatched.json

New / changed fields per card
  text_current        printed text with the erratum applied; equals text_as_printed when the printing
                      already shows the corrected wording; null when an erratum could not be applied
  errata_status       None | 'printing_current' | 'text_current_derived' | 'unresolved'
  errata_note         readable summary of the ERRATUM entries (original, updated, MRP pointers)
  ruling_note         readable summary of RULING entries (FanZ CRD and Panini CRD)
  card_type_current   only when an erratum changes the card type
  crd_entries         structured list of every CRD entry attached (source, kind, match method, status)
  is_mrp              True = this printing is named as (or shows) the most recent printing of an errata'd
                      card; False = errata'd card, this printing is not the MRP; null = no erratum
  frozen, frozen_listed_printing, gold_title_reprint, gold_title_note
  limit_per_deck, restrictions, deck_rules, keywords, icons  re-derived from the current text
Text is never invented: text_current is either the printed text, a verbatim CRD replacement of a span of
the printed text, or the printed text plus the CRD's "This Card Gains" line.
"""
import copy
import csv
import difflib
import json
import re
import sys

from common import DB, load_json, save_json
from crd_parse import clean_quotes, REF_SET, NUM
from derive import KEYWORDS, ICONS, derive_restrictions

CRD = DB / "work" / "crd"


# ----------------------------------------------------------------------------- text helpers
def tok_norm(t):
    t = clean_quotes(t).lower()
    m = {"[sword icon]": "tkattack", "[attack]": "tkattack", "[defense]": "tkdefense",
         "[continuous]": "tkcontinuous", "∞": "tkcontinuous", "[instant]": "tkinstant",
         "Ϟ": "tkinstant", "[desperation]": "tkdesperation", "[warning]": "tkwarning"}
    if t in m:
        return m[t]
    mm = re.match(r"^\[(?:trait:)?(\w+)(?: trait)?\]$", t)
    if mm:
        return "tktrait" + mm[1]
    return re.sub(r"[^a-z0-9]", "", t)


TOKEN_RE = re.compile(r"\[[^\]]+\]|∞|Ϟ|[A-Za-z0-9]+")


def tokens(s):
    raw = [(tok_norm(m[0]), m.start(), m.end()) for m in TOKEN_RE.finditer(s) if tok_norm(m[0])]
    out = []
    for t, a, b in raw:
        # FanZ text style: "anger 2 levels" == "anger 2"; "shield icon" == the Defense icon
        if t in ("level", "levels") and len(out) >= 2 and out[-1][0].isdigit() and out[-2][0] == "anger":
            continue
        if t == "icon" and out and out[-1][0] == "shield":
            out[-1] = ("tkdefense", out[-1][1], b)
            continue
        out.append((t, a, b))
    return out


def conv_crd(s):
    """CRD notation -> the notation used in text_as_printed."""
    s = clean_quotes(s)
    s = re.sub(r"\[CARD TYPE:[^\]]*\]\s*", "", s)
    s = s.replace("[Sword Icon]", "[Attack]")
    s = re.sub(r"\[(\w+) Trait\]", r"[Trait:\1]", s)
    s = re.sub(r"\((\w+) Trait only\.\)", r"([Trait:\1] only.)", s)
    s = s.replace("Ϟ", "[Instant]").replace("∞", "[Continuous]")
    return re.sub(r"\s+", " ", s).strip()


def find_span(text, snippet):
    """Locate the token sequence of snippet inside text; return (start, end) char span or None."""
    a = tokens(text)
    b = [t for t, _, _ in tokens(conv_crd(snippet))]
    if not b:
        return None
    n = len(b)
    for i in range(len(a) - n + 1):
        if [t for t, _, _ in a[i:i + n]] == b:
            start, end = a[i][1], a[i + n - 1][2]
            mlev = re.match(r"\s+levels?\b", text[end:])
            if mlev and a[i + n - 1][0].isdigit():
                end += mlev.end()
            tail = re.search(r"[^A-Za-z0-9\]]*$", clean_quotes(snippet).strip())
            tail = tail[0] if tail else ""
            while tail and text[end:end + len(tail)] == tail:
                end += len(tail)
                break
            if clean_quotes(snippet).lstrip().startswith("(") and start > 0 and text[start - 1] == "(":
                start -= 1
            return start, end
    return None


def contains(text, snippet):
    return find_span(text, snippet) is not None


def norm_name(s):
    s = clean_quotes(s or "").lower()
    s = re.sub(r"[^a-z0-9 ]", " ", s.replace("'", ""))
    return re.sub(r"\s+", " ", s).strip()


def full_name(c):
    return (c["card_name"] + (" " + c["subtitle"] if c.get("subtitle") else "")).strip()


def name_ok(entry_name, c, thr=0.82):
    a, b = norm_name(entry_name), norm_name(full_name(c))
    b2 = norm_name(c["card_name"])
    if not a:
        return False
    if a == b:
        return True
    if c.get("subtitle"):   # personalities: the subtitle must agree, not just the character name
        return difflib.SequenceMatcher(None, a, b).ratio() >= max(thr, 0.88)
    if a == b2 or (len(b2) > 4 and (b2.startswith(a) or a.startswith(b2))):
        return True
    return difflib.SequenceMatcher(None, a, b2).ratio() >= thr


def num_key(card_number):
    return (card_number or "").split()[-1].upper() if card_number else ""


# ----------------------------------------------------------------------------- indexes
def build_index(cards):
    idx = {}
    for c in cards:
        c["_set_code"] = c["card_id"].split("_")[0]
        sk = "OP" if c["_set_code"].startswith("OP") else c["set_number"]
        if c["_set_code"] == "PZP":
            sk = "PZP"
        c["_sk"] = sk
        idx.setdefault((sk, num_key(c["card_number"])), []).append(c)
    return idx


def resolve_set_name(txt):
    m = re.search(r"OP Series (OP\d)", txt)
    if m:
        return "OP"
    for nm, n in sorted(REF_SET, key=lambda x: -len(x[0])):
        if nm in txt:
            return n
    return None


# ----------------------------------------------------------------------------- applying errata
def type_from_crd(txt):
    t = txt.replace("[", "").replace("]", "").replace("CARD TYPE:", "").strip()
    return {"Hero Ally": "Ally", "Hero": "Main Personality"}.get(t, t)


OVERRIDES = load_json(CRD / "overrides.json", {})


def apply_override(cur, ov):
    if ov["action"] == "printing_current":
        return cur, "printing_current", {"override": ov["reason"]}
    if ov["action"] == "set_text":
        return ov["text"], "text_current_derived", {"override": ov["reason"]}
    new = cur
    for find, rep in ov["edits"]:
        if find == "PREPEND":
            new = rep + (" " if "\n" not in new else "\n") + new
        elif find in new:
            new = new.replace(find, rep, 1)
        else:
            return cur, "unresolved", {"why": f"override edit text not found: {find!r}"}
    return new, "text_current_derived", {"override": ov["reason"]}


def apply_erratum(cur, e, card):
    """Return (new_text, status, detail). Status strings are stable (used in the report)."""
    final = e.get("fanz_updated_text") or e.get("updated_text") or e.get("panini_updated_text")
    orig = e.get("original_text")
    gains, loses = e.get("gains"), e.get("loses")
    # card-type errata
    probe = " ".join(x for x in (orig, final, gains) if x)
    if "CARD TYPE" in probe:
        want = type_from_crd(final or gains)
        have = card["card_type"]
        if "Hero" in (final or gains or "") and have in ("Main Personality", "Ally"):
            ok = have == "Ally"
        else:
            ok = have == want
        return cur, ("printing_current" if ok else "type_changed"), ({} if ok else {"card_type_current": want})
    if gains:
        g = conv_crd(gains)
        if g == "[Attack]":
            if "[Attack]" in cur:
                return cur, "printing_current", {}
            m = re.search(r"(?<![A-Za-z])(Physical|Energy) attack", cur)
            if m:
                return cur[:m.start()] + "[Attack] " + cur[m.start():], "text_current_derived", {"how": "attack icon added"}
            return cur, "unresolved", {"why": "no attack line to attach the icon to"}
        if contains(cur, g):
            return cur, "printing_current", {}
        m = re.match(r"^ENDURANCE (\d+)$", g)
        if m:
            if re.search(r"ENDURANCE \d+", cur):
                return cur, "unresolved", {"why": "printing shows a different Endurance value"}
            return f"ENDURANCE {m[1]}.\n" + cur if "\n" in cur else f"ENDURANCE {m[1]}. " + cur, \
                "text_current_derived", {"how": "endurance line added"}
        sep = "\n" if "\n" in cur else " "
        lead = re.match(r"^(ENDURANCE \d+\.)[\n ]", cur)
        if lead:
            return cur[:lead.end(1)] + sep + g + sep + cur[lead.end():].lstrip("\n "), \
                "text_current_derived", {"how": "gained line added after the Endurance line"}
        return g + sep + cur, "text_current_derived", {"how": "gained line added at the start"}
    if loses:
        sp = find_span(cur, loses)
        if not sp:
            return cur, "printing_current", {"how": "lost line not present"}
        new = (cur[:sp[0]] + cur[sp[1]:]).replace("  ", " ").strip(" \n")
        return new, "text_current_derived", {"how": "line removed"}
    if final:
        if contains(cur, final):
            return cur, "printing_current", {}
        # printing may show the intermediate Panini wording
        pu = e.get("panini_updated_text")
        for old in [x for x in (orig, pu) if x and x != final]:
            sp = find_span(cur, old)
            if sp:
                return cur[:sp[0]] + conv_crd(final) + cur[sp[1]:], "text_current_derived", \
                    {"how": "verbatim span replaced"}
        return cur, "unresolved", {"why": "neither the original nor the updated wording was found in the printed text"}
    return cur, "unresolved", {"why": "entry has no replacement text"}


# ----------------------------------------------------------------------------- main
def main():
    cards = copy.deepcopy(load_json(DB / "work" / "full" / "cards.json"))
    idx = build_index(cards)
    by_id = {c["card_id"]: c for c in cards}
    entries = load_json(CRD / "entries.json")
    frozen = load_json(CRD / "frozen.json")
    gold = load_json(CRD / "gold.json")
    for c in cards:
        c["_attached"] = []  # structured entries
        c["_mrp"] = None
        c["_status"] = []

    unmatched, match_log = [], []

    def match_spec(e, spec):
        sk = e["section_set"]
        found, notes, weak = [], [], []
        missing = []
        for n in spec["numbers"]:
            cand = idx.get((sk, n), [])
            ok = [c for c in cand if name_ok(spec["name"], c)]
            if ok:
                found += [(c, "number+name") for c in ok]
            else:
                missing.append(n)
                if len(cand) == 1:
                    weak.append((cand[0], n))
                elif cand:
                    notes.append(f"{n}: {len(cand)} candidates, none matches name '{spec['name']}'")
        if missing:  # a number that does not carry this name: look for the name in the same set
            pool = [c for c in cards if c["_sk"] == sk and name_ok(spec["name"], c, 0.9)
                    and c["card_id"] not in {x.get("card_id") for x, _ in found}]
            if pool:
                found += [(c, "name_only") for c in pool]
                notes.append(f"number(s) {missing} do not match this name in the records; matched by name")
            elif not found:
                for c, n in weak:   # last resort: the number alone (name differs)
                    found.append((c, "number_only"))
                    notes.append(f"{n}: name '{spec['name']}' vs card '{full_name(c)}'")
        seen, out = set(), []
        for c, how in found:
            if c["card_id"] not in seen:
                seen.add(c["card_id"])
                out.append((c, how))
        return out, notes

    fanz_hits = {}  # card_id -> list of FanZ entry records
    for e in [x for x in entries if x["source"].startswith("FanZ")]:
        e["_matched"] = []
        for spec in e["cards"]:
            m, notes = match_spec(e, spec)
            if not m:
                unmatched.append({"source": e["source"], "kind": e["kind"], "section": e["section"],
                                  "numbers": spec["numbers"], "name": spec["name"], "notes": notes})
            for c, how in m:
                e["_matched"].append((c["card_id"], how, notes))
        for cid, how, notes in e["_matched"]:
            fanz_hits.setdefault(cid, []).append(e)

    # --- apply errata & attach rulings -------------------------------------------------------
    def record(c, e, how, notes, status=None, detail=None, listed=True):
        rec = {"source": e["source"], "kind": e["kind"], "match": how, "listed_for_this_printing": listed}
        if notes:
            rec["match_notes"] = notes
        if e["kind"] == "ERRATUM":
            for k in ("original_text", "panini_updated_text", "fanz_updated_text", "updated_text", "gains",
                      "loses", "mrp_raw", "note_raw"):
                if e.get(k):
                    rec[k] = e[k]
            rec["status"] = status
            if detail:
                rec["detail"] = detail
        else:
            rec["ruling_text"] = e["ruling_text"]
        rec["crd_heading"] = "{} {}".format("/".join(e["cards"][0]["numbers"]), e["cards"][0]["name"]) \
            if len(e["cards"]) == 1 else " and ".join("/".join(s["numbers"]) + " " + s["name"] for s in e["cards"])
        rec["crd_section"] = e["section"]
        c["_attached"].append(rec)

    errata_entries = [e for e in entries if e["source"].startswith("FanZ") and e["kind"] == "ERRATUM"]
    for e in [x for x in entries if x["source"].startswith("FanZ")]:
        for cid, how, notes in e["_matched"]:
            c = by_id[cid]
            if e["kind"] == "ERRATUM":
                new, status, detail = apply_erratum(c.get("_cur", c["text_as_printed"]), e, c)
                if status == "unresolved":
                    ov = OVERRIDES.get(f"{c['card_id']}|{e['cards'][0]['numbers'][0]}")
                    if ov:
                        new, status, detail = apply_override(c.get("_cur", c["text_as_printed"]), ov)
                if status == "type_changed":
                    c["card_type_current"] = detail["card_type_current"]
                elif status == "printing_current" and detail.get("card_type_current"):
                    pass
                c["_cur"] = new
                c["_status"].append(status)
                record(c, e, how, notes, status, detail)
            else:
                record(c, e, how, notes)

    # --- propagate by content to unlisted printings with the same card name ----------------------
    prop_log = []
    for e in errata_entries:
        listed = {cid for cid, _, _ in e["_matched"]}
        if not listed:
            continue
        ref = by_id[next(iter(listed))]
        target = norm_name(full_name(ref))
        for c in cards:
            if c["card_id"] in listed or norm_name(full_name(c)) != target or c["card_type"] != ref["card_type"]:
                continue
            final = e.get("fanz_updated_text") or e.get("updated_text") or e.get("panini_updated_text")
            probe = e.get("original_text") or e.get("gains") or final
            if "CARD TYPE" in " ".join(x for x in (e.get("original_text"), final, e.get("gains")) if x):
                continue
            cur = c.get("_cur", c["text_as_printed"])
            if final and contains(cur, final) or (e.get("gains") and contains(cur, conv_crd(e["gains"]))):
                record(c, e, "name_propagation", [], "printing_current", None, listed=False)
                c["_status"].append("printing_current")
                prop_log.append((c["card_id"], "shows updated wording"))
            elif e.get("original_text") and contains(cur, e["original_text"]):
                new, status, detail = apply_erratum(cur, e, c)
                c["_cur"] = new
                c["_status"].append(status)
                record(c, e, "name_propagation", [], status, detail, listed=False)
                prop_log.append((c["card_id"], "original wording found -> " + status))
    for e in [x for x in entries if x["source"].startswith("FanZ") and x["kind"] == "RULING"]:
        listed = {cid for cid, _, _ in e["_matched"]}
        for cid in list(listed):
            ref = by_id[cid]
            for c in cards:
                if c["card_id"] not in listed and norm_name(full_name(c)) == norm_name(full_name(ref)) \
                        and c["card_type"] == ref["card_type"] and ref["card_type"] not in ("Main Personality", "Ally"):
                    record(c, e, "name_propagation", [], listed=False)
                    listed.add(c["card_id"])

    # --- Panini CRD entries --------------------------------------------------------------------
    for e in [x for x in entries if x["source"].startswith("Panini")]:
        e["_matched"] = []
        for spec in e["cards"]:
            m, notes = match_spec(e, spec)
            if not m:
                unmatched.append({"source": e["source"], "kind": "RULING", "section": e["section"],
                                  "numbers": spec["numbers"], "name": spec["name"], "notes": notes})
            for c, how in m:
                dup = any(r["source"].startswith("FanZ") for r in c["_attached"]
                          if r.get("listed_for_this_printing"))
                rec_how = how
                c["_attached"].append({"source": e["source"], "kind": "RULING", "match": rec_how,
                                       "listed_for_this_printing": True, "ruling_text": e["ruling_text"],
                                       "crd_heading": "/".join(spec["numbers"]) + " " + spec["name"],
                                       "crd_section": e["section"], "also_in_fanz_crd": dup,
                                       **({"match_notes": notes} if notes else {})})

    # --- MRP resolution --------------------------------------------------------------------------
    mrp_true, mrp_unresolved = set(), []

    def resolve_ref(txt, e, own):
        out = []
        sk_default = e["section_set"]
        pat = re.compile(rf"(?:(?P<set>FanZ )?(?P<nm>Heroes & Villains|Movie Collection [23]|The Movie Collection|"
                         rf"Movie Collection|Premiere|Evolution|Perfection|Vengeance|Awakening|Celestial Tournament|"
                         rf"Legends|Revelation|Escalation|Fusion|Showdown|Super Premier|Premier: Dragon Ball Super|"
                         rf"Universal Clash: Dragon Ball Super|Universal Clash|OP Series OP\d)"
                         rf"(?: Promos?)?\s+)?(?P<num>{NUM}|PXX)(?:/(?P<n2>{NUM}))?(?P<rest>[^,;]*)")
        for m in pat.finditer(txt):
            sk = resolve_set_name(m["nm"]) if m["nm"] else sk_default
            if sk is None:
                continue
            for n in [m["num"], m["n2"]]:
                if not n:
                    continue
                if n == "PXX":
                    nm = re.sub(r"^[\s\-]+", "", clean_quotes(m["rest"]))
                    cands = [c for c in cards if c["_sk"] == sk and norm_name(c["card_name"]) == norm_name(nm)]
                else:
                    cands = idx.get((sk, n), [])
                    nm = re.sub(r"^[\s\-]+", "", clean_quotes(m["rest"]))
                    if nm:
                        good = [c for c in cands if name_ok(nm, c)]
                        cands = good or cands
                out += cands
        return out

    for e in errata_entries:
        own = [by_id[cid] for cid, _, _ in e["_matched"]]
        mrp = (e.get("mrp_raw") or "")
        note = (e.get("note_raw") or "")
        targets = []
        if re.match(r"^None", mrp):
            pass
        elif "currently up to date in" in mrp:
            m = re.search(r"in the (.*?) card images\s*(.*)$", mrp.rstrip("."))
            sk = resolve_set_name(m[1]) if m else None
            extra = m[2].strip() if m else ""
            if extra:
                targets = resolve_ref(extra, {"section_set": sk}, own)
            else:
                targets = [c for c in own if c["_sk"] == sk or (sk is None)]
            if not targets:
                mrp_unresolved.append((e["raw"][:60], mrp))
        elif mrp:
            targets = resolve_ref(mrp, e, own)
            if not targets:
                mrp_unresolved.append((e["raw"][:60], mrp))
        if "matches the printed text of" in note:
            targets += resolve_ref(note.split("matches the printed text of")[1], e, own)
        for c in targets:
            mrp_true.add(c["card_id"])
        e["_mrp_targets"] = [c["card_id"] for c in targets]

    # --- finalize card fields ------------------------------------------------------------------
    for c in cards:
        c["is_mrp"] = None
        c["errata_status"] = None
        c.setdefault("card_type_current", None)
        eps = [r for r in c["_attached"] if r["kind"] == "ERRATUM"]
        rls = [r for r in c["_attached"] if r["kind"] != "ERRATUM"]
        if eps:
            st = c["_status"]
            if "unresolved" in st:
                c["errata_status"] = "unresolved"
                c["text_current"] = None
                c["needs_review"] = True
                c["review_reason"] = "; ".join(filter(None, [c.get("review_reason"),
                                               "CRD erratum could not be applied automatically; read errata_note"]))
            elif c.get("_cur") and c["_cur"] != c["text_as_printed"]:
                c["errata_status"] = "text_current_derived"
                c["text_current"] = c["_cur"]
            else:
                c["errata_status"] = "printing_current" if all(s in ("printing_current", "type_changed") for s in st) else "printing_current"
                c["text_current"] = c["text_as_printed"]
            if any(s == "type_changed" for s in st):
                c["errata_status"] = "text_current_derived" if c["errata_status"] == "printing_current" else c["errata_status"]
            c["is_mrp"] = c["card_id"] in mrp_true
            lines = []
            for r in eps:
                bits = [f"{r['source']} {r['crd_section']} {r['crd_heading']}"]
                if not r["listed_for_this_printing"]:
                    bits.append("(same card name; this printing not listed separately)")
                if r.get("original_text"):
                    bits.append(f"Original: \"{r['original_text']}\"")
                if r.get("panini_updated_text"):
                    bits.append(f"Panini updated: \"{r['panini_updated_text']}\"")
                if r.get("fanz_updated_text"):
                    bits.append(f"FanZ updated: \"{r['fanz_updated_text']}\"")
                if r.get("updated_text"):
                    bits.append(f"Updated: \"{r['updated_text']}\"")
                if r.get("gains"):
                    bits.append(f"Gains: \"{r['gains']}\"")
                if r.get("loses"):
                    bits.append(f"Loses: \"{r['loses']}\"")
                if r.get("mrp_raw"):
                    bits.append(f"MRP: {r['mrp_raw']}")
                if r.get("note_raw"):
                    bits.append(f"Note: {r['note_raw']}")
                bits.append({"printing_current": "This printing already shows the updated wording.",
                             "text_current_derived": "text_current = printed text with this erratum applied.",
                             "type_changed": "Card type corrected by the erratum (see card_type_current).",
                             "unresolved": "Could not be applied automatically."}[r["status"]])
                lines.append(" | ".join(bits))
            c["errata_note"] = "\n".join(lines)
        else:
            c["errata_note"] = None
            c["text_current"] = None
        c["ruling_note"] = "\n".join(
            f"{r['source']} {r['crd_section']} {r['crd_heading']}: {r['ruling_text']}"
            + ("" if r["listed_for_this_printing"] else " (same card name; this printing not listed separately)")
            for r in rls) or None
        c["crd_entries"] = c["_attached"]

    # --- Frozen list ---------------------------------------------------------------------------
    frozen_report = []
    for f in frozen:
        tgt = norm_name(f["name"].replace(",", " "))
        hit = [c for c in cards if norm_name(full_name(c)) == tgt or norm_name(c["card_name"]) == tgt]
        listed = set()
        for p in f["printings"]:
            sk = resolve_set_name(p["set"])
            found = [c for c in idx.get((sk, p["number"]), []) if norm_name(c["card_name"]) == norm_name(hit[0]["card_name"] if hit else f["name"])]
            if found:
                listed |= {c["card_id"] for c in found}
            else:
                frozen_report.append({"name": f["name"], "printing": p, "problem": "listed printing not found in the records"})
        if not hit:
            frozen_report.append({"name": f["name"], "problem": "no card with this name in the records"})
        for c in hit:
            c["_frozen"] = True
            c["_frozen_listed"] = c["card_id"] in listed
    for c in cards:
        flag = "Frozen" in c["filename_flags"]
        c["frozen_filename_flag"] = flag
        c["frozen"] = bool(c.get("_frozen"))
        c["frozen_listed_printing"] = bool(c.get("_frozen_listed"))
        if flag and not c["frozen"]:
            frozen_report.append({"card_id": c["card_id"], "problem": "filename says Frozen but the name is not on the CRD list"})
    # --- Gold title reprints ----------------------------------------------------------------------
    gmap = {(norm_name(g["name"]), g["set"]): g for g in gold}
    for c in cards:
        c["gold_title_reprint"] = None
        c["gold_title_note"] = None
        g = gmap.get((norm_name(c["card_name"]), c["set_number"]))
        if g:
            c["gold_title_reprint"] = not g["crossed_out"]
            c["gold_title_note"] = ("On the CRD Gold Title Reprint list" + (" but crossed out (redacted): the original Score "
                                    "Entertainment card may NOT replace it." if g["crossed_out"] else
                                    ": the original Score Entertainment card of the same title may replace it in official FanZ tournaments."))
    # --- derived fields from the current text ----------------------------------------------------
    for c in cards:
        eff = c["text_current"] or c["text_as_printed"] or ""
        lim = re.search(r"Limit (\d+) per deck", eff)
        c["limit_per_deck_printed"] = c.get("limit_per_deck")
        c["limit_per_deck"] = int(lim[1]) if lim else None
        c["restrictions"], c["deck_rules"] = derive_restrictions(eff)
        c["icons"] = sorted({i for i in ICONS if f"[{i}]" in eff}) + \
            [f"Trait:{t}" for t in sorted(set(re.findall(r"\[Trait:([^\]]+)\]", eff)))]
        kw = [k for k in KEYWORDS if re.search(rf"\b{k}\b", eff)]
        for k in ("Remain", "Foresee"):
            kw += [f"{k} {n}" for n in re.findall(rf"\b{k} (\d+)", eff)]
        end = re.search(r"\bENDURANCE (\d+)", eff)
        if end:
            kw.append(f"Endurance {end[1]}")
        if re.search(r"Banish after use", eff):
            kw.append("Banish after use")
        c["keywords"] = kw

    # --- write ------------------------------------------------------------------------------------
    for c in cards:
        for k in [k for k in c if k.startswith("_")]:
            del c[k]
    save_json(DB / "cards.json", cards)
    with open(DB / "cards.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(cards[0].keys()))
        w.writeheader()
        for c in cards:
            w.writerow({k: (json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict)) else v)
                        for k, v in c.items()})
    save_json(CRD / "unmatched.json", unmatched)
    save_json(CRD / "match_report.json", {"frozen_problems": frozen_report, "mrp_unresolved": mrp_unresolved,
                                          "name_propagation": prop_log})
    n_err = sum(1 for c in cards if c["errata_status"])
    from collections import Counter
    print("cards with errata:", n_err, dict(Counter(c["errata_status"] for c in cards if c["errata_status"])))
    print("cards with ruling:", sum(1 for c in cards if c["ruling_note"]), "| frozen:", sum(c["frozen"] for c in cards),
          "| gold:", Counter(c["gold_title_reprint"] for c in cards), "| mrp True:", sum(1 for c in cards if c["is_mrp"]))
    print("unmatched CRD entries:", len(unmatched), "| unresolved MRP refs:", len(mrp_unresolved))
    return 0


if __name__ == "__main__":
    sys.exit(main())
