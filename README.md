# Microsoft Surface RT (Tegra 3) — kernel and Mesa patches

Patches and a reference devicetree for running mainline-ish Linux on a Microsoft Surface RT
(Tegra 3 / T30), pulled out of a larger, mostly-private working repo. Kernel target is
[libre-tegra/linux](https://codeberg.org/libre-tegra/linux) `v7.0.1-stable`
(commit `bfffc6d6656e87f3de3aa4c09d852849081ef088`), the tree postmarketOS ships as
`linux-postmarketos-grate`.

## `patches/`

Apply in numeric order with `patch -p1` to the kernel tree above.

| Patch | What |
|---|---|
| `0001-ASoC-wm8962-restore-SYSCLK_ENA-after-bclk-setup.patch` | Fixes silent audio output: a cold stream start clears the WM8962 codec's `SYSCLK_ENA` bit and nothing sets it again, because mic-jack detection keeps the DAPM `SYSCLK` pin forced on. Verified on hardware by writing the register by hand; the patch itself was kernel-built, not yet booted. |
| `0002-ARM-dts-tegra30-surface-rt-keep-vdd_cover-always-on.patch` | Fixes the Type/Touch cover keyboard: its supply rail was only referenced by a child node created after the cover is detected, so the kernel switched it off before detection could ever happen. Verified on hardware. |

## `patches/camera/`

21 patches (`0003`–`0021`): a V4L2 driver for the on-board OmniVision OV9726 sensor (I2C
`0x10`), the upstream "tegra-video: add CSI support for Tegra20 and Tegra30" series ported to
the `grate` host1x stack this kernel uses (mainline `VIDEO_TEGRA` only supports the other,
mutually-exclusive host1x implementation), and the devicetree wiring to connect it. See
`patches/camera/README.md` for what's verified versus still guessed (e.g. which CSI port).
The sensor driver passed a self-test on real hardware (chip ID, full register table, stream
on/off); full video capture through CSI hasn't been tried yet.

## `patches/upstream-csi-v7/`

Unmodified copy of the upstream series `patches/camera/` is ported from — Svyatoslav Ryhel's
"tegra-video: add CSI support for Tegra20 and Tegra30", v7, posted to linux-media
2026-03-03. Kept here for reference; all credit for that work is the original author's.

## `patches/mesa/`

One patch so far, ported from a third party's work-in-progress Mesa `grate` (Gallium3D)
driver fix for this exact device
([grate-driver/mesa#19](https://github.com/grate-driver/mesa/issues/19)), re-landed against
a current mirror of the actively-developed driver branch. Builds clean; not yet proven to
render anything (a separate, unrelated gap — shader binding appears unimplemented on that
branch — would need solving first). See `patches/mesa/README.md`.

## `tegra30-microsoft-surface-rt.dts`

A reference devicetree. Differs from the pinned kernel's own copy in small ways (noted where
it matters in the patches above); kept here mainly for the camera and audio rail wiring
comments, which took some probing on real hardware to work out.
