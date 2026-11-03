#!/usr/bin/env python3
"""Extract the REA-verified Surface RT BT_UART image; never install it."""

import argparse
import hashlib
from pathlib import Path
import struct


SOURCE_SHA256 = "ac47a0927099cffac55d51dbc91da32f848481f04987a8de5027548245a87fde"
IMAGE_SHA256 = "97cc4df3d978db1485c3531c13749cc91d12eae7570c38edeabfd2dd9e6d8b74"
IMAGE_RVA = 0xB2830
IMAGE_SIZE = 0x6A058
TAG = b"$Id: w8797-B0, RF878X, FP62_WIN7, 14.62.17.p215, BT_UART $"


def extract(source: Path) -> bytes:
    data = source.read_bytes()
    if hashlib.sha256(data).hexdigest() != SOURCE_SHA256:
        raise ValueError("Source hash differs from the analysed Surface RT driver")
    pe = struct.unpack_from("<I", data, 0x3C)[0]
    if data[:2] != b"MZ" or data[pe:pe + 4] != b"PE\0\0":
        raise ValueError("Expected a PE image")
    count = struct.unpack_from("<H", data, pe + 6)[0]
    optional_size = struct.unpack_from("<H", data, pe + 20)[0]
    matches = []
    for index in range(count):
        section = pe + 24 + optional_size + 40 * index
        _, rva, raw_size, raw_offset = struct.unpack_from("<IIII", data, section + 8)
        delta = IMAGE_RVA - rva
        if 0 <= delta and delta + IMAGE_SIZE <= raw_size:
            offset = raw_offset + delta
            image = data[offset:offset + IMAGE_SIZE]
            matches.append(image)
    if len(matches) != 1:
        raise ValueError("Firmware range must map to exactly one file-backed section")
    image = matches[0]
    if len(image) != IMAGE_SIZE or hashlib.sha256(image).hexdigest() != IMAGE_SHA256:
        raise ValueError("Extracted firmware hash/size mismatch")
    if TAG not in image:
        raise ValueError("Expected BT_UART identity missing")
    return image


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("driver", type=Path)
    parser.add_argument("output", type=Path, help="new output file; existing files are refused")
    args = parser.parse_args()
    try:
        image = extract(args.driver)
        with args.output.open("xb") as output:
            output.write(image)
    except (ValueError, OSError, struct.error) as error:
        parser.exit(1, f"{error}\n")
    print(f"{IMAGE_SHA256}  {args.output} ({len(image)} bytes)")
    print(TAG.decode())


if __name__ == "__main__":
    main()
