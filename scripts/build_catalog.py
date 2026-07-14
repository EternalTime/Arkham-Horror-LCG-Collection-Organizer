#!/usr/bin/env python3
"""Build the purchasable-product catalog from the ArkhamDB pack list.

Writes:
  data/catalog.json - list of products, used by fetch_collection.py
  data/catalog.js   - same data as `const AHLCG_CATALOG = [...]` for collection.html

Each catalog entry:
  name   - product name as printed on the box (key used in collection.json)
  group  - drawer/setup-page grouping
  packs  - [[pack_code, filter], ...] where filter is null, "player" or
           "encounter" (which of the pack's cards the product physically contains)
  note   - optional human hint shown on the setup page

The mapping from physical products to ArkhamDB pack codes is embedded below
(PRODUCT_DEFS); ArkhamDB is only consulted to discover packs we don't know
about yet, which land in the "Uncategorized" group so the catalog never goes
silently stale. Re-run after FFG releases new product.
"""

import json
import urllib.request
from pathlib import Path

OUT_DIR = Path(__file__).resolve().parent.parent / "data"
PACKS_API = "https://arkhamdb.com/api/public/packs/"

# The repackaged Investigator/Campaign expansions for the first six cycles are
# catalogued on ArkhamDB under the ORIGINAL deluxe + Mythos-pack codes; the
# repackage simply splits the cycle into its player half ("player") and its
# encounter half ("encounter").
CYCLES = {
    "The Dunwich Legacy":       ["dwl", "tmm", "tece", "bota", "uau", "wda", "litas"],
    "The Path to Carcosa":      ["ptc", "eotp", "tuo", "apot", "tpm", "bsr", "dca"],
    "The Forgotten Age":        ["tfa", "tof", "tbb", "hote", "tcoa", "tdoy", "sha"],
    "The Circle Undone":        ["tcu", "tsn", "wos", "fgg", "uad", "icc", "bbt"],
    "The Dream-Eaters":         ["tde", "sfk", "tsh", "dsm", "pnr", "wgd", "woc"],
    "The Innsmouth Conspiracy": ["tic", "itd", "def", "hhg", "lif", "lod", "itm"],
}
NEW_CYCLES = {  # sold split from the start: (investigator pack code, campaign pack code)
    "Edge of the Earth":         ("eoep", "eoec"),
    "The Scarlet Keys":          ("tskp", "tskc"),
    "The Feast of Hemlock Vale": ("fhvp", "fhvc"),
    "The Drowned City":          ("tdcp", "tdcc"),
}
STANDALONES = {
    "Curse of the Rougarou": "cotr",
    "Carnevale of Horrors": "coh",
    "The Labyrinths of Lunacy": "lol",
    "Guardians of the Abyss": "guardians",
    "Murder at the Excelsior Hotel": "hotel",
    "The Blob That Ate Everything": "blob",
    "War of the Outer Gods": "wog",
    "Machinations Through Time": "mtt",
    "Fortune and Folly": "fof",
    "The Blob That Ate Everything ELSE!": "blbe",
    "The Midwinter Gala": "tmg",
    "Film Fatale": "film_fatale",
}
RETURN_TOS = {
    "Return to the Night of the Zealot": "rtnotz",
    "Return to the Dunwich Legacy": "rtdwl",
    "Return to the Path to Carcosa": "rtptc",
    "Return to the Forgotten Age": "rttfa",
    "Return to the Circle Undone": "rttcu",
}
STARTERS = {
    "Nathaniel Cho Starter": "nat",
    "Harvey Walters Starter": "har",
    "Winifred Habbamock Starter": "win",
    "Jacqueline Fine Starter": "jac",
    "Stella Clark Starter": "ste",
}
PACKS_2026 = {
    "Tommy Muldoon Pack": "tom",
    "Carolyn Fern Pack": "car",
    "André Patel Pack": "and",
    "Marie Lambeau Pack": "mar",
    "Miguel de la Cruz Pack": "mig",
}
PARALLELS = {  # free print-and-play, PDFs on FFG's support page
    "Read or Die (Daisy Walker)": "rod",
    "All or Nothing (\"Skids\" O'Toole)": "aon",
    "Bad Blood (Agnes Baker)": "bad",
    "By the Book (Roland Banks)": "btb",
    "Red Tide Rising (Wendy Adams)": "rtr",
    "On the Road Again (\"Ashcan\" Pete)": "otr",
    "Laid to Rest (Jim Culver)": "ltr",
    "Path of the Righteous (Zoey Samaras)": "ptr",
    "Relics of the Past (Monterey Jack)": "rop",
    "Hunting for Answers (Rex Murphy)": "hfa",
    "Pistols and Pearls (Jenny Barnes)": "pap",
    "Aura of Faith (Father Mateo)": "aof",
    "Enthralling Encore (Lola Hayes)": "enc",
}
# ArkhamDB lists pack codes for the repackaged first-six-cycle boxes
# (dwlp/dwlc etc.) but keeps the cards under the ORIGINAL cycle codes, so
# these are empty aliases of products already defined above.
ALIASES = {"dwlp", "dwlc", "ptcp", "ptcc", "tfap", "tfac",
           "tcup", "tcuc", "tdep", "tdec", "ticp", "ticc"}

NOVELLAS = {  # promo investigator cards bundled with the novellas
    "Hour of the Huntress": "hoth",
    "The Dirge of Reason": "tdor",
    "Ire of the Void": "iotv",
    "The Deep Gate": "tdg",
    "To Fight the Black Wind": "tftbw",
    "Blood of Baalshandor": "bob",
    "Dark Revelations": "dre",
}


def build_defs():
    defs = []

    def add(name, group, packs, note=None):
        entry = {"name": name, "group": group, "packs": packs}
        if note:
            entry["note"] = note
        defs.append(entry)

    g = "Core Sets"
    add("Core Set", g, [["core", None]],
        "original 2016 core box")
    add("Revised Core Set", g, [["rcore", None], ["core", "encounter"]],
        "player cards under rcore; its encounter cards are catalogued under the original core")
    add("Core Set (2026)", g, [["core_2026", None]])

    g = "Campaign Expansions"
    for name, packs in CYCLES.items():
        add(f"{name} Investigator Expansion", g,
            [[p, "player"] for p in packs],
            "repackaged; player cards of the original cycle")
        add(f"{name} Campaign Expansion", g,
            [[p, "encounter"] for p in packs],
            "repackaged; encounter cards of the original cycle")
        add(f"{name} (original deluxe + Mythos packs)", g,
            [[p, None] for p in packs],
            "complete original cycle; equivalent to owning both repackaged boxes")
    for name, (inv, camp) in NEW_CYCLES.items():
        add(f"{name} Investigator Expansion", g, [[inv, None]])
        add(f"{name} Campaign Expansion", g, [[camp, None]])

    g = "Return to..."
    for name, code in RETURN_TOS.items():
        add(name, g, [[code, None]])

    g = "Investigator Starter Decks"
    for name, code in STARTERS.items():
        add(name, g, [[code, None]])

    g = "Investigator Packs (2026)"
    for name, code in PACKS_2026.items():
        add(name, g, [[code, None]])

    g = "Standalone Scenarios"
    for name, code in STANDALONES.items():
        add(name, g, [[code, None]])

    g = "Parallel Investigators (print-and-play)"
    for name, code in PARALLELS.items():
        add(name, g, [[code, None]], "free PDF on FFG's support page")

    g = "Novella Promos"
    for name, code in NOVELLAS.items():
        add(name, g, [[code, None]], "promo cards bundled with the novella")

    add("Promotional Cards", "Promos", [["promo", None]],
        "convention/organized-play promos on ArkhamDB")
    add("Books (misc promo cards)", "Promos", [["books", None]])
    return defs


def main():
    defs = build_defs()
    known = {code for d in defs for code, _ in d["packs"]} | ALIASES

    try:
        with urllib.request.urlopen(PACKS_API, timeout=15) as r:
            packs = json.load(r)
    except Exception as e:
        print(f"WARNING: could not reach ArkhamDB ({e}); writing embedded catalog only")
        packs = []

    for p in sorted(packs, key=lambda x: (x["cycle_position"], x["position"])):
        if p["code"] not in known:
            defs.append({
                "name": p["name"], "group": "Uncategorized (new on ArkhamDB)",
                "packs": [[p["code"], None]],
                "note": "new pack not yet classified - update build_catalog.py",
            })

    OUT_DIR.mkdir(exist_ok=True)
    (OUT_DIR / "catalog.json").write_text(
        json.dumps(defs, ensure_ascii=False, indent=1), encoding="utf-8")
    (OUT_DIR / "catalog.js").write_text(
        "const AHLCG_CATALOG = " + json.dumps(defs, ensure_ascii=False) + ";\n",
        encoding="utf-8")
    uncat = sum(1 for d in defs if d["group"].startswith("Uncategorized"))
    print(f"{len(defs)} products ({uncat} uncategorized); wrote data/catalog.json and data/catalog.js")


if __name__ == "__main__":
    main()
