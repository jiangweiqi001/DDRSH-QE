# Strict DD-RSH-CAM vs experiment — EFT-ARPES-bench subset

Non-empirical DD-RSH-CAM (patched QE 7.5) applied to the clean sp materials of the
[EFT-ARPES-bench](https://github.com/kunyuan/EFT-ARPES-bench) set. Each material runs
the same pipeline with **no empirical parameters**:

```
PBE SCF  →  turboEELS ε⁻¹(q)  →  fit (ε∞, μ)  →  DD-RSH-CAM SCF  →  gap
```

`aexx = 1/ε∞` (long-range Fock), `bexx = 1` (full short-range Fock), `μ = hfscreen`
from the fit; Fock q-grid nqx 6×6×6, `exxdiv = gygi-baldereschi`, SG15 ONCV PBE
norm-conserving pseudopotentials, experimental lattice constants from the bench TOMLs.

## Non-empirical parameters (from turboEELS fit)

| material | structure | a (bohr) | ε∞ (fit) | ε∞ (expt) | μ (bohr⁻¹) | aexx = 1/ε∞ |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Si | diamond | 10.263 | 10.95 | ~11.7 | 0.657 | 0.091 |
| C (diamond) | diamond | 6.741 | 5.40 | ~5.7 | 0.901 | 0.185 |
| MgO | rocksalt | 7.9104 | 3.09 | ~2.96 | 0.726 | 0.323 |
| NaCl | rocksalt | 10.573 | 2.53 | ~2.34 | 0.594 | 0.395 |
| LiF | rocksalt | 7.605 | 2.04 | ~1.9 | 0.725 | 0.490 |

## Band gaps vs experiment (eV)

| material | gap type | PBE | **DD-RSH-CAM** | expt | error | G₀W₀ | HSE06 | PBE0 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Si | indirect | 0.60 | **1.27** | 1.17 | **+0.10** | 1.29 | 1.16 | 1.97 |
| Si | direct Γ→Γ | — | **3.28** | 3.40 | **−0.12** | 3.35 | 3.32 | 3.96 |
| C | indirect | 4.18 | **5.67** | 5.48 | **+0.19** | 5.50 | 5.42 | 6.66 |
| C | direct Γ→Γ | — | **7.50** | 7.30 | **+0.20** | 7.50 | 7.04 | 8.40 |
| NaCl | direct Γ→Γ | 5.21 | **8.88** | 8.97 | **−0.09** | 8.7 | 6.56 | 8.5 |
| MgO | direct Γ→Γ | 4.95 | **8.55** | 7.83 | **+0.72** | 7.69 | 6.51 | 7.23 |
| LiF | direct Γ→Γ | 9.15 | **15.90** | 14.20 | **+1.70** | 14.3 | 11.50 | 14.7 |

(G₀W₀/HSE06/PBE0 columns are literature values from the bench TOMLs; MgO row from
`results/MgO-results.md`.)

## Verdict against the benchmark tolerances

| material | tol (eV) | DD-RSH-CAM error | pass? |
| --- | ---: | ---: | :--: |
| Si (indirect) | 0.30 | +0.10 | ✅ |
| Si (direct) | 0.30 | −0.12 | ✅ |
| C (indirect) | 0.40 | +0.19 | ✅ |
| C (direct) | 0.40 | +0.20 | ✅ |
| NaCl | 0.40 | −0.09 | ✅ |
| MgO | 0.50 | +0.72 | ❌ (over) |
| LiF | 0.50 | +1.70 | ❌ (over) |

## What the numbers say

- **Covalent / mid-gap (Si, C, NaCl): excellent.** All within ≤0.2 eV of experiment,
  essentially on top of G₀W₀ and far better than PBE0's systematic over-opening. The
  non-empirical 1/ε∞ + screened long-range Fock recipe works cleanly here.
- **`must_open_gap` passes everywhere.** Every material opens from the PBE value to
  near experiment (e.g. NaCl 5.21 → 8.88, C 4.18 → 5.67) without the empirical 25%
  mixing of PBE0.
- **Most ionic wide-gap oxide/fluoride over-open (MgO +0.72, LiF +1.70).** As ε∞ drops
  (aexx → 0.5), strict DD-RSH-CAM with full short-range Fock (`bexx = 1`) overshoots.
  LiF lands at 15.90 eV — right on **QSGW (15.9)**, which is also known to overshoot
  before the electron–hole vertex correction brings it back to ~14.5. This is a real
  physical trend (more screening error where ε∞ is smallest), not a code defect: the
  PBE0/HSE limits are still reproduced bit-for-bit (see `results/MgO-results.md`).

## Files

```text
runs/Si/   runs/C/   runs/LiF/   runs/NaCl/     per-material PBE, eels, ddrshcam inputs
scripts/scan_eps_q.sh                           generic turboEELS ε⁻¹(q) q-scan
results/Si-results.md                           Si detail
```

> Toolchain notes: all QE steps use the self-built patched `~/qe-7.5/bin` (writes
> `charge-density.dat`; the conda `qe` build writes HDF5 that self-built `turbo_eels.x`
> cannot read). turboEELS fails at q=1.00 (2π/a) with a `minus_q` symmetry bug; that q
> is auto-skipped by `scan_eps_q.sh`. NaCl uses ecutwfc 50 Ry (gap converged to 0.002 eV
> vs 80 Ry; the soft alkali halide does not need the 80 Ry used for the harder solids).
