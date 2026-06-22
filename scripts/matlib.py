#!/usr/bin/env python3
"""Loader for config/materials.toml — the per-material run configuration.

Derives `nat` (number of atoms) and `ntyp` (number of species) from the structure
so they cannot drift from the positions/species lists. Resolves the path to the
DD-RSH-CAM production output (with an optional per-material override).
"""

from __future__ import annotations

import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "materials.toml"


def load_materials(path: Path | str = CONFIG) -> dict[str, dict]:
    """Return the materials table, insertion order preserved (coverage order)."""
    with open(path, "rb") as fh:
        data = tomllib.load(fh)
    for name, m in data.items():
        m["name"] = name
        m["nat"] = len(m["positions"])
        m["ntyp"] = len(m["species"])
    return data


def run_dir(name: str) -> Path:
    return ROOT / "runs" / name


def pbe_out(name: str, mat: dict) -> Path:
    return run_dir(name) / "01-pbe-scf" / f"{mat['prefix']}.scf.out"


def eels_data(name: str, mat: dict) -> Path:
    return run_dir(name) / "p2" / "eels" / "eps_q_clean.dat"


def ddrshcam_out(name: str, mat: dict) -> Path:
    rel = mat.get("ddrshcam_out", f"p2/ddrshcam/{mat['prefix']}.ddrshcam.out")
    return run_dir(name) / rel


def rsddh_out(name: str, mat: dict) -> Path:
    """Skone 2016 RS-DDH (bexx=0.25) hybrid output."""
    rel = mat.get("rsddh_out", f"p2/rsddh/{mat['prefix']}.rsddh.out")
    return run_dir(name) / rel


if __name__ == "__main__":
    mats = load_materials()
    print(f"{len(mats)} materials in {CONFIG.relative_to(ROOT)}:")
    for name, m in mats.items():
        print(
            f"  {name:5s} {m['structure']:11s} a={m['celldm1']:>8} bohr  "
            f"ecut={m['ecutwfc']:g}/{m['ecutrho']:g}  nbnd={m['nbnd']:>2}  "
            f"nat={m['nat']} ntyp={m['ntyp']}  edges={m['edges']}"
        )
