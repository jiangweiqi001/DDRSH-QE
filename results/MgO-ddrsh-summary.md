# MgO QE STRICT DD-RSH-CAM (patched QE) Summary

A patched Quantum ESPRESSO 7.5 (`lmodelhf`, hand-added) implements the true DD-RSH-CAM
Fock kernel V(q) = 4*pi*e2/q^2 * [BEXX - (BEXX-AEXX) exp(-q^2/4mu^2)] with the matching
semilocal complement (1-AEXX)*E_x^PBE - (BEXX-AEXX)*E_x^PBE,SR(mu). The patch was verified
to reproduce native QE PBE0 (AEXX=BEXX=0.25) and HSE (AEXX=0, BEXX=0.25, mu=0.106) bit-for-bit
(total energy to 8 d.p. and every eigenvalue at every SCF iteration).

Non-empirical parameters from PBE turboEELS eps^-1(q) (RPA + local fields) fit:
- eps_inf = 3.092  ->  AEXX = 1/eps_inf = 0.3234
- mu = 0.726 bohr^-1 (from eps^-1(q) = 1 - (1-1/eps_inf) exp(-q^2/4mu^2), RMSE 0.006)
- BEXX = 1.0 (full short-range Fock, DD-RSH-CAM definition)

| Quantity | Value |
| --- | ---: |
| Strict DD-RSH-CAM gap (k 6x6x6, nqx 3x3x3) | 8.674 eV |
| Strict DD-RSH-CAM gap (k 6x6x6, nqx 6x6x6, q-converged) | 8.548 eV (HOMO 6.270 / LUMO 14.817) |
| Paper DD0-RSH-CAM (MgO) | 8.32 eV |
| Paper RS-DDH (MgO) | 7.88 eV |
| Approximate DD-HSE (long-range Fock removed) | 5.227 eV |
| Experimental gap | 7.83 eV |

Interpretation: the strict DD-RSH-CAM gap (8.55 eV) matches the paper's DD-RSH-CAM family
(8.32 eV) within ~0.2 eV -- NOT the approximate DD-HSE (5.23 eV) which removes long-range Fock.
The residual vs paper is consistent with parameter differences (paper eps_inf=2.81 -> AEXX=0.356;
mu source/value), lattice constant (exp 4.186 A here vs paper 4.148 A), pseudopotentials and
k/cutoff convergence. The DD-RSH-CAM family overshoots the experimental 7.83 eV for MgO in the
paper too (8.32), so the strict implementation reproduces the functional's known behaviour.

---

# MgO QE DDRSH-Approximation Summary (earlier, unpatched)

Reference: Chen et al., Phys. Rev. Materials 2, 073803 (2018); Skone, Govoni, Galli, Phys. Rev. B 89, 195112 (2014) for global DDH

Primary QE-reproducible target is the global DDH, i.e. PBE0 with exx_fraction = 1 / epsilon_inf. The DD-HSE run is only an approximation of the range-separated family: QE HSE removes Fock exchange in the long range, while DD-RSH-CAM keeps screened Fock there. A strict DD-RSH-CAM reproduction needs a patched QE with separate short- and long-range exact-exchange fractions.

| Quantity | Value |
| --- | ---: |
| Material | MgO |
| Engine | Quantum ESPRESSO (pw.x + epsilon.x) |
| Structure source | rocksalt fcc primitive cell, a = 4.186 A experimental (celldm(1) = 7.9104 bohr) |
| PBE band gap | 4.952 eV |
| epsilon components (eps.x) | 3.2172, 3.2172, 3.2172 |
| epsilon_inf | 3.217165 |
| exx_fraction = 1 / epsilon_inf | 0.310833 |
| mu (DD-HSE screening_parameter) | 0.630 bohr^-1 (used directly in QE) |
| DDH / PBE0 gap (primary QE target) | 8.111 eV |
| DD-HSE gap (approximate RS) | 5.227 eV |
| Paper values | PBE 4.79; HSE06 6.47; DDH 7.70; RS-DDH 7.88; DD0-RSH-CAM 8.32 |
| Experimental gap | 7.83 eV |

## Comparison (DDH, primary target)

- DDH gap (this run): 8.111 eV
- vs paper DDH (7.70 eV): +0.411 eV
- vs experiment (7.83 eV): +0.281 eV

Likely contributions to the deviation:

- Lattice constant: this run uses the experimental a = 4.186 A; PBE here is 4.95 eV vs paper 4.79 eV (paper used a = 4.148 A).
- epsilon_inf source: PBE DFPT gives 3.217 (exx_fraction 0.311) vs paper 2.81; a self-consistent hybrid epsilon_inf would change the EXX fraction.
- k-mesh (6x6x6) and Fock q-grid (nqx 3x3x3) are not converged; hybrid gaps rise toward the converged value as these grids are densified.
- Pseudopotential and cutoffs (SG15 ONCV, ecutwfc 80 Ry) differ from the paper's setup.

## Error Sources To Record

- Lattice constant and whether the structure was optimized or taken from literature.
- QE version and whether `epsilon.x` and hybrid (`input_dft`) are both available.
- Pseudopotential files (must be norm-conserving for epsilon.x) and their provenance.
- `ecutwfc`, `ecutrho`, k-mesh, and `nqx` Fock-grid convergence for PBE, eps, and hybrid.
- Whether epsilon_inf comes from PBE eps.x (RPA, no local fields) or a hybrid recompute.
- That DD-HSE is an approximation, not exact DD-RSH-CAM (long-range topology differs).
- Whether the hybrid run is one-shot or iterated with a recomputed epsilon_inf.
