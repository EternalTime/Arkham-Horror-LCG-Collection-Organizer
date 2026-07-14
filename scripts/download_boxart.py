#!/usr/bin/env python3
"""Download box/cycle cover art into boxart/.

Source: the arkham.build project's cycle covers,
https://raw.githubusercontent.com/fspoettel/arkham.build/main/frontend/public/assets/cycles/<key>.avif

index.html's CAMPAIGN_ART map references these files by key. Resumable:
existing files are skipped; re-run until it prints COMPLETE. Return-to
campaigns have no dedicated cover there and reuse the base cycle's art.
"""

import urllib.request
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "boxart"
URL = ("https://raw.githubusercontent.com/fspoettel/arkham.build/"
       "main/frontend/public/assets/cycles/{}.avif")

KEYS = [
    "core",          # Night of the Zealot (original + revised core)
    "core_ch2",      # Core Set (2026) / Brethren of Ash
    "dwl", "ptc", "tfa", "tcu", "tde", "tic",   # cycles 2-7
    "eoe", "tsk", "fhv", "tdc",                 # cycles 8-11
    "side_stories",  # standalone scenarios
    "investigator",            # starter decks
    "investigator_decks_ch2",  # 2026 investigator packs
    "parallel",                # parallel investigators
]


def main():
    OUT.mkdir(exist_ok=True)
    failed = []
    for key in KEYS:
        dest = OUT / f"{key}.avif"
        if dest.exists():
            continue
        try:
            with urllib.request.urlopen(URL.format(key), timeout=15) as r:
                dest.write_bytes(r.read())
            print(f"fetched {key}.avif")
        except Exception as e:
            print(f"FAILED {key}: {e}")
            failed.append(key)
    print(f"\n{'INCOMPLETE - rerun to retry: ' + str(failed) if failed else 'COMPLETE'}")


if __name__ == "__main__":
    main()
