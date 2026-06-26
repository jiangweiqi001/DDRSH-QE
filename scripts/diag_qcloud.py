#!/usr/bin/env python3
"""Diagnostic for the density-scale finite-q model — NO QE runs, just the endpoint table.

For every material and η in {0.5, 0.6, 1.0} it prints the short-range Fock endpoint
B_η = ε⁻¹(η·q_WS) and verifies A ≤ B_η ≤ 1. All inputs come from existing runs:
  * N_val (total valence electrons) and cell volume Ω  -> PBE SCF output (matlib.pbe_density)
  * (ε∞, μ, A = 1/ε∞)                                  -> turboEELS fit (write_comparison.fit_eps)

Definitions (bohr units):
  n_v     = N_val / Ω
  q_WS    = (4π n_v / 3)^(1/3)
  q_cloud = η · q_WS
  B_η     = 1 − (1 − A)·exp[ −(η·q_WS)² / (4 μ²) ],   A = aexx = 1/ε∞,  μ = hfscreen

Usage:  python3 scripts/diag_qcloud.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gen_inputs import q_ws, qcloud_bexx  # noqa: E402
from matlib import eels_data, load_materials, pbe_density  # noqa: E402
from write_comparison import fit_eps  # noqa: E402

ETAS = (0.5, 0.6, 1.0)


def main() -> None:
    mats = load_materials()
    hdr = (f"{'material':<8} {'N_val':>6} {'Ω(bohr³)':>11} {'n_v':>9} {'q_WS':>7} "
           f"{'μ':>6} {'qWS/μ':>7} {'η':>4} {'q_cloud':>8} {'A':>6} {'B_η':>6}  ok")
    print(hdr)
    print("-" * len(hdr))
    violations = 0
    for name, m in mats.items():
        nval, vol = pbe_density(name, m)
        _eps_inf, mu, A = fit_eps(eels_data(name, m))
        qws = q_ws(nval, vol)
        n_v = nval / vol
        for eta in ETAS:
            B = qcloud_bexx(A, mu, qws, eta)
            q_cloud = eta * qws
            ok = A <= B <= 1.0
            violations += not ok
            print(f"{name:<8} {nval:>6.1f} {vol:>11.3f} {n_v:>9.5f} {qws:>7.4f} "
                  f"{mu:>6.3f} {qws / mu:>7.3f} {eta:>4.1f} {q_cloud:>8.4f} "
                  f"{A:>6.3f} {B:>6.3f}  {'✓' if ok else '✗'}")
    print()
    print(f"all materials satisfy A ≤ B_η ≤ 1:  "
          f"{'YES' if violations == 0 else f'NO — {violations} violation(s)'}")


if __name__ == "__main__":
    main()
