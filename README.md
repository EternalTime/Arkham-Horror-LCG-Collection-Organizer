<p align="center">
  <img src="assets/title.svg" alt="Arkham Horror — The Card Game — Collection Organizer" width="600">
</p>

Offline card browser, deckbuilder, and campaign tracker for *your* Arkham
Horror: The Card Game collection. Everything runs from local files — open
`index.html` in a browser, no server, no accounts.

This repo hosts **no card data, images, or rules PDFs** (they're Fantasy
Flight Games' copyrighted material). Instead it ships the app plus a pipeline
that downloads exactly the content for the products you physically own, from
public sources: [ArkhamDB](https://arkhamdb.com), the
[arkham.build](https://github.com/fspoettel/arkham.build) assets,
the [ArkhamCards data project](https://github.com/zzorba/arkham-cards-data),
and FFG's own document CDN.

## Setup

**Give this repo to your AI assistant** (Claude Code, Cursor, or any coding
agent), tell it which Arkham products you own, and it does everything else:
records your collection, downloads the card data, images, box art, and rules
PDFs, and verifies the result. The instructions it needs are already here, in
`AGENTS.md`. Then open `index.html` in your browser.

Bought something new? Tell your assistant.

<details>
<summary>Manual setup (no AI assistant)</summary>

Requires Python 3.8+ (stdlib only) and a browser.

1. Open `collection.html`, tick every product you own, hit **Export**, and
   save the file as `collection.json` in this folder (next to `index.html`).
2. Run `python3 scripts/setup.py` — it downloads and builds everything else.
   The images step is the long one; the script is resumable, rerun it if
   interrupted.
3. Open `index.html`. Done.

Bought something new? Re-export `collection.json` and rerun `setup.py`.

For MCP-capable clients, `mcp/server.py` exposes the same pipeline as an
[MCP](https://modelcontextprotocol.io) server with a one-call `run_pipeline`
tool — see its header for registration.
</details>

## Layout

    index.html        the whole app: card browser, scenario views, deckbuilder, campaign log
    collection.html   setup page: mark what you own, export collection.json
    collection.json   your collection (gitignored; created by you)
    data/             catalog (committed) + generated card/scenario databases (gitignored)
    scripts/          the pipeline, stdlib-only Python
    images/, boxart/, guides/   downloaded content (gitignored)
    fonts/, icons/    static assets, included
    decks/            your deck exports/backups (gitignored)
    mcp/              MCP server wrapping the pipeline

## Notes

- Decks, deck sets, and campaign logs live in your browser's localStorage.
  Use the deckbuilder's **Export JSON** for backups; keep them in `decks/`.
- The deckbuilder enforces your *physical* pool: two decks in the same deck
  set can't share more copies of a card than you own.
- Maintenance (new products, data refreshes, special cases): MAINTENANCE.md.

*This is an unofficial fan project, not affiliated with Fantasy Flight Games.*
