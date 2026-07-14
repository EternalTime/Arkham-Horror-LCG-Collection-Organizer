#!/usr/bin/env python3
"""Build scenario -> encounter set -> owned cards mapping.

Scenario definitions come from the ArkhamCards data repo
(github.com/zzorba/arkham-cards-data); encounter set codes there match
ArkhamDB's encounter_code. A scenario is included only if every encounter
set it gathers resolves to cards in cards.json (this naturally excludes
Carnevale of Horrors and promo/print-and-play scenarios not in the
collection).

Writes scenarios.json and scenarios.js (const AHLCG_SCENARIOS).
"""

import io
import json
import tarfile
import urllib.request
from pathlib import Path

OUT_DIR = Path(__file__).resolve().parent.parent / "data"
REPO_TGZ = ("https://codeload.github.com/zzorba/arkham-cards-data/"
            "tar.gz/refs/heads/master")
REPO_DIR = Path("/tmp/arkham-cards-data-master")

# official campaign/scenario folders (z* are fan campaigns)
FOLDERS = ["notz", "dwl", "ptc", "tfa", "tcu", "tdea", "tdeb", "tic",
           "eoe", "tskc", "fhv", "tdc", "boa", "gob", "fof", "side"]

# folders holding standalone scenarios -> merge under one campaign label
STANDALONE = "Standalone Scenarios"
STANDALONE_FOLDERS = {"gob", "fof", "side"}

# arkham-cards-data set code -> arkhamdb encounter_code
ALIASES = {
    "tekeli_li": "tekelili",
    "sewers": "arkham_sewers",
    "machinations_epic_multiplayer":
        "machinations_through_time_epic_multiplayer",
    "machinations_single_group": "machinations_through_time_single_group",
}


def ensure_repo():
    if REPO_DIR.exists():
        return
    print("downloading arkham-cards-data...")
    data = urllib.request.urlopen(REPO_TGZ, timeout=60).read()
    tarfile.open(fileobj=io.BytesIO(data)).extractall("/tmp")


def gather_sets(scenario):
    """Encounter set codes from every encounter_sets step, in order."""
    seen, out = set(), []
    for step in scenario.get("steps", []):
        if step.get("type") == "encounter_sets":
            for s in step.get("encounter_sets", []):
                s = ALIASES.get(s, s)
                if s not in seen:
                    seen.add(s)
                    out.append(s)
    return out


def main():
    ensure_repo()
    cards = json.loads((OUT_DIR / "cards.json").read_text(encoding="utf-8"))
    by_set = {}
    set_names = {}
    # pack order = release order (PRODUCTS iteration order in fetch_collection)
    pack_order = {}
    for c in cards:
        pack_order.setdefault(c["pack_code"], len(pack_order))
    set_sort = {}   # encounter set -> earliest (pack, position): physical play order
    for c in cards:
        ec = c.get("encounter_code")
        if ec:
            by_set.setdefault(ec, []).append(c["code"])
            set_names.setdefault(ec, c.get("encounter_name") or ec)
            key = (pack_order[c["pack_code"]], c.get("position") or 0)
            if ec not in set_sort or key < set_sort[ec]:
                set_sort[ec] = key

    scenarios, skipped, seen_ids = [], [], set()
    for folder in FOLDERS:
        cdir = REPO_DIR / "campaigns" / folder
        campaign = STANDALONE if folder in STANDALONE_FOLDERS else json.loads(
            (cdir / "campaign.json").read_text(encoding="utf-8"))["name"]
        folder_scen = []
        for f in sorted(cdir.glob("*.json")):
            if f.name in ("campaign.json", "core.json"):
                continue
            d = json.loads(f.read_text(encoding="utf-8"))
            sets = gather_sets(d)
            if not sets or d["id"] in seen_ids:
                continue
            seen_ids.add(d["id"])
            unowned = [s for s in sets if s not in by_set]
            if unowned:
                skipped.append((campaign, d.get("scenario_name", d["id"]),
                                unowned))
                continue
            # play order: position of the scenario's own (first-gathered)
            # encounter set within the campaign's packs
            key = min(set_sort.get(s, (999, 0)) for s in sets[:1]) \
                if sets else (999, 0)
            folder_scen.append((key, len(folder_scen), {
                "id": d["id"],
                "campaign": campaign,
                "name": d.get("scenario_name") or d["id"],
                "full_name": d.get("full_name") or d.get("scenario_name"),
                "header": d.get("header", ""),
                "sets": [{"code": s, "name": set_names[s],
                          "cards": sorted(by_set[s])} for s in sets],
            }))
        folder_scen.sort(key=lambda t: (t[0], t[1]))
        scenarios.extend(s for _, _, s in folder_scen)

    (OUT_DIR / "scenarios.json").write_text(
        json.dumps(scenarios, ensure_ascii=False, indent=1), encoding="utf-8")
    (OUT_DIR / "scenarios.js").write_text(
        "const AHLCG_SCENARIOS = " + json.dumps(scenarios, ensure_ascii=False)
        + ";\n", encoding="utf-8")

    print(f"{len(scenarios)} scenarios written")
    print(f"\nskipped ({len(skipped)}) for unowned sets:")
    for camp, name, un in skipped:
        print(f"  {camp} / {name}: missing {un}")


if __name__ == "__main__":
    main()
