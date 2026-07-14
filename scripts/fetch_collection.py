#!/usr/bin/env python3
"""Build a card database of your Arkham Horror LCG collection from ArkhamDB.

Reads which products you own from collection.json (repo root; create it with
collection.html or by hand) and their pack composition from data/catalog.json
(regenerate with scripts/build_catalog.py). Fetches every card (player +
encounter) for each owned product and writes:
  cards.json - plain JSON array, one record per card
  cards.js   - same data as `const AHLCG_CARDS = [...]` for local HTML pages

Re-run after buying new packs; re-export collection.json first.
"""

import json
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "data"
COLLECTION = ROOT / "collection.json"
CATALOG = OUT_DIR / "catalog.json"
API = "https://arkhamdb.com/api/public/cards/{}.json?encounter=1"


def load_products():
    """collection.json + catalog.json -> {product name: [(pack, filter), ...]}"""
    if not COLLECTION.exists():
        sys.exit("collection.json not found. Open collection.html in a browser, "
                 "mark what you own, export, and save the file next to index.html.")
    if not CATALOG.exists():
        sys.exit("data/catalog.json not found. Run: python3 scripts/build_catalog.py")
    owned = json.loads(COLLECTION.read_text(encoding="utf-8"))["products"]
    catalog = {d["name"]: d["packs"]
               for d in json.loads(CATALOG.read_text(encoding="utf-8"))}
    unknown = [p for p in owned if p not in catalog]
    if unknown:
        sys.exit(f"collection.json lists products missing from the catalog: {unknown}\n"
                 "Re-run scripts/build_catalog.py or fix the names.")
    return {p: [tuple(pk) for pk in catalog[p]] for p in owned}


# filter name -> predicate selecting which of a pack's cards the product contains
FILTERS = {
    None: lambda c: True,
    "player": lambda c: not c.get("encounter_code"),
    "encounter": lambda c: bool(c.get("encounter_code")),
}

FIELDS = [
    "code", "name", "subname", "faction_code", "faction2_code", "faction3_code",
    "type_code", "subtype_code", "cost", "xp", "traits", "text",
    "skill_willpower", "skill_intellect", "skill_combat", "skill_agility",
    "skill_wild", "health", "sanity", "enemy_fight", "enemy_evade",
    "enemy_damage", "enemy_horror", "shroud", "clues", "doom",
    "victory", "quantity", "deck_limit", "slot", "is_unique", "permanent",
    "exceptional", "myriad", "pack_code", "pack_name", "position",
    "encounter_name", "encounter_position", "encounter_code",
    "url", "imagesrc", "backimagesrc", "double_sided",
    # deckbuilding
    "real_name", "deck_requirements", "deck_options", "restrictions",
    "bonded_to", "bonded_cards", "tags", "duplicate_of", "alternate_of",
]

CACHE = Path(__file__).resolve().parent / ".pack_cache"


def fetch(pack_code):
    """Fetch one pack, using the on-disk cache; return list or None on failure."""
    cached = CACHE / f"{pack_code}.json"
    if cached.exists():
        return json.loads(cached.read_text(encoding="utf-8"))
    try:
        with urllib.request.urlopen(API.format(pack_code), timeout=12) as r:
            data = json.load(r)
    except Exception as e:
        print(f"  FAILED {pack_code}: {e}")
        return None
    cached.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    time.sleep(0.5)
    return data


def main():
    CACHE.mkdir(exist_ok=True)
    cards = []
    missing = []
    for product, packs in load_products().items():
        for pack, flt in packs:
            data = fetch(pack)
            if data is None:
                missing.append(pack)
                continue
            data = [c for c in data if FILTERS[flt](c)]
            for c in data:
                rec = {f: c[f] for f in FIELDS if f in c}
                rec["product"] = product
                # some new cards lack scans on ArkhamDB but exist on the
                # assets.arkham.build CDN that download_images.py tries first
                if not rec.get("imagesrc"):
                    rec["imagesrc"] = f"/bundles/cards/{c['code']}.jpg"
                cards.append(rec)
            print(f"{product:40s} {pack:12s} {len(data):4d} cards")
    if missing:
        print(f"\nINCOMPLETE - rerun to fetch missing packs: {missing}")
        return

    cards.sort(key=lambda c: c["code"])
    total = len(cards)
    copies = sum(c.get("quantity", 1) for c in cards)
    print(f"\n{total} distinct cards, {copies} physical cards")

    (OUT_DIR / "cards.json").write_text(
        json.dumps(cards, ensure_ascii=False, indent=1), encoding="utf-8")
    (OUT_DIR / "cards.js").write_text(
        "const AHLCG_CARDS = " + json.dumps(cards, ensure_ascii=False) + ";\n",
        encoding="utf-8")
    print("wrote cards.json and cards.js")


if __name__ == "__main__":
    main()
