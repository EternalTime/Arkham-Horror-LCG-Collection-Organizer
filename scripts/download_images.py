#!/usr/bin/env python3
"""Download card images for the collection in cards.json.

Primary source: assets.arkham.build CDN (fast), falling back to arkhamdb.com
for anything the CDN lacks. Saves images/{code}.jpg (front) and
images/{code}b.jpg (back, double-sided cards only). Resumable: existing
files are skipped, so re-run until it prints COMPLETE.
"""

import json
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "data"
IMG_DIR = ROOT / "images"
CDN = "https://assets.arkham.build/optimized/{}.jpg"
FALLBACK = "https://arkhamdb.com{}"
HDRS = {"User-Agent": "Mozilla/5.0"}


def targets():
    """(filename, cdn_key, fallback_src) for every front and back image."""
    cards = json.loads((OUT_DIR / "cards.json").read_text(encoding="utf-8"))
    out = {}
    for c in cards:
        if c.get("imagesrc"):
            out[c["code"] + ".jpg"] = (c["code"], c["imagesrc"])
        if c.get("backimagesrc"):
            out[c["code"] + "b.jpg"] = (c["code"] + "b", c["backimagesrc"])
    return out


def grab(item):
    fname, (key, fallback_src) = item
    dest = IMG_DIR / fname
    if dest.exists() and dest.stat().st_size > 0:
        return None
    for url in (CDN.format(key), FALLBACK.format(fallback_src)):
        try:
            req = urllib.request.Request(url, headers=HDRS)
            with urllib.request.urlopen(req, timeout=10) as r:
                dest.write_bytes(r.read())
            return None
        except Exception:
            continue
    return fname


def main():
    IMG_DIR.mkdir(exist_ok=True)
    all_t = targets()
    todo = {f: v for f, v in all_t.items()
            if not (IMG_DIR / f).exists() or (IMG_DIR / f).stat().st_size == 0}
    print(f"{len(all_t) - len(todo)}/{len(all_t)} downloaded, {len(todo)} to go")
    if not todo:
        print("COMPLETE")
        return
    failed = []
    with ThreadPoolExecutor(max_workers=12) as ex:
        for err in ex.map(grab, sorted(todo.items())):
            if err:
                failed.append(err)
    if failed:
        print(f"failed this pass ({len(failed)}): {failed[:10]}")
    remaining = sum(1 for f in all_t if not (IMG_DIR / f).exists())
    print("COMPLETE" if remaining == 0 else f"remaining: {remaining} - rerun")


if __name__ == "__main__":
    main()
