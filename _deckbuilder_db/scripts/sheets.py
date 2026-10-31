"""Build review sheets for the vision pass.

Personality cards (MP/Ally layout) and Masteries are shown whole; FanZ personalities also
get a zoomed strip of the Trait icon area. Other cards are shown as header + lower text
area (the art is cropped out) and tiled several to a sheet. Each tile is labelled with its
card_id. Sheets are sized to avoid downscaling when viewed.

Usage: python sheets.py --sets S01,S14,PZP
Writes work/sheets/<set_code>/NNN.png and work/sheets/<set_code>/manifest.json
"""
import argparse
import re
import sys

from PIL import Image, ImageDraw, ImageFont

from common import INVENTORY, OCR_CACHE, ROOT, SHEETS, load_json, save_json

FONT = ImageFont.truetype(r"C:\Windows\Fonts\arialbd.ttf", 18)
MAX_PX = 1_150_000
LABEL_H = 24


def is_personality(row):
    if row["collection"] in ("promo_mp", "promo_ally"):
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
    ImageDraw.Draw(out).text((4, 2), text, fill="black", font=FONT)
    return out


def tile_for(row):
    with Image.open(ROOT / row["rel_path"]) as im:
        im = im.convert("RGB")
    w, h = im.size
    tag = f"{row['card_id']}  |  {row['filename']}"
    if row["orientation"] == "landscape":
        return "full", label(im, tag)
    if is_personality(row):
        if row["era"] == "FanZ" and w >= 600:
            zoom = im.crop((int(0.40 * w), int(0.60 * h), int(0.72 * w), int(0.70 * h)))
            zoom = zoom.resize((zoom.width * 2, zoom.height * 2), Image.LANCZOS)
            canvas = Image.new("RGB", (w + zoom.width + 8, h), "white")
            canvas.paste(im, (0, 0))
            canvas.paste(zoom, (w + 8, 0))
            ImageDraw.Draw(canvas).text((w + 12, zoom.height + 6), "trait-area zoom x2",
                                        fill="black", font=FONT)
            return "full", label(canvas, tag)
        return "full", label(im, tag)
    top = im.crop((0, 0, w, int(0.16 * h)))
    low = im.crop((0, int(0.50 * h), w, int(0.93 * h)))
    both = Image.new("RGB", (w, top.height + low.height + 4), "gray")
    both.paste(top, (0, 0))
    both.paste(low, (0, top.height + 4))
    return "crop", label(both, tag)


def fit(tiles, cols):
    """Paste tiles into a grid; shrink uniformly if over the pixel budget."""
    rows_n = (len(tiles) + cols - 1) // cols
    tw = max(t.width for t in tiles)
    th = max(t.height for t in tiles)
    sheet = Image.new("RGB", (tw * cols + 6 * (cols - 1), th * rows_n + 6 * (rows_n - 1)), "black")
    for i, t in enumerate(tiles):
        sheet.paste(t, ((i % cols) * (tw + 6), (i // cols) * (th + 6)))
    px = sheet.width * sheet.height
    if px > MAX_PX or max(sheet.size) > 1568:
        s = min((MAX_PX / px) ** 0.5, 1568 / max(sheet.size))
        sheet = sheet.resize((int(sheet.width * s), int(sheet.height * s)), Image.LANCZOS)
    return sheet


def plan(kind, tile):
    """How many tiles of this kind/size go on one sheet, and in how many columns."""
    if kind == "full":
        if tile.width > tile.height:                 # mastery
            return 1, 1
        return (2, 2) if tile.width <= 520 else (1, 1)
    if tile.width <= 520:                            # low-res PanZ crop
        return 6, 3
    return 4, 2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sets", required=True)
    a = ap.parse_args()
    inv = load_json(INVENTORY)
    for code in a.sets.split(","):
        rows = sorted([r for r in inv if r["set_code"] == code],
                      key=lambda r: (r["collection"], r["prefix"] or "", r["number"] or 0, r["card_id"]))
        outdir = SHEETS / code
        outdir.mkdir(parents=True, exist_ok=True)
        manifest, buf, n = [], [], 0

        def flush():
            nonlocal buf, n
            if not buf:
                return
            n += 1
            per, cols = plan(buf[0][1], buf[0][2])
            sheet = fit([t for _, _, t in buf], cols)
            name = f"{n:03d}.png"
            sheet.save(outdir / name)
            manifest.append({"sheet": name, "kind": buf[0][1], "card_ids": [c for c, _, _ in buf]})
            buf = []

        for r in rows:
            kind, tile = tile_for(r)
            per, _ = plan(kind, tile)
            if buf and (buf[0][1] != kind or buf[0][2].size != tile.size or len(buf) >= plan(buf[0][1], buf[0][2])[0]):
                flush()
            buf.append((r["card_id"], kind, tile))
            if len(buf) >= per:
                flush()
        flush()
        save_json(outdir / "manifest.json", manifest)
        print(f"{code}: {len(rows)} cards -> {n} sheets "
              f"({sum(1 for m in manifest if m['kind'] == 'full')} full-card sheets)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
