# Mesa (grate) patches

Patch [0020-grate-honor-draw-scissor-rectangles.patch](0020-grate-honor-draw-scissor-rectangles.patch)
fixes ignored draw scissoring, used by Phoc for window damage clipping. A
180-case imported-buffer/scanout alpha diagnostic improves from 120 failures
on 0019 to zero on 0020. Phoc is confirmed to use 0020 after login. The reported
coloured window border was separately identified as Phoc's focus frame and
disabled with `gsettings set mobi.phosh.phoc focus-frame false`.
Hardware results and rollback.

Patch [0021-grate-trace-how-long-GPU-waits-block-and-why.patch](0021-grate-trace-how-long-GPU-waits-block-and-why.patch)
is trace-only (no effect unless `GRATE_DRM_TRACE` is set): it logs every fence wait with its caller (queue drain, buffer
wait, job wait) and how long it blocked, the pending job count at each drain, and a marker per context flush. Built to find out
whether Phosh stalls on the GPU at every flush (0018) and for how long. Built and installed for the next login; results pending.

Patch [0023-grate-sample-texture-coordinates-computed-by-the-shader.patch](0023-grate-sample-texture-coordinates-computed-by-the-shader.patch)
lets `texture2D` take a coordinate the shader computed (Tabula's wallpaper remaps `0.5*v+0.5`), which used to abort in
`emit_TEX`. Per-pixel values did not survive in the global registers or R4 and up between instructions once the program had a
texture fetch (constants and uniforms did; cause unknown), so temporaries feeding the coordinate live in R0-R3. The Tabula-shaped
test `tools/gpu/grate-texture-affine-coord-test.c` goes from an abort to 0/1024 bad pixels; the other fragment/texture tests are
unchanged. Limit: values that must outlive the fetch cannot be allocated (`no row register survives to the texture fetch`).
The register experiments and open bugs are in docs/grate-fragment-registers.md.

Patch [0026-grate-expose-Z24S8-and-Z24X8-depth-buffers-as-Z16NL-plus-an-S8-stencil-plane.patch](0026-grate-expose-Z24S8-and-Z24X8-depth-buffers-as-Z16NL-plus-an-S8-stencil-plane.patch)
offers d24 and d24/s8 EGL configs the way the Windows driver does D24S8: 16-bit non-linear depth (surface format Z16NL, slot 0) plus a
separate S8 plane (slot 2) after it in the same buffer, with the stencil test/ops/reference programmed and separate clears for the planes.
Tested on the tablet 2026-11-05: `grate-depth-probe 24` reports `GL_DEPTH_BITS` 24, the control draw passes and the curve is the Z16NL
one (coarser than Z16 near z=1); `tools/gpu/grate-stencil-test.c` (clear value, REPLACE, INCR, write mask, two-sided, depth-only clear,
zfail) passes all cases; the cube regression gives the same faces as before (5 with nodepth/always, 3 with GL_LESS). Epitaph, Tabula and
Tzompantli (stock Alpine builds, without their former no-depth-stencil patches) start and draw on it. Limits: no sampling of Z24 textures; stencil is dropped with more than one
colour buffer; `glColorMask` is still ignored by the driver (a stencil-only pass paints colour too).

Patches 0027-0030 (2026-11-05) are on top of 0026 and are what made Epitaph's panel text and icons render (dual-source blending).

Patch [0027-grate-keep-values-alive-across-fetches-add-SNE-and-RCP-drop-dead-code.patch](0027-grate-keep-values-alive-across-fetches-add-SNE-and-RCP-drop-dead-code.patch)
fixes the fragment compiler, found with a ladder of small shaders around a texture fetch: a varying read after a fetch (tile-constant garbage), SNE, RCP through
the SFU, a TEX coordinate copy and dead code. It also settles why global registers looked broken: R4 and up and the globals are storage of four lanes shared by every pixel in
flight, so a program that needs one runs with `MAX_OUT 4` (about 25x slower per pixel, only that program). The earlier "MAX_OUT <= 8 is enough" was measured with flat values and
is wrong.

Patch [0028-grate-blend-with-any-factor-pair-and-equation-and-honour-the-colormask.patch](0028-grate-blend-with-any-factor-pair-and-equation-and-honour-the-colormask.patch)
generates the blend epilogue from the blend state (`fp/blend.c`, table driven; the top of the file says how to add a factor or an equation): ADD, SUBTRACT, REVERSE_SUBTRACT,
ten factors, separate rgb and alpha, and the colormask (also with blending off). 318 of 318 cases match a CPU reference. Not yet: constant colour factors, SRC_ALPHA_SATURATE, MIN/MAX,
logic ops.

Patch [0029-grate-dual-source-blending-in-two-passes.patch](0029-grate-dual-source-blending-in-two-passes.patch)
implements `GL_EXT_blend_func_extended`. The epilogue cannot hold src0, src1 and the destination at once, so a draw is split into up to two single-source blend passes
(`dst * Fd`, then `+ src0 * Fs`), exact for non-overlapping fragments such as text. Epitaph's text shader renders exactly in both glyph paths and the pulled-down panel shows its text and
icons on the tablet. Measured (1024x1024 draw): plain texture 9.7 ms, blended 16 ms, dual source 339 ms.

Patch [0030-grate-format-the-lines-added-since-the-fork-to-the-Mesa-style.patch](0030-grate-format-the-lines-added-since-the-fork-to-the-Mesa-style.patch)
wraps the lines added by the earlier patches to 78 columns in the Mesa style (formatting only; `drm/` keeps its libdrm style).

Patches 0031-0033 (2026-11-06) are on top of 0030 and come from running Firefox ESR (WebRender) on the tablet, which aborted on instructions the fragment
compiler did not know. A test program checks 21 expressions against libm on the tablet, all within 1/255.

Patch [0031-grate-compile-POW-EX2-LG2-RSQ-and-SQRT-in-the-fragment-shader.patch](0031-grate-compile-POW-EX2-LG2-RSQ-and-SQRT-in-the-fragment-shader.patch)
gives the fragment compiler the scalar SFU ops: RCP, RSQ, SQRT and LG2 are one op each, EX2 is PREEX2 then EX2 on the row PREEX2 wrote, POW is
EX2(PREEX2(y * LG2(x))) with y in a row as the second factor of the LG2 multiplier. Firefox aborted on `TGSI_OPCODE_POW` before.

Patch [0032-grate-skip-draws-while-no-vertex-or-fragment-shader-is-bound.patch](0032-grate-skip-draws-while-no-vertex-or-fragment-shader-is-bound.patch)
skips a draw while no vertex or fragment shader is bound. A program the compilers refuse is never created, the state tracker binds nothing, and the next
draw dereferenced the NULL pointer: Firefox's compositor died with a SIGSEGV and no message as soon as one WebRender shader was too big.

Patch [0033-grate-compile-LRP-DP2-DP3-DP4-and-MIN-and-refuse-what-is-not-known.patch](0033-grate-compile-LRP-DP2-DP3-DP4-and-MIN-and-refuse-what-is-not-known.patch)
adds LRP (GLSL `mix()`, in the vertex compiler too, because Mesa moves `mix()` of varyings there), DP2/DP3/DP4 and MIN to the fragment compiler, and makes both
compilers refuse an instruction they do not know instead of calling `assert()`: the opcode is printed, the shader is not created and its draws are skipped
(0032). Still refused: loops (BGNLOOP/IF/BRK), FRC and FLR (the SFU FRC op returned its operand unchanged), DP4 of a varying, LRP/DP of two different varyings, and
shaders that run out of registers. Firefox's compositor can still die silently some seconds after start; the cause is not found yet.

Against [`github.com/external-mirrors/libre-tegra-mesa`](https://github.com/external-mirrors/libre-tegra-mesa),
branch `grate-26.2.3` — a current mirror of `codeberg.org/libre-tegra/mesa` (which 404s;
the longer research notes are kept in a private repo). Not a
clone of the kernel this repo's other patches target; this is Mesa, a separate project,
kept here only for a written record.

| Patch | What |
|---|---|
| [`0001-grate_bo-port-dmabuf-RDWR-and-size-overflow-fixes.patch`](0001-grate_bo-port-dmabuf-RDWR-and-size-overflow-fixes.patch) | Hand-ported from [`grate-surface-rt-48283c9.patch`](https://github.com/grate-driver/mesa/issues/19) (which doesn't apply here: it targets `drm/tegra.c`, a standalone libdrm-style wrapper that this branch has since folded into `grate_bo.c` with different function names and Mesa's own logging). Same two fixes, re-landed against the current code: `DRM_RDWR` on the exported dmabuf fd (needed for CPU access to an imported scanout buffer — cursor updates, clears), and a 64-bit-to-`uint32_t` overflow check on the imported size (this file's `off_t` already avoided the original's `SEEK_CUR`-on-a-DMA-BUF bug, so only the overflow half needed porting). |
| [`0002-grate-drm-use-the-classic-Tegra-DRM-ioctls.patch`](0002-grate-drm-use-the-classic-Tegra-DRM-ioctls.patch) | Translation layer in the driver's own `drm/` directory: maps its new-style Tegra DRM calls (channel open, mappings, syncpoints, submit) onto the classic ioctls the libre-tegra grate kernel exposes. New `drm/tegra_classic.h`; changes `channel.c`, `job.c`, `syncpt.c`, `tegra.h` and one call in `grate_stream.c`. Adds optional tracing (`GRATE_DRM_TRACE`, `GRATE_DRM_WAIT`). Result on the Surface (2026-10-31): channel opens, the 2D clear passes and a 3D triangle without shader constants is drawn pixel-exact; shaders with constants fail because the driver does not support them (not part of this patch); details in the private research notes. |
| [`0003-grate-support-immediates-in-the-shader-compilers.patch`](0003-grate-support-immediates-in-the-shader-compilers.patch) | Immediates in the shader compilers. Vertex program: the immediates are recorded and uploaded with the uniforms (immediates in the first constant slots, uniforms after them, one block from slot 0). Fragment program: immediates of 0.0 and 1.0 work, other values and uniforms print a message instead of reading an undefined register; also fixes a write through an empty list head for fragment shaders with no interpolated input. Result: triangles with constants in the shaders and the cube without depth now render correctly on the Surface. Applies on top of 0002 (touches `grate_state.c` and `grate_compiler.h`, not the files 0002 changes). |

Patch [`0004-grate-reserve-render-target-zero-for-depth.patch`](0004-grate-reserve-render-target-zero-for-depth.patch)
applies after 0003. It reserves hardware surface 0 for depth, maps colour attachment/output
`i` to surface `i + 1` in both framebuffer setup and fragment stores, emits only populated
surfaces, and sets the separate DW depth-enable bit when depth testing is active with a
depth attachment. Patch application, whitespace checks and the armv7 incremental build passed.
On the Surface RT (2026-11-02), the clear, constant-colour triangle, and cube
with `nodepth`, `always`, and default depth testing all passed using Grate/Tegra.
The depth-tested cube shows three faces and zero unmatched pixels; the other
two show five faces and zero unmatched pixels.
Logs retain the results.
Expected target-enable masks for one colour attachment: `0x2` without depth, `0x10003`
with a depth attachment and depth testing enabled (including `GL_ALWAYS`).

Patch [`0005-grate-invalidate-framebuffer-depth-cache-before-draws.patch`](0005-grate-invalidate-framebuffer-depth-cache-before-draws.patch)
adds the missing FDC cache invalidation bit before each draw. Mesa clears colour
and depth through gr2d; gr3d must invalidate cached framebuffer/depth contents.
Repeated rotating-cube captures show the horizontal streaks disappearing, with
or without forced submission waits. Static clear, triangle and all three cube
variants pass. Isolated pixel differences remain, so this is a partial rendering
fix, not complete depth/raster validation. Applies after 0004; armv7 build and
reverse patch application checks pass. Validation.

Patch [`0006-grate-complete-draws-before-releasing-jobs.patch`](0006-grate-complete-draws-before-releasing-jobs.patch)
waits for draw completion inside the driver. Draw jobs were released without
resource-fence tracking, allowing CPU readback and gr2d clears to race a draw.
This is a synchronous correctness fallback with a performance cost. A longer
720-frame rotation exposed a missing-face frame after 0005 alone; 0006 avoids
that event without `GRATE_DRM_WAIT`. Static regression checks pass.

Patch [`0007-grate-assign-alternating-raster-swaths-on-Tegra30.patch`](0007-grate-assign-alternating-raster-swaths-on-Tegra30.patch)
configures alternating horizontal raster swaths separately for Tegra30's two
pixel pipelines, following libgrate. With 0005–0006 applied, three 720-frame
rotations show zero interior wrong-colour pixels, versus 121 over 720 frames
with 0006 alone. Two repeated captures have identical RGB comparison counts.
Clear, triangle and nodepth/GL_ALWAYS/GL_LESS static cubes pass. Edge pixels
still differ from llvmpipe. Armv7 builds and reverse-application checks pass.
Logs, captured frames and comparison method.
The isolated hardware build is `~/mesa-swath`.

Not ported (out of scope so far, not tried): the premultiplied-blend fragment-shader logic
in `grate_state.c`, the biggest and roughest part of the original patch against this
branch (7 of 12 hunks fail even with fuzz).

Builds clean (native x86_64 meson smoke test, 1018/1018 targets, zero warnings). An earlier
version of this note claimed a separate, more serious gap (shader binding unimplemented on
this branch) — that was a misread, retracted in
the private research notes. Patch 0001 alone was not cross-compiled or run; with 0002 the armv7 build runs on the Surface (see
the private research notes).


Candidate [0008-grate-compile-fragment-MUL-and-dependent-ALU.patch](0008-grate-compile-fragment-MUL-and-dependent-ALU.patch)
retains the in-progress fragment MUL compiler and scheduling corrections after
0007. Ten readback cases passed on the preceding hardware candidate; final
cleanup and an added perspective case still need final hardware validation.
Weston headless GL passes its original MUL failure, then encounters unsupported
fragment uniforms and a resource-format assertion. It is not a working desktop.
See the Weston handoff
for the exact scope, remaining checks and remote locations.

Patch [0009-grate-handle-RGBA-texture-storage-and-format-rejection.patch](0009-grate-handle-RGBA-texture-storage-and-format-rejection.patch)
applies after 0008. Identifies Weston's failing request as a sampler-only
`PIPE_FORMAT_R8G8B8A8_UNORM` 1x1 resource (`bind=0x8`), adds RGBA/X storage,
and rejects unmapped non-buffer formats during capability queries. Allocation
and import now report unsupported formats rather than asserting, and release
resources on failure. Removes an incorrect RGBA32F-to-RGBA16F storage alias.
RGBA render-target/scanout support remains disabled: advertising it selected an
incomplete GPU conversion path and broke readback regressions.

ARM build, Tegra texture uploads (RGBA, RGB, alpha, luminance, luminance-alpha),
clear, triangle and the installed ten-case fragment suite pass. Headless Weston
runs for a bounded ten-second test without the format assertion, then receives
SIGTERM from timeout; fragment uniform/link errors remain. This validates
storage/upload only, not texture sampling or an accelerated desktop.
Isolated bundle: `~/mesa-formats`; the normal launcher default is unchanged.
Logs and limitations.

Patch [0010-grate-add-initial-2D-texture-sampling.patch](0010-grate-add-initial-2D-texture-sampling.patch)
adds the initial base-level 2D sampler path. The nearest RGBA sample test passes
all pixels, and a depth-tested textured cube renders on Tegra, including the
user-supplied Shrek texture. The user confirmed the viewer works.
Scope and captures.

Patch [0011-grate-upload-fragment-uniforms-and-immediates.patch](0011-grate-upload-fragment-uniforms-and-immediates.patch)
adds scalar constant allocation, per-draw FP20 upload and correct uniform-buffer
size reporting. Ten full-image uniform/immediate tests and rendering regressions
pass on Tegra; the software reference passes too. Headless Weston now reaches
unsupported fragment `SLT` (0x0e), beyond the former uniform errors. It still
aborts and is not a working desktop. Evidence.

Patch [0012-grate-compile-fragment-comparisons-and-selection.patch](0012-grate-compile-fragment-comparisons-and-selection.patch)
corrects/encodes ALU conditions and adds SLT, SGE, SEQ, CMP and ADD. Thirteen
full-image tests pass in three Tegra runs and on llvmpipe, including equality
boundaries, varying inputs, selection, masks and spatial thresholds. Rendering
regressions pass. Weston proceeds from the SLT abort to the two-vec4 temporary
limit; register allocation remains necessary. Isolated build: `~/mesa-compare`.
Evidence and limits.

Patch [0013-grate-allocate-fragment-scalars-and-defer-colour-stores.patch](0013-grate-allocate-fragment-scalars-and-defer-colour-stores.patch)
adds component liveness, bounded scalar allocation, packed sampled-colour storage
and deferred final colour stores. The five-temporary channel-selection shader
passes 24 full-image cases in three consecutive Tegra runs and on llvmpipe;
existing rendering/shader regressions pass. Weston compiles that shader and
next aborts on padded texture pitch. This is not yet a working compositor.
Isolated build: `~/mesa-registers`. Validation and limits.

Patch [0014-grate-sample-padded-single-row-textures.patch](0014-grate-sample-padded-single-row-textures.patch)
accepts padding for single-row textures directly, fixes texture channel formats
and XRGB alpha, and removes incorrect blit-upload capability reporting. Thirty
native DMA-BUF pixel cases pass three times, including updates and GPU clears;
shader/rendering regressions pass. Headless Weston survives the 15-second test
and launches its shell. This is not physical-desktop validation, and arbitrary
multi-row padding remains unsupported. Isolated build: `~/mesa-pitch`.
Evidence and documentation review.

Patch [0015-grate-use-native-texture-strides-and-upright-scanout.patch](0015-grate-use-native-texture-strides-and-upright-scanout.patch)
uses native 64-byte NPOT rows for sampled allocations and selects the matching
descriptor mode. It also omits BOTTOM_UP on scanout buffers, correcting the
physical desktop orientation confirmed by the user. Twenty-one multi-row cases
pass three times; scanout flags and rendering regressions pass.
Evidence and scope.

Patch [0016-grate-blend-premultiplied-source-over-in-fragment-stage.patch](0016-grate-blend-premultiplied-source-over-in-fragment-stage.patch)
implements Weston's premultiplied source-over blend mode through framebuffer
fetch and a final GPU ALU stage. Nine pixel tests pass three times, including
textured transparent borders; regressions pass. Native Weston is running with
~/mesa-blend; the user confirmed correct transparency, terminal rendering,
overlapping/fullscreen windows, movement, resizing and redraws. Other blend
modes remain unsupported.
Evidence and limitations.

Patch [0017-grate-reuse-the-classic-command-staging-buffer.patch](0017-grate-reuse-the-classic-command-staging-buffer.patch)
reuses the classic submit staging GEM buffer per channel. Isolated timings did
not show a clear speedup; it removes repeated allocation/mapping overhead.

Patch [0018-grate-track-buffer-uses-and-queue-draws.patch](0018-grate-track-buffer-uses-and-queue-draws.patch)
replaces 0006's per-draw wait with BO last-use fences and retained references.
Maps, cross-channel use, exports, flush and teardown synchronize work, and a
128-submit limit bounds the queue. Context flush remains synchronous.

Patch [0019-grate-keep-varying-products-in-pixel-registers.patch](0019-grate-keep-varying-products-in-pixel-registers.patch)
keeps final single-input fetches in pixel rows and streams direct two-varying
products without persistent global-register scratch. The original perspective
test changes from 821 bad pixels to zero; affine, separate varying and swizzled
gradient cases also pass, with the same tolerance. The 32×32 draw benchmark
median improves from 326 to 150 ms per 1,000 draws. These patches are active
through a per-user Phosh override; the image archive remains at 0016. General
multi-input temporary allocation is still incomplete.
Results, rollback and failed experiment.

Patch [0034-grate-use-the-register-rows-like-NVIDIA-s-compiler-n.patch](0034-grate-use-the-register-rows-like-NVIDIA-s-compiler-n.patch)
(2026-11-07, on top of 0033) replaces the guessed handling of registers R4 and up and the globals 16-23, which had turned into a `MAX_OUT 4` rule
(about six times slower for every program that touched them). The hardware keeps those registers per pixel when the program declares how many
register rows it uses (`GLOBAL_PIX_ATTR.NUM_ROWS`, `MAX_QID` from the row count), which NVIDIA's driver does and ours did not. The patch follows what
NVIDIA's compiler produces for the same GLSL (compiled on the tablet with the Android userland and replayed on this driver): R4-R11 for overflow
temporaries, the step layout of a multi-row program (whole rounds, unit steps on multiples of the row count, output write on the first step of the last
round, a bubble packet between dependent steps), no scratch registers in the output stage, the SFU in place on R0-R3 (one op per step) and a blend stage
that fits the layout. Shaders the compiler used to refuse now compile.

Checked against a CPU model of eight test shaders (worst error 1/255 also at 1024×768), against NVIDIA's compiled programs (30000 of 30000 pixels identical)
and by running 21 self-checking tests with the previous and the new driver (identical output). Full-screen fill at 1024×768, Mpixel/s before → after:
texture 90 → 140, texture with a coordinate transform 71 → 97, ALU-heavy shader 3.4 → 29, dual-source text 1.7 → 15.5.

Known gaps, not done yet: NVIDIA's container link record (the fragment-input lane map) is not parsed and only a single `vec2` varying was compared; a
program that needs more registers than R4–R15 is refused (no spill buffer); NVIDIA's streams can only be replayed for programs without uniforms, so uniform
handling is checked against the CPU model and the old driver only; ALU immediates are not used; patches 0001–0033 were written without this knowledge and
their descriptions (0024 scratch registers, 0027 "global registers are four lanes", 0031 SFU through the multipliers) are superseded; no compositor-level run
(Weston, Phosh, Firefox) of the new driver yet.

Patches 0035-0037 (2026-11-07/08) come from running a Qt 6 / Material application on the tablet:

* [0035-grate-compile-MIN-SNE-DP2-and-CMP-in-the-vertex-prog.patch](0035-grate-compile-MIN-SNE-DP2-and-CMP-in-the-vertex-prog.patch): the vertex compiler refused MIN, SNE, DP2 and CMP.
* [0036-grate-select-with-condition-flags-for-CMP-in-the-vertex-program.patch](0036-grate-select-with-condition-flags-for-CMP-in-the-vertex-program.patch):
  0035 built CMP as a blend, which is wrong for very different values and NaN for infinity (visible as glitches). NVIDIA's compiler has no CMP: it sets per-lane
  condition flags and predicates a write on them; 0036 does the same. Checked against the layout NVIDIA's compiler produced and with 15 test cases.
* [0037-grate-sample-the-base-level-of-mipmapped-textures.patch](0037-grate-sample-the-base-level-of-mipmapped-textures.patch): a texture with a mipmap filter aborted the
  application. The driver has memory for one level only, so it samples level 0; writes to higher levels went over level 0 and now go to scratch memory, and
  `resource_copy_region` copies level 0 (it did nothing, which emptied textures that Mesa reallocates to add mipmap levels). Real mipmap levels are not implemented.

Patch [0038](0038-grate-spill-fragment-temporaries-to-surface-4.patch)
adds scalar register spilling using NVIDIA's surface-4 ST_R20/LD_R20
sequence and makes all four register rows available. Register exhaustion
retries allocation with spill backing instead of refusing the shader.
Automatic-spill tests pass at 200x150 and 1024x768 within 1/255, including
source-over blending; 24 regression tests pass with one expected 3D-texture
skip. Programs must still fit one 64-step epoch; predicate spilling and
NVIDIA's vector-spill instructions remain unsupported. This patch has not
been validated in a compositor session or installed in the system bundle.

Patches 0039-0041 (2026-11-09) follow NVIDIA's fragment compiler:
* [0039](0039-grate-implement-fragment-floor-and-fract-with-the-SFU.patch):
  `fract` uses SFU FRC on FP20; `floor` subtracts that fraction from the
  original. Six fixtures pass CPU checks at 200x150 and 1024x768.
* [0040](0040-grate-unroll-bounded-shader-loops.patch): enable NIR's
  32-iteration unroll budget; bounded loops and conditional breaks become
  straight-line selections. Runtime-count loops remain unsupported.
* [0041](0041-grate-preserve-FP20-comparisons-feeding-fragment-selections.patch):
  keep scalar comparisons feeding selections in FP20, following NVIDIA's
  difference/sign sequence. Fixes a two-column branch-threshold error;
  the texture-selection fixture matches all 786432 pixels exactly.
The existing GPU suite passes 24 tests with one expected 3D texture skip.
These patches have not been validated in a compositor or bundled image.

Step 3 (2026-11-09), patches 0042–0043, applies after 0041:
* [0042](0042-grate-split-oversized-draws-and-use-indexed-fan-and-loop-pivots.patch):
  split large draws while preserving topology, skip empty draws, and use
  the first index value for indexed fan/loop pivots, following NVIDIA.
  All 392 draw cases pass at 200x150 and 1024x768.
* [0043](0043-grate-store-and-sample-linear-mip-chains-without-texture-aborts.patch):
  store and sample real mip levels, handle mirrored repeat, and repack
  non-native imported strides without aborting. NVIDIA instruction replay
  matches 63 resource cases and 328 sampler descriptors; Tegra passes
  219 mipmap cases and all nine wrap combinations.
The full suite has 27 successful tests and one expected 3D texture skip;
interleaved benchmarks show no material slowdown. These changes have not
been installed or added to the image bundle.

Step 4, patch [0044](0044-grate-raise-logical-fragment-uniform-limit-with-safe-bank-exhaustion.patch) (after 0043):
fragment uniform compaction and logical limits.
It raises the logical fragment uniform limit to 256 floats (64 vec4),
preserves uploads of only referenced components, and refuses physical-bank
exhaustion without aborting. The 32 scalar FP20 slots still share uniforms
and immediates. Exact Qt and sparse fixtures were checked against NVIDIA's
compiler and Tegra pixel results; the system library is unchanged.

Step 5, patch [0045](0045-grate-compile-DDX-and-DDY-in-the-fragment-program.patch) (after 0044):
`dFdx`, `dFdy` and `fwidth`. Values are exchanged inside the 2x2 pixel quad through the write port r32 and read back as
r32/r40/r48/r56 (top left, top right, bottom left, bottom right); the derivatives are coarse, `r40 - r32` and `r48 - r32`.
Constant slots 0, 8, 16 and 24 are left free for programs with derivatives, which also get three register rows, and the
result scale field is packed now. Checked with a self-checking test (4 tests, worst error 1/255) and 24 other
self-checking tests, which are unchanged.

Patch [0046](0046-grate-clear-the-PSEQ-command-slots-through-the-even-.patch) (after 0045): the per-draw clear of the sequencer command slots writes the 16 even slots with one
single-word packet each, not 32 words over `0x520..0x53f`. Needed by kernel patch 0031: once the odd slots are address registers of the Grate command
stream patcher, every word written to them is a relocation descriptor, and the zeros of the old clear would be patched with the address of buffer 0.

Patch [0047](0047-grate-run-fragment-programs-of-more-than-one-epoch-t.patch) (after 0046): the driver half of NVIDIA's multi-epoch fragment programs. `grate_fp_info` gets an optional
`grate_fp_epochs` (program blocks, constant packets, instruction counts); `emit_epochs()` writes three sequencer command pairs per epoch (constant DMA, program DMA,
run), a closing pair and `PSEQ_PC`, and the pixel spill address once for every one of the two Tegra 30 pixel pipes (`GSHIM_WRITE_MASK` 1, 2, then 3), as NVIDIA's
driver does. One address broadcast to both pipes made them overwrite each other's spilled pixels: 100 to 480 of 1024 pixels of a draw were never written and a
second draw hung the job. Needs kernel patch 0031.

Patch [0048](0048-grate-split-fragment-programs-that-read-more-than-32.patch) (after 0047): the compiler half. A program that reads more than 32 distinct constants is cut into at most five epochs at round
borders (32 constants, 64 steps, 61 ALU and MFU instructions each), the constants of each epoch take the bank slots from 0, and the blocks are written like NVIDIA's.
Refused with the reason in the message: derivatives, register spills, a round that does not fit, more than five epochs (about 90 scalars). Checked on the tablet with
sums of 33, 48 and 80 uniform floats and NVIDIA's d12t shader shape (every pixel correct, three draws in a row, 32x32 and 64x64) and 21 other self-checking tests.
Not done: blending of a split program, chaining beyond five epochs.

Patch [0049](0049-grate-name-the-unimplemented-TGSI-opcode-and-texture.patch) (after 0048): the unimplemented-opcode message names the TGSI opcode (`0x0d MAX`), and a `TEX` on anything but a
2D texture (a cube map) refuses the shader with `TEX on CUBE (only 2D)` instead of aborting the process. The next two missing features for three.js are `max()` and cube
map sampling.

Patch [0050](0050-grate-implement-fragment-max.patch) (after 0049): `max()` (TGSI `MAX`, 0x0d) in the fragment compiler, the ALU op MAX next to MIN with the second value in the third source. Checked against a CPU model (six new cases in `grate-frag-compare-test`) and against NVIDIA's compiler, which emits ALU op 2 with the same operand layout as `min()`.

Patch [0051](0051-grate-compile-SQRT-and-SEQ-in-the-vertex-program.patch) (independent of 0050): `SQRT` in the vertex program as `RCP(RSQ(x))` per lane through a temporary, and `SEQ` as the vector op, both as NVIDIA's vertex compiler emits them. Seven new cases in `grate-vertex-ops-test`.

Patch [0053](0053-grate-leave-SFU-results-fetch-results-and-SFU-operan.patch) (after 0052): the fragment compiler stops copying every value into a register of its own. An SFU result of one channel stays in the SFU's row register, a fetch result stays in the R2/R3 half it lands in, and the SFU operand is written by its producer step straight into the SFU row; with it come `forward_tex_coord` for temporaries, no copy for result channels that are never read, the step before a fetch writing R0/R1 itself, and a TGSI pass that moves a coordinate producer down to its fetch. The glmark2 bump-height shader went from 77 slot ops, 41 packets and 24 plain copies to 54, 32 and 13 (NVIDIA: 40 real ops, 13 packets, 1 copy). Checked with the self-checking suite (`run-grate-tests.sh`: same lines as without the patch), `grate-pow-test` 21/21 and `grate-texture-multi-fetch-test`. Dropping the load step also drops the `|x|` the RSQ operand copy applied, as in NVIDIA's output (inversesqrt of a negative value is undefined in GLSL); not yet compared against a fresh `cgtest` compile.

Patch [0054](0054-grate-put-the-blend-stage-in-the-last-epoch-fill-epo.patch) (after 0053, independent of it): the blend stage of a fragment program of more than one epoch goes into the last epoch, as NVIDIA's `libcgdrv` does (measured on a 160-op shader: the other epochs untouched, the blend the last step of the last epoch); before, such a program was refused for blending (avio-qt's rounded album picture). An epoch now holds up to 64 ALU packets (NVIDIA's measured fill), `GRATE_PACKING_DEBUG` prints slot operations, plain copies and packets per program. Test (private repo): `tools/gpu/grate-blend-epoch-test.c` (80 packets, 3 epochs, 2 pass / 5 fail before, 7/7 after).

Patch [0055](0055-grate-compile-FLR-in-the-vertex-program-and-SSG-in-t.patch) (after 0054, independent of it): the two ops the Plasma lockscreen logged as unimplemented. Vertex TGSI `0x1a` is `FLR`: the vector op 15, one instruction like `MOV`, as NVIDIA's compiler emits `floor()` (operand in slot A, `ar20vp-dump.py`). Fragment `SSG` (`sign()`) is lowered before packing to `SLT(0, x) - SLT(x, 0)`; NVIDIA builds it from condition flags in two steps and three packets, which is not decoded yet, so ours is longer (two scratch temporaries) but uses only checked ops. Tests: three `floor` cases in `tools/gpu/grate-vertex-ops-test.c` (25/25) and three `sign` cases in `tools/gpu/grate-frag-compare-test.c` (22/22). On the tablet the lockscreen keypad arrow and backspace buttons draw correctly and the journal has no more `0x1a` or `SSG` refusals.
