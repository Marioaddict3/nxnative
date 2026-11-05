# Clubhouse Games: 51 Worldwide Classics (010047700D540000): the rewriter's patches of this game's own builds. dm/tools/patch_nso.py loads every profile's patches.py and applies
# those of a module's NSO build ID (FRAME_STEP as described there, "Registered patches"). The game has no frame step stubs: FRAME_STEP only gives its main the state page that the
# screen shape stubs read (DM_SCREEN_ASPECT, as for Breath of the Wild and Animal Crossing: New Horizons); with DM_SCREEN_ASPECT unset the page stays zero and every stub runs
# the original instruction only.
import struct
from nso_asm import ADRP, B

# Screen shape (DM_SCREEN_ASPECT, loader.c): a screen taller than 16:9 keeps the picture's width and takes the height of the screen's ratio: state +0x48 u32 output height
# (1920 → 1344 at 1.43), +0x4c u32 layout height (1280 → 896), +0x50 the same as a float; 0 = 16:9. The game runs on NDcube's NintendoWare Bezel engine, not sead / agl, so
# none of Breath of the Wild's or New Horizons' functions exist here: every site below was found by its 1920x1080 / 1280x720 immediates and their rodata pairs in update
# v262144's main (notes in README.md). Each stub is one bit of the conversion site mask (+0x54, DM_SCREEN_ASPECT_SITES, all on by default), so a build can try the sites
# one by one; a height of 0 leaves the original value. Each stub runs the site's original instruction first, then (bit set, height set) puts the host's height in the
# register the instruction wrote. x16 / x17 are scratch at every site: each is in straight-line code that calls out (or tail-calls) right after, where a veneer may clobber them
_tbz17 = lambda bit, n: 0x36000000 | (bit & 0x1f) << 19 | bit >> 5 << 31 | n << 5 | 17   # tbz w17,#bit,+n
_cbz17 = lambda n: 0x34000000 | n << 5 | 17                                                # cbz w17,+n
_out, _lay, _layf = 0xb9404a11, 0xb9404e11, 0xb9405211   # ldr w17,[x16,#0x48] / #0x4c / #0x50
_mask = 0xb9405611                                      # ldr w17,[x16,#0x54]
_mov = lambda d: 0x2a1103e0 | d                        # mov w<d>,w17
_hi8, _lo8 = 0xb3607e28, 0xb3407e28                     # bfi x8,x17,#32,#32 / bfi x8,x17,#0,#32
_fmov = lambda d: 0x1e270220 | d                       # fmov s<d>,w17

# (site, original instruction, bit, height load, the words that apply w17, reason). Sites marked "index" first test the index register's bit 0 (odd = a height)
_sites = [
    # top-level render / display init (main+0x5cac4..: x0 = [[main+0x152e500]]): docked 1920x1080 into main+0x259690, then 1280x720 into main+0x259620 (BotW-style size stubs)
    (0x5cad0, 0x52808702, 0, _out, [_mov(2)], 'render init: 1920x1080 into main+0x259690: mov w2,#1080 → the output height (bit 0)'),
    (0x5cae8, 0x52805a02, 1, _lay, [_mov(2)], 'render init: 1280x720 into main+0x259620: mov w2,#720 → the layout height (bit 1)'),
    # display-mode table in the graphics system constructor (main+0x689158..): packed pairs stored at +0x64 / +0x8c (1920x1080), +0x74 (720,720), +0x84 (900,1080)
    (0x68915c, 0xf2c08708, 2, _out, [_hi8], 'display-mode table +0x64 / +0x8c: 1920x1080 → 1920 x the output height (bit 2)'),
    (0x689178, 0xf2c05a08, 3, _lay, [_lo8, _hi8], 'display-mode table +0x74: the 720 heights → the layout height (bit 3)'),
    (0x689190, 0xf2c08708, 4, _out, [0x0b110a30, 0x528000c8, 0x1ac80a08, _hi8],   # add w16,w17,w17,lsl #2; mov w8,#6; udiv w8,w16,w8 (1600 x h / 1920); bfi x8,x17,#32,#32
     'display-mode table +0x84: 900,1080 → 5/6 of the output height, the output height (bit 4)'),
    # render-target pool (main+0x338330..: 0x14 entries of 16 bytes at rodata main+0x11c3c54 {format, 1, 1920, 1080}, w and h x the scale, into main+0x2f25b0): a 1080 height grows
    (0x338344, 0x29412109, 5, _out, [0x7110e11f, 0x54000041, _mov(8)],   # cmp w8,#1080; b.ne back (+2); mov w8,w17
     'render-target pool: a 1080 entry height → the output height (bit 5)'),
    # per-resolution set-size thunks: 1280x720 into main+0x68a110 / main+0x6f0b00
    (0x2537e0, 0x52805a03, 6, _lay, [_mov(3)], 'set-size helper main+0x2537dc: mov w3,#720 → the layout height (bit 6)'),
    (0x2539d4, 0x52805a04, 7, _lay, [_mov(4)], 'set-size helper main+0x2539d0: mov w4,#720 → the layout height (bit 7)'),
    (0x253c54, 0x52805a04, 8, _lay, [_mov(4)], 'set-size helper main+0x253c50: mov w4,#720 → the layout height (bit 8)'),
    # default 2D / layout viewports {0, 0, 1280, 720, depth 0..1} built on the stack (ACNH-style layout size)
    (0x2864e8, 0x52805a08, 9, _lay, [_mov(8)], 'default viewport main+0x2864e0: height 720 → the layout height (bit 9)'),
    (0x28672c, 0x52805a09, 10, _lay, [_mov(9)], 'default viewport main+0x28672c: height 720 → the layout height (bit 10)'),
]
# UI anchor math (main+0x3cb718.., main+0x3cbd18..): the layout's anchor index (0..3) picks a float of rodata main+0x11ba310 {1280.0, 720.0, 1280.0, 720.0} and positions the
# pane at (a + b) x 0.5: an odd index is a height, which takes the layout height so edge widgets anchored to the bottom move to the taller screen's edge (bit 11)
_anchor = [(0x3cb728, 0xbc687921, 8, 1), (0x3cb744, 0xbc697940, 9, 0), (0x3cbd28, 0xbc687920, 8, 0), (0x3cbd44, 0xbc697941, 9, 1)]   # ldr s<d>,[x<base>,x<idx>,lsl #2]

# Window sizes (what NVN's window crop and the presented picture follow): the window object (main+0x6e7ae0 copies its config) keeps the swap chain texture size at +0x70a4
# and per mode (handheld, docked) two requested sizes at +0x7708..; main+0x6f0b00 sets a requested size and the crop (+0x7738 / +0x7740, into nvnWindowSetCrop at
# main+0x6e85a4 / main+0x6ef428) is the request clamped to the texture size. The game's boot script overrides the constructor's defaults (bits 2-4) through the config
# setters below (callers main+0x9a249c..0x9a2c00), so the texture stayed 1920x1080 and the crops 1280x720 / 1920x1080. A size of 16:9 (16 x h = 9 x w) takes the height
# w x the output height / 1920 (1280 → 896, 1600 → 1120, 1920 → 1344); others pass. These stubs work on a store, so the height register is set before the original store runs
_win = [
    (0x6f0b40, 0xb8296904, 12, 3, 4, 'set-size main+0x6f0b00: str w4 (the requested height of w3 x w4) → the screen shape height (bit 12)'),
    (0x68952c, 0xb9006902, 13, 1, 2, 'window config SetDisplaySize main+0x689520 (+0x64 / +0x68, the swap chain texture): str w2 → the screen shape height (bit 13)'),
    (0x68954c, 0xb9007502, 13, 1, 2, 'window config handheld sizes main+0x689540 (+0x74 / +0x78): str w2 → the screen shape height (bit 13)'),
    (0x689588, 0xb9007503, 13, 2, 3, 'window config handheld size [i] main+0x689570 (+0x74): str w3 → the screen shape height (bit 13)'),
    (0x68959c, 0xb9008502, 13, 1, 2, 'window config docked sizes main+0x689590 (+0x84 / +0x88): str w2 → the screen shape height (bit 13)'),
    (0x6895d8, 0xb9008503, 13, 2, 3, 'window config docked size [i] main+0x6895c0 (+0x84): str w3 → the screen shape height (bit 13)'),
]


def screen_shape(ctx):
    here, emit, site, put, STATE = ctx.here, ctx.emit, ctx.site, ctx.put, ctx.state
    def stub(at, orig, bit, load, apply, why, index=None):
        site(at, struct.pack('<I', orig).hex())
        start = here(); emit(orig)
        rest = 4 + len(apply)   # adrp, ldr sites, tbz, ldr height, cbz, apply...: words from each test to the branch back
        if index is not None: emit(0x36000000 | (rest + 2) << 5 | index)   # tbz w<index>,#0,back: an even index is a width
        emit(ADRP(16, here(), STATE))
        emit(_mask); emit(_tbz17(bit, rest - 1)); emit(load); emit(_cbz17(len(apply) + 1))
        for w in apply: emit(w)
        emit(B(here(), at + 4))
        put(at, [B(at, start)], why)
    for at, orig, bit, load, apply, why in _sites:
        stub(at, orig, bit, load, apply, why)
    for at, orig, idx, d in _anchor:
        stub(at, orig, 11, _layf, [_fmov(d)], 'UI anchor size: an odd (height) index takes the layout height (bit 11)', index=idx)
    for at, orig, bit, w, h, why in _win:
        site(at, struct.pack('<I', orig).hex())
        start = here()
        for word in (ADRP(16, here(), STATE), _mask, _tbz17(bit, 10), _out, _cbz17(8),
                     0x531c6c10 | h << 5, 0x4b000e10 | w << 16, 0x6b00021f | w << 16,   # lsl w16,wH,#4; sub w16,w16,wW,lsl #3; cmp w16,wW (16h - 8w = w: 16:9)
                     0x54000081, 0x1b117c10 | w << 5, 0x5280f011, 0x1ad10a00 | h):     # b.ne orig; mul w16,wW,w17; mov w17,#1920; udiv wH,w16,w17
            emit(word)
        emit(orig); emit(B(here(), at + 4))
        put(at, [B(at, start)], why)


FRAME_STEP = {
    'fad4615a54dcc997b07a7be8588505dd': screen_shape,   # v262144 main
}

# How general each patch is and could be (dm/tools/docs_patches.py "Binding", listed in docs/agents/game-patches.md): what, its binding now, the loosest it could have (goal),
# purpose, why; blocked or kept: why the gap stays open
BINDING = [
    {'what': 'screen shape: the render, display-mode, window (swap chain / crop), render-target and layout sizes and the UI anchors (DM_SCREEN_ASPECT)', 'now': 'build', 'goal': 'unreviewed',
     'purpose': 'rendering',
     'why': "found at bring-up from the Bezel engine's 1920x1080 / 1280x720 constants in this build; whether a Bezel engine rule (Big Brain Academy shares the engine) could carry it is not judged yet"},
]
