# Building the AHLCG desktop app (macOS, from zero)

The app is a thin native shell: a ~10 MB binary that serves your AHLCG
folder to its own window and autosaves your builder state to
`decks/autosave.json` (so a wiped browser can never lose a campaign).
Cards, images, and PDFs stay in the folder — nothing is bundled.

## One-time toolchain install

1. **Xcode command-line tools** (compiler):

       xcode-select --install

   Click Install in the dialog; takes a few minutes.

2. **Rust** (accept the defaults):

       curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

   Then restart Terminal (or `source "$HOME/.cargo/env"`).

3. **Tauri CLI** (compiles for a while, one time only):

       cargo install tauri-cli --version "^2"

No Node/npm needed — the app has no frontend build step.

## Generate the icon set (one time)

    cd ~/Documents/AHLCG/app
    cargo tauri icon icon.png

(`icon.png` is a placeholder monogram — replace it with any square
1024x1024 PNG and rerun if you want different art.)

## Run / build

    cd ~/Documents/AHLCG/app
    cargo tauri dev        # run it now (first compile takes several minutes)
    cargo tauri build      # produce the installable .app

The built app lands in `app/src-tauri/target/release/bundle/macos/AHLCG.app`
— drag it to /Applications.

## First run: bring your data over

The app window is a different browser context from Safari/Chrome, so its
localStorage starts empty. Once: open index.html in your usual browser,
**Export JSON**, then in the app use **Import JSON** on the same file.
From then on the app autosaves everything to `decks/autosave.json` on every
change, and restores from it automatically if its storage is ever cleared.

## Notes

- The app serves `~/Documents/AHLCG` by default. If your clone lives
  anywhere else, set `AHLCG_DIR` to its path before launching, e.g.
  `AHLCG_DIR="$HOME/code/arkham" open AHLCG.app` (or export it in your
  shell profile / LaunchAgent).
- Port 17845 must be free (it isn't used by anything common).
- Cmd+R reloads the page (the window has no browser shortcuts).
- Docs-panel PDFs and external links (ArkhamDB) open through macOS in your
  default viewer/browser — the app window itself never navigates away.
- Confirm/prompt dialogs render in-page (Tauri's webview has no native ones).
- Autosave and link-opening go through the app's local server
  (`/__autosave`, `/__open`), not Tauri IPC — no permissions config needed.
- `app/src-tauri/target/` is build output and can get large — safe to
  delete anytime; the next build just takes longer.
- Rebuilding after data changes is never needed: the app reads the folder
  live, so `git pull` + rerunning the data scripts is picked up on restart
  (or reload with Cmd+R).
