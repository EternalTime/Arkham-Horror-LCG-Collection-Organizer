#!/usr/bin/env python3
"""Download official rules/campaign PDFs into guides/ and generate data/docs.js.

Sources: FFG's support page for Arkham Horror: The Card Game,
<https://www.fantasyflightgames.com/en/products/arkham-horror-the-card-game/>.
FFG blocks scripted fetching of the page itself, but the
images-cdn.fantasyflightgames.com links it contains download fine, so this
script carries a manifest of those links. When FFG posts new or updated PDFs,
grab the new link from the page in a browser and update MANIFEST below.

Only PDFs relevant to the products in collection.json are downloaded
(General Reference docs always are); pass --all to fetch everything.
Resumable: existing files are skipped; re-run until it prints COMPLETE.

After downloading it rewrites data/docs.js (the viewer's Docs panel) to list
exactly the PDFs present in guides/.
"""

import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GUIDES = ROOT / "guides"
DATA = ROOT / "data"
CDN = "https://images-cdn.fantasyflightgames.com/filer_public/"

# Product-name shorthands (must match data/catalog.json names)
CORES_CH1 = ["Core Set", "Revised Core Set"]
CORE_2026 = ["Core Set (2026)"]


def cyc(name):
    inv = [f"{name} Investigator Expansion", f"{name} (original deluxe + Mythos packs)"]
    camp = [f"{name} Campaign Expansion", f"{name} (original deluxe + Mythos packs)"]
    return inv, camp


DWL_I, DWL_C = cyc("The Dunwich Legacy")
PTC_I, PTC_C = cyc("The Path to Carcosa")
TFA_I, TFA_C = cyc("The Forgotten Age")
TCU_I, TCU_C = cyc("The Circle Undone")
TDE_I, TDE_C = cyc("The Dream-Eaters")
TIC_I, TIC_C = cyc("The Innsmouth Conspiracy")
EOE_I = ["Edge of the Earth Investigator Expansion"]
EOE_C = ["Edge of the Earth Campaign Expansion"]
TSK_I = ["The Scarlet Keys Investigator Expansion"]
TSK_C = ["The Scarlet Keys Campaign Expansion"]
FHV_I = ["The Feast of Hemlock Vale Investigator Expansion"]
FHV_C = ["The Feast of Hemlock Vale Campaign Expansion"]
TDC_I = ["The Drowned City Investigator Expansion"]
TDC_C = ["The Drowned City Campaign Expansion"]

# group -> [(key, title, cdn-path-or-None, owning products or None=always)]
# key is the filename in guides/ (<key>.pdf); groups whose names match a
# campaign get that campaign's color in the Docs panel.
MANIFEST = [
    ("General Reference", [
        ("rulebook_2026", "Rulebook (2026)", "0e/d0/0ed09507-1705-47ed-a630-cd15885cabb0/ahc100_rulebook-web.pdf", CORE_2026),
        ("learn_to_play", "Learn to Play", "dd/78/dd7818fe-0c9a-4a6c-b685-e32ab55b1702/ahc60_learn_to_play_web.pdf", None),
        ("rules_reference", "Rules Reference", "50/be/50bed4be-034c-4ed5-9ce6-8509ce8d3352/ahc60_rules_reference_eng-compressed.pdf", None),
        ("faq", "FAQ v2.5", "c1/d0/c1d0fab6-7fa6-4ce2-af6a-16416381a19b/ahc_faq_v25_february_2026-web.pdf", None),
        ("grimoire", "Arkham Grimoire v1.1", "4e/da/4eda7782-c983-47cc-8d9f-ae372a44d87b/arkham_grimoire_v11.pdf", None),
        ("taboo", "Taboo Cards v2.5", "77/f5/77f5b8a9-7552-49c3-9a5c-6b9f22410e66/chapter_one_taboo_cards_v25_web.pdf", None),
    ]),
    ("The Night of the Zealot", [
        ("notz", "Campaign Guide", "8d/30/8d308b73-92f1-4b1e-aa7f-ce39e8d79786/night_of_the_zealot_campaign_guide.pdf", CORES_CH1),
        ("log_notz", "Campaign Log", "d6/2c/d62c2eb4-fe03-4a40-993c-af3239212d8b/ahc01_campaign-guide.pdf", CORES_CH1),
    ]),
    ("Brethren of Ash", [
        ("boa", "Campaign Guide", "f0/22/f022ac7c-9c30-4521-ac16-1f74f00e1d31/ahc100_campaign_guide-web.pdf", CORE_2026),
        # FFG publishes no separate log; page 15 of the campaign guide IS the
        # campaign log, extracted locally by derive_boa_log() below.
        ("log_boa", "Campaign Log", None, CORE_2026),
    ]),
    ("The Dunwich Legacy", [
        ("dwl", "Campaign Guide", "2e/2e/2e2e9b07-e5e4-4538-8d04-b009e20efb50/ahc66_campaign_guide_v6-compressed.pdf", DWL_C),
        ("log_dwl", "Campaign Log", "31/58/315827ac-a881-41c8-a1fb-436e32a6bf18/ahc02_campaign_log.pdf", DWL_C),
        ("inv_dwl", "Investigator Expansion Rules", "90/47/90474853-0f01-457b-b96c-098924eadd97/ahc65_dunwich_legacy_rules_insert-compressed.pdf", DWL_I),
    ]),
    ("The Path to Carcosa", [
        ("ptc", "Campaign Guide", "58/cd/58cd918c-fdd0-4cee-99df-eb9b5fd43c13/ahc68_campaign_guide_v4-compressed.pdf", PTC_C),
        ("log_ptc", "Campaign Log", "4a/f4/4af4ec21-3c77-4f35-ade1-ea1aa5b7ed19/ahc11_campaign-guide_web.pdf", PTC_C),
        ("inv_ptc", "Investigator Expansion Rules", "0f/d1/0fd1af70-e6fe-40da-9a5e-a194c2a9f201/ahc67_rules_insert_v2-compressed.pdf", PTC_I),
    ]),
    ("The Forgotten Age", [
        ("tfa", "Campaign Guide", "2c/08/2c081137-f89f-4c53-b432-a513eecc466e/ahc73_campaign_guide_v2-compressed.pdf", TFA_C),
        ("log_tfa", "Campaign Log", "37/eb/37ebfdb4-d7de-49c5-aed3-99a428502a57/ahc19_campaign_log.pdf", TFA_C),
        ("inv_tfa", "Investigator Expansion Rules", "86/17/86170eb5-15e4-42ca-a674-77e2f1746650/ahc72_forgotten_age_rules_insert-compressed.pdf", TFA_I),
    ]),
    ("The Circle Undone", [
        ("tcu", "Campaign Guide", "7f/d8/7fd88e9d-a98d-42f9-9d15-56d4de0ac811/ahc75_campaign_guide-compressed.pdf", TCU_C),
        ("log_tcu", "Campaign Log", "bc/b9/bcb94042-7b25-4331-940f-12918e622680/ahc29_campaign_log.pdf", TCU_C),
        ("inv_tcu", "Investigator Expansion Rules", "69/29/6929edad-38f2-491a-b929-4797e2fc26a4/ahc74_rules_insert-compressed.pdf", TCU_I),
    ]),
    ("The Dream-Eaters", [
        ("tde_a", "Campaign Guide A — The Dream-Quest", "32/db/32db52a4-73af-41c7-9a2c-56351115148e/ahc79_campaign_guide_a-web.pdf", TDE_C),
        ("tde_b", "Campaign Guide B — The Web of Dreams", "21/d0/21d09986-923e-4137-9d61-8f37c51ff242/ahc79_campaign_guide_b-web.pdf", TDE_C),
        ("log_tde", "Campaign Log", "67/f0/67f01d24-551e-4b76-87c8-5f75a74c95a8/the_dream-eaters_campaign_log.pdf", TDE_C),
        ("inv_tde", "Investigator Expansion Rules", "64/62/646226e5-f057-42f0-afa8-ad5cc6350b67/ahc78_rules_insert-web.pdf", TDE_I),
    ]),
    ("The Innsmouth Conspiracy", [
        ("tic", "Campaign Guide", "9d/71/9d71f59e-6ca6-469c-b00a-0a7c6d27b148/ahc82_campaign_guide-web_1.pdf", TIC_C),
        ("log_tic", "Campaign Log", "97/84/9784f06c-64b0-4871-95bf-b433707a9f76/innsmouth_campaign_log.pdf", TIC_C),
        ("inv_tic", "Investigator Expansion Rules", "12/d6/12d68c8f-f130-4566-beb2-206e8766b51d/ahc81_rules_insert-web.pdf", TIC_I),
    ]),
    ("Edge of the Earth", [
        ("eoe", "Campaign Guide", "3f/b5/3fb51dbf-2508-4a28-bf7d-fed5fea4905e/ahc64_edge_of_the_earth_campaign_guide-compressed.pdf", EOE_C),
        ("log_eoe", "Campaign Log", "54/56/5456514a-2344-495b-8d65-2acdedf8b84c/edge_of_the_earth_campaign_log-compressed.pdf", EOE_C),
        ("inv_eoe", "Investigator Expansion Rules", "73/04/7304c443-18f4-41e2-9f3c-7d0b21a1791d/ahc63_edge_of_the_earth_rules_insert-compressed.pdf", EOE_I),
    ]),
    ("The Scarlet Keys", [
        ("tsk", "Campaign Guide", "f0/f9/f0f98966-1063-420c-8e31-4d95f0142aa2/ahc70_the_scarlet_keys_campaign_guide-compressed.pdf", TSK_C),
        ("log_tsk", "Campaign Log", "6c/6a/6c6aa3e7-92ca-4d1b-aa72-92bb02725c82/ahc70_the_scarlet_keys_campaign_log.pdf", TSK_C),
        ("map_tsk", "World Map Sheet", "34/92/3492d2ce-d90f-47e0-a391-430a3bd8eb85/ahc70_world_map_sheet.pdf", TSK_C),
        ("inv_tsk", "Investigator Expansion Rules", "24/c5/24c5bf42-7f5e-45af-bc32-9d088f31442e/ahc69_scarlet_keys_rules_insert-compressed.pdf", TSK_I),
    ]),
    ("The Feast of Hemlock Vale", [
        ("fhv", "Campaign Guide", "5e/db/5edb4588-8583-4dc8-941c-26e1b7cfba56/ahc77_campaign_guide_web-compressed.pdf", FHV_C),
        ("log_fhv", "Campaign Log", "c5/84/c58490c6-93d2-4aa6-a4ec-f45e9f5a2953/ahc77_campaign_log.pdf", FHV_C),
        ("inv_fhv", "Investigator Expansion Rules", "44/31/443155f3-f978-40ca-b0e1-e406bb4789da/ahc76_rules_insert_web-compressed.pdf", FHV_I),
    ]),
    ("The Drowned City", [
        ("tdc", "Campaign Guide", "c1/3b/c13b0e74-62bb-49bc-bc85-036ab9d1ef10/ahc84_campaign_guide-web_1.pdf", TDC_C),
        ("log_tdc", "Campaign Log", "1b/ab/1bab5d6c-cc13-42a6-a65f-cd01e955e786/ahc84_campaign_log-web.pdf", TDC_C),
        ("inv_tdc", "Investigator Expansion Rules", "54/dd/54ddbd11-d83c-4010-8783-6cf74b1e6699/ahc83_rules_insert-web.pdf", TDC_I),
    ]),
    ("Return to...", [
        ("rules_rtnotz", "Return to the Night of the Zealot — Rules", "d4/64/d4646915-30d8-49a4-9d90-95be8f15b69f/ahc26_rules_insert.pdf", ["Return to the Night of the Zealot"]),
        ("rules_rtdwl", "Return to the Dunwich Legacy — Rules", "8d/bb/8dbbd753-6086-4760-a3a6-d7b9234e2313/return_to_the_dunwich_legacy_rules.pdf", ["Return to the Dunwich Legacy"]),
        ("rules_rtptc", "Return to the Path to Carcosa — Rules", "51/7e/517e98cc-7a54-42e8-96f0-bb600f240d9f/ahc36_rules_insert.pdf", ["Return to the Path to Carcosa"]),
        ("rules_rttfa", "Return to the Forgotten Age — Rules", "78/89/78897328-d162-4d5a-9f02-2fe1e3a19993/ahc46_rules_insert.pdf", ["Return to the Forgotten Age"]),
        ("rules_rttcu", "Return to the Circle Undone — Rules", "98/92/98925ac3-c087-4833-9081-9b03372f6362/ahc61_rules_insert_v2.pdf", ["Return to the Circle Undone"]),
    ]),
    ("Standalone Scenarios", [
        # FFG's page has no rules PDF for Curse of the Rougarou or Carnevale of
        # Horrors; their rules come printed in the pack.
        ("rules_lol", "The Labyrinths of Lunacy — Rules", "3a/bc/3abc09ae-b9f5-4426-863f-540c548870ee/the_labyrinths_of_lunacy_rules.pdf", ["The Labyrinths of Lunacy"]),
        ("rules_gob", "Guardians of the Abyss — Rules", "4f/34/4f34877d-f095-41d0-bd52-202a5b35d864/guardians_of_the_abyss_rules.pdf", ["Guardians of the Abyss"]),
        ("rules_hotel", "Murder at the Excelsior Hotel — Rules", "71/c2/71c24ce4-4582-4f4d-bcc4-b74e7758e7a8/ahc38_rules.pdf", ["Murder at the Excelsior Hotel"]),
        ("rules_blob", "The Blob That Ate Everything — Rules", "48/a4/48a43b7f-85c5-415d-8f84-5143d904d62c/ahc45_rulebook.pdf", ["The Blob That Ate Everything"]),
        ("rules_wog", "War of the Outer Gods — Rules", "b4/fb/b4fb1d96-2a6d-4e2a-9afd-fe87033feb07/ahc59_rulebook.pdf", ["War of the Outer Gods"]),
        ("rules_mtt", "Machinations Through Time — Rules", "f1/f4/f1f4dfa2-5f23-44e3-90fa-7539fbbf4de1/ahc62_rulebook.pdf", ["Machinations Through Time"]),
        ("rules_fof", "Fortune and Folly — Rules", "51/57/5157fe87-df13-4508-aa54-aece3052f499/ahc71_rulebook_v2-compressed.pdf", ["Fortune and Folly"]),
        ("rules_blbe", "The Blob That Ate Everything ELSE! — Rules", "ec/04/ec04d8d6-e6c2-44dc-bd19-c750bf3f288f/gcop2301_the_blob_that_ate_everything_else_rules_v7.pdf", ["The Blob That Ate Everything ELSE!"]),
        ("rules_tmg", "The Midwinter Gala — Rules", "d2/14/d2144b64-6fa6-456f-9268-2685f49310b9/ahc80_rulebook-web.pdf", ["The Midwinter Gala"]),
        ("rules_film", "Film Fatale — Rules", "f6/87/f68792a2-04f2-42a1-8954-f61dc42ad7d5/ahc85_film_fatale_rulebook-web.pdf", ["Film Fatale"]),
    ]),
    ("Parallel Investigators", [
        ("pnp_rod_cards", "Read or Die — Cards", "2a/1e/2a1e1533-5aea-4838-8af3-d9678b32cead/read_or_die_cards.pdf", ["Read or Die (Daisy Walker)"]),
        ("pnp_rod_rules", "Read or Die — Rules", "28/54/28547425-6352-43db-a2e7-b2fb99ad37c1/read_or_die_rules_insert_good.pdf", ["Read or Die (Daisy Walker)"]),
        ("pnp_aon_cards", "All or Nothing — Cards", "ed/49/ed49f432-38e7-49a3-8172-5943359a6869/all_or_nothing_cards.pdf", ["All or Nothing (\"Skids\" O'Toole)"]),
        ("pnp_aon_rules", "All or Nothing — Rules", "f7/f6/f7f6d8d4-7f5a-4066-a3c7-d1cdefcb376b/all_or_nothing_rules_insert.pdf", ["All or Nothing (\"Skids\" O'Toole)"]),
        ("pnp_bad_cards", "Bad Blood — Cards", "b4/c6/b4c6cebc-a096-4a90-83a9-5a5be037df91/bad_blood_cards.pdf", ["Bad Blood (Agnes Baker)"]),
        ("pnp_bad_rules", "Bad Blood — Rules", "5f/dc/5fdcad96-faae-44ae-98c7-b2083508b778/bad_blood_rules_insert-good.pdf", ["Bad Blood (Agnes Baker)"]),
        ("pnp_btb_cards", "By the Book — Cards", "50/4b/504b1ea6-041c-40b9-8976-020f9e7f2330/bythebookcards.pdf", ["By the Book (Roland Banks)"]),
        ("pnp_btb_rules", "By the Book — Rules", "6f/5b/6f5b617f-f5c6-4b95-a86a-0d3d7c80635e/bythebookinsert.pdf", ["By the Book (Roland Banks)"]),
        ("pnp_rtr_cards", "Red Tide Rising — Cards", "00/4f/004f56eb-c0d4-444a-a616-56a859f2fdcf/red_tide_rising_cards_v2.pdf", ["Red Tide Rising (Wendy Adams)"]),
        ("pnp_rtr_rules", "Red Tide Rising — Rules", "7a/86/7a86ba75-849a-45ba-b1ee-d0a4b760b780/red_tide_rising_rules_insert_v2.pdf", ["Red Tide Rising (Wendy Adams)"]),
        ("pnp_otr_cards", "On the Road Again — Cards", "eb/d5/ebd5b060-5c39-4152-9d83-03901d0b06f6/ashcan_pete_parallel_investigator_cards.pdf", ["On the Road Again (\"Ashcan\" Pete)"]),
        ("pnp_otr_rules", "On the Road Again — Rules", "37/53/3753a37e-a265-48a1-b4f8-826ee5b0e9cc/ashcan_pete_parallel_investigator_rules.pdf", ["On the Road Again (\"Ashcan\" Pete)"]),
        ("pnp_ltr_cards", "Laid to Rest — Cards", "2d/09/2d09c406-e05c-4a87-a668-296c0283d4fb/laid_to_rest_cards.pdf", ["Laid to Rest (Jim Culver)"]),
        ("pnp_ltr_rules", "Laid to Rest — Rules", "c8/40/c840a302-06f7-4d86-9122-1d636ee9c889/laid_to_rest_rules_insert.pdf", ["Laid to Rest (Jim Culver)"]),
        ("pnp_ptr_cards", "Path of the Righteous — Cards", "f6/60/f660c8ec-2f54-4a1c-8730-4aa4864622b0/zoey_samaras_parallel_investigator_cards.pdf", ["Path of the Righteous (Zoey Samaras)"]),
        ("pnp_ptr_rules", "Path of the Righteous — Rules", "9f/00/9f0026a5-25b7-4fcd-a6ec-e4798dd93688/zoey_samaras_parallel_investigator_rules.pdf", ["Path of the Righteous (Zoey Samaras)"]),
        ("pnp_rop_cards", "Relics of the Past — Cards", "94/37/94374018-ff42-4971-8e58-42af89197691/relics_of_the_past_cards_v2.pdf", ["Relics of the Past (Monterey Jack)"]),
        ("pnp_rop_rules", "Relics of the Past — Rules", "19/6f/196fb2a2-9595-4c23-a7d4-de8ebea2a299/relics_of_the_past_rules_insert.pdf", ["Relics of the Past (Monterey Jack)"]),
        ("pnp_hfa_cards", "Hunting for Answers — Cards", "e5/52/e5522fd6-deb7-43d3-a3fa-f4a24f14c1a3/rex_murphy_parallel_investigator_cards.pdf", ["Hunting for Answers (Rex Murphy)"]),
        ("pnp_hfa_rules", "Hunting for Answers — Rules", "a1/05/a1051c95-5c9e-45ac-9d9c-d362b7135c86/rex_murphy_parallel_investigator_rules.pdf", ["Hunting for Answers (Rex Murphy)"]),
        ("pnp_pap_cards", "Pistols and Pearls — Cards", "17/58/17587f1a-d347-483b-a373-9de4df609cbe/arkham_horror_dark_horse_comic_issue01_lcg_parallel_investigators.pdf", ["Pistols and Pearls (Jenny Barnes)"]),
        ("pnp_aof_cards", "Aura of Faith — Cards", "6e/18/6e185d55-e207-440e-8f32-02c9be9a80db/aura_of_faith.pdf", ["Aura of Faith (Father Mateo)"]),
        ("pnp_aof_rules", "Aura of Faith — Rules", "c5/10/c510acb5-0838-489c-bdad-0c047dc68ad7/aura_of_faith_insert.pdf", ["Aura of Faith (Father Mateo)"]),
        ("pnp_enc_cards", "Enthralling Encore — Cards", "0a/49/0a49d47f-731a-4c92-841d-56c22fa9099e/enthralling_encore.pdf", ["Enthralling Encore (Lola Hayes)"]),
        ("pnp_enc_rules", "Enthralling Encore — Rules", "46/5f/465f7b17-87c4-41b0-bae9-8538aaa646cb/enthralling_encore_rules_insert.pdf", ["Enthralling Encore (Lola Hayes)"]),
    ]),
]


def owned_products():
    coll = ROOT / "collection.json"
    if not coll.exists():
        sys.exit("collection.json not found (or pass --all). Open collection.html, "
                 "mark what you own, export, and save it next to index.html.")
    return set(json.loads(coll.read_text(encoding="utf-8"))["products"])


def derive_boa_log():
    """The Brethren of Ash campaign log is page 15 of its campaign guide."""
    src, dest = GUIDES / "boa.pdf", GUIDES / "log_boa.pdf"
    if dest.exists() or not src.exists():
        return
    try:
        from pypdf import PdfReader, PdfWriter
    except ImportError:
        print("NOTE: log_boa.pdf not created - the Brethren of Ash campaign log "
              "is page 15 of boa.pdf. `pip install pypdf` and rerun, or extract "
              "the page manually.")
        return
    w = PdfWriter()
    w.add_page(PdfReader(str(src)).pages[14])
    with open(dest, "wb") as f:
        w.write(f)
    print("extracted log_boa.pdf (page 15 of boa.pdf)")


def main():
    fetch_all = "--all" in sys.argv
    owned = None if fetch_all else owned_products()
    GUIDES.mkdir(exist_ok=True)
    failed = []
    for group, docs in MANIFEST:
        for key, title, path, products in docs:
            if path is None:
                continue
            if owned is not None and products is not None and not owned & set(products):
                continue
            dest = GUIDES / f"{key}.pdf"
            if dest.exists():
                continue
            try:
                req = urllib.request.Request(CDN + path, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=60) as r:
                    dest.write_bytes(r.read())
                print(f"fetched {key}.pdf  ({title})")
            except Exception as e:
                print(f"FAILED {key}: {e}")
                failed.append(key)

    derive_boa_log()

    # regenerate data/docs.js from what's actually on disk
    groups = []
    for group, docs in MANIFEST:
        present = [[title, key] for key, title, _, _ in docs if (GUIDES / f"{key}.pdf").exists()]
        if present:
            groups.append({"group": group, "docs": present})
    DATA.mkdir(exist_ok=True)
    (DATA / "docs.js").write_text(
        "const AHLCG_DOCS = " + json.dumps(groups, ensure_ascii=False, indent=1) + ";\n",
        encoding="utf-8")
    print(f"\nwrote data/docs.js ({sum(len(g['docs']) for g in groups)} documents)")
    print("INCOMPLETE - rerun to retry: " + str(failed) if failed else "COMPLETE")


if __name__ == "__main__":
    main()
