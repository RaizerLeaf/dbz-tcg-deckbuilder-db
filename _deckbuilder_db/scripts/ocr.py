"""OCR first pass: Tesseract on cropped regions of each card image.

Usage: python ocr.py [--sets S01,S14,PZP] [--workers 12]
Writes cache/ocr/<card_id>.json; existing files are skipped (resumable).
OCR is a cross-check only. Icons are invisible to it; the vision pass is authoritative.
"""
import argparse
import shutil
import sys
import time
from multiprocessing import Pool

import pytesseract
from PIL import Image, ImageOps

from common import INVENTORY, OCR_CACHE, ROOT, load_json, save_json

pytesseract.pytesseract.tesseract_cmd = (shutil.which("tesseract")
                                         or r"C:\Program Files\Tesseract-OCR\tesseract.exe")

# (x0, y0, x1, y1) as fractions of the card. Generous on purpose: layouts shift a little
# between PanZ and FanZ printings.
REGIONS = {
    "portrait": {
        "header": (0.0, 0.02, 1.0, 0.16),
        "stages": (0.66, 0.13, 0.97, 0.72),
        "lower": (0.0, 0.52, 1.0, 0.93),
    },
    "landscape": {
        "header": (0.30, 0.03, 1.0, 0.17),
        "lower": (0.15, 0.66, 0.85, 0.95),
    },
}


def ocr_region(img, psm, whitelist=None):
    cfg = f"--psm {psm}"
    if whitelist:
        cfg += f" -c tessedit_char_whitelist={whitelist}"
    best = None
    # Title and stage bars are light-on-dark over texture; try the plain crop plus a
    # bright-text threshold (white glyphs -> black on white) and keep the better read.
    bright = img.point(lambda v: 0 if v > 185 else 255)
    for variant in (img, bright):
        d = pytesseract.image_to_data(variant, config=cfg, output_type=pytesseract.Output.DICT)
        words = [(t, float(c)) for t, c in zip(d["text"], d["conf"]) if t.strip() and float(c) >= 0]
        conf = sum(c for _, c in words) / len(words) if words else 0.0
        text = pytesseract.image_to_string(variant, config=cfg).strip() if words else ""
        if best is None or conf > best["conf"]:
            best = {"text": text, "conf": round(conf, 1), "n_words": len(words)}
    return best


def process(row):
    out = OCR_CACHE / f"{row['card_id']}.json"
    if out.exists():
        return row["card_id"], "cached"
    try:
        with Image.open(ROOT / row["rel_path"]) as im:
            im = im.convert("L")
            short = min(im.size)
            scale = max(1.0, 1500 / short)           # PanZ scans are ~465 px wide
            if scale > 1.0:
                im = im.resize((round(im.width * scale), round(im.height * scale)), Image.LANCZOS)
            res = {}
            for name, (x0, y0, x1, y1) in REGIONS[row["orientation"]].items():
                crop = im.crop((int(x0 * im.width), int(y0 * im.height),
                                int(x1 * im.width), int(y1 * im.height)))
                if name == "stages":
                    res[name] = ocr_region(crop, 6, "0123456789,")
                else:
                    res[name] = ocr_region(crop, 6)
        save_json(out, {"card_id": row["card_id"], "rel_path": row["rel_path"],
                        "scale": round(scale, 2), "regions": res})
        return row["card_id"], "ok"
    except Exception as e:  # never skip silently
        save_json(out, {"card_id": row["card_id"], "rel_path": row["rel_path"], "error": repr(e)})
        return row["card_id"], f"error {e!r}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sets", default="", help="comma list of set codes, e.g. S01,S14,PZP")
    ap.add_argument("--workers", type=int, default=12)
    a = ap.parse_args()
    rows = load_json(INVENTORY)
    if a.sets:
        want = set(a.sets.split(","))
        rows = [r for r in rows if r["set_code"] in want]
    todo = [r for r in rows if not (OCR_CACHE / f"{r['card_id']}.json").exists()]
    print(f"{len(rows)} selected, {len(rows) - len(todo)} cached, {len(todo)} to OCR", flush=True)
    t0 = time.time()
    with Pool(a.workers) as pool:
        for i, (cid, status) in enumerate(pool.imap_unordered(process, todo), 1):
            if status.startswith("error"):
                print(f"  {cid}: {status}", flush=True)
            if i % 50 == 0 or i == len(todo):
                el = time.time() - t0
                print(f"  {i}/{len(todo)}  {el:.0f}s elapsed, ~{el / i * (len(todo) - i):.0f}s left", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
