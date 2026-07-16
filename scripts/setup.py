#!/usr/bin/env python3
"""One-shot setup: build the whole library from collection.json.

Runs the full pipeline in order, retrying the resumable download steps until
they report COMPLETE:

  fetch_collection.py   card database from ArkhamDB
  download_images.py    card scans (large; the long step)
  build_scenarios.py    scenario / encounter-set data
  build_campaigns.py    campaign-tracker data (chaos bags, logs, scenarios)
  download_boxart.py    campaign covers
  download_guides.py    official rules & campaign-guide PDFs + docs.js

Prerequisite: collection.json at the repo root (export it from
collection.html, or have your AI assistant write it - see AGENTS.md).
Safe to rerun anytime; already-downloaded files are skipped.
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = Path(__file__).resolve().parent

# (script, retry-until-COMPLETE, max attempts)
STEPS = [
    ("fetch_collection.py", True, 5),
    ("download_images.py", True, 20),
    ("build_scenarios.py", False, 1),
    ("build_campaigns.py", False, 1),
    ("download_boxart.py", True, 3),
    ("download_guides.py", True, 3),
]


def run(script):
    proc = subprocess.run([sys.executable, str(SCRIPTS / script)],
                          cwd=ROOT, text=True,
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    print(proc.stdout, end="")
    return proc.returncode == 0 and "INCOMPLETE" not in proc.stdout


def main():
    if not (ROOT / "collection.json").exists():
        sys.exit("collection.json not found. Open collection.html in a browser "
                 "(or ask your AI assistant), then rerun this script.")
    failed = []
    for script, retry, attempts in STEPS:
        print(f"\n=== {script} ===")
        ok = False
        for i in range(attempts if retry else 1):
            if i:
                print(f"--- retrying ({i + 1}/{attempts}) ---")
            if run(script):
                ok = True
                break
        if not ok:
            failed.append(script)

    print("\n" + "=" * 40)
    if failed:
        print(f"Some steps did not finish: {failed}")
        print("Rerun this script to resume; nothing already downloaded is lost.")
        sys.exit(1)
    print("Setup complete. Open index.html in your browser.")


if __name__ == "__main__":
    main()
