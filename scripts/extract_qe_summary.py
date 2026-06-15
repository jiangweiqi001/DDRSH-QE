#!/usr/bin/env python3
"""Extract the minimal quantities needed for the QE DDRSH-approximation table.

Parses:
- a pw.x output file for the band gap (highest occupied / lowest unoccupied),
- a ph.x output file for the clamped-ion electronic dielectric tensor (epsilon_inf).
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


def parse_pw_gap(pw_out: Path) -> dict[str, Any] | None:
    if not pw_out.exists():
        return None

    text = pw_out.read_text(errors="replace")

    # Hybrid (EXX) runs print this line multiple times: once for the initial
    # semilocal convergence and once per EXX refinement. Take the LAST one.
    matches = re.findall(
        r"highest occupied, lowest unoccupied level \(ev\):\s*"
        r"([-+]?\d+\.\d+)\s+([-+]?\d+\.\d+)",
        text,
    )
    if matches:
        vbm = float(matches[-1][0])
        cbm = float(matches[-1][1])
        return {
            "vbm_eV": vbm,
            "cbm_eV": cbm,
            "gap_eV": cbm - vbm,
            "method": "ho_lu_line",
            "n_occurrences": len(matches),
        }

    ho_matches = re.findall(r"highest occupied level \(ev\):\s*([-+]?\d+\.\d+)", text)
    if ho_matches:
        return {
            "vbm_eV": float(ho_matches[-1]),
            "cbm_eV": None,
            "gap_eV": None,
            "method": "ho_only",
            "note": "No unoccupied level printed; increase nbnd or use nscf.",
        }

    return None


def parse_ph_epsilon(ph_out: Path) -> dict[str, Any] | None:
    if not ph_out.exists():
        return None

    lines = ph_out.read_text(errors="replace").splitlines()
    for idx, line in enumerate(lines):
        if "Dielectric constant in cartesian axis" not in line:
            continue

        rows: list[list[float]] = []
        for candidate in lines[idx + 1 : idx + 8]:
            values = [float(x) for x in re.findall(r"[-+]?\d+\.\d+(?:[Ee][-+]?\d+)?", candidate)]
            if len(values) >= 3:
                rows.append(values[:3])
            if len(rows) == 3:
                break

        if len(rows) == 3:
            diagonal = [rows[i][i] for i in range(3)]
            epsilon_inf = sum(diagonal) / 3.0
            return {
                "tensor": rows,
                "components": diagonal,
                "epsilon_inf": epsilon_inf,
            }

    return None


def summarize(pbe_out: Path, ph_out: Path) -> dict[str, Any]:
    pbe_gap = parse_pw_gap(pbe_out)
    eps = parse_ph_epsilon(ph_out)

    epsilon_inf = eps["epsilon_inf"] if eps else None
    exx_fraction = (1.0 / epsilon_inf) if epsilon_inf else None

    return {
        "pbe_out": str(pbe_out),
        "ph_out": str(ph_out),
        "pbe_gap": pbe_gap,
        "epsilon": eps,
        "epsilon_inf": epsilon_inf,
        "exx_fraction": exx_fraction,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("pbe_out", type=Path, help="pw.x SCF output file")
    parser.add_argument("ph_out", type=Path, help="ph.x output file with dielectric tensor")
    parser.add_argument("--json", type=Path, required=True)
    args = parser.parse_args()

    data = summarize(args.pbe_out, args.ph_out)
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(json.dumps(data, indent=2))


if __name__ == "__main__":
    main()
