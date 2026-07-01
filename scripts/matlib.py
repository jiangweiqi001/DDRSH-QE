#!/usr/bin/env python3
"""Loader for config/materials.toml — the per-material run configuration.

Derives `nat` (number of atoms) and `ntyp` (number of species) from the structure
so they cannot drift from the positions/species lists. Resolves the path to the
DD-RSH-CAM production output (with an optional per-material override).
"""

from __future__ import annotations

import re
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


def finiteg_out(name: str, mat: dict, a: float) -> Path:
    """Finite-G model (bexx = ε⁻¹(a·μ)) hybrid output for global constant `a`."""
    return run_dir(name) / f"p2/finiteG_a{a:.1f}" / f"{mat['prefix']}.fg.out"


def eta_tag(eta: float) -> str:
    """Directory-safe η label: 0.5 -> '0p5', 1.0 -> '1p0'."""
    return f"{eta:.1f}".replace(".", "p")


def qcloud_out(name: str, mat: dict, eta: float) -> Path:
    """Density-scale finite-q model (bexx = ε⁻¹(η·q_WS)) output for global constant η."""
    return run_dir(name) / f"p2/qcloud_eta{eta_tag(eta)}" / f"{mat['prefix']}.qc.out"


def kappa_tag(kappa: float) -> str:
    """Directory-safe κ label: 0.25 -> '0p25', 0.50 -> '0p50'."""
    return f"{kappa:.2f}".replace(".", "p")


def qpeak_out(name: str, mat: dict, kappa: float) -> Path:
    """Density-peak log-curvature model (bexx = ε⁻¹(κ/σ_peak)) output for global κ."""
    return run_dir(name) / f"p2/qpeak_kappa{kappa_tag(kappa)}" / f"{mat['prefix']}.qp.out"


def densmu_out(name: str, mat: dict, c: float) -> Path:
    """Density-peak range-separation model (β=1, μ_eff = c/σ_peak) output for global c."""
    return run_dir(name) / f"p2/densmu_c{kappa_tag(c)}" / f"{mat['prefix']}.dm.out"


def pbe_density(name: str, mat: dict) -> tuple[float, float]:
    """(N_val, cell volume in bohr³) from the PBE SCF output.

    N_val is the total number of valence electrons in the cell ("number of electrons"
    in pw.x, set by the pseudopotential z_valence); the volume is pw.x "unit-cell volume",
    already in (a.u.)³ = bohr³.
    """
    text = pbe_out(name, mat).read_text()
    vol = re.search(r"unit-cell volume\s*=\s*([\d.]+)", text)
    nval = re.search(r"number of electrons\s*=\s*([\d.]+)", text)
    if not vol or not nval:
        raise SystemExit(f"could not parse N_val / volume from {pbe_out(name, mat)}")
    return float(nval.group(1)), float(vol.group(1))


if __name__ == "__main__":
    mats = load_materials()
    print(f"{len(mats)} materials in {CONFIG.relative_to(ROOT)}:")
    for name, m in mats.items():
        print(
            f"  {name:5s} {m['structure']:11s} a={m['celldm1']:>8} bohr  "
            f"ecut={m['ecutwfc']:g}/{m['ecutrho']:g}  nbnd={m['nbnd']:>2}  "
            f"nat={m['nat']} ntyp={m['ntyp']}  edges={m['edges']}"
        )
