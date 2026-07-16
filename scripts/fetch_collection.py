#!/usr/bin/env python3
"""Build a card database of Damian's Arkham Horror LCG collection from ArkhamDB.

Fetches every card (player + encounter) for each owned product and writes:
  cards.json - plain JSON array, one record per card
  cards.js   - same data as `const AHLCG_CARDS = [...]` for local HTML pages

Re-run after buying new packs; edit PRODUCTS below to add them.
"""

import json
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

OUT_DIR = Path(__file__).resolve().parent.parent / "data"
API = "https://arkhamdb.com/api/public/cards/{}.json?encounter=1"

# product name -> list of ArkhamDB pack codes containing its cards.
# The repackaged Investigator/Campaign expansions (Dunwich..Innsmouth) are
# catalogued on ArkhamDB under the original deluxe + Mythos pack codes.
PRODUCTS = {
    # rcore on ArkhamDB holds only the player cards; the Revised Core's
    # encounter cards are catalogued under the original core pack (filtered
    # to encounter cards below).
    "Revised Core Set": ["rcore", "core"],
    "Core Set (2026)": ["core_2026"],
    "The Dunwich Legacy": ["dwl", "tmm", "tece", "bota", "uau", "wda", "litas"],
    "The Path to Carcosa": ["ptc", "eotp", "tuo", "apot", "tpm", "bsr", "dca"],
    "The Forgotten Age": ["tfa", "tof", "tbb", "hote", "tcoa", "tdoy", "sha"],
    "The Circle Undone": ["tcu", "tsn", "wos", "fgg", "uad", "icc", "bbt"],
    "The Dream-Eaters": ["tde", "sfk", "tsh", "dsm", "pnr", "wgd", "woc"],
    "The Innsmouth Conspiracy": ["tic", "itd", "def", "hhg", "lif", "lod", "itm"],
    "Edge of the Earth": ["eoep", "eoec"],
    "The Scarlet Keys": ["tskp", "tskc"],
    "The Feast of Hemlock Vale": ["fhvp", "fhvc"],
    "The Drowned City": ["tdcp", "tdcc"],
    # Standalone scenarios (all except Carnevale of Horrors)
    "Curse of the Rougarou": ["cotr"],
    "The Labyrinths of Lunacy": ["lol"],
    "Guardians of the Abyss": ["guardians"],
    "Murder at the Excelsior Hotel": ["hotel"],
    "The Blob That Ate Everything": ["blob"],
    "War of the Outer Gods": ["wog"],
    "Machinations Through Time": ["mtt"],
    "Fortune and Folly": ["fof"],
    "The Midwinter Gala": ["tmg"],
    "Film Fatale": ["film_fatale"],
    # Investigator starter decks
    "Nathaniel Cho Starter": ["nat"],
    "Harvey Walters Starter": ["har"],
    "Winifred Habbamock Starter": ["win"],
    "Jacqueline Fine Starter": ["jac"],
    "Stella Clark Starter": ["ste"],
    # 2026 evergreen investigator packs
    "Tommy Muldoon Pack": ["tom"],
    "Carolyn Fern Pack": ["car"],
    "André Patel Pack": ["and"],
    "Marie Lambeau Pack": ["mar"],
    "Miguel de la Cruz Pack": ["mig"],
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
    "back_name", "back_text", "back_flavor",
    # deckbuilding
    "real_name", "deck_requirements", "deck_options", "restrictions",
    "bonded_to", "bonded_cards", "tags", "duplicate_of", "alternate_of",
]

# pack code -> predicate selecting which of its cards count as owned
PACK_FILTER = {
    "core": lambda c: bool(c.get("encounter_code")),
}


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
    for product, packs in PRODUCTS.items():
        for pack in packs:
            data = fetch(pack)
            if data is None:
                missing.append(pack)
                continue
            keep = PACK_FILTER.get(pack, lambda c: True)
            data = [c for c in data if keep(c)]
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
