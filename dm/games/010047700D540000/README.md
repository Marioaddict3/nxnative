# Clubhouse Games: 51 Worldwide Classics (`010047700D540000`)

Update v262144, `main` build ID `FAD4615A54DCC997B07A7BE8588505DD62DD9A49` (the rewriter's key: `fad4615a54dcc997b07a7be8588505dd`). NDcube's NintendoWare **Bezel** engine (strings `D:/home/Bezel/...`, `BEXViewport`, `ProjectionType_PerspectiveFovy` / `ProjectionType_Orthographic`, `MultiViewport[%d]`), the engine of [Big Brain Academy: Brain vs. Brain](../0100620012D6E000/README.md) too; not sead / agl, so none of Breath of the Wild's or Animal Crossing: New Horizons' screen-shape functions exist here.

**Status: screen-shape (Duo fill-aspect) profile, IPA keys partly guessed.** Not brought up: never run on the Mac or a device.

## What it needs

| Setting | Where | Why |
|---|---|---|
| `screen_aspect on` | [`game.tsv`](game.tsv) | the iOS launcher offers DM_SCREEN_ASPECT; the stubs in [`patches.py`](patches.py) read the state page loader.c fills |
| `build v262144 … main=fad4615a…` | `game.tsv` | the build the stubs are keyed by |

### IPA keys (filled so `scripts/build_ipa_from_nsp.py` loads the profile)

Filled from what is known: `program_id` (= title ID), `ipa` (`ClubhouseGames51WorldwideClassics.ipa`), `package` / `shader_versions` (`v262144`), `shader_note`, and the empty shader tables the NSP script writes for a provisional profile (filled by the shader split).

**Guessed, TODO at bring-up** (`# TODO` in [`game.tsv`](game.tsv)): `app_category` (board-games), `modules main sdk` (the subsdks and every build ID but main's are unknown; the NSP script's NRO pass adds subsdks NROs import), `romfs_marker` / `zip_store`, `shader_groups`, the memory keys (`sys_resource 0`, `mem_reserve`, `mem_alias`, `mem_stack`, `app_pool`) and `op_mode handheld` / `perf_mode boost`, all from [Big Brain Academy](../0100620012D6E000/game.tsv) (same Bezel engine). Still missing: v262144's display version, `depth_mode`, `mem_used` (the heap check sets it), the SDK version.

## Screen shape

DM_SCREEN_ASPECT (loader.c) puts the output height at state +0x48 (1344 at 1.43:1), the layout height at +0x4c (896) and its float at +0x50; 0 = 16:9, and every stub then runs only the original instruction. Widths stay (1920, 1280); heights rise. Each stub is gated by one bit of the site mask at +0x54 (`DM_SCREEN_ASPECT_SITES`, all on by default), so sites can be tried one by one. Each stub runs the site's original instruction, then writes the host's height into the register it set. x16 / x17 are scratch: every site is in straight-line code ending in a call or tail call; the anchor function (main+0x3cb600..0x3cc200) uses neither register anywhere.

Hybrid of the two references: Breath of the Wild-style size stubs for the render / display sizes (bits 0-5) and New Horizons-style layout sizes for the 2D viewports and UI anchors (bits 6-11).

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

**Why no `duo_anchor.c`.** Breath of the Wild's and New Horizons' anchoring hooks `nn::ui2d::Pane::Calculate` and walks NintendoWare Ui2d pane fields (parent, translation, size, global matrix, name). Bezel's layout panes have not been identified (no class, vtable or field offsets), so porting it would be guesswork. The anchor-size loads (bit 11) are the nearest honest equivalent: they move what Bezel anchors to the layout's bottom edge, but they do not stretch full-screen backgrounds or move the HUD's children the way duo_calc does.

### Verified

- Every site's original instruction was checked against the decompressed v262144 `main` (all LZ4 segments, sizes match the header). `fs_site` asserts these at rewrite time.
- The emitted stubs were disassembled (capstone) with a mock ctx: branches land on the branch back, and each stub returns to site + 4.

### Open

- **No device or Mac test.** Which bits help or hurt is unknown; start with `DM_SCREEN_ASPECT_SITES` covering a few bits at a time.
- **No projection (FOV) writer found.** No fovy / aspect float constants were located. Bezel's `ProjectionType_PerspectiveFovy` is known only from reflection strings. If the camera's aspect comes from the resized viewport, the 3D view keeps its vertical angle and loses 16:9's sides; if it is fixed at 16:9 elsewhere, the picture stretches. Either way a projection stub (BotW's fov_stub) is still to be written once the writer is found (Ghidra).
- Callee semantics (main+0x259690 / 0x259620 / 0x68a110 / 0x6f0b00 / 0x2f25b0 / 0x843340) are inferred from their arguments, not named. The display-mode table's layout (+0x6c..+0x84 as width / height arrays) is a reading of its stores.
- Not stubbed: the second render-target table (rodata main+0x11c3d8c, read from main+0x338cdc), the UI rect main+0x11ba318 (main+0x3ff4c0), the {1920.0,1080.0,…} block main+0x11ba700 (no direct reference found), the 1152x648 / 1600x900 thunks next to bits 6-8, and ORR-immediate / literal-load forms (only MOVZ immediates and rodata pairs were scanned).
- Binding: `build` → unreviewed. Big Brain Academy is on the same engine (1.56); whether these functions match there (an engine rule) is not checked.
- **Shader tables are placeholders** (`shader_map.tsv`, `shader_facts.tsv`, `shader_pairs.tsv`, `shader_map.tsv.conflicts.tsv`: EMPTY_TABLES, no rows). The first full build's shader split writes its real tables into this folder (build_ipa_from_nsp.py seeds placeholder tables instead of comparing them); commit them, after which later splits are checked against them.
