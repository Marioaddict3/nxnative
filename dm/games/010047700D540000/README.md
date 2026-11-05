# Clubhouse Games: 51 Worldwide Classics (`010047700D540000`)

Update v262144, `main` build ID `FAD4615A54DCC997B07A7BE8588505DD62DD9A49` (the rewriter's key: `fad4615a54dcc997b07a7be8588505dd`). NDcube's NintendoWare **Bezel** engine (strings `D:/home/Bezel/...`, `BEXViewport`, `ProjectionType_PerspectiveFovy` / `ProjectionType_Orthographic`, `MultiViewport[%d]`), the engine of [Big Brain Academy: Brain vs. Brain](../0100620012D6E000/README.md) too; not sead / agl, so none of Breath of the Wild's or Animal Crossing: New Horizons' screen-shape functions exist here.

**Status: screen-shape (Duo fill-aspect) profile, IPA keys partly guessed.** Window fill verified on Duo at `0a54a56` (stretched); bits 14–15 (Bezel perspective aspect + layout orthography) untested on device.

## What it needs

| Setting | Where | Why |
|---|---|---|
| `screen_aspect on` | [`game.tsv`](game.tsv) | the iOS launcher offers DM_SCREEN_ASPECT; the stubs in [`patches.py`](patches.py) read the state page loader.c fills |
| `build v262144 … main=fad4615a…` | `game.tsv` | the build the stubs are keyed by |

### IPA keys (filled so `scripts/build_ipa_from_nsp.py` loads the profile)

Filled from what is known: `program_id` (= title ID), `ipa` (`ClubhouseGames51WorldwideClassics.ipa`), `package` / `shader_versions` (`v262144`), `shader_note`, and the empty shader tables the NSP script writes for a provisional profile (filled by the shader split).

**Confirmed at bring-up:** `romfs_marker` is `Archive/boot.nx.bea` (Clubhouse RomFS; there is no `Permanent~01Boot`).

**Confirmed at bring-up:** `modules` is `main subsdk0 subsdk1 sdk` with build IDs from the v262144 ExeFS (`main=fad4615a…`, `subsdk0=0e0956c8…`, `subsdk1=5a7ada8d…`, `sdk=ad3fdfbd…`). Display version in the `build` row is still a placeholder (`v262144`); replace from control.nacp when known. SDK major is read from the loaded `sdk` module at run time.

**Guessed, TODO at bring-up** (`# TODO` in [`game.tsv`](game.tsv)): `app_category` (board-games), `zip_store`, `shader_groups`, the memory keys (`sys_resource 0`, `mem_reserve`, `mem_alias`, `mem_stack`, `app_pool`) and `op_mode handheld` / `perf_mode boost`, all from [Big Brain Academy](../0100620012D6E000/game.tsv) (same Bezel engine). Still missing: v262144's display version, `depth_mode`, `mem_used` (the heap check sets it), the SDK version.

## Screen shape

DM_SCREEN_ASPECT (loader.c) puts the output height at state +0x48 (1344 at 1.43:1), the layout height at +0x4c (896) and its float at +0x50; 0 = 16:9, and every stub then runs only the original instruction. Widths stay (1920, 1280); heights rise. Each stub is gated by one bit of the site mask at +0x54 (`DM_SCREEN_ASPECT_SITES`, all on by default), so sites can be tried one by one. Each stub runs the site's original instruction, then writes the host's height into the register it set. x16 / x17 are scratch: every site is in straight-line code ending in a call or tail call; the anchor function (main+0x3cb600..0x3cc200) uses neither register anywhere.

Hybrid of the two references: Breath of the Wild-style size stubs for the render / display / window sizes (bits 0-5, 12-13), New Horizons-style layout sizes for the 2D viewports and UI anchors (bits 6-11), and Bezel projection stubs for perspective aspect and layout orthography (bits 14-15).

| Bit | Site (`main+`) | Original | Change |
|---|---|---|---|
| 0 | `0x5cad0` | `mov w2,#1080` (1920x1080 into main+0x259690) | the output height |
| 1 | `0x5cae8` | `mov w2,#720` (1280x720 into main+0x259620; the notes' `0x5cae4` is its `mov w1,#1280`) | the layout height |
| 2 | `0x68915c` | `movk x8,#1080,lsl #32` (display-mode pair 1920x1080 at +0x64 / +0x8c) | high half = the output height |
| 3 | `0x689178` | `movk x8,#720,lsl #32` (pair 720,720 at +0x74) | both halves = the layout height |
| 4 | `0x689190` | `movk x8,#1080,lsl #32` (pair 900,1080 at +0x84) | 5/6 of the output height (1600-wide mode, 1120), the output height |
| 5 | `0x338344` | `ldp w9,w8,[x8,#8]` (render-target pool, rodata main+0x11c3c54, 20 entries {fmt,1,1920,1080}) | a 1080 height → the output height (before the x1 / x2 scale) |
| 6 | `0x2537e0` | `mov w3,#720` (set-size thunk main+0x2537dc → main+0x68a110) | the layout height |
| 7 | `0x2539d4` | `mov w4,#720` (thunk main+0x2539d0 → main+0x6f0b00) | the layout height |
| 8 | `0x253c54` | `mov w4,#720` (thunk main+0x253c50 → main+0x6f0b00) | the layout height |
| 9 | `0x2864e8` | `mov w8,#720` (default viewport {0,0,1280,720} of main+0x2864d0) | the layout height |
| 10 | `0x28672c` | `mov w9,#720` (default viewport of main+0x286720) | the layout height |
| 11 | `0x3cb728`, `0x3cb744`, `0x3cbd28`, `0x3cbd44` | `ldr s,[x,idx,lsl #2]` from rodata main+0x11ba310 {1280.0,720.0,1280.0,720.0} by anchor index 0..3 | an odd (height) index → the layout height (float), so bottom-anchored panes sit at the taller screen's edge |
| 12 | `0x6f0b40` | `str w4,[x8,x9]` (set-size request height) | a 16:9 request → w × output height / 1920 |
| 13 | `0x68952c` / `0x68954c` / `0x689588` / `0x68959c` / `0x6895d8` | window config `SetDisplaySize` / handheld / docked height stores | a 16:9 height → w × output height / 1920 (swap chain + crops) |
| 14 | `0x61f898` | `mov v8.16b,v1.16b` in `nn::bezel::Camera::SetProjectionPerspectiveFovy(ffff)` | a 16:9 aspect → the screen ratio at state +0x58 (covers the 3-arg overload's hard-coded 16/9 load too) |
| 15 | `0x64d18` | `ldp s2,s1,[x19,#0x2c]` (orthographic branch of the projection-type dispatch) | 720 × 16:9 → layout height + ratio; 1080 × 16:9 → output height + ratio |

**Why no `duo_anchor.c`.** Breath of the Wild's and New Horizons' anchoring hooks `nn::ui2d::Pane::Calculate` and walks NintendoWare Ui2d pane fields (parent, translation, size, global matrix, name). Bezel's layout panes have not been identified (no class, vtable or field offsets), so porting it would be guesswork. The anchor-size loads (bit 11) are the nearest honest equivalent: they move what Bezel anchors to the layout's bottom edge, but they do not stretch full-screen backgrounds or move the HUD's children the way duo_calc does.

### Verified

- Every site's original instruction was checked against the decompressed v262144 `main` (all LZ4 segments, sizes match the header). `fs_site` asserts these at rewrite time.
- The emitted stubs were disassembled (capstone) with a mock ctx: branches land on the branch back, and each stub returns to site + 4.
- Window sizes (bits 12-13): George's Duo log (DM_SCREEN_ASPECT=1.43) still had WindowInitialize 1920x1080 and crops 1280x720 / 1920x1080 because the boot script sets the window config through setters (main+0x689520 display/texture, +0x689540 / +0x689570 handheld, +0x689590 / +0x6895c0 docked; callers main+0x9a249c..0x9a2c00) after the constructor defaults of bits 2-4. The window (main+0x6e7ae0) copies that config; nvnWindowSetCrop (main+0x6e85a4, main+0x6ef428) gets the request of main+0x6f0b00 clamped to the texture size. Bit 13 stubs the setters' height stores, bit 12 the request store in main+0x6f0b00 (0x6f0b40); a 16:9 size takes w x output height / 1920. Traced in the image; not yet run on a device.

### Open

- **No device or Mac test.** Which bits help or hurt is unknown; start with `DM_SCREEN_ASPECT_SITES` covering a few bits at a time.
- **Bits 12-13 verified on Duo** (`0a54a56`): window fills (WindowCrop / present 1920x1344) but 2D and 3D content was stretched.
- **Bits 14-15 untested on a device**: bit 14 sets Bezel camera aspect to the screen ratio for 16:9 inputs; bit 15 retargets layout orthography 720/1080 × 16:9. Expect no vertical stretch; 3D keeps its vertical FOV and loses a little of each side (BotW-style fovy widen not applied). If UI is still stretched, try `DM_SCREEN_ASPECT_SITES=0xc000` (bits 14–15 only) then add layout bits back.
- Callee semantics (main+0x259690 / 0x259620 / 0x68a110 / 0x6f0b00 / 0x2f25b0 / 0x843340) are inferred from their arguments, not named. The display-mode table's layout (+0x6c..+0x84 as width / height arrays) is a reading of its stores.
- Not stubbed: the second render-target table (rodata main+0x11c3d8c, read from main+0x338cdc), the UI rect main+0x11ba318 (main+0x3ff4c0), the {1920.0,1080.0,…} block main+0x11ba700 (no direct reference found), the 1152x648 / 1600x900 thunks next to bits 6-8, and ORR-immediate / literal-load forms (only MOVZ immediates and rodata pairs were scanned).
- Binding: `build` → unreviewed. Big Brain Academy is on the same engine (1.56); whether these functions match there (an engine rule) is not checked.
- **Shader tables are placeholders** (`shader_map.tsv`, `shader_facts.tsv`, `shader_pairs.tsv`, `shader_map.tsv.conflicts.tsv`: EMPTY_TABLES, no rows). The first full build's shader split writes its real tables into this folder (build_ipa_from_nsp.py seeds placeholder tables instead of comparing them); commit them, after which later splits are checked against them.
