#!/usr/bin/env python3

from argparse import ArgumentParser
from pathlib import Path

from build_lib import *

PATCH_DIR = "Patches"


def main() -> int:
    parser = ArgumentParser(description="A script to build vfuse-enabled HVK RGL patches for a shadowboot (also rglXam patches).")
    parser.add_argument("input", type=str, help="A text file containing each fuse row, one per line")
    args = parser.parse_args()

    sbfuses = []

    with open(args.input, "r") as fuses:
        count = 0
        for line in fuses.readlines():
            sbfuses.append(f"SBFUSES{count:02}={line.rstrip()}")
            count += 1

    print(sbfuses)
    assemble_rgl_vfuses_hdd("Patches/RGL/17559-dev/RGLoader-dev.S", "Output/Zero/VRGL_sb_hdd.bin", "SYSROOT", "SBFUSES",
        *sbfuses
    )
    
    assemble_patch("Patches/XAM/17559-dev/rglXam.S", "Output/Compiled/Patches/rglXam.bin")
    
    with open("Output/Compiled/Patches/rglXam.bin", "rb") as bin, open("Output/Compiled/Patches/rglXam.rglp", "wb") as rglp:
        rglp.write(b"RGLP")
        rglp.write(bin.read())

    return 0


if __name__ == "__main__":
    exit(main())
