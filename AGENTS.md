# Instructions for AI agents

This repo is an offline collection library, deckbuilder, and campaign tracker
for Arkham Horror: The Card Game. It ships **no card data, images, or PDFs** —
those are downloaded per-user, restricted to the products the user physically
owns. Your job, when a user asks for help, is usually one of: initial setup,
adding a newly bought product, or explaining the pipeline. These instructions
are agent-agnostic; nothing here assumes a particular LLM or client.

**Design intent: the user's only job is stating what they own.** Don't hand
the user commands to run — establish their collection (interview them, or
have them use collection.html), write `collection.json`, then run the
pipeline yourself: `python3 scripts/setup.py` (or the `run_pipeline` MCP
tool) does every remaining step in order, resumably. The numbered steps
below are what setup.py runs — use them individually only for debugging or
partial refreshes.

## Two ways to drive the pipeline

1. **MCP server** (preferred if your client supports MCP): register
   `mcp/server.py` (stdio; requires `pip install "mcp[cli]"`). It exposes
   `list_catalog`, `build_catalog`, `get_collection`, `set_collection`,
   `run_pipeline` (all of setup in one call), plus per-step tools
   (`fetch_cards`, `download_images`, `build_scenarios`, `build_campaigns`,
   `download_boxart`, `download_guides`) and `status`. The tools wrap the scripts below 1:1.
2. **Shell**: `python3 scripts/setup.py` runs everything after
   `collection.json` exists; the individual scripts in `scripts/` are the
   same steps (stdlib only, no dependencies).

## The pipeline (what setup.py / run_pipeline does)

1. **Catalog** — `data/catalog.json`/`.js` are committed, but regenerate if
   stale or missing: `python3 scripts/build_catalog.py`. The catalog maps
   every purchasable product to its ArkhamDB pack codes (with player/encounter
   filters for the repackaged cycle boxes).
2. **Collection** — establish what the user owns, as exact catalog product
   names, into `collection.json` at the repo root:
   either have the user open `collection.html` in a browser, tick boxes,
   export, and save the file next to `index.html` — or interview the user
   and write the file yourself:
   `{"generated": "YYYY-MM-DD", "products": ["Revised Core Set", ...]}`.
   Mind the repackaging: owning "The Dunwich Legacy Investigator Expansion"
   and "... Campaign Expansion" is NOT the same catalog entry as
   "The Dunwich Legacy (original deluxe + Mythos packs)"; ask which form the
   user owns. At least one Core Set is required for meaningful deckbuilding.
3. **Cards** — `python3 scripts/fetch_collection.py` → `data/cards.json`/`.js`.
   Per-pack API responses are cached in `scripts/.pack_cache/`; delete a
   pack's cache file to force a refetch. Rerun if it prints INCOMPLETE.
4. **Images** — `python3 scripts/download_images.py`. Long (up to ~1.6 GB);
   resumable; rerun until it prints COMPLETE.
5. **Scenarios** — `python3 scripts/build_scenarios.py` → `data/scenarios.*`.
   Uses a local `arkham-cards-data/` clone if one exists at the repo root,
   else downloads the repo to `/tmp/arkham-cards-data-master` (delete that
   folder to pick up newer scenario data).
6. **Campaigns** — `python3 scripts/build_campaigns.py` → `data/campaigns.js`
   (chaos bags per difficulty, campaign-log sections, scenario order and
   resolutions — powers the campaign screen). Same data source and
   local-clone/tarball behavior as step 5.
7. **Box art** — `python3 scripts/download_boxart.py`. Rerun until COMPLETE.
8. **Guides** — `python3 scripts/download_guides.py`. Downloads official
   rules/campaign PDFs for owned products and regenerates `data/docs.js`
   (the viewer's Docs panel). `--all` fetches everything regardless of
   ownership.
9. **Verify** — open `index.html` in a browser (no server needed). The
   Products drawer should list exactly the owned products; card images and
   the Docs panel should populate. Or check file counts:
   `data/cards.json` nonempty, `images/*.jpg` ≈ number of cards (plus `b`
   suffixed backs), `guides/*.pdf` present.

## Adding a newly bought product

Add its name to `collection.json` (or re-export from `collection.html`),
then rerun `setup.py`. If the product is so new it isn't in the catalog,
rerun `scripts/build_catalog.py`; if ArkhamDB has the pack but the catalog
generator doesn't classify it, add it to the appropriate dict in
`scripts/build_catalog.py` (see the "Uncategorized" group in its output).

## Facts that save debugging time

- Data sources: card data and card-image fallback from
  <https://arkhamdb.com> (public API, be polite — the fetch script sleeps
  between packs); primary card images from the assets.arkham.build CDN;
  box art from the arkham.build GitHub repo; scenario structure from
  github.com/zzorba/arkham-cards-data; PDFs from FFG's CDN
  (images-cdn.fantasyflightgames.com — the FFG *page* blocks scripts, the
  CDN links don't; URLs are pinned in `scripts/download_guides.py`).
- The Revised Core Set's player cards live under pack `rcore`, its encounter
  cards under the original `core` pack (hence the encounter filter in the
  catalog). The viewer's `canon()` maps rcore codes to original ones
  ("original code + 500").
- Repackaged cycle boxes (Dunwich…Innsmouth) are catalogued on ArkhamDB under
  the ORIGINAL deluxe + Mythos pack codes; the repackage is exactly the
  player half or encounter half of the cycle. ArkhamDB's `dwlp`/`dwlc`-style
  codes for them are empty aliases — ignore them.
- Decks, deck sets, and campaign runs live in the browser's localStorage.
  The builder's Export JSON is the backup mechanism; keep exports in `decks/`.
- A deck set's campaign run is `s.run = { code, difficulty, bag, log, notes }`
  where `code` is the arkham-cards-data campaign code (`CAMPAIGN_CODE` map in
  index.html), `bag` the current chaos-token list, `log` per-scenario results
  (`{ sid, scenario, resolution, xp: {deckId: n}, trauma: {deckId: [p, m]} }`)
  and `notes` free text per campaign-log section. Old exports that kept
  results in `set.log` are migrated to `run` automatically on load/import.
  Starting a campaign requires every deck to have its random basic weakness.
- `index.html` is the entire app (single file, no build step, no server).
  `data/*.js` files are the same data as the `.json` files wrapped in a
  `const`, because `file://` pages can't fetch local JSON.
- Everything downloadable is gitignored; never commit card images, PDFs, or
  card data — they're FFG's copyrighted material.

## Card/rules questions

Use <https://arkhamdb.com> for card lookups and rulings. Deckbuilding
validity (class access, XP, restrictions) is enforced by the deckbuilder in
`index.html` against the *owned* pool — physical copies matter: two decks in
one "deck set" can't use more copies of a card than the user owns.
