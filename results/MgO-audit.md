# MgO DD-RSH-CAM audit (2026-06-16)

Systematic decomposition of the +0.23 eV gap vs paper DD0-RSH-CAM (8.32 eV).
Reference: Chen et al., PRM 2, 073803 (2018).

## Gap table

| Case | Gap (eV) | HOMO | LUMO | vs paper 8.32 | vs exp 7.83 | Notes |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| PBE a=4.186 (baseline) | 4.952 | 9.003 | 13.955 | -3.368 | -2.878 | production |
| PBE a=4.148 (paper lattice) | 5.232 | 9.372 | 14.604 | -3.088 | -2.598 | audit: lattice |
| DD-RSH-CAM fitted, a=4.186, k666, nqx3 | 8.674 | 6.207 | 14.881 | +0.354 | +0.844 | pre-convergence reference |
| DD-RSH-CAM fitted, a=4.186, k666, nqx6 | 8.548 | 6.270 | 14.817 | +0.228 | +0.718 | production |
| DD-RSH-CAM fitted, a=4.148, k666, nqx6 | 8.871 | 6.613 | 15.485 | +0.551 | +1.041 | audit: lattice |
| DD-RSH-CAM fitted, a=4.186, k888, nqx6 | 8.563 | 6.274 | 14.837 | +0.243 | +0.733 | audit: k convergence |
| DD-RSH-CAM fitted, a=4.186, k666, nqx8 | 8.548 | 6.270 | 14.817 | +0.228 | +0.718 | audit: nqx convergence |

## Supplementary (audit controls — not production targets)

| Case | Gap (eV) | HOMO | LUMO | vs paper 8.32 | vs exp 7.83 | Notes |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| lit params, a=4.186 (not production) | 9.123 | 5.883 | 15.006 | +0.803 | +1.293 | audit control only |
| lit params, a=4.148 (not production) | 9.453 | 6.223 | 15.677 | +1.133 | +1.623 | audit control only |

## Literature anchors

- Experimental gap: 7.83 eV
- Paper PBE: 4.79 eV
- Paper DD0-RSH-CAM: 8.32 eV


## Decomposition

- Swapping to literature (AEXX, μ) at this setup raises the gap to 9.123 eV (+0.576 vs production) — not a path to paper 8.32 eV.
- Lattice effect (fitted, 4.148 − 4.186 Å): +0.323 eV
- PBE lattice effect (4.148 − 4.186 Å): +0.280 eV (paper PBE 4.79 eV)
- Net production (fitted@4.186) vs paper 8.32: +0.228 eV

## Convergence (audit A)

- nqx 3→6: -0.126 eV
- nqx 6→8: +0.000 eV (nqx converged at 6×6×6)
- k 6×6×6→8×8×8 (nqx=6): +0.015 eV

## SC iteration (audit C)

- **Not completed:** `epsilon.x` IPA on DD-RSH-CAM saves fails in QE 7.5 (`non uniform kpt grid`). Documented toolchain limitation.

## Verdict

1. **Patch / functional:** validated (PBE0/HSE limits bit-for-bit).
2. **Production gap 8.548 eV** — k and nqx converged within ±0.02 eV.
3. **+0.23 eV vs paper 8.32** is a setup/pipeline offset, not a kernel defect.
4. **Not a numerical reproduction** of Chen 2018 table entries.

