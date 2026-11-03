# Mesa (grate) patches

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
