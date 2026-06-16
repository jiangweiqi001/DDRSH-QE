# Si (diamond) — strict DD-RSH-CAM in patched QE 7.5

Non-empirical DD-RSH-CAM pipeline applied to silicon, following the same
recipe validated on MgO: PBE SCF → turboEELS ε⁻¹(q) → fit (ε∞, μ) →
DD-RSH-CAM SCF → gap. Experimental targets from the
[EFT-ARPES-bench](https://github.com/kunyuan/EFT-ARPES-bench) `data/si.toml`.

## Setup

- Structure: diamond, ibrav 2, celldm(1) = 10.263 bohr (a = 5.431 Å, experimental).
- Pseudopotential: `Si_ONCV_PBE-1.2.upf` (SG15 ONCV scalar-relativistic PBE, NC).
- Cutoffs: ecutwfc 60 Ry, ecutrho 240 Ry; k-mesh 8×8×8 (PBE/eels), 6×6×6 (hybrid).
- Fock q-grid: nqx 6×6×6, `exxdiv_treatment = gygi-baldereschi`.

## Non-empirical parameters (from turboEELS ε⁻¹(q) fit)

| quantity | value | note |
| --- | ---: | --- |
| ε∞ | 10.95 | expt ε∞ ≈ 11.7 (PBE-RPA, no e–h) |
| μ (hfscreen) | 0.657 bohr⁻¹ | range-separation parameter |
| aexx = 1/ε∞ | 0.0913 | long-range Fock fraction |
| bexx | 1.0 | full short-range Fock |
| fit RMSE | 0.0074 | 8 q-points (q=1.00 dropped: turboEELS minus_q symmetry bug) |

## Gaps vs experiment

| method | indirect gap (eV) | direct Γ→Γ (eV) |
| --- | ---: | ---: |
| PBE (this build) | 0.60 | 2.55¹ |
| **strict DD-RSH-CAM** | **1.27** | **3.28** |
| experiment | 1.17 | 3.40 |
| G₀W₀ (HL 1986) | 1.29 | 3.35 |
| HSE06 | 1.16 | 3.32 |
| PBE0 | 1.97 | 3.96 |

¹ PBE direct gap from `ref.lda` in si.toml (not separately extracted here).

- DD-RSH-CAM indirect gap **1.27 eV** vs expt 1.17 eV → **+0.10 eV** (within the
  benchmark tolerance of 0.30 eV; essentially on top of G₀W₀ 1.29 eV).
- DD-RSH-CAM direct gap at Γ **3.28 eV** vs expt 3.40 eV → **−0.12 eV** (within
  tolerance; matches HSE06 3.32 and G₀W₀ 3.35).
- Both `must_open_gap` targets pass: PBE 0.60 eV → 1.27 eV opens the indirect gap
  to experiment without the PBE0 over-opening (1.97 eV).

## Files

```text
runs/Si/01-pbe-scf/si.scf.in       PBE baseline
runs/Si/p2/eels/si.scf.in          ground state for turboEELS
runs/Si/p2/eels/scan_q.sh          ε⁻¹(q) q-scan
runs/Si/p2/eels/eps_q_clean.dat    ε⁻¹(q) data (q=1.00 removed)
runs/Si/p2/ddrshcam/si.ddrshcam.in DD-RSH-CAM production (aexx=0.0913, μ=0.657, nqx6)
```

> Toolchain note: all QE steps use the self-built patched `~/qe-7.5/bin` (writes
> `charge-density.dat`); the conda `qe` build writes HDF5 which the self-built
> `turbo_eels.x` cannot read.
