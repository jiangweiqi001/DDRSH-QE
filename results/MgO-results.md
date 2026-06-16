# MgO results — strict DD-RSH-CAM in patched QE 7.5

Reference: Chen et al., *Phys. Rev. Materials* **2**, 073803 (2018); Skone, Govoni, Galli,
*Phys. Rev. B* **89**, 195112 (2014).

## Computational setup (production runs)

| Item | Value |
| --- | --- |
| Code | Quantum ESPRESSO 7.5 + `lmodelhf` patch (`patch/ddrshcam-qe-7.5.patch`) |
| Structure | rocksalt fcc primitive cell |
| Lattice | **a = 4.186 Å** experimental (`celldm(1) = 7.9104` bohr) |
| Pseudopotentials | SG15 ONCV PBE (`Mg_ONCV_PBE-1.2.upf`, `O_ONCV_PBE-1.2.upf`) |
| Cutoffs | `ecutwfc = 80` Ry, `ecutrho = 320` Ry |
| k-mesh | 6×6×6 (converged, see audit) |
| Fock q-grid | 6×6×6 (converged, see audit) |

## Non-empirical DD-RSH-CAM parameters

From PBE `turbo_eels.x` static ε⁻¹(q) (RPA + crystal local fields) fit
(`runs/MgO/p2/eels/eps_q_clean.dat`, `scripts/fit_mu.py`):

| Parameter | Value |
| --- | ---: |
| ε∞ | 3.092 |
| AEXX = 1/ε∞ | 0.3234 |
| μ | 0.726 bohr⁻¹ |
| BEXX | 1.0 |
| Fit RMSE | 0.006 |

Model: ε⁻¹(q) = 1 − (1 − 1/ε∞) exp(−q²/4μ²).

## Band gaps (eV)

| Method | This work | Paper | Experiment |
| --- | ---: | ---: | ---: |
| PBE | 4.95 | 4.79 | — |
| DDH / global PBE0 (1/ε∞ from DFPT) | 8.11 | 7.70 | — |
| Approx. DD-HSE (QE HSE, LR Fock removed) | 5.23 | — | — |
| **Strict DD-RSH-CAM (production)** | **8.548** | **8.32** | **7.83** |
| Paper RS-DDH | — | 7.88 | — |

Production DD-RSH-CAM: `runs/MgO/p2/ddrshcam/mgo.nqx6.in` → gap **8.548 eV**
(HOMO 6.270 / LUMO 14.817 eV).

Earlier approximate pipeline (unpatched QE): `runs/MgO/01-pbe-scf` … `04-dd-hse`.

## Patch verification

Native QE vs `lmodelhf` reproduce **bit-for-bit** in both limits
(`runs/MgO/validate/`):

| Limit | Gap (eV) |
| --- | ---: |
| PBE0 (AEXX = BEXX = 0.25) | 7.2006 |
| HSE (AEXX = 0, BEXX = 0.25, μ = 0.106) | 6.4175 |

## Convergence (audit 2026-06-16)

Fitted parameters, a = 4.186 Å (`runs/MgO/p2/audit/`):

| Scan | Δ gap vs production |
| --- | ---: |
| nqx 3×3×3 → 6×6×6 | −0.126 eV |
| nqx 6×6×6 → 8×8×8 | 0.000 eV |
| k 6×6×6 → 8×8×8 | +0.015 eV |

Production gap **8.548 eV** is converged on k and nqx within ±0.02 eV.

Full audit table: [`MgO-audit.md`](MgO-audit.md).

## What this repository demonstrates

1. **Implementation** — true DD-RSH-CAM Fock kernel + semilocal complement in QE 7.5
   (not the approximate DD-HSE shortcut).
2. **Non-empirical workflow** — turboEELS ε⁻¹(q) → fit (ε∞, μ) → hybrid SCF.
3. **Physical placement** — strict gap 8.55 eV sits in the DD-RSH-CAM family (paper 8.32 eV,
   above experiment 7.83 eV), **not** near approximate DD-HSE (5.23 eV).

## What we do **not** claim

- **Numerical reproduction of Chen 2018 Table values** — same engine/pseudopotentials/lattice
  differ from the paper; +0.23 eV vs paper DD0-RSH-CAM is a **setup + parameter-pipeline**
  offset, not an implementation defect (see audit decomposition).
- **Experimental agreement** — DD-RSH-CAM overshoots experiment for MgO in the paper too.

## Known limitations

- μ from PBE-level turboEELS (QE DFPT/turboEELS are semilocal-only); documented in README.
- Hybrid ε∞ self-consistency via `epsilon.x` IPA is **not available** on DD-RSH-CAM saves in
  this QE toolchain (`non uniform kpt grid`); one SC iteration was not completed.

## Reproduce

```bash
# toolchain + patched pw.x (once)
scripts/make_build_env.sh
scripts/build_qe.sh   # after applying patch to ~/qe-7.5

# fit parameters
python3 scripts/fit_mu.py runs/MgO/p2/eels/eps_q_clean.dat

# production DD-RSH-CAM
cd runs/MgO/p2/ddrshcam && bash run_nqx6.sh

# regenerate audit table
python3 scripts/collect_audit_gaps.py
```

## Key paths

| Path | Content |
| --- | --- |
| `patch/ddrshcam-qe-7.5.patch` | Source patch |
| `runs/MgO/p2/eels/eps_q_clean.dat` | ε⁻¹(q) data |
| `runs/MgO/p2/ddrshcam/mgo.nqx6.in` | Production input |
| `runs/MgO/validate/` | PBE0/HSE limit checks |
| `runs/MgO/p2/audit/` | Convergence / decomposition runs |
| `results/MgO-qe-summary.json` | PBE + DFPT ε∞ (DDH pipeline) |
| `results/MgO-audit.md` | Detailed audit appendix |
