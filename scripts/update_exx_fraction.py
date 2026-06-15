#!/usr/bin/env python3
"""Update exx_fraction in QE pw.x input files from an extracted summary JSON."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def update_exx_fraction(infile: Path, exx_fraction: float) -> None:
    text = infile.read_text(encoding="utf-8")
    replacement = f"  exx_fraction        = {exx_fraction:.6f}"
    pattern = re.compile(r"(?m)^\s*exx_fraction\s*=.*$")
    if pattern.search(text):
        text = pattern.sub(replacement, text, count=1)
    else:
        raise SystemExit(f"{infile} has no exx_fraction line to update")
    infile.write_text(text, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("inputs", nargs="+", type=Path)
    args = parser.parse_args()

    summary = json.loads(args.summary.read_text(encoding="utf-8"))
    exx_fraction = summary.get("exx_fraction")
    if exx_fraction is None:
        raise SystemExit("summary JSON has no `exx_fraction`; run the epsilon step first")

    for infile in args.inputs:
        update_exx_fraction(infile, float(exx_fraction))
        print(f"Updated {infile} with exx_fraction = {exx_fraction:.6f}")


if __name__ == "__main__":
    main()
