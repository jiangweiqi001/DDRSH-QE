#!/usr/bin/env python3
"""Shared literature / experimental reference values.

Single source of truth so the summary and audit reports cannot drift apart.
"""

from __future__ import annotations

LITERATURE: dict[str, dict[str, object]] = {
    "MgO": {
        "structure_source": "rocksalt fcc primitive cell, a = 4.186 A experimental (celldm(1) = 7.9104 bohr)",
        "epsilon_inf": 2.81,
        "mu_bohr_inv": 0.63,
        "pbe_gap_eV": 4.79,
        "hse06_gap_eV": 6.47,
        "ddh_gap_eV": 7.70,
        "rs_ddh_gap_eV": 7.88,
        "dd0_rsh_cam_gap_eV": 8.32,
        "experimental_gap_eV": 7.83,
        "zpr_correction_eV": 0.53,
        "reference": "Chen et al., Phys. Rev. Materials 2, 073803 (2018); "
        "Skone, Govoni, Galli, Phys. Rev. B 89, 195112 (2014) for global DDH",
    }
}


# ---------------------------------------------------------------------------
# Benchmark reference values (experiment + other methods) for the multi-material
# DD-RSH-CAM comparison. Separate schema from LITERATURE (which the MgO audit
# scripts depend on) so neither can break the other.
#
# Per material:
#   eps_inf_expt : experimental high-frequency dielectric constant
#   tol_eV       : bench gap tolerance (from the EFT-ARPES-bench TOML `targets`)
#   edges[<kind>]: {expt, gw, hse06, pbe0} reference gaps in eV (None if N/A)
# Values from the EFT-ARPES-bench TOMLs (kunyuan/EFT-ARPES-bench) and, for MgO,
# results/MgO-results.md. CaF2 hybrid/GW literature is sparse -> bench estimates.
# Insertion order = coverage order (covalent -> ionic), matches materials.toml.
# ---------------------------------------------------------------------------
BENCHMARK: dict[str, dict] = {
    "Si": {
        "eps_inf_expt": 11.7, "tol_eV": 0.30,
        "edges": {
            "indirect": {"expt": 1.17, "gw": 1.29, "hse06": 1.16, "pbe0": 1.97},
            "direct": {"expt": 3.40, "gw": 3.35, "hse06": 3.32, "pbe0": 3.96},
        },
    },
    "C": {
        "eps_inf_expt": 5.7, "tol_eV": 0.40,
        "edges": {
            "indirect": {"expt": 5.48, "gw": 5.50, "hse06": 5.42, "pbe0": 6.66},
            "direct": {"expt": 7.30, "gw": 7.50, "hse06": 7.04, "pbe0": 8.40},
        },
    },
    "AlAs": {
        "eps_inf_expt": 8.16, "tol_eV": 0.30,
        "edges": {
            "indirect": {"expt": 2.23, "gw": 2.18, "hse06": 2.04, "pbe0": 2.86},
            "direct": {"expt": 3.13, "gw": 2.88, "hse06": 2.97, "pbe0": 3.86},
        },
    },
    "MgO": {
        "eps_inf_expt": 2.96, "tol_eV": 0.50,
        "edges": {
            "direct": {"expt": 7.83, "gw": 7.69, "hse06": 6.51, "pbe0": 7.23},
        },
    },
    "LiCl": {
        "eps_inf_expt": 2.75, "tol_eV": 0.40,
        "edges": {
            "direct": {"expt": 9.40, "gw": 9.1, "hse06": 7.80, "pbe0": 9.0},
        },
    },
    "NaCl": {
        "eps_inf_expt": 2.34, "tol_eV": 0.40,
        "edges": {
            "direct": {"expt": 8.97, "gw": 8.7, "hse06": 6.56, "pbe0": 8.5},
        },
    },
    "CaF2": {
        "eps_inf_expt": 2.04, "tol_eV": 0.50,
        "edges": {
            "indirect": {"expt": 11.80, "gw": 11.4, "hse06": 10.4, "pbe0": 11.0},
            "direct": {"expt": 12.10, "gw": 11.8, "hse06": None, "pbe0": None},
        },
    },
    "LiF": {
        "eps_inf_expt": 1.9, "tol_eV": 0.50,
        "edges": {
            "direct": {"expt": 14.20, "gw": 14.3, "hse06": 11.50, "pbe0": 14.7},
        },
    },
}
