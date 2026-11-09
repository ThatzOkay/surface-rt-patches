# ALSA UCM2 profile for the Surface RT's WM8962

Without a profile, PipeWire/WirePlumber falls back to `stereo-fallback`. Its only capture port is the headset jack
(`analog-input-mic`), which is "not available" while nothing is plugged in, so the built-in microphone shows as
"unplugged" in volume controls and `parecord` fails with `Stream error: No such entity`. This profile describes the real
card: speakers, headphones, the **always-available built-in microphone** (Input Mode = Digital, the PDM microphones that
patch 0030 clocks from the codec's GPIO2) and the headset microphone, which appears only while the jack reports one.

| File | What |
|---|---|
| `Tegra/wm8962/Surface-RT.conf` | verb list and `BootSequence` (speaker volume 110, digital capture gain 127, Input Mode Digital) |
| `Tegra/wm8962/Surface-RT-HiFi.conf` | the devices `Speaker`, `Headphones`, `Mic`, `Headset` |
| `conf.d/tegra/Microsoft Surface RT WM8962.conf` | symlink the lookup uses: driver `tegra` (`/proc/asound/cards`), card long name `Microsoft Surface RT WM8962` |

## Verified on the device (2026-11-05, r22 / kernel 7.0.1-r17, PipeWire 1.6.9, alsa-ucm-conf from Alpine edge)

- `alsaucm` lists the verb `HiFi` and the four devices; `CapturePCM/Mic` resolves to `hw:WM8962`, `CaptureMixerElem` to `Digital Capture`.
- WirePlumber offers the source `alsa_input.platform-sound.HiFi__Mic__source` ("Built-in Microphone", port availability
  *unknown*, i.e. usable, not "unplugged"); `parecord` from it records live samples on both channels (peaks 220 to 640 over a
  floor near 20, taps visible; before: `Stream error: No such entity`).
- The speaker sink `HiFi__Speaker__sink` plays a test tone and the headphone sink `HiFi__Headphones__sink` was selected with a
  headset plugged in (`Headphone Jack` on, route available). The user reports that plugging and unplugging switches the output.
- **Not verified:** the `Headset` microphone (nothing with a microphone was plugged in), and the headphone volume range.

## Why only one output is listed at a time

The jack devices must **outrank** the always-present ones (`Headphones` 200 over `Speaker` 100, `Headset` 200 over `Mic` 100): a
device whose `JackControl` reads off is "not available" and loses; one that reads on wins. With the order reversed the Speaker
(availability "unknown", which counts as available) won even with headphones plugged in.

PipeWire's ACP (checked in `spa/plugins/alsa/acp/alsa-ucm.c`, 1.6.9) makes **one sink per UCM device**, never ports of one sink, and
builds the card's profiles from combinations of devices: here `HiFi (Headphones, Mic)`, `HiFi (Mic, Speaker)`,
`HiFi (Headset, Speaker)` and `HiFi (Headphones, Headset)`. Two devices on one PCM are never in the same profile, and the
WM8962 has a single stereo playback stream, so Speaker and Headphones cannot be listed together: when ACP probes a profile it opens
every sink's PCM at once, and a variant with different PCM spellings (`hw:${CardId}` and `hw:${CardId},0`) failed with
`output PCM open failed` / `Profile HiFi not supported`. WirePlumber therefore switches the **profile** with the jack; the other
output is only visible as a profile (pavucontrol, Configuration tab). Having both as selectable ports of one sink needs the classic
ALSA mixer-path model (a custom ACP profile-set plus paths, selected by a udev rule, UCM disabled for the card), which is not done.

## Try it without root

```sh
cp -r /usr/share/alsa/ucm2 ~/ucm2-test           # a private copy of the system tree
cp -r Tegra/wm8962 ~/ucm2-test/Tegra/
cp -P "conf.d/tegra/Microsoft Surface RT WM8962.conf" ~/ucm2-test/conf.d/tegra/
ALSA_CONFIG_UCM2=$HOME/ucm2-test alsaucm -c "Microsoft Surface RT WM8962" set _verb HiFi list _devices
systemctl --user set-environment ALSA_CONFIG_UCM2=$HOME/ucm2-test && systemctl --user restart wireplumber   # until logout
```

## Install (root)

```sh
sudo cp -r Tegra/wm8962 /usr/share/alsa/ucm2/Tegra/
sudo cp -P "conf.d/tegra/Microsoft Surface RT WM8962.conf" /usr/share/alsa/ucm2/conf.d/tegra/
systemctl --user restart wireplumber
```

`tools/build/make-image.sh` installs these files (package `surface-rt-audio`, staged by `tools/build/prepare-audio.py`; `AUDIO_PROFILE=0` omits it)
and checks them in the finished image. Untested until the next flash.
`BootSequence` only runs with `alsaucm boot` at boot, not when WirePlumber activates the profile.
