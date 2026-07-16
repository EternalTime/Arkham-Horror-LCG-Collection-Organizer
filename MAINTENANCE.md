# Maintenance Guide

Two audiences: **users** adding a newly bought product (first section — no
code changes), and **maintainers** updating the repo when FFG releases new
product (everything after).

## Adding a product you bought (no code changes)

1. Re-export `collection.json` from `collection.html` (or add the product's
   exact catalog name to the `products` array by hand).
2. Rerun the pipeline: `python3 scripts/setup.py` (runs every step in
   order, resumably; the individual scripts in `scripts/` remain available
   for partial refreshes).

If the product doesn't appear in `collection.html`, the catalog predates it —
run `python3 scripts/build_catalog.py`; if it lands in the "Uncategorized"
group, the repo needs a maintainer update (below).

## Maintainer: new FFG product checklist

### 1. Catalog — `scripts/build_catalog.py`

1. Find the pack code(s): <https://arkhamdb.com/api/public/packs/> (a big-box
   expansion usually has two, e.g. `tdcp` investigator + `tdcc` campaign).
2. Add the product to the appropriate dict (`NEW_CYCLES`, `STANDALONES`, ...).
   The product name is what appears in the setup page, the Products drawer,
   and on every card — keep it consistent. Rerun the script; commit the
   regenerated `data/catalog.json` + `catalog.js`.
3. Special cases:
   - A pack filter (`"player"`/`"encounter"`) keeps only part of a pack's
     cards — how the repackaged cycle boxes and the Revised Core's encounter
     half are modelled.
   - Repackaged first-six-cycle boxes are catalogued under the ORIGINAL
     deluxe + Mythos codes; ArkhamDB's `dwlp`-style codes are empty aliases
     (listed in `ALIASES`).
   - If ArkhamDB reprints a pack under new codes, the viewer's `canon()`
     (index.html, first deckbuilder script block) may need a rule — Revised
     Core uses "original code + 500".

### 2. Cards — `scripts/fetch_collection.py`

Driven entirely by `collection.json` + `data/catalog.json`; rarely needs
edits. Per-pack API responses cache in `scripts/.pack_cache/` — delete a
pack's file to force a refetch (e.g. after ArkhamDB adds missing scans).

### 3. Images — `scripts/download_images.py`

Rerun until `COMPLETE`. Primary source: assets.arkham.build CDN keyed by
card code (`images/{code}.jpg`, `{code}b.jpg` backs), ArkhamDB fallback.
Cards with no ArkhamDB scan get a synthesized `imagesrc` in step 2 so
they're still tried against the CDN.

### 4. Scenarios — `scripts/build_scenarios.py`

Data: github.com/zzorba/arkham-cards-data. A local `arkham-cards-data/`
clone at the repo root takes priority (`git pull` it to update); otherwise
the repo is downloaded to `/tmp/arkham-cards-data-master` — **delete that
folder to pick up new scenario data**; it is not refreshed automatically.

- New campaign: add its folder name to `FOLDERS` (inspect the repo's
  `campaigns/` directory; e.g. Brethren of Ash = `boa`).
- New standalone: usually lands in the `side` folder, already scanned; add
  its folder to `STANDALONE_FOLDERS` if it gets its own.
- A scenario "skipped for unowned sets" the user DOES own means the
  ArkhamCards set code differs from ArkhamDB's `encounter_code` — add to
  `ALIASES` (e.g. `tekeli_li` → `tekelili`).
- Scenarios are play-ordered by their encounter set's card positions.

### 4b. Campaigns — `scripts/build_campaigns.py`

Same data source (and local-clone/tarball behavior) as step 4. Extracts,
per campaign: chaos bags per difficulty, campaign-log sections, scenario
order; per scenario: resolutions, story text (with "when to read" context
labels), scenario-level chaos bags, and the full step graph powering the
guided Play walkthrough (`guideRun`/`applyEffects` in index.html). A
synthetic `side` entry collects the owned standalone scenarios with XP
costs and their own bags. Only campaigns in the user's collection are
included (matched against `data/scenarios.json`, so it runs after
build_scenarios). New campaigns need no script changes, but need a
`CAMPAIGN_CODE` entry (step 5).

### 5. Viewer maps — `index.html`

Keyed by **campaign name as it appears in scenarios.js** (the ArkhamCards
`campaign.json` name; standalones merge into "Standalone Scenarios"):

- `CAMPAIGN_COLOR` — border/glow color for deck sets, scenario panels, doc
  groups, and the window tint. Extracted from the ARKHAM HORROR logo band on
  page 1 of each campaign guide PDF (median of the starry rectangle, logo
  masked, saturation capped / brightness floored for visibility).
- `SIDE_COLOR` — the same for standalone packs, extracted from their card
  art (their rulebooks all share one generic starry cover).
- `CAMPAIGN_GUIDE` — campaign → `guides/<key>.pdf` for the 📄 Guide button.
- `SIDE_GUIDE` — standalone pack → its `guides/rules_<key>.pdf`, for the
  per-pack guide buttons on the campaign screen.
- `CAMPAIGN_ART` — campaign → `boxart/<key>.avif` banner.
- `CAMPAIGN_CODE` — campaign → arkham-cards-data campaign code (folder name
  under `campaigns/`, the key in `data/campaigns.js`); powers the campaign
  screen (chaos bag, campaign log, story, guided play, scenario recording).

`PRODUCT_GROUPS` (first script block) is generated from the catalog's
`group` field — no per-product edits needed.

### 6. Box art — `scripts/download_boxart.py`

Covers come from arkham.build:
`https://raw.githubusercontent.com/fspoettel/arkham.build/main/frontend/public/assets/cycles/<key>.avif`.
Add the new key to `KEYS` and to `CAMPAIGN_ART`.

### 7. Documents — `scripts/download_guides.py`

All official PDFs are linked from FFG's game page (Support section):
<https://www.fantasyflightgames.com/en/products/arkham-horror-the-card-game/>.
FFG blocks scripted fetching of the page itself, but the
`images-cdn.fantasyflightgames.com` links it contains download fine — grab
the link in a browser and add it to `MANIFEST` with the right owning
products. Key naming (`<key>.pdf` guide, `log_<key>` log, `inv_<key>`
investigator insert, `rules_<key>` scenario rules, `map_<key>` sheets).
`data/docs.js` is regenerated by the script — don't hand-edit it. Give new
groups the campaign's exact name so the Docs panel picks up its color.

### 8. Icons — `icons/` + `data/icons.js` (rarely)

Only if FFG invents a new class, skill, or asset slot. Glyph paths extracted
from arkham.build's icomoon project into `data/icons.js` (`{name: {vb, d}}`,
tight square viewBoxes); referenced by `iconSVG()` in index.html. Slot icons
also need a `SLOT_ICON` entry in `deckAnalysis()`.

### 9. Verify

- Setup page lists the product; export → pipeline runs clean.
- Product appears in the Products drawer under the right group; header
  count rises.
- New scenarios appear in play order; encounter deck / setup split sane.
- New investigators: test deck; unusual `deck_options` render as choice
  dropdowns and off-class cards are blocked with sensible reasons (novel
  keys may need engine work in the `DL` script block).
- Campaign attach: color, box art, 📄 Guide, Docs panel entries.

## What's generated vs. hand-maintained

| Path                          | Status                                  |
|-------------------------------|-----------------------------------------|
| data/catalog.js/.json         | generated (build_catalog.py), committed |
| data/cards.js/.json           | generated (fetch_collection.py)         |
| data/scenarios.js/.json       | generated (build_scenarios.py)          |
| data/campaigns.js             | generated (build_campaigns.py)          |
| data/docs.js                  | generated (download_guides.py)          |
| data/icons.js                 | generated once, committed               |
| app/ (Rust sources)           | hand-maintained; target/ is build junk  |
| images/, boxart/, guides/     | downloaded, resumable                   |
| fonts/, icons/                | static, committed                       |
| index.html, collection.html   | hand-maintained (the entire app)        |
| scripts/*.py, mcp/server.py   | hand-maintained                         |
| decks/                        | your exports/notes                      |
