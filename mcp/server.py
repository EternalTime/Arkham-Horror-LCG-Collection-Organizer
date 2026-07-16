#!/usr/bin/env python3
"""MCP server exposing the AHLCG collection pipeline as tools.

Lets any MCP-capable LLM client (Claude, Cursor, ChatGPT desktop, ...) build
and maintain the collection library conversationally: browse the product
catalog, record what the user owns, and run the data/image/PDF pipeline.

Requires:  pip install "mcp[cli]"
Register (stdio transport), e.g. for Claude Code:
  claude mcp add ahlcg -- python3 /path/to/repo/mcp/server.py
or in any client's MCP config:
  { "command": "python3", "args": ["/path/to/repo/mcp/server.py"] }

The equivalent manual workflow is documented in AGENTS.md; this server is a
convenience wrapper around the same scripts.
"""

import json
import subprocess
import sys
from pathlib import Path

from mcp.server.fastmcp import FastMCP

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
COLLECTION = ROOT / "collection.json"
CATALOG = ROOT / "data" / "catalog.json"

mcp = FastMCP("ahlcg-collection")


def run(script, *args, timeout=1800):
    """Run a pipeline script; return its combined output."""
    proc = subprocess.run(
        [sys.executable, str(SCRIPTS / script), *args],
        capture_output=True, text=True, timeout=timeout, cwd=ROOT)
    out = (proc.stdout + proc.stderr).strip()
    return out if proc.returncode == 0 else f"EXIT {proc.returncode}\n{out}"


@mcp.tool()
def list_catalog() -> str:
    """All purchasable AHLCG products (name, group, note), grouped. Product
    names are the keys used by set_collection. Run build_catalog first if
    the catalog is missing."""
    if not CATALOG.exists():
        return "No catalog yet - call build_catalog first."
    out = []
    for d in json.loads(CATALOG.read_text(encoding="utf-8")):
        note = f"  ({d['note']})" if d.get("note") else ""
        out.append(f"[{d['group']}] {d['name']}{note}")
    return "\n".join(out)


@mcp.tool()
def build_catalog() -> str:
    """(Re)generate data/catalog.json + catalog.js from the ArkhamDB pack
    list. Run when the catalog is missing or FFG released new product."""
    return run("build_catalog.py")


@mcp.tool()
def get_collection() -> str:
    """The products currently recorded as owned in collection.json."""
    if not COLLECTION.exists():
        return "No collection.json yet - call set_collection with the owned product names."
    return COLLECTION.read_text(encoding="utf-8")


@mcp.tool()
def set_collection(products: list[str]) -> str:
    """Write collection.json. `products` must be exact names from
    list_catalog. Replaces the whole list - pass the complete collection."""
    if not CATALOG.exists():
        return "No catalog yet - call build_catalog first."
    valid = {d["name"] for d in json.loads(CATALOG.read_text(encoding="utf-8"))}
    unknown = [p for p in products if p not in valid]
    if unknown:
        return f"Unknown product names (see list_catalog): {unknown}"
    from datetime import date
    COLLECTION.write_text(json.dumps(
        {"generated": date.today().isoformat(), "products": products},
        ensure_ascii=False, indent=1), encoding="utf-8")
    return f"collection.json written ({len(products)} products). Next: fetch_cards."


@mcp.tool()
def run_pipeline() -> str:
    """Build the whole library from collection.json in one call: cards,
    images, scenarios, campaigns, box art, guides. The images step can take a long time
    for large collections. Resumable - if it reports unfinished steps, call
    again. Preferred over the individual step tools for setup."""
    return run("setup.py", timeout=7200)


@mcp.tool()
def fetch_cards() -> str:
    """Fetch card data for every owned product from ArkhamDB and write
    data/cards.json + cards.js. Rerun if it reports INCOMPLETE."""
    return run("fetch_collection.py")


@mcp.tool()
def download_images() -> str:
    """Download card images into images/ (~1.6 GB for a large collection).
    Resumable - rerun until it reports COMPLETE."""
    return run("download_images.py", timeout=3600)


@mcp.tool()
def build_scenarios() -> str:
    """Build scenario -> encounter set data (data/scenarios.json + .js) from
    the ArkhamCards data project. Run after fetch_cards."""
    return run("build_scenarios.py")


@mcp.tool()
def build_campaigns() -> str:
    """Build campaign-tracker data (data/campaigns.js: chaos bags per
    difficulty, campaign-log sections, scenario order + resolutions) from
    the ArkhamCards data project. Powers the campaign screen."""
    return run("build_campaigns.py")


@mcp.tool()
def download_boxart() -> str:
    """Download campaign box art into boxart/. Rerun until COMPLETE."""
    return run("download_boxart.py")


@mcp.tool()
def download_guides(all: bool = False) -> str:
    """Download official rules/campaign PDFs into guides/ and regenerate
    data/docs.js. Only owned products' PDFs unless all=True. Rerun until
    COMPLETE."""
    return run("download_guides.py", *(["--all"] if all else []))


@mcp.tool()
def status() -> str:
    """Which pipeline outputs exist and roughly how complete they are."""
    def count(d, glob):
        return len(list((ROOT / d).glob(glob))) if (ROOT / d).exists() else 0
    cards = 0
    if (ROOT / "data/cards.json").exists():
        cards = len(json.loads((ROOT / "data/cards.json").read_text(encoding="utf-8")))
    lines = [
        f"catalog.json:    {'yes' if CATALOG.exists() else 'MISSING - run build_catalog'}",
        f"collection.json: {'yes' if COLLECTION.exists() else 'MISSING - run set_collection'}",
        f"cards:           {cards or 'MISSING - run fetch_cards'}",
        f"scenarios:       {'yes' if (ROOT / 'data/scenarios.json').exists() else 'MISSING - run build_scenarios'}",
        f"campaigns:       {'yes' if (ROOT / 'data/campaigns.js').exists() else 'MISSING - run build_campaigns'}",
        f"images:          {count('images', '*.jpg')} files (run download_images until COMPLETE)",
        f"boxart:          {count('boxart', '*.avif')} files",
        f"guides:          {count('guides', '*.pdf')} PDFs",
        f"docs.js:         {'yes' if (ROOT / 'data/docs.js').exists() else 'MISSING - run download_guides'}",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    mcp.run()
