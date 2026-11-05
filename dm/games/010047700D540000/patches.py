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

# Perspective Hor+ (bit 14): nn::bezel::Camera::SetProjectionPerspectiveFovy(ffff) at main+0x61f880.
# After mov v8,v1 (aspect→s8), a 16:9 or already-screen-ratio aspect takes the screen ratio at +0x58 and widens
# fovy to 2 atan(tan(fovy/2)×k), k at +0x5c = (16/9)/ratio, so the taller picture keeps 16:9's sides and shows
# more above and below (mush8 / BotW Hor+). tanf / atanf via main's PLT (0xfda760 / 0xfda770). Last widened fovy
# at state +0x100 skips a second widen when the 3-arg overload (hard-coded 16/9) is called again with the
# widened angle. s2 / s3 / x0 spilled across the calls; s1 is scratch (next insn is fmov s1,#0.5).
_proj_at, _proj_orig, _proj_bit = 0x61f898, 0x4ea11c28, 14
_TANF, _ATANF = 0xfda760, 0xfda770

# 2D / layout orthography (bit 15): nn::bezel::Camera::SetOrthography at main+0x61ffa0. Several builders
# (the type-0 dispatch at main+0x64d18, and at least main+0x6def00) pass top/bottom/left/right; a 16:9
# span of ~720 (or ~1080) still stretched UI after the single-builder stub. This entry hook keeps L/R
# (horizontal FOV of the layout) and expands T/B around the centre to the layout / output height so
# 1280×720 content stays native scale with more above and below (mush8). s6/s7/s16/s17 are scratch.
_ortho_at, _ortho_orig, _ortho_bit = 0x61ffa0, 0xfc1c0fee, 15



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
    # bit 14: Hor+ (keep H FOV, widen V fovy) + aspect → ratio
    site(_proj_at, struct.pack('<I', _proj_orig).hex())
    start = here()
    words = []
    def E(w):
        words.append(w & 0xffffffff)
    E(_proj_orig)
    E(0x6dbf0fe2); E(0xf81f0fe0)                                   # stp d2,d3,[sp,#-0x10]!; str x0,[sp,#-0x10]!
    E(ADRP(16, start + len(words) * 4, STATE)); E(_mask)
    i_tbz = len(words); E(0)                                      # tbz bit14 → restore
    E(0xbd405a11); E(0x1e202228)                                   # s17 = ratio; fcmp #0
    i_off = len(words); E(0)                                      # b.eq restore
    E(0xbd407610); E(0x1e303901); E(0x1e20c021)                     # |s8 − 16/9|
    E(0xbd407a10); E(0x1e302020)
    i_not169 = len(words); E(0)                                   # b.ge try_ratio
    i_b_do = len(words); E(0)                                     # b do
    i_try = len(words)
    E(0x1e313901); E(0x1e20c021); E(0xbd407a10); E(0x1e302020)     # |s8 − ratio|; wtol; fcmp
    i_other = len(words); E(0)                                    # b.ge restore
    i_do = len(words)
    E(0x1e204228)                                                  # s8 = ratio
    E(0xbd410210); E(0x1e302000)                                   # last widened; fcmp s0
    i_same = len(words); E(0)                                     # b.eq restore
    E(0x1e2c1001); E(0x1e210800)                                   # half = fovy × 0.5
    i_bl_tan = len(words); E(0)
    E(ADRP(16, start + (len(words) + 0) * 4, STATE)); E(0xbd405e01); E(0x1e210800)  # × k
    i_bl_atan = len(words); E(0)
    E(0x1e202800)                                                  # × 2
    E(ADRP(16, start + len(words) * 4, STATE)); E(0xbd010200)     # store last widened
    i_restore = len(words)
    E(0xf84107e0); E(0x6cc10fe2)                                   # pop x0; pop d2,d3
    i_back = len(words); E(0)                                     # b site+4
    # patch PC-relative
    def cond(i, target_i, c):
        pc = start + i * 4; tgt = start + target_i * 4
        words[i] = 0x54000000 | (((tgt - pc) // 4) & 0x7ffff) << 5 | c
    def tbz(i, target_i, bit=_proj_bit):
        pc = start + i * 4; tgt = start + target_i * 4
        words[i] = _tbz17(bit, ((tgt - pc) // 4) & 0x3fff)
    def bl(i, target):
        pc = start + i * 4; words[i] = B(pc, target) | 0x80000000
    def b_to(i, target_i):
        pc = start + i * 4; words[i] = B(pc, start + target_i * 4)
    # fix ADRPs that were emitted with wrong here() when using start+len — recompute
    # word index of first ADRP after pops: indices
    # Rebuild ADRP words properly:
    # After E(_mask) the next is tbz; first ADRP is at index 3 (0=orig,1=stp,2=str,3=adrp)
    words[3] = ADRP(16, start + 3 * 4, STATE)
    # ADRP before ×k: after bl tanf
    # ADRP before store: after fadd
    tbz(i_tbz, i_restore)
    cond(i_off, i_restore, 0)
    cond(i_not169, i_try, 0xa)
    b_to(i_b_do, i_do)
    cond(i_other, i_restore, 0xa)
    cond(i_same, i_restore, 0)
    bl(i_bl_tan, _TANF)
    words[i_bl_tan + 1] = ADRP(16, start + (i_bl_tan + 1) * 4, STATE)
    bl(i_bl_atan, _ATANF)
    words[i_bl_atan + 2] = ADRP(16, start + (i_bl_atan + 2) * 4, STATE)  # after fadd is +1 from bl_atan... 
    # layout after i_bl_atan: bl; fadd; adrp; str; restore...
    # i_bl_atan points to bl; +1 = fadd; +2 = adrp. Yes.
    words[i_back] = B(start + i_back * 4, _proj_at + 4)
    for w in words: emit(w)
    put(_proj_at, [B(_proj_at, start)], 'SetProjectionPerspectiveFovy: Hor+ fovy widen + 16:9 aspect → screen ratio (bit 14)')
    # bit 15: SetOrthography entry — expand T/B when span ≈ 720/1080; keep L/R (Hor+ 2D)
    site(_ortho_at, struct.pack('<I', _ortho_orig).hex())
    start = here()
    words = []
    def E(w):
        words.append(w & 0xffffffff)
    def cond(i, ti, c):
        pc = start + i * 4; tgt = start + ti * 4
        words[i] = 0x54000000 | (((tgt - pc) // 4) & 0x7ffff) << 5 | c
    def tbz(i, ti, bit=_ortho_bit):
        pc = start + i * 4; tgt = start + ti * 4
        words[i] = _tbz17(bit, ((tgt - pc) // 4) & 0x3fff)
    def b_to(i, ti):
        words[i] = B(start + i * 4, start + ti * 4)
    E(ADRP(16, start, STATE)); E(_mask)
    i_tbz = len(words); E(0)
    E(0xbd405a11); E(0x1e202228); i_r0 = len(words); E(0)                 # ratio on?
    E(0xbd405211); E(0x1e202228); i_l0 = len(words); E(0)                 # layf on?
    E(0x1e213806); E(0x1e20c0c6)                                         # s6 = |top-bottom|
    E(0x52800011); E(0x72a88691); E(0x1e270227)                           # s7 = 720
    E(0x1e2738d1); E(0x1e20c231); E(0x1e2e1010); E(0x1e302220)           # |s6-720|<1?
    i_ge720 = len(words); E(0)
    E(0xbd405207); i_do = len(words); E(0)                               # s7 = layf; b expand
    i_try1080 = len(words)
    E(0x52800011); E(0x72a890f1); E(0x1e270227)                           # s7 = 1080
    E(0x1e2738d1); E(0x1e20c231); E(0x1e2e1010); E(0x1e302220)
    i_ge1080 = len(words); E(0)
    E(0xb9404a11); E(0x1e220227)                                         # s7 = (float)output
    i_expand = len(words)
    E(0x1e212810); E(0x1e2c1011); E(0x1e310a10); E(0x1e3108e7)           # centre, half
    E(0x1e272a00); E(0x1e273a01)                                         # top/bottom
    i_orig = len(words); E(_ortho_orig)
    i_back = len(words); E(0)
    words[0] = ADRP(16, start, STATE)
    tbz(i_tbz, i_orig)
    cond(i_r0, i_orig, 0); cond(i_l0, i_orig, 0)
    cond(i_ge720, i_try1080, 0xa); b_to(i_do, i_expand)
    cond(i_ge1080, i_orig, 0xa)
    words[i_back] = B(start + i_back * 4, _ortho_at + 4)
    for w in words: emit(w)
    put(_ortho_at, [B(_ortho_at, start)], 'SetOrthography: 720/1080 T/B span → layout/output height, L/R kept (bit 15)')


FRAME_STEP = {
    'fad4615a54dcc997b07a7be8588505dd': screen_shape,   # v262144 main
}

# How general each patch is and could be (dm/tools/docs_patches.py "Binding", listed in docs/agents/game-patches.md): what, its binding now, the loosest it could have (goal),
# purpose, why; blocked or kept: why the gap stays open
BINDING = [
    {'what': 'screen shape: the render, display-mode, window (swap chain / crop), render-target, layout sizes, UI anchors, Bezel Hor+ fovy + perspective aspect and SetOrthography T/B expand (DM_SCREEN_ASPECT)', 'now': 'build', 'goal': 'unreviewed',
     'purpose': 'rendering',
     'why': "found at bring-up from the Bezel engine's 1920x1080 / 1280x720 constants, Camera::SetProjectionPerspectiveFovy (Hor+ fovy) and SetOrthography (Hor+ 2D T/B) in this build; whether a Bezel engine rule (Big Brain Academy shares the engine) could carry it is not judged yet"},
]
