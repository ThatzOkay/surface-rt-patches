# Battery charge limit

The Surface RT's embedded controller (EC, I2C bus 4 at `0x0a`; `i2c-4` in Linux, `\_SB.I2C5` in the
Windows firmware's ACPI tables) can stop charging while the adapter keeps powering the tablet. Windows
RT uses it for thermal charge throttling. These files keep the battery between two levels while
plugged in, or hold it where it is.

## Files

| File | Install as | What |
|---|---|---|
| `charge-limit` | `/usr/local/sbin/charge-limit` | the policy loop and the commands below (POSIX sh) |
| `charge-limit.service` | `/etc/systemd/system/charge-limit.service` | runs the loop; every stop restores normal charging |
| `charge-limit.conf` | `/etc/charge-limit.conf` | thresholds and mode, re-read every cycle |

    sudo install -m 755 charge-limit /usr/local/sbin/
    sudo install -m 644 charge-limit.service /etc/systemd/system/
    sudo install -m 644 charge-limit.conf /etc/
    sudo systemctl enable --now charge-limit

With kernel patch `0037` the script uses the battery's standard `charge_behaviour` attribute
(`auto` / `inhibit-charge`). Without it, it writes the EC register directly and needs `i2c-tools`.

## Use

| Command | While plugged in |
|---|---|
| `sudo charge-limit limit` | keep the battery between `START` and `STOP` (75–80 % by default) |
| `sudo charge-limit hold` | do not charge at all: the adapter powers the tablet, the battery stays idle |
| `sudo charge-limit full` | charge normally to 100 % |
| `sudo charge-limit status` | show the EC setting, the battery and the policy |

Below `FLOOR` (20 %) it always charges. Each change is logged (`journalctl -t charge-limit`).

## Things to know

- **The EC keeps the setting across adapter removal, suspend, reboot and power-off.** A tablet left
  switched off with charging inhibited will not charge. The service therefore writes "charge" when it
  stops (every normal shutdown and reboot) and applies the right state as soon as it starts, so the
  next boot also fixes a crash or a long press.
- The loop does not run during suspend: charging that was on when the tablet went to sleep goes on.
- On EC firmware `0x0a.0x0d` any value below 100 stops charging completely (0, 25, 50, 80, 90 and 99
  were tried). It is neither a target level nor a charge rate in practice, so the limit has to come
  from software watching the level.

## EC registers used by the Windows firmware

From the battery (`\_SB.BAT0`) and adapter (`\_SB.ADP0`) methods in the Windows firmware's SSDT
(`AP20EDK2`). Accesses are SMBus byte reads/writes to `0x0a` with the register as the command byte
(`GenericSerialBus`, `AttribByte`).

| Register | Access | Meaning |
|---|---|---|
| `0x04`, `0x05` | read | EC firmware version, major and minor. Register choices below depend on it. |
| `0x00` (fw ≥ 10) / `0x0d` (older) | write | Battery Thermal Limit, `_DSM` `4c2067e3-887d-475c-9720-4af1d3ed602e` function 1: 0–100 (% of the maximum charge rate per Microsoft; on this EC 100 = charge, anything lower = no charging). Only `0x00` has been tested. |
| `0x67` (fw ≥ 10) / `0x01` (older) | read/write | adapter status (bit 0 = online) and the `_BTP` battery trip point |
| `0x02` | read | battery status (bit 0 = charging) |
| `0x20`/`0x21`, `0x24`/`0x25`, `0x28`/`0x29`, `0x2c`/`0x2d` | read | voltage, current, remaining capacity, full charge capacity (word pairs) |
| `0x3a`–`0x3f`, `0x44`–`0x5d` | read | cycle count, design values, serial number, manufacturer, model, chemistry |

The charger (TI BQ24725A, SMBus `0x09`) and the fuel gauge (TI BQ28400, `0x0b`) sit on the EC's private
bus; they do not answer on any of the Tegra's I2C buses, also with the adapter plugged in.

**Do not sweep-read the EC** (for example with `i2cdump`). A full 0x00–0xff dump hung the tablet once
and caused system-wide memory corruption: bus 4 also carries the PMIC and the CPU voltage regulator.
Read only the registers above, one at a time.
