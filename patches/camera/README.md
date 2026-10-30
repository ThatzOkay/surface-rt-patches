# Camera kernel patches (OV9726 on the Surface RT)

Apply in order, after `0001` (audio) and `0002` (cover keyboard) in `../`, to the pinned kernel
(libre-tegra `v7.0.1-stable`, `bfffc6d6656e87f3de3aa4c09d852849081ef088`). All 21 patches were
checked to apply in sequence with `patch -p1` to a fresh copy of that kernel with no fuzz, offsets or
rejects, and the resulting tree was compiled (see below). They are not yet booted on the device.

| Patch | What |
|---|---|
| `0003` | OV9726 V4L2 sensor driver and devicetree binding (new) |
| `0004` | Surface RT devicetree: 1.8 V camera supply and the sensor node |
| `0005`..`0019` | The upstream series "tegra-video: add CSI support for Tegra20 and Tegra30", v7, patches 1 to 15. Unmodified except patch 5 (`0009`), which converts the MIPI calibration code: it is ported to `drivers/gpu/host1x-grate/` and `drivers/gpu/drm/grate/dsi.c` because this kernel uses the grate host1x |
| `0020` | Lets the Tegra video driver build against the grate host1x (`host1x-compat.h`, Kconfig) |
| `0021` | Surface RT devicetree: enable `vi` and `csi`, link sensor to VI through CSI-A |

Kernel config: `CONFIG_VIDEO_TEGRA=m` and `CONFIG_VIDEO_OV9726=m` (the only two lines that change).

What was verified: the series applies; with the aport's config plus those two options, the camera
driver, the grate host1x directory and the grate DRM directory compile with no warnings; the
devicetree compiles. What was not: a full kernel build, booting it, or any video.

Known risks: the grate sync point wait is a polling loop on the hardware counter (the grate host1x
has no wait-on-threshold call); CSI-A is a guess for the sensor's port; the Bayer order, pixel rate
and link frequency in the sensor driver are unverified; changes in `0009` touch the shared MIPI
calibration code the display driver also uses (the DSI path, which this board does not use).
