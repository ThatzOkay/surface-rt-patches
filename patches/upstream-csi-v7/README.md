# Upstream: tegra-video CSI support for Tegra20 and Tegra30, v7

The 15-patch series "[PATCH v7 00/15] tegra-video: add CSI support for Tegra20 and Tegra30"
(linux-media, 2026-03-03, by the author of the libre-tegra tree), unmodified, saved from
`https://lore.kernel.org/linux-media/20260303084239.15007-1-clamor95@gmail.com/`.

Checked on 2026-10-30: all 15 apply in order with `git am` to the files of the pinned kernel
(libre-tegra `v7.0.1-stable`, `bfffc6d6656e87f3de3aa4c09d852849081ef088`). Only the files the series
touches were checked, not a full build. They change no devicetree: the pinned `tegra30.dtsi` already
has `vi@54080000` with `csi@800` (`nvidia,tegra30-csi`).

Authorship is the original authors'; these are not part of this project's own patches. They are not
applied to the kernel recipe yet.
