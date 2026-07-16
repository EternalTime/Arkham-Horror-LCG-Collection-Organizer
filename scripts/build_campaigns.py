#!/usr/bin/env python3
"""Extract campaign data from the arkham-cards-data clone into data/campaigns.js.

Pulls, per campaign: name, campaign log sections, chaos bags per difficulty,
and the ordered scenario list (with resolutions) for the campaign screen.

Prefers a local arkham-cards-data/ clone (git pull it to update); falls back
to downloading a tarball snapshot to /tmp.
"""
import io
import json
import re
import sys
import tarfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "campaigns.js"
REPO_TGZ = ("https://codeload.github.com/zzorba/arkham-cards-data/"
            "tar.gz/refs/heads/master")
REPO_DIR = Path("/tmp/arkham-cards-data-master")
LOCAL_REPO = ROOT / "arkham-cards-data"


def repo_dir():
    if (LOCAL_REPO / "campaigns").is_dir():
        print(f"using local clone: {LOCAL_REPO}")
        return LOCAL_REPO
    if not REPO_DIR.exists():
        print("downloading arkham-cards-data...")
        data = urllib.request.urlopen(REPO_TGZ, timeout=60).read()
        tarfile.open(fileobj=io.BytesIO(data)).extractall("/tmp")
    return REPO_DIR

DIFFICULTIES = ("easy", "standard", "hard", "expert")


def load_scenarios(folder):
    """Index every scenario/interlude file in a campaign folder by its id."""
    by_id = {}
    for f in sorted(folder.glob("*.json")):
        if f.name == "campaign.json":
            continue
        try:
            d = json.loads(f.read_text())
        except json.JSONDecodeError:
            print(f"  warning: bad JSON in {f}", file=sys.stderr)
            continue
        if "id" in d:
            by_id[d["id"]] = d
    return by_id


def chaos_bags(doc):
    """Chaos bag per difficulty, from any step offering difficulty token choices."""
    bags = {}
    for step in doc.get("steps", []):
        for choice in (step.get("input") or {}).get("choices", []):
            if choice.get("id") in DIFFICULTIES and choice.get("tokens"):
                bags.setdefault(choice["id"], choice["tokens"])
    return bags or None


def story_context(d):
    """Map story-step id -> when it is read (from choices/branches that lead there)."""
    ctx = {}
    def clip(t):
        t = re.sub(r"<[^>]+>", "", " ".join((t or "").split())).rstrip(":")
        return t[:140] + ("…" if len(t) > 140 else "")
    for s in d.get("steps", []):
        inp = s.get("input") or {}
        for c in inp.get("choices", []):
            for target in c.get("steps", []):
                if c.get("text"):
                    ctx.setdefault(target, clip(c["text"]))
        if s.get("type") == "branch":
            text = clip(s.get("text"))
            if not text:
                continue
            opts = (s.get("condition", {}) or {}).get("options", [])
            for i, opt in enumerate(opts):
                cond = opt.get("condition")
                label = clip(str(cond)) if isinstance(cond, str) else text
                if i > 0 and label == text:
                    label = "Otherwise — not: " + text
                for target in opt.get("steps", []):
                    ctx.setdefault(target, label)
    return ctx


def story_blocks(d):
    """Narrative text: every 'story' step, in file order, with read-when context."""
    ctx = story_context(d)
    out = []
    for s in d.get("steps", []):
        if s.get("type") != "story" or not s.get("text"):
            continue
        text = s["text"]
        for b in s.get("bullets", []):
            if b.get("text"):
                text += "\n- " + b["text"]
        out.append({"id": s.get("id", ""), "title": s.get("title") or "",
                    "when": ctx.get(s.get("id"), ""), "text": text})
    return out


def strip_deep(o):
    """Drop narration/audio metadata recursively; keep game structure."""
    if isinstance(o, dict):
        return {k: strip_deep(v) for k, v in o.items()
                if k not in ("narration", "lang")}
    if isinstance(o, list):
        return [strip_deep(x) for x in o]
    return o


def scenario_entry(sid, files):
    d = files.get(sid)
    if d is None:
        return None
    return {
        "id": sid,
        "name": d.get("scenario_name", sid),
        "header": d.get("header", ""),
        "fullName": d.get("full_name", d.get("scenario_name", sid)),
        "type": d.get("type", "scenario"),
        "xpCost": d.get("xp_cost"),
        "chaosBags": chaos_bags(d),
        "story": story_blocks(d),
        # full step graph for the guided walkthrough
        "setup": d.get("setup", []),
        "steps": {s["id"]: strip_deep(s) for s in d.get("steps", []) if "id" in s},
        "resolutions": [
            {"id": r["id"], "title": r.get("title", r["id"]),
             "text": r.get("text", ""),
             "steps": r.get("steps", [])}
            for r in d.get("resolutions", [])
        ],
    }


def build_campaign(folder):
    campaign = json.loads((folder / "campaign.json").read_text())
    files = load_scenarios(folder)
    order = campaign.get("scenarios", []) + campaign.get("hidden_scenarios", [])
    scenarios, missing = [], []
    for sid in order:
        e = scenario_entry(sid, files)
        (scenarios if e else missing).append(e or sid)
    if missing:
        print(f"  {folder.name}: no file for {missing}", file=sys.stderr)
    return {
        "name": campaign.get("name", folder.name),
        "position": campaign.get("position", 999),
        "log": [
            {"id": s["id"], "title": s["title"]}
            for s in campaign.get("campaign_log", [])
            if not s.get("hidden")
        ],
        "chaosBags": chaos_bags(campaign),
        "scenarios": scenarios,
    }


def main():
    src = repo_dir() / "campaigns"
    if not src.is_dir():
        sys.exit(f"missing {src}")
    # only campaigns present in the owned collection (run build_scenarios first)
    scen_file = ROOT / "data" / "scenarios.json"
    if not scen_file.exists():
        sys.exit("data/scenarios.json not found — run build_scenarios.py first")
    scen_data = json.loads(scen_file.read_text())
    owned = {s["campaign"] for s in scen_data}
    out = {}
    for folder in sorted(src.iterdir()):
        if not (folder / "campaign.json").exists():
            continue
        c = build_campaign(folder)
        if c["name"] in owned:
            out[folder.name] = c
    # owned standalone scenarios (any folder), in scenarios.json play order
    side_names = [s["name"] for s in scen_data
                  if s["campaign"] == "Standalone Scenarios"]
    found, score = {}, {}
    for folder in sorted(src.iterdir()):
        if not folder.is_dir():
            continue
        files = load_scenarios(folder)
        # pack-level bags (e.g. Fortune and Folly, Guardians of the Abyss)
        cj = folder / "campaign.json"
        folder_bags = chaos_bags(json.loads(cj.read_text())) if cj.exists() else None
        for sid, d in files.items():
            nm = d.get("scenario_name")
            if nm not in side_names:
                continue
            e = scenario_entry(sid, files)
            if e["chaosBags"] is None and folder_bags:
                e["chaosBags"] = folder_bags
            # prefer the variant that knows its cost and its bag
            sc = (e["xpCost"] is not None) * 2 + (e["chaosBags"] is not None)
            if nm not in found or sc > score[nm]:
                found[nm], score[nm] = e, sc
    # house rule: adding any side scenario costs 1 XP, except All or Nothing
    for e in found.values():
        if e["id"] != "all_or_nothing":
            e["xpCost"] = 1
    out["side"] = {
        "name": "Standalone Scenarios", "position": 998, "log": [],
        "chaosBags": None,
        "scenarios": [found[n] for n in side_names if n in found],
    }
    missing = [n for n in side_names if n not in found]
    if missing:
        print(f"  side: no story data found for {missing}", file=sys.stderr)
    OUT.write_text(
        "const AHLCG_CAMPAIGNS = "
        + json.dumps(out, ensure_ascii=False, separators=(",", ":"))
        + ";\n"
    )
    n_scen = sum(len(c["scenarios"]) for c in out.values())
    print(f"wrote {OUT.name}: {len(out)} campaigns, {n_scen} scenarios, "
          f"{OUT.stat().st_size // 1024} KB")


if __name__ == "__main__":
    main()
