# Mesa (grate) patches

Against [`github.com/external-mirrors/libre-tegra-mesa`](https://github.com/external-mirrors/libre-tegra-mesa),
branch `grate-26.2.3` — a current mirror of `codeberg.org/libre-tegra/mesa` (which 404s;
see [docs/3d-acceleration.md](../../docs/3d-acceleration.md) for that whole story). Not a
clone of the kernel this repo's other patches target; this is Mesa, a separate project,
kept here only for a written record.

| Patch | What |
|---|---|
| [`0001-grate_bo-port-dmabuf-RDWR-and-size-overflow-fixes.patch`](0001-grate_bo-port-dmabuf-RDWR-and-size-overflow-fixes.patch) | Hand-ported from [`grate-surface-rt-48283c9.patch`](https://github.com/grate-driver/mesa/issues/19) (which doesn't apply here: it targets `drm/tegra.c`, a standalone libdrm-style wrapper that this branch has since folded into `grate_bo.c` with different function names and Mesa's own logging). Same two fixes, re-landed against the current code: `DRM_RDWR` on the exported dmabuf fd (needed for CPU access to an imported scanout buffer — cursor updates, clears), and a 64-bit-to-`uint32_t` overflow check on the imported size (this file's `off_t` already avoided the original's `SEEK_CUR`-on-a-DMA-BUF bug, so only the overflow half needed porting). |

Not ported (out of scope so far, not tried): the premultiplied-blend fragment-shader logic
in `grate_state.c`, the biggest and roughest part of the original patch against this
branch (7 of 12 hunks fail even with fuzz).

Builds clean (native x86_64 meson smoke test, 1018/1018 targets, zero warnings) — see
[docs/3d-acceleration.md](../../docs/3d-acceleration.md) for that and for a separate,
more serious gap found independent of this patch (shader binding is unimplemented on this
branch). Not cross-compiled for armv7 or run on hardware.
