#!/usr/bin/env python3
"""Density-peak range-separation diagnostic (no QE).

Idea: keep the short-range Fock fraction = 1 (DD-RSH-CAM β=1) and the long-range fraction
A = 1/ε∞, but REPLACE the EELS-fitted screening μ by a density-derived one,

    μ_eff = c · q_char,   q_char = 1/σ_peak  (active species, log-curvature peak width)

with c a single global constant. Because in the β=1 model the gap DECREASES with μ
(μ→0 ⇒ α≡1 full Fock; μ→∞ ⇒ α≡A), and the ionic anions (O/F) have the most localised
peaks (smallest σ_peak ⇒ largest q_char ⇒ largest μ_eff ⇒ smallest gap), this finally
moves in the SAME direction as the gap error (β=1 over-opens the ionic crystals).

This script only prints μ_eff(c) next to the fitted μ and the current β=1 error — it does
NOT run QE. Use it to choose c before any calibration run.

Usage:  python3 scripts/diag_density_mu.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from literature import BENCHMARK  # noqa: E402
from matlib import load_materials  # noqa: E402
from qpeak import ACTIVE_SPECIES, species_sigma  # noqa: E402
from write_comparison import collect  # noqa: E402

CS = (0.3, 0.4, 0.5, 0.6, 0.7)


def main() -> None:
    rows = collect()
    mats = load_materials()
    print(f"{'mat':6} {'sp':3} {'sigma':>6} {'q_char':>6} {'mu_fit':>6} {'A':>5} "
          f"{'b1_gap':>6} {'expt':>5} {'err':>6} | "
          + "  ".join(f"mu(c={c})" for c in CS))
    for name, r in rows.items():
        sp = ACTIVE_SPECIES[name]
        sig = species_sigma(name, mats[name]["prefix"])[sp]["sigma"]
        qchar = 1.0 / sig
        mu_fit, A = r["mu"], r["aexx"]
        m = r["mat"]
        fund_kind = "indirect" if "indirect" in m["edges"] else "direct"
        # representative edge = the fundamental edge
        gap = r["ddh_fund"] if fund_kind == "indirect" else r["ddh_direct"]
        exp = BENCHMARK[name]["edges"][fund_kind]["expt"]
        err = gap - exp if (gap and exp) else None
        mus = "  ".join(f"{c * qchar:7.3f}" for c in CS)
        print(f"{name:6} {sp:3} {sig:6.3f} {qchar:6.3f} {mu_fit:6.3f} {A:5.3f} "
              f"{gap:6.2f} {exp:5.2f} {err:+6.2f} | {mus}")
    print("\nμ_eff = c/σ_peak (bohr⁻¹). In β=1, larger μ ⇒ smaller gap. The ionic anions"
          " (O/F, σ_peak≈0.30) get the largest μ_eff ⇒ biggest gap reduction — the right"
          " direction. err = β=1 gap − expt on the fundamental edge.")


if __name__ == "__main__":
    main()
