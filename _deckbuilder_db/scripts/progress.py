"""Phase 2 progress: vision records per set vs inventory (Trait reference cards excluded).

Usage: python progress.py   -> prints a table and appends a line to logs/phase2_progress.log
"""
import json
import sys
import time
from collections import Counter

from common import DB, INVENTORY, VISION_DIR, load_json


def main():
    inv = [r for r in load_json(INVENTORY) if r["collection"] != "trait"]
    done = set()
    for f in VISION_DIR.glob("*.jsonl"):
        for line in f.read_text(encoding="utf-8").splitlines():
            if line.strip():
                done.add(json.loads(line)["id"])
    tot, got = Counter(r["set_code"] for r in inv), Counter(r["set_code"] for r in inv
                                                          if r["card_id"] in done)
    for code in sorted(tot):
        print(f"{code:4} {got[code]:4}/{tot[code]:4}" + ("  done" if got[code] == tot[code] else ""))
    n, t = sum(got.values()), sum(tot.values())
    line = f"{time.strftime('%Y-%m-%d %H:%M')} read {n}/{t}, {t - n} remaining"
    print(line)
    with open(DB / "logs" / "phase2_progress.log", "a", encoding="utf-8") as f:
        f.write(line + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
