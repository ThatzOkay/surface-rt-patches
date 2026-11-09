# Microsoft Surface RT (Tegra 3): kernel, Mesa and userspace patches

Patches, a reference devicetree and one extraction script for running Linux
(postmarketOS) on a Microsoft Surface RT (Tegra 3 / T30), booted from a microSD card over APX
(Fusée Gelée) so the Windows RT install on the eMMC is never touched. The longer notes, test tools
and measurement data live in a private working repo; this one holds only what is useful to apply.

Kernel target: [libre-tegra/linux](https://codeberg.org/libre-tegra/linux) `v7.0.1-stable`
(commit `bfffc6d6656e87f3de3aa4c09d852849081ef088`), the tree postmarketOS ships as
`linux-postmarketos-grate`. Userspace: Grate Mesa 26.2.6.

## Status

Measured on one device, 2026-10-29 to 2026-11-05.

| Area | State |
|---|---|
| Display, backlight, touchscreen, USB Ethernet | work |
| Cover keyboard | works with patch 0002 |
| Audio (speakers) | works with patch 0001 |
| Wi-Fi (Marvell 88W8797) | works with NetworkManager after patch 0025 |
| Bluetooth | works alongside Wi-Fi (patches 0026–0028 and the combo firmware below); pairing and use of Bluetooth headphones confirmed |
| 3D (Grate Mesa, GLES 2.0) | works: Weston, Phosh and the Catacomb panel (Epitaph) run accelerated (Mesa patches 0001–0037). Blending covers any source/destination factor pair of ZERO, ONE and the (inverse) source/destination colour and alpha, the equations ADD, SUBTRACT and REVERSE_SUBTRACT, separate RGB and alpha state and the colour mask; `GL_EXT_blend_func_extended` (dual-source) is drawn in two passes, which is what makes Epitaph's text and icons render. Limits: GLES 2.0 only (GTK4 and Firefox's WebRender need ES 3.0, so Firefox composites in software; WebGL 1 uses the GPU); maximum texture size 2048 (Epitaph's 4096 glyph atlas needs a one-line patch, not in this repo); register rows are declared like NVIDIA's compiler does (patch 0034): programs with many live values run at full speed (an ALU-heavy shader 3.4 → 29 Mpixel/s, a plain texture draw 90 → 140); constant-colour blend factors, SRC_ALPHA_SATURATE, MIN/MAX and logic ops are not supported; Phosh is still somewhat slow |
| Front camera | raw Bayer capture works (patches 0003–0022); the rear camera has never answered |
| H.264 decode, 2D engine | work for a subset, from userspace |
| Microphone (on-board digital) | not working; patches 0023 and 0024 are written, the mic does not appear in Phosh settings |
| HDMI output | works at 1920x1080@60 once GPIO PDD4 is driven high (confirmed at runtime with a userspace register write, with hotplug); patch 0029 does this from the devicetree and has not been booted yet |
| Light, motion and temperature sensors | enumerate over I2C/IIO; cover response untested |

## `patches/` (kernel)

Apply in numeric order with `patch -p1` to the kernel tree above.

| Patch | What |
|---|---|
| `0001-ASoC-wm8962-restore-SYSCLK_ENA-after-bclk-setup.patch` | Silent audio: a cold stream start clears the codec's `SYSCLK_ENA` bit and nothing set it again. |
| `0002-ARM-dts-tegra30-surface-rt-keep-vdd_cover-always-on.patch` | Cover keyboard: its supply rail was switched off before the cover could be detected. |
| `0023-ASoC-tegra_wm8962-do-not-dereference-a-missing-runtime-.patch` | Oops when unbinding the codec: the card's remove hook dereferenced a PCM runtime that is already gone. |
| `0024-ARM-dts-tegra30-surface-rt-configure-the-WM8962-GPIOs-.patch` | Digital microphone: codec GPIO configuration and the `Digital Mic` route. Not validated. |
| `0025-ARM-dts-tegra30-surface-rt-enable-WiFi-via-GPIO-D4.patch` | Wi-Fi power: PD4 as an output without tristate plus a fixed regulator as SDMMC3's `vmmc-supply`. |
| `0026-ARM-dts-tegra30-surface-rt-configure-Bluetooth-UARTC-pins.patch` | Bluetooth: UARTC TX/RX/RTS/CTS pinmux. |
| `0027-wifi-mwifiex-sdio-add-opt-in-legacy-scan.patch` | `mwifiex_sdio.force_legacy_scan=1`: needed for scanning with the combo firmware below. |
| `0028-ARM-dts-tegra30-surface-rt-hold-Bluetooth-PD1-active.patch` | Bluetooth: PD1 as a kernel-owned output-low GPIO hog. |
| `0029-ARM-dts-tegra30-surface-rt-enable-HDMI-via-GPIO-DD4.patch` | HDMI: PDD4 as a fixed regulator, the connector's `hdmi-pwr-supply`. Windows RT holds it high; with it low HPD stays low and DDC reads return zeros. Not yet booted. |

Sub-series:

- [`patches/camera/`](patches/camera/README.md): `0003`–`0022`, the OV9726 sensor driver and Tegra30 CSI/VI support ported to the grate host1x stack.
- [`patches/upstream-csi-v7/`](patches/upstream-csi-v7/README.md): unmodified copy of the upstream series the camera patches are ported from (Svyatoslav Ryhel, v7, linux-media 2026-03-03). All credit for that work is the original author's.
- [`patches/mesa/`](patches/mesa/README.md): `0001`–`0041` against `libre-tegra-mesa` (`0001`–`0019` were written on branch `grate-26.2.3`; `0001`–`0037` are also commits on `grate-26.2.6` of [ThatzOkay/libre-tegra-mesa](https://github.com/ThatzOkay/libre-tegra-mesa)).
- [`patches/gnome-session/`](patches/gnome-session/): two patches for the Phosh session (select GLES before the GTK probe; guard the X11 helper and empty EGL config results).

## Bluetooth/Wi-Fi combo firmware (not included)

Bluetooth needs the SDIO+UART combo firmware `14.62.17.p215` installed as
`/lib/firmware/mrvl/sd8797_uapsta.bin` (or `/usr/lib/firmware/updates/mrvl/`), together with patch
0027 (`mwifiex_sdio.force_legacy_scan=1`), PD1 held LOW (patch 0028) and an H4 attach at 3 Mbaud with
RTS/CTS. Booting the stock `p59` firmware instead (user test, 2026-11-03) left UART Bluetooth non-functional while Wi-Fi worked, so p215 is required for Bluetooth.

The image is Marvell/Microsoft firmware taken from the Surface RT Windows driver, and extracting it
does not give a redistribution licence, so it is **not in this repository**. Instead,
[`tools/bluetooth/extract-windows-uart-firmware.py`](tools/bluetooth/extract-windows-uart-firmware.py)
cuts it out of the driver you already have:

    python3 tools/bluetooth/extract-windows-uart-firmware.py mwls97w8arm.sys sd8797_uapsta.bin

- Input: `mwls97w8arm.sys` from the Windows RT 8.1 IR5 driver package
  (`Devices/Nvidia/SurfaceRT/Install/mwls97w8arm.inf_arm_*`), SHA256
  `ac47a0927099cffac55d51dbc91da32f848481f04987a8de5027548245a87fde`. Other versions are refused.
- Output: 434264 bytes (RVA `0xb2830`, size `0x6a058`), SHA256
  `97cc4df3d978db1485c3531c13749cc91d12eae7570c38edeabfd2dd9e6d8b74`, identity string
  `$Id: w8797-B0, RF878X, FP62_WIN7, 14.62.17.p215, BT_UART $`. The script verifies all of this and
  refuses to overwrite an existing file; it never installs anything.

## `tegra30-microsoft-surface-rt.dts`

The full Surface RT devicetree (`arch/arm/boot/dts/nvidia/tegra30-microsoft-surface-rt.dts`) with
the devicetree patches applied: 0002, 0024, 0025, 0026, 0028 and 0029 from this repository, plus
the digital-microphone clock patch (GPIO2 and the S3 hog, `0030`, not published here yet). It
compiles with `dtc` (only the usual `tegra30.dtsi` warnings). Use it to see the end result of the
devicetree patches or as a starting point; the patches remain the way to apply the changes.
