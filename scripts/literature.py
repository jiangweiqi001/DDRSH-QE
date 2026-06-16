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
