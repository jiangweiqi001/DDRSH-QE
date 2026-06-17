#!/usr/bin/env python3
"""Extract band gaps from a Quantum ESPRESSO pw.x output.

Reports, in eV:
  * fundamental gap  -- from the "highest occupied, lowest unoccupied level" line
    (the global VBM->CBM gap; equals the indirect gap when the CBM is off-Gamma).
  * direct Gamma->Gamma gap -- from the eigenvalue block at k = (0,0,0): the
    (nocc+1)-th minus the nocc-th eigenvalue, with nocc = nelectrons / 2.

Usage:
    python3 extract_gap.py path/to/pw.out [--nocc N]

Importable: parse_gaps(path, nocc=None) -> dict.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

_GAMMA = re.compile(r"k =\s*0\.0000\s+0\.0000\s+0\.0000.*bands\s*\(ev\)\s*:", re.I)
_FLOAT = re.compile(r"-?\d+\.\d+")


def _gamma_eigenvalues(lines: list[str]) -> list[float]:
    """Eigenvalues (eV) of the LAST k=(0,0,0) block (i.e. final SCF iteration)."""
    start = None
    for idx, ln in enumerate(lines):
        if _GAMMA.search(ln):
            start = idx
    if start is None:
        return []
    vals: list[float] = []
    for ln in lines[start + 1:]:
        toks = _FLOAT.findall(ln)
        if not toks:
            if vals:  # blank line after we started collecting -> block ended
                break
            continue  # leading blank line(s) right after the header
        vals.extend(float(t) for t in toks)
    return vals


def parse_gaps(path: str | Path, nocc: int | None = None) -> dict:
    text = Path(path).read_text()
    lines = text.splitlines()

    out: dict[str, float | int | None] = {
        "homo": None, "lumo": None, "fundamental": None,
        "gamma_vbm": None, "gamma_cbm": None, "gamma_direct": None, "nocc": nocc,
    }

    m = re.findall(r"highest occupied, lowest unoccupied level \(ev\):\s*"
                   r"(-?\d+\.\d+)\s+(-?\d+\.\d+)", text)
    if m:
        homo, lumo = float(m[-1][0]), float(m[-1][1])
        out.update(homo=homo, lumo=lumo, fundamental=lumo - homo)

    if nocc is None:
        ne = re.findall(r"number of electrons\s*=\s*(-?\d+\.\d+)", text)
        if ne:
            nocc = int(round(float(ne[-1]) / 2.0))
    out["nocc"] = nocc

    eigs = _gamma_eigenvalues(lines)
    if nocc and len(eigs) >= nocc + 1:
        vbm, cbm = eigs[nocc - 1], eigs[nocc]
        out.update(gamma_vbm=vbm, gamma_cbm=cbm, gamma_direct=cbm - vbm)
    return out


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    path = sys.argv[1]
    nocc = None
    if "--nocc" in sys.argv:
        nocc = int(sys.argv[sys.argv.index("--nocc") + 1])
    g = parse_gaps(path, nocc)
    print(f"file            = {path}")
    print(f"nocc            = {g['nocc']}")
    if g["fundamental"] is not None:
        print(f"HOMO / LUMO     = {g['homo']:.4f} / {g['lumo']:.4f} eV")
        print(f"fundamental gap = {g['fundamental']:.4f} eV")
    if g["gamma_direct"] is not None:
        print(f"Gamma VBM/CBM   = {g['gamma_vbm']:.4f} / {g['gamma_cbm']:.4f} eV")
        print(f"direct Gamma gap= {g['gamma_direct']:.4f} eV")


if __name__ == "__main__":
    main()
