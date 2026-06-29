#!/usr/bin/env python3
"""Density-peak log-curvature finite-q endpoint — shared core.

Reads the PBE valence charge density (G-space `charge-density.dat`) and structure
(`data-file-schema.xml`) from a material's PBE `.save`, forms the exact per-species
spherical average around its atoms,

    ρ̄_s(r) = Σ_G ρ(G) · S_s(G) · j₀(|G| r),   S_s(G) = ⟨e^{iG·τ}⟩_{τ∈s},  j₀(x)=sin x / x

fits a parabola to ln ρ̄ near the peak,

    ln ρ̄_s(r) ≈ c₀ + c₁(r−r₀) + c₂(r−r₀)²,   σ_peak = sqrt(−1/(2 c₂)),

and turns it into a short-range Fock endpoint at q_peak = κ/σ_peak:

    B_κ = ε⁻¹(q_peak) = 1 − (1 − A)·exp[ −q_peak² / (4 μ²) ],   A = 1/ε∞,  μ = hfscreen.

κ is a fixed global parameter — not tuned per material, not fitted to gaps. The active
species (the one whose σ_peak sets B_κ) is fixed in ACTIVE_SPECIES before any benchmark.

No QE call is made here; this only reads existing PBE output.
"""

from __future__ import annotations

import struct
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]

# Active species per material: anion / VBM-localised element (Si, C are single-element).
ACTIVE_SPECIES = {
    "Si": "Si", "C": "C", "AlAs": "As", "MgO": "O",
    "LiCl": "Cl", "NaCl": "Cl", "CaF2": "F", "LiF": "F",
}

KAPPAS = (0.25, 0.35, 0.50)


def save_dir(name: str, prefix: str) -> Path:
    return ROOT / "runs" / name / "01-pbe-scf" / "out" / f"{prefix}.save"


def _records(path: Path):
    """Yield raw payloads of a sequential Fortran unformatted file (4-byte markers)."""
    with open(path, "rb") as fh:
        data = fh.read()
    i, n = 0, len(data)
    while i < n:
        (rl,) = struct.unpack_from("<i", data, i)
        i += 4
        yield data[i:i + rl]
        i += rl
        (rl2,) = struct.unpack_from("<i", data, i)
        i += 4
        if rl != rl2:
            raise ValueError(f"corrupt Fortran record in {path} ({rl} != {rl2})")


def read_rhog(path: Path):
    """Parse QE charge-density.dat -> (gamma_only, mill[ngm,3] int, rho_g[ngm] complex)."""
    recs = _records(path)
    r1 = next(recs)
    gamma_only = struct.unpack_from("<i", r1, 0)[0] != 0
    ngm, nspin = struct.unpack_from("<ii", r1, 4)
    next(recs)  # b1,b2,b3 (tpiba) — not needed; we build G from the real cell
    mill = np.frombuffer(next(recs), dtype="<i4").reshape(ngm, 3).astype(float)
    rho = np.frombuffer(next(recs), dtype="<c16").copy()
    for _ in range(nspin - 1):  # spin-polarised: add the other channel (none of ours are)
        rho = rho + np.frombuffer(next(recs), dtype="<c16")
    return gamma_only, mill, rho


def read_structure(path: Path):
    """Parse data-file-schema.xml -> (cell[3,3] bohr rows a1,a2,a3, [(species, xyz bohr)])."""
    root = ET.parse(path).getroot()
    struct_el = root.find(".//atomic_structure")
    cell_el = struct_el.find("cell")
    cell = np.array([[float(x) for x in cell_el.find(f"a{i}").text.split()]
                     for i in (1, 2, 3)])
    atoms = [(a.get("name"), np.array([float(x) for x in a.text.split()]))
             for a in struct_el.find("atomic_positions").findall("atom")]
    return cell, atoms


def recip(cell: np.ndarray) -> np.ndarray:
    """Reciprocal vectors (bohr⁻¹) as rows, b_i·a_j = 2π δ_ij; cell rows are a1,a2,a3."""
    return 2.0 * np.pi * np.linalg.inv(cell.T)


def nn_distance(cell: np.ndarray, atoms, idx: int) -> float:
    """Nearest-neighbour distance (bohr) to atom `idx` over the 3×3×3 image shell."""
    tau0 = atoms[idx][1]
    shifts = [(i, j, k) for i in (-1, 0, 1) for j in (-1, 0, 1) for k in (-1, 0, 1)]
    best = np.inf
    for a, (_, tau) in enumerate(atoms):
        for s in shifts:
            if a == idx and s == (0, 0, 0):
                continue
            d = np.linalg.norm(tau + s @ cell - tau0)
            if 1e-6 < d < best:
                best = d
    return float(best)


def species_profile(mill, rho_g, B, atoms_xyz, rmax, npts):
    """Spherically-averaged valence density ρ̄_s(r) on [0, rmax] (bohr) for one species."""
    G = mill @ B                       # (ngm, 3) cartesian bohr⁻¹
    Gmag = np.linalg.norm(G, axis=1)
    phases = np.exp(1j * (np.asarray(atoms_xyz) @ G.T))  # (natom, ngm)
    C = (rho_g * phases.mean(axis=0)).real               # (ngm,)
    r = np.linspace(0.0, rmax, npts)
    j0 = np.sinc(np.outer(r, Gmag) / np.pi)              # sin(x)/x, =1 at x=0
    return r, j0 @ C


def fit_log_curv(r, rho):
    """Fit ln ρ̄ ≈ c0 + c1 u + c2 u² (u=r−r0) near the peak; return a result dict.

    Window starts at ρ̄ > 0.8·ρ̄(r0); relaxes to 0.7 if too few points. Reports σ_peak,
    c2, R², point count, window threshold, FWHM (sanity only), and a status/warning."""
    i0 = int(np.argmax(rho))
    r0, rho0 = float(r[i0]), float(rho[i0])
    out = {"r0": r0, "rho0": rho0, "sigma": None, "c2": None, "c1": None,
           "R2": None, "npts": 0, "thr": None, "fwhm": None, "status": ""}
    if rho0 <= 0:
        out["status"] = "WARNING: non-positive peak density"
        return out
    for thr in (0.8, 0.7):
        mask = rho > thr * rho0
        # contiguous window around the peak
        lo = i0
        while lo > 0 and mask[lo - 1]:
            lo -= 1
        hi = i0
        while hi < len(r) - 1 and mask[hi + 1]:
            hi += 1
        npts = hi - lo + 1
        out["thr"], out["npts"] = thr, npts
        if npts >= 5:
            break
    u = r[lo:hi + 1] - r0
    y = np.log(rho[lo:hi + 1])
    if out["npts"] < 4:
        out["status"] = f"WARNING: only {out['npts']} fit points (window {out['thr']})"
        return out
    c2, c1, c0 = np.polyfit(u, y, 2)
    resid = y - (c2 * u ** 2 + c1 * u + c0)
    ss_tot = np.sum((y - y.mean()) ** 2)
    out["c2"], out["c1"] = float(c2), float(c1)
    out["R2"] = float(1.0 - np.sum(resid ** 2) / ss_tot) if ss_tot > 0 else 1.0
    out["fwhm"] = _fwhm(r, rho, i0, rho0)
    if c2 >= 0:
        out["status"] = "WARNING: c2 >= 0 (not a peak)"
        return out
    out["sigma"] = float(np.sqrt(-1.0 / (2.0 * c2)))
    out["status"] = "ok"
    return out


def _fwhm(r, rho, i0, rho0):
    """Full width at half maximum of ρ̄ around r0 (bohr); optional sanity output only."""
    half = 0.5 * rho0
    hi = i0
    while hi < len(r) - 1 and rho[hi] > half:
        hi += 1
    right = float(np.interp(half, [rho[hi], rho[hi - 1]], [r[hi], r[hi - 1]])) \
        if rho[hi] <= half < rho[hi - 1] else float(r[hi])
    if i0 == 0:
        return 2.0 * right
    lo = i0
    while lo > 0 and rho[lo] > half:
        lo -= 1
    left = float(np.interp(half, [rho[lo], rho[lo + 1]], [r[lo], r[lo + 1]])) \
        if rho[lo] <= half < rho[lo + 1] else float(r[lo])
    return right - left


def qpeak_bexx(aexx: float, mu: float, sigma: float, kappa: float):
    """(q_peak, B_κ) for sampling wavevector q_peak = κ/σ_peak under the single-μ model."""
    q_peak = kappa / sigma
    bexx = 1.0 - (1.0 - aexx) * np.exp(-(q_peak ** 2) / (4.0 * mu ** 2))
    return q_peak, float(bexx)


def species_sigma(name: str, prefix: str):
    """Per-species σ_peak diagnostics for a material: {species: fit-dict (+ r0, npts...)}.

    Returns (results, n_per_species) where results[species] is the fit_log_curv dict."""
    cden = save_dir(name, prefix) / "charge-density.dat"
    xml = save_dir(name, prefix) / "data-file-schema.xml"
    _gamma, mill, rho_g = read_rhog(cden)
    cell, atoms = read_structure(xml)
    B = recip(cell)
    species = {}
    for sp in dict.fromkeys(n for n, _ in atoms):       # preserve order, unique
        idxs = [i for i, (n, _) in enumerate(atoms) if n == sp]
        xyz = [atoms[i][1] for i in idxs]
        dnn = min(nn_distance(cell, atoms, i) for i in idxs)
        rmax = 0.5 * dnn
        npts = max(60, int(rmax / 0.02))
        r, rho = species_profile(mill, rho_g, B, xyz, rmax, npts)
        fit = fit_log_curv(r, rho)
        fit["nat"] = len(idxs)
        fit["dnn"] = dnn
        species[sp] = fit
    return species
