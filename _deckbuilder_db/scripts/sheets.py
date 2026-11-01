"""Build review sheets for the vision pass.

Layouts (chosen per image; every sheet stays within ~1568 px so nothing is downscaled again):
  hi-res portrait personality (short side >= 600): whole card at 0.66, 3 per sheet
  hi-res portrait other: title band + text area (art cropped out) at 0.66, 6 per sheet
  hi-res landscape: whole card at 0.66, 4 per sheet
  lo-res portrait personality (PanZ scans ~465 px): whole card at 1.0, 3 per sheet
  lo-res portrait other: title band + text area at 1.0, 6 per sheet
  lo-res landscape: whole card scaled to ~700 px wide, 4 per sheet
Personalities are detected from the OCR stage column (>= 7 numbers) or "LEVEL" in the header,
or the PZP MP/Ally folders. A miss only means a cropped tile; the original is opened then.
Trait reference cards (collection "trait") are shown whole like personalities.

Usage: python sheets.py --sets S02,S03
Writes work/sheets/<set_code>/NNN.png and work/sheets/<set_code>/manifest.json
"""
import argparse
import re
import sys

from PIL import Image, ImageDraw, ImageFont

from common import INVENTORY, OCR_CACHE, ROOT, SHEETS, load_json, save_json


def _font(size):
    for f in (r"C:\Windows\Fonts\arialbd.ttf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"):
        try:
            return ImageFont.truetype(f, size)
        except OSError:
            pass
    return ImageFont.load_default(size)


FONT = _font(14)
LABEL_H = 18
GAP = 6
HI = 0.66
# kind -> (cards per sheet, columns)
PLAN = {"hi_full": (3, 3), "hi_crop": (6, 3), "hi_land": (4, 2),
        "lo_full": (3, 3), "lo_crop": (6, 3), "lo_land": (4, 2)}


def is_personality(row):
    if row["collection"] in ("promo_mp", "promo_ally", "trait"):
        return True
    if row["orientation"] != "portrait":
        return False
    o = load_json(OCR_CACHE / f"{row['card_id']}.json", {}) or {}
    reg = o.get("regions", {})
    nums = re.findall(r"\d[\d,]*", reg.get("stages", {}).get("text", ""))
    return len(nums) >= 7 or "LEVEL" in reg.get("header", {}).get("text", "").upper()


def label(img, text):
    out = Image.new("RGB", (img.width, img.height + LABEL_H), "white")
    out.paste(img, (0, LABEL_H))
    ImageDraw.Draw(out).text((3, 1), text, fill="black", font=FONT)
    return out


def scaled(im, s):
    return im if s == 1 else im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)


def tile_for(row):
    with Image.open(ROOT / row["rel_path"]) as im:
        im = im.convert("RGB")
    w, h = im.size
    hi = min(w, h) >= 600
    tag = f"{row['card_id']} | {row['filename']}"
    if row["orientation"] == "landscape":
        return ("hi_land" if hi else "lo_land"), label(scaled(im, 700 / w if not hi else HI), tag)
    s = HI if hi else 1
    if is_personality(row):
        return ("hi_full" if hi else "lo_full"), label(scaled(im, s), tag)
    top = im.crop((0, 0, w, int(0.16 * h)))
    low = im.crop((0, int(0.50 * h), w, int(0.95 * h)))
    both = Image.new("RGB", (w, top.height + low.height + 4), "gray")
    both.paste(top, (0, 0))
    both.paste(low, (0, top.height + 4))
    return ("hi_crop" if hi else "lo_crop"), label(scaled(both, s), tag)


def grid(tiles, cols):
    rows_n = (len(tiles) + cols - 1) // cols
    tw = max(t.width for t in tiles)
    th = max(t.height for t in tiles)
    sheet = Image.new("RGB", (tw * cols + GAP * (cols - 1), th * rows_n + GAP * (rows_n - 1)),
                      "black")
    for i, t in enumerate(tiles):
        sheet.paste(t, ((i % cols) * (tw + GAP), (i // cols) * (th + GAP)))
    if max(sheet.size) > 1568:
        s = 1568 / max(sheet.size)
        sheet = sheet.resize((int(sheet.width * s), int(sheet.height * s)), Image.LANCZOS)
    return sheet


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sets", required=True)
    a = ap.parse_args()
    inv = load_json(INVENTORY)
    for code in a.sets.split(","):
        rows = sorted([r for r in inv if r["set_code"] == code],
                      key=lambda r: (r["collection"], r["prefix"] or "", r["number"] or 0,
                                     r["card_id"]))
        outdir = SHEETS / code
        outdir.mkdir(parents=True, exist_ok=True)
        for old in outdir.glob("*.png"):
            old.unlink()
        manifest, buf, n = [], [], 0

        def flush():
            nonlocal buf, n
            if not buf:
                return
            n += 1
            name = f"{n:03d}.png"
            grid([t for _, _, t in buf], PLAN[buf[0][1]][1]).save(outdir / name)
            manifest.append({"sheet": name, "kind": buf[0][1],
                             "card_ids": [c for c, _, _ in buf]})
            buf = []

        for r in rows:
            kind, tile = tile_for(r)
            if buf and (buf[0][1] != kind or len(buf) >= PLAN[kind][0]):
                flush()
            buf.append((r["card_id"], kind, tile))
        flush()
        save_json(outdir / "manifest.json", manifest)
        print(f"{code}: {len(rows)} cards -> {n} sheets", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
