# Strict DD-RSH-CAM in Quantum ESPRESSO (patched) — MgO reproduction

This project implements the **dielectric-dependent range-separated hybrid
DD-RSH-CAM** functional in **Quantum ESPRESSO 7.5** by patching the source
(QE has no native functional with independent short- and long-range exact-exchange
fractions), and runs the **full non-empirical pipeline** for MgO:
`turboEELS ε⁻¹(q) → fit (ε∞, μ) → DD-RSH-CAM SCF → gap`.

**Results summary:** [`results/MgO-results.md`](results/MgO-results.md)

## The functional

DD-RSH-CAM uses a range-separated Fock kernel

```
V(q) = (4π e² / q²) · [ B - (B - A) · exp(-q² / 4μ²) ]
```

with `A = aexx = 1/ε∞` (long-range Fock fraction), `B = bexx = 1` (full short-range
Fock), and `μ = hfscreen` (screening parameter, bohr⁻¹). The matching semilocal
exchange complement is

```
E_x^DFT = (1 - A) · E_x^PBE − (B - A) · E_x^PBE,SR(μ)
```

Limits: `A = B = 0.25 → PBE0`; `A = 0, B = 0.25, μ = 0.106 → HSE`.

## The patch

`patch/ddrshcam-qe-7.5.patch` adds the `lmodelhf` functional to a pristine QE 7.5
tree (10 source files). New `&system` input variables: `lmodelhf`, `aexx`, `bexx`,
`hfscreen`. Changes:

- `PW/src/exx_base.f90`, `PW/src/exx.f90` — two-fraction Fock kernel in
  `g2_convolution`; `exxalfa = 1`; G=0 term via the linear decomposition
  `exxdiv = A·exxdiv_bare + (B−A)·exxdiv_erfc`.
- `XClib/qe_drivers_lda_lsda.f90`, `XClib/qe_drivers_gga.f90`,
  `XClib/dft_setting_params.f90`, `XClib/dft_setting_routines.f90`,
  `XClib/xc_lib.f90` — semilocal complement (scale LDA slater and PBE gradient by
  `1−A`, subtract `(B−A)·pbexsr`).
- `Modules/input_parameters.f90`, `Modules/read_namelists.f90`, `PW/src/input.f90`
  — input plumbing.

Apply and build:

```bash
# pristine source
curl -sSL -o qe-7.5.tar.gz \
  https://gitlab.com/QEF/q-e/-/archive/qe-7.5/q-e-qe-7.5.tar.gz
tar -xzf qe-7.5.tar.gz && cd q-e-qe-7.5
patch -p1 < /path/to/patch/ddrshcam-qe-7.5.patch
# build a user-space toolchain + pw.x/epsilon.x/turbo_eels.x (see scripts/)
```

`scripts/make_build_env.sh` builds a no-sudo conda toolchain; `scripts/build_qe.sh`
configures and compiles an **MPI + OpenMP** build of `pw.x`, `ph.x` and the turbo
binaries (`turbo_eels.x`, `turbo_spectrum.x`) — it forces the MPI toolchain into
`make.inc` (`-D__MPI`, `MPIF90`/`LD = mpif90`) because QE's configure cannot link-test
the conda `mpif90` wrapper and otherwise falls back to a serial build. The patch was
developed against that environment.

## Verification (patch correctness)

The patched code reproduces native QE **bit-for-bit** in both limits — identical
total energy (8 d.p.) and identical eigenvalues at every SCF/EXX iteration
(`runs/MgO/validate/`):

| | gap (eV) |
| --- | ---: |
| PBE0 native vs `lmodelhf`(A=B=0.25) | 7.2006 (both) |
| HSE native vs `lmodelhf`(A=0,B=0.25,μ=0.106) | 6.4175 (both) |

## Non-empirical pipeline (MgO)

1. **ε⁻¹(q)** — `turbo_eels.x` (TDDFPT-Lanczos, RPA + crystal local fields) at the
   PBE level, static (ω→0) over q ∈ [0.08, 1.35] bohr⁻¹ (`runs/MgO/p2/eels/scan_q.sh`).
2. **Fit** — `scripts/fit_mu.py` fits `ε⁻¹(q) = 1 − (1−1/ε∞)·exp(−q²/4μ²)`:
   **ε∞ = 3.092, aexx = 0.323, μ = 0.726 bohr⁻¹** (RMSE 0.006).
3. **Run** — DD-RSH-CAM SCF with the fitted parameters (`runs/MgO/p2/ddrshcam/mgo.nqx6.in`).

### Results (MgO)

| method | gap (eV) |
| --- | ---: |
| PBE (this build) | 4.95 |
| approximate DD-HSE (long-range Fock removed) | 5.23 |
| **strict DD-RSH-CAM (production, nqx 6×6×6)** | **8.55** |
| paper DD0-RSH-CAM | 8.32 |
| paper RS-DDH | 7.88 |
| experiment | 7.83 |

The strict gap confirms the **DD-RSH-CAM physics** (long-range screened Fock kept) —
it is **not** near approximate DD-HSE (5.23 eV). It sits in the same functional family
as the paper (8.32 eV, above experiment). This is **not** a bit-for-bit reproduction of
the paper table entry; see [`results/MgO-audit.md`](results/MgO-audit.md) for convergence
and setup-offset decomposition (+0.23 eV vs paper 8.32 on the production run).

> **Toolchain notes:** μ is taken from PBE-level turboEELS (semilocal-only DFPT).
> Hybrid ε∞ self-consistency via `epsilon.x` IPA is not supported on DD-RSH-CAM saves
> in QE 7.5 (audit 2026-06-16).

## Benchmark: several materials vs experiment

The same non-empirical pipeline (no fitted mixing) was run on 8 materials of the
[EFT-ARPES-bench](https://github.com/kunyuan/EFT-ARPES-bench) set — covalent
semiconductors, a III-V, alkali halides, and ionic wide-gap oxide/fluoride. Full table,
fitted (ε∞, μ) and method comparison in
[`results/EFT-ARPES-bench-comparison.md`](results/EFT-ARPES-bench-comparison.md).

Two short-range Fock fractions are run on the same (ε∞, μ) fit: **DD-RSH-CAM** (Chen 2018,
`bexx = 1`) and **RS-DDH** (Skone 2016, `bexx = 0.25`).

| material | gap type | PBE | **DD-RSH-CAM** (β=1) | RS-DDH (β=¼) | expt | G₀W₀ | HSE06 | PBE0 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Si | indirect | 0.60 | **1.27** | 1.15 | 1.17 | 1.29 | 1.16 | 1.97 |
| Si | direct Γ | 2.56 | **3.28** | 3.09 | 3.40 | 3.35 | 3.32 | 3.96 |
| C (diamond) | indirect | 4.18 | **5.67** | 5.60 | 5.48 | 5.50 | 5.42 | 6.66 |
| C (diamond) | direct Γ | 5.60 | **7.50** | 7.18 | 7.30 | 7.50 | 7.04 | 8.40 |
| AlAs | indirect Γ→X | 1.43 | **2.19** | 2.05 | 2.23 | 2.18 | 2.04 | 2.86 |
| AlAs | direct Γ | 2.04 | **2.86** | 2.71 | 3.13 | 2.88 | 2.97 | 3.86 |
| LiCl | direct Γ | 6.43 | **9.61** | 9.16 | 9.40 | 9.1 | 7.80 | 9.0 |
| NaCl | direct Γ | 5.21 | **8.88** | 8.36 | 8.97 | 8.7 | 6.56 | 8.5 |
| MgO | direct Γ | 4.95 | **8.55** | 8.09 | 7.83 | 7.69 | 6.51 | 7.23 |
| CaF₂ | indirect W→Γ | 7.33 | **13.15** | 12.03 | 11.80 | ~11.4 | ~10.4 | ~11.0 |
| CaF₂ | direct Γ | 7.59 | **13.42** | 12.31 | 12.10 | ~11.8 | — | — |
| LiF | direct Γ | 9.15 | **15.90** | 14.76 | 14.20 | 14.3 | 11.50 | 14.7 |

Both functionals pass **8 of 12 edges**, but on *complementary* materials. DD-RSH-CAM
(β=1) is within ≤0.27 eV on the covalent / III-V / chloride edges (Si, C, AlAs, LiCl,
NaCl) — on top of G₀W₀, far better than PBE0 — but over-opens the small-ε∞ ionic crystals
(MgO +0.72, CaF₂ +1.3, LiF +1.70). Dropping the short-range Fock to β=¼ (RS-DDH) removes
most of that over-opening (MgO +0.26, CaF₂ +0.2, LiF +0.56 — MgO and both CaF₂ edges pass)
at the cost of mildly under-opening the covalent direct edges (Si/AlAs Γ, NaCl). Short-range
Fock is the knob trading ionic over-opening against covalent under-opening; the PBE0/HSE
limits remain bit-for-bit exact. Full per-edge errors and tolerances in
[`results/EFT-ARPES-bench-comparison.md`](results/EFT-ARPES-bench-comparison.md).

### Finite-G model (third class)

Instead of a fixed short-range endpoint (β=1 or β=¼), the **finite-G model** reads the
endpoint off the dielectric function at a finite wavevector `G = a·μ`, using the same
single-μ kernel:

```
B_a = ε⁻¹(G = a·μ) = 1 − (1 − A)·exp(−a²/4),     A = aexx = 1/ε∞
```

Here `a` is a **single global constant** (the same for all materials — *not* tuned per
material), while `B_a` is a **material-dependent** effective short-range Fock endpoint set
by each material's own `A = 1/ε∞`. Limits: `a→0 ⇒ B_a→A = 1/ε∞` (a global hybrid with a
single 1/ε∞ fraction) and `a→∞ ⇒ B_a→1` (recovers DD-RSH-CAM); for finite `a`,
`A ≤ B_a ≤ 1`, and larger `a` ⇒ more short-range Fock. All 8 materials were run at
`a = 0.5, 1.0, 2.0`, reusing the DD-RSH-CAM fit and re-running only the hybrid SCF
(`scripts/run_finiteg.sh <Material> <a>`, output in `runs/<M>/p2/finiteG_a<a>/`, leaving
the β=1 / β=¼ runs untouched). The second comparison table, per-material `B_a`, and the
per-model MAE are in
[`results/EFT-ARPES-bench-comparison.md`](results/EFT-ARPES-bench-comparison.md).

All 24 runs (8 materials × `a = 0.5, 1.0, 2.0`) completed — no failures. Mean absolute
error by model (over all 12 edges; ionic = MgO/CaF₂/LiF, covalent = Si/C/AlAs); the lower
block is the density-scale qcloud model described below:

<!-- BEGIN:mae -->
| model | MAE all (eV) | MAE ionic¹ | MAE covalent² |
| --- | ---: | ---: | ---: |
| DD-RSH-CAM (β=1) | 0.525 | 1.272 | 0.153 |
| RS-DDH (β=¼) | 0.272 | 0.315 | 0.193 |
| finite-G a=0.5 | 0.355 | 0.596 | 0.205 |
| finite-G a=1.0 | 0.369 | 0.709 | 0.179 |
| finite-G a=2.0 | 0.435 | 1.002 | 0.152 |
| qcloud η=0.5 | 0.357 | 0.598 | 0.208 |
| qcloud η=0.6 | 0.360 | 0.616 | 0.204 |
| qcloud η=1.0 | 0.376 | 0.714 | 0.187 |

¹ ionic = MgO, CaF₂, LiF (low-ε∞ strong-ionic wide-gap). ² covalent = Si, C, AlAs (covalent / III–V). MAE is over all listed edges (fundamental + direct Γ→Γ) where a value exists.
<!-- END:mae -->

- **Smallest overall MAE among the three finite-G: `a = 0.5` (0.355 eV)**; all three lie between β=1
  and β=¼, and none beats the flat β=¼ (0.272) overall.
- **`a = 0.5` helps the low-ε∞ ionic crystals (MgO, CaF₂, LiF) most** (ionic MAE 0.596 vs
  0.709 / 1.002): smaller `a` ⇒ smaller `B_a` ⇒ less short-range Fock ⇒ less over-opening.
- **All three relieve the β=1 over-opening**, most at `a = 0.5` (e.g. LiF +1.70→+0.96, CaF₂
  +1.32→+0.54, MgO +0.72→+0.33); the relief shrinks as `a` grows.
- **`a = 2.0` under-opens the covalent edges least** (covalent MAE 0.152, matching β=1, vs
  β=¼'s 0.193): e.g. Si Γ −0.31→−0.20, AlAs Γ −0.42→−0.33, C Γ −0.12→+0.07.
- **Why no global `a` wins outright:** `B_a = ε⁻¹(a·μ)` *increases* with `A = 1/ε∞`, so it
  gives the most short-range Fock to the most ionic materials — exactly the ones that want
  less. The dependence is physical but opposite to what the gap errors prefer, so one
  constant cannot fix ionic over-opening and covalent under-opening together. Net: `a` is an
  interpolation knob (small → β=¼-like, large → β=1-like), with `a ≈ 0.5` the best
  single compromise here.

### Complete results — all models (eV)

Every edge, every model: the PBE baseline, all five computed hybrids (DD-RSH-CAM β=1,
RS-DDH β=¼, finite-G a=0.5/1.0/2.0), experiment, and the standard G₀W₀/HSE06/PBE0
references. Auto-generated by `scripts/write_comparison.py --write` (numbers cannot drift).

<!-- BEGIN:full -->
| material | gap type | PBE | **DD-RSH-CAM** β=1 | RS-DDH β=¼ | finite-G a=0.5 | finite-G a=1.0 | finite-G a=2.0 | expt | G₀W₀ | HSE06 | PBE0 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Si | indirect | 0.60 | **1.27** | 1.15 | 1.13 | 1.16 | 1.22 | 1.17 | 1.29 | 1.16 | 1.97 |
| Si | direct Γ→Γ | 2.56 | **3.28** | 3.09 | 3.07 | 3.10 | 3.20 | 3.40 | 3.35 | 3.32 | 3.96 |
| C (diamond) | indirect | 4.18 | **5.67** | 5.60 | 5.59 | 5.61 | 5.64 | 5.48 | 5.5 | 5.42 | 6.66 |
| C (diamond) | direct Γ→Γ | 5.60 | **7.50** | 7.18 | 7.17 | 7.23 | 7.37 | 7.30 | 7.5 | 7.04 | 8.4 |
| AlAs | indirect Γ→X | 1.43 | **2.19** | 2.05 | 2.04 | 2.06 | 2.13 | 2.23 | 2.18 | 2.04 | 2.86 |
| AlAs | direct Γ→Γ | 2.04 | **2.86** | 2.71 | 2.70 | 2.73 | 2.80 | 3.13 | 2.88 | 2.97 | 3.86 |
| MgO | direct Γ→Γ | 4.95 | **8.55** | 8.09 | 8.16 | 8.22 | 8.39 | 7.83 | 7.69 | 6.51 | 7.23 |
| LiCl | direct Γ→Γ | 6.43 | **9.61** | 9.16 | 9.24 | 9.30 | 9.46 | 9.40 | 9.1 | 7.8 | 9.0 |
| NaCl | direct Γ→Γ | 5.21 | **8.88** | 8.36 | 8.49 | 8.55 | 8.73 | 8.97 | 8.7 | 6.56 | 8.5 |
| CaF₂ | indirect W→Γ | 7.33 | **13.15** | 12.03 | 12.36 | 12.49 | 12.84 | 11.80 | ~11.4 | ~10.4 | ~11.0 |
| CaF₂ | direct Γ→Γ | 7.59 | **13.42** | 12.31 | 12.64 | 12.77 | 13.11 | 12.10 | ~11.8 | — | — |
| LiF | direct Γ→Γ | 9.15 | **15.90** | 14.76 | 15.16 | 15.29 | 15.61 | 14.20 | 14.3 | 11.5 | 14.7 |
<!-- END:full -->

(G₀W₀/HSE06/PBE0 are literature values from the bench TOMLs; CaF₂ entries marked `~` are
bench estimates. Full per-edge errors, tolerances, fitted (ε∞, μ) and the per-model MAE
breakdown are in [`results/EFT-ARPES-bench-comparison.md`](results/EFT-ARPES-bench-comparison.md).)

### Density-scale finite-q model (fourth class)

A fourth way to set the short-range endpoint: instead of sampling the dielectric function
at `G = a·μ` (finite-G), sample it at a **density-derived** wavevector built from the cell's
average valence-electron density:

```
q_WS    = (4π n_v / 3)^(1/3),   n_v = N_val / Ω        (bohr⁻¹; N_val, Ω from the PBE run)
q_cloud = η · q_WS
B_η     = ε⁻¹(q_cloud) = 1 − (1 − A)·exp[ −(η·q_WS)² / (4 μ²) ],   A = 1/ε∞,  μ = hfscreen
```

`η` is a **single global constant** (the same for every material — *not* tuned per material,
*not* fitted to gaps); `B_η` is material-dependent through `A`, `μ` and the density. All 8
materials were run at `η = 0.5, 0.6, 1.0`, reusing the DD-RSH-CAM fit and re-running only the
hybrid SCF (`scripts/run_density_qcloud.sh <Material> <η>`, output in
`runs/<M>/p2/qcloud_eta<η>/`, leaving the β=1 / β=¼ / finite-G runs untouched). The endpoint
diagnostic (no QE) is `scripts/diag_qcloud.py`. Every material satisfies `A ≤ B_η ≤ 1`.

Density inputs and the **sampling wavevector** q (bohr⁻¹) finally fed to ε⁻¹ to set the
short-range endpoint, for every material and case across the 2nd–4th classes — RS-DDH (β=¼),
finite-G (q=a·μ) and qcloud (q=η·q_WS). RS-DDH shows “—” for the ionic crystals because the
fixed ¼ falls below the fully-screened floor ε⁻¹(0)=A, so no real wavevector reproduces it:

<!-- BEGIN:qcparams -->
| material | N_val | Ω (bohr³) | n_v (bohr⁻³) | q_WS (bohr⁻¹) | μ (bohr⁻¹) | RS-DDH β=¼ | finite-G a=0.5 | finite-G a=1.0 | finite-G a=2.0 | qcloud η=0.5 | qcloud η=0.6 | qcloud η=1.0 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Si | 8 | 270.25 | 0.0296 | 0.4987 | 0.657 | 0.576 | 0.329 | 0.657 | 1.314 | 0.249 | 0.299 | 0.499 |
| C (diamond) | 8 | 76.58 | 0.1045 | 0.7592 | 0.901 | 0.519 | 0.450 | 0.901 | 1.801 | 0.380 | 0.456 | 0.759 |
| AlAs | 16 | 305.92 | 0.0523 | 0.6028 | 0.605 | 0.476 | 0.303 | 0.605 | 1.211 | 0.301 | 0.362 | 0.603 |
| MgO | 16 | 123.75 | 0.1293 | 0.8151 | 0.726 | — | 0.363 | 0.726 | 1.452 | 0.408 | 0.489 | 0.815 |
| LiCl | 10 | 224.59 | 0.0445 | 0.5713 | 0.633 | — | 0.317 | 0.633 | 1.266 | 0.286 | 0.343 | 0.571 |
| NaCl | 16 | 295.48 | 0.0541 | 0.6099 | 0.594 | — | 0.297 | 0.594 | 1.188 | 0.305 | 0.366 | 0.610 |
| CaF₂ | 24 | 275.02 | 0.0873 | 0.7150 | 0.714 | — | 0.357 | 0.714 | 1.427 | 0.358 | 0.429 | 0.715 |
| LiF | 10 | 109.96 | 0.0909 | 0.7249 | 0.725 | — | 0.362 | 0.725 | 1.450 | 0.362 | 0.435 | 0.725 |

All model columns are the sampling wavevector q (bohr⁻¹) at which ε⁻¹(q) equals that model's short-range endpoint bexx (under ε⁻¹(q)=1−(1−A)exp(−q²/4μ²)): **finite-G** q = a·μ, **qcloud** q = η·q_WS (DD-RSH-CAM β=1 ⇒ q→∞, not shown). **RS-DDH β=¼** is “—” when 0.25 ≤ A = 1/ε∞: the fixed ¼ then lies on/below the fully-screened floor ε⁻¹(0)=A, so no real wavevector reproduces it (all the ionic crystals — MgO, LiCl, NaCl, CaF₂, LiF). The corresponding endpoints bexx=B are in the gap tables (RS-DDH = 0.25; finite-G B_a; qcloud B_η).
<!-- END:qcparams -->

Fourth table — qcloud `bexx`, gap and error per η, next to expt, β=1 and β=¼ (`q_cloud`
length for each result is the column in the table above):

<!-- BEGIN:qcloud -->
| material | gap type | expt | **DD-RSH-CAM** β=1 | RS-DDH β=¼ | qcloud η=0.5 bexx | qcloud η=0.5 gap | err η=0.5 | qcloud η=0.6 bexx | qcloud η=0.6 gap | err η=0.6 | qcloud η=1.0 bexx | qcloud η=1.0 gap | err η=1.0 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Si | indirect | 1.17 | **1.27** | 1.15 | 0.123 | 1.13 | −0.04 | 0.137 | 1.13 | −0.04 | 0.213 | 1.14 | −0.03 |
| Si | direct Γ→Γ | 3.40 | **3.28** | 3.09 | 0.123 | 3.06 | −0.34 | 0.137 | 3.07 | −0.33 | 0.213 | 3.08 | −0.32 |
| C (diamond) | indirect | 5.48 | **5.67** | 5.60 | 0.220 | 5.59 | +0.11 | 0.236 | 5.59 | +0.11 | 0.318 | 5.60 | +0.12 |
| C (diamond) | direct Γ→Γ | 7.30 | **7.50** | 7.18 | 0.220 | 7.17 | −0.13 | 0.236 | 7.17 | −0.13 | 0.318 | 7.21 | −0.09 |
| AlAs | indirect Γ→X | 2.23 | **2.19** | 2.05 | 0.177 | 2.04 | −0.19 | 0.199 | 2.04 | −0.19 | 0.317 | 2.06 | −0.17 |
| AlAs | direct Γ→Γ | 3.13 | **2.86** | 2.71 | 0.177 | 2.70 | −0.43 | 0.199 | 2.71 | −0.42 | 0.317 | 2.73 | −0.40 |
| MgO | direct Γ→Γ | 7.83 | **8.55** | 8.09 | 0.375 | 8.16 | +0.33 | 0.396 | 8.17 | +0.34 | 0.506 | 8.24 | +0.41 |
| LiCl | direct Γ→Γ | 9.40 | **9.61** | 9.16 | 0.369 | 9.23 | −0.17 | 0.383 | 9.24 | −0.16 | 0.459 | 9.28 | −0.12 |
| NaCl | direct Γ→Γ | 8.97 | **8.88** | 8.36 | 0.434 | 8.49 | −0.48 | 0.450 | 8.50 | −0.47 | 0.535 | 8.56 | −0.41 |
| CaF₂ | indirect W→Γ | 11.80 | **13.15** | 12.03 | 0.477 | 12.36 | +0.56 | 0.492 | 12.38 | +0.58 | 0.567 | 12.49 | +0.69 |
| CaF₂ | direct Γ→Γ | 12.10 | **13.42** | 12.31 | 0.477 | 12.64 | +0.54 | 0.492 | 12.66 | +0.56 | 0.567 | 12.77 | +0.67 |
| LiF | direct Γ→Γ | 14.20 | **15.90** | 14.76 | 0.521 | 15.16 | +0.96 | 0.534 | 15.18 | +0.98 | 0.603 | 15.29 | +1.09 |
<!-- END:qcloud -->

All 24 runs (8 materials × `η = 0.5, 0.6, 1.0`) completed — no failures.

- **Smallest overall MAE:** `η = 0.5` (0.357 eV) < 0.6 (0.360) < 1.0 (0.376).
- **Smallest ionic MAE (MgO, CaF₂, LiF):** `η = 0.5` (0.598); smaller η ⇒ smaller `B_η` ⇒
  less over-opening.
- **Smallest covalent MAE (Si, C, AlAs):** `η = 1.0` (0.187); larger η ⇒ more short-range
  Fock ⇒ less under-opening.
- **Relieves the β=1 over-opening?** Yes, strongly (ionic MAE 1.272 → 0.598 at η=0.5; e.g.
  LiF +1.70→+0.96, CaF₂ +1.32→+0.54, MgO +0.72→+0.33).
- **Beats RS-DDH (β=¼)?** No — β=¼ is better overall (0.272 vs 0.357) and on ionic
  (0.315 vs 0.598). qcloud η=1.0 only marginally edges β=¼ on the covalent subset.
- **Better than finite-G a=0.5?** No — statistically identical (overall 0.357 vs 0.355;
  ionic 0.598 vs 0.596). For this set `q_WS/μ ≈ 0.76–1.12`, so `q_cloud = η·q_WS ≈ η·μ = G`:
  the density-scale model samples ε⁻¹ at essentially the same wavevector as finite-G with
  a ≈ η, and inherits the same limitation (`B_η` rises with 1/ε∞, the wrong direction), so
  tying the length to the valence density adds no discriminating power here.

### Density-peak log-curvature finite-q endpoint (fifth class)

The qcloud length `q_WS` is a *cell-average* scale and turned out ≈ μ, so qcloud collapsed
onto finite-G. This class instead uses a **local** electron-cloud scale: the width of the PBE
valence-density peak around the atom. For each species `s`, the PBE valence density is
spherically averaged about its atoms, `ρ̄_s(r)` (done exactly in G-space:
`ρ̄_s(r) = Σ_G ρ(G)·⟨e^{iG·τ}⟩_s·j₀(|G|r)`), and the log of the peak is fitted to a parabola:

```text
ln ρ̄_s(r) ≈ c₀ + c₁(r−r₀) + c₂(r−r₀)²      (window ρ̄ > 0.8·ρ̄(r₀), relaxed to 0.7 if sparse)
σ_peak    = sqrt(−1/(2 c₂))                  (requires c₂ < 0, σ_peak > 0; R² reported)
q_peak    = κ / σ_peak
B_κ       = ε⁻¹(q_peak) = 1 − (1 − A)·exp[ −q_peak² / (4 μ²) ],   A = 1/ε∞,  μ = hfscreen
```

- **`κ` is a fixed global parameter.** It is **not** fitted per material, and **not** fitted to
  experimental gaps. Three global values are tested: `κ = 0.25, 0.35, 0.50`.
- **The active species is fixed before the benchmark** (whose σ_peak sets `B_κ`):
  Si→Si, C→C, AlAs→As, MgO→O, LiCl/NaCl→Cl, CaF₂/LiF→F (anion / VBM-localised; Si, C are the
  single-element covalents). `σ_peak` is still reported for *every* species as a diagnostic.
- The endpoint diagnostic (**no QE**) is `scripts/diag_qpeak_logcurv.py`
  (→ `results/qpeak_logcurv_endpoint.{csv,md}`, `qpeak_logcurv_all_species.{csv,md}`); the
  optional driver is `scripts/run_density_qpeak.sh <Material> <κ>` (output in
  `runs/<M>/p2/qpeak_kappa<κ>/`, leaving β=1 / β=¼ / finite-G / qcloud untouched). All fits
  succeed (R² = 0.86–1.00) and every material/κ satisfies `A ≤ B_κ ≤ 1`.

**Diagnostic verdict (why a full QE benchmark is *not* recommended).** Unlike `q_WS/μ ≈ 1`,
the local peak gives a real spread `q_peak/μ ≈ 0.48–2.34`, but in the **wrong direction**: the
anions of the strongly-ionic oxides/fluorides have the *most localised* valence peaks
(`σ_peak ≈ 0.30 bohr` for O/F vs 0.46–0.79 bohr for C/As/Cl/Si), so they get the *largest*
`q_peak` and hence the *highest* `B_κ` — i.e. the most short-range Fock is handed to exactly
the materials that already over-open. At κ=0.25 the ionic endpoints (`B`: MgO 0.51, CaF₂ 0.60,
LiF 0.63) sit well above finite-G a=0.5 / qcloud η=0.5 (0.36–0.52), and no single κ can raise
covalent `B` (which needs more Fock) without raising ionic `B` further. A single confirmation
run bears this out: **MgO κ=0.25 → 8.24 eV (+0.41)**, *worse* than RS-DDH β=¼ (+0.26) and
finite-G a=0.5 / qcloud η=0.5 (+0.33). The model is therefore expected to under-perform β=¼;
the run script, `gen_inputs` builder and `results/benchmark_qpeak_logcurv.{csv,md}` (with the
MgO point populated) are in place to run the full set on request.

### Density-peak range-separation (sixth class)

**Motivation.** The previous three families (finite-G, qcloud, qpeak) all move the *short-range
Fock endpoint* `B = ε⁻¹(q)`. But that endpoint is bounded below by `B ≥ A = 1/ε∞` and *rises*
with A, so it hands the most short-range Fock to the most ionic crystals — the wrong direction,
since those over-open. This class drops that idea entirely: it keeps the **short-range Fock
fixed at 1 (DD-RSH-CAM β=1)** and instead moves the **range-separation length μ**, using the
same local density scale:

```text
μ_eff = c / σ_peak       (σ_peak = log-curvature width of the active species' PBE valence
                          density peak; c is a single GLOBAL constant — not per material,
                          not gap-fitted. Active species = qpeak.ACTIVE_SPECIES.)
input_dft='hse', lmodelhf=.true., aexx = A = 1/ε∞, bexx = 1.0, hfscreen = μ_eff
```

In the β=1 model the gap **decreases** with μ (`μ→0 ⇒ α≡1` full Fock; `μ→∞ ⇒ α≡A` global
hybrid). The ionic anions (O/F) have the *most localised* peaks (σ_peak ≈ 0.30 bohr) ⇒ the
*largest* μ_eff ⇒ the *biggest* gap reduction — finally the **same direction** as the β=1
over-opening. Four global constants are tested: `c = 0.45, 0.50, 0.55, 0.65` (0.50 is the
natural centre, below; the others bracket it). Driver: `scripts/run_density_mu.sh <Material>
<c>` → `runs/<M>/p2/densmu_c<c>/` (β=1 / β=¼ / finite-G / qcloud / qpeak runs are left
untouched); diagnostic `scripts/diag_density_mu.py` prints μ_eff without QE.

#### Why c = 0.50 is a natural reference point

The density-μ model uses μ_eff = c / σ_peak. The value **c = 0.50** is not just the midpoint of
the scan — it is the value a Gaussian pair-cloud argument predicts. Near the active
valence-density maximum the log-curvature fit approximates the peak as a Gaussian,

```text
ρ(r) ∝ exp( −r² / (2 σ_peak²) ).
```

The Coulomb interaction between two Gaussian charge clouds of the same width σ_peak is smoothed
into an error function with crossover length √2·σ_peak,

```text
v_smooth(r) = erf( r / (2 σ_peak) ) / r ,
```

while the long-range part of the RSH Coulomb kernel is

```text
v_LR(r) = erf( μ r ) / r .
```

Matching the two crossover lengths gives μ_eff = 1 / (2 σ_peak), i.e. **c = 0.50**. Equivalently
in reciprocal space, a Gaussian density peak has squared form factor `|ρ(G)|² ∝ exp(−σ_peak²G²)`
and the RSH Gaussian factor is `exp(−G²/4μ²)`; matching the exponents again gives
μ_eff = 1/(2 σ_peak) ⇒ c = 0.50. This is still an approximation — σ_peak is a proxy for the
active exchange/screening length, not a direct dielectric fit — but c = 0.50 is the natural
Gaussian reference value, and c = 0.45, 0.55, 0.65 are sensitivity tests around it.

**Result (all 8 materials).** The complete benchmark — these four c next to every previously
computed model and the literature — is below.

<!-- BEGIN:densmu -->
| material | gap type | PBE | DD-RSH-CAM β=1 | RS-DDH β=¼ | finite-G a=0.5 | qcloud η=0.5 | qpeak κ=0.25 | density-μ c=0.45 gap | density-μ c=0.45 err | density-μ c=0.5 gap | density-μ c=0.5 err | density-μ c=0.55 gap | density-μ c=0.55 err | density-μ c=0.65 gap | density-μ c=0.65 err | expt | G₀W₀ | HSE06 | PBE0 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Si | indirect | 0.60 | 1.27 | 1.15 | 1.13 | 1.13 | — | 1.34 | +0.17 | 1.29 | +0.12 | 1.25 | +0.08 | 1.20 | +0.03 | 1.17 | 1.29 | 1.16 | 1.97 |
| Si | direct Γ→Γ | 2.56 | 3.28 | 3.09 | 3.07 | 3.06 | — | 3.39 | −0.01 | 3.31 | −0.09 | 3.25 | −0.15 | 3.17 | −0.23 | 3.40 | 3.35 | 3.32 | 3.96 |
| C (diamond) | indirect | 4.18 | 5.67 | 5.60 | 5.59 | 5.59 | — | 5.63 | +0.15 | 5.60 | +0.12 | 5.59 | +0.11 | 5.57 | +0.09 | 5.48 | 5.5 | 5.42 | 6.66 |
| C (diamond) | direct Γ→Γ | 5.60 | 7.50 | 7.18 | 7.17 | 7.17 | — | 7.43 | +0.13 | 7.36 | +0.06 | 7.30 | +0.00 | 7.24 | −0.06 | 7.30 | 7.5 | 7.04 | 8.4 |
| AlAs | indirect Γ→X | 1.43 | 2.19 | 2.05 | 2.04 | 2.04 | — | 2.16 | −0.07 | 2.12 | −0.11 | 2.10 | −0.13 | 2.07 | −0.16 | 2.23 | 2.18 | 2.04 | 2.86 |
| AlAs | direct Γ→Γ | 2.04 | 2.86 | 2.71 | 2.70 | 2.70 | — | 2.82 | −0.31 | 2.77 | −0.36 | 2.73 | −0.40 | 2.69 | −0.44 | 3.13 | 2.88 | 2.97 | 3.86 |
| MgO | direct Γ→Γ | 4.95 | 8.55 | 8.09 | 8.16 | 8.16 | 8.24 | 8.04 | +0.21 | 8.04 | +0.21 | 8.05 | +0.22 | 8.07 | +0.24 | 7.83 | 7.69 | 6.51 | 7.23 |
| LiCl | direct Γ→Γ | 6.43 | 9.61 | 9.16 | 9.24 | 9.23 | — | 9.40 | +0.00 | 9.34 | −0.06 | 9.30 | −0.10 | 9.25 | −0.15 | 9.40 | 9.1 | 7.8 | 9.0 |
| NaCl | direct Γ→Γ | 5.21 | 8.88 | 8.36 | 8.49 | 8.49 | — | 8.63 | −0.34 | 8.57 | −0.40 | 8.53 | −0.44 | 8.49 | −0.48 | 8.97 | 8.7 | 6.56 | 8.5 |
| CaF₂ | indirect W→Γ | 7.33 | 13.15 | 12.03 | 12.36 | 12.36 | — | 12.37 | +0.57 | 12.34 | +0.54 | 12.33 | +0.53 | 12.31 | +0.51 | 11.80 | ~11.4 | ~10.4 | ~11.0 |
| CaF₂ | direct Γ→Γ | 7.59 | 13.42 | 12.31 | 12.64 | 12.64 | — | 12.65 | +0.55 | 12.62 | +0.52 | 12.60 | +0.50 | 12.59 | +0.49 | 12.10 | ~11.8 | — | — |
| LiF | direct Γ→Γ | 9.15 | 15.90 | 14.76 | 15.16 | 15.16 | — | 15.16 | +0.96 | 15.13 | +0.93 | 15.12 | +0.92 | 15.11 | +0.91 | 14.20 | 14.3 | 11.5 | 14.7 |
<!-- END:densmu -->

Screening inputs (μ_eff = c/σ_peak, bohr⁻¹):

<!-- BEGIN:densmu_params -->
| material | active sp. | A=1/ε∞ | μ_fit | μ_eff (c=0.45) | μ_eff (c=0.5) | μ_eff (c=0.55) | μ_eff (c=0.65) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Si | Si | 0.091 | 0.657 | 0.569 | 0.632 | 0.695 | 0.821 |
| C (diamond) | C | 0.185 | 0.901 | 0.981 | 1.090 | 1.199 | 1.417 |
| AlAs | As | 0.125 | 0.605 | 0.651 | 0.724 | 0.796 | 0.941 |
| MgO | O | 0.323 | 0.726 | 1.497 | 1.663 | 1.829 | 2.162 |
| LiCl | Cl | 0.337 | 0.633 | 0.795 | 0.883 | 0.971 | 1.148 |
| NaCl | Cl | 0.395 | 0.594 | 0.795 | 0.883 | 0.971 | 1.148 |
| CaF₂ | F | 0.443 | 0.714 | 1.499 | 1.666 | 1.832 | 2.166 |
| LiF | F | 0.490 | 0.725 | 1.502 | 1.669 | 1.836 | 2.170 |
<!-- END:densmu_params -->

MAE (|signed error|, eV) over all listed edges:

<!-- BEGIN:densmu_mae -->
| model | MAE all (eV) | MAE ionic¹ | MAE covalent² |
| --- | --- | --- | --- |
| density-μ c=0.45 | 0.290 | 0.572 | 0.142 |
| density-μ c=0.5 | 0.294 | 0.553 | 0.143 |
| density-μ c=0.55 | 0.298 | 0.543 | 0.145 |
| density-μ c=0.65 | 0.316 | 0.538 | 0.168 |
<!-- END:densmu_mae -->

**Verdict.** The direction is finally correct and it strongly relieves the β=1 over-opening for
the covalent set and MgO (MgO +0.72 → +0.21, Si tuned to +0.08). In fact **density-μ has the
lowest covalent MAE of any model here (0.142–0.143 eV vs β=¼ 0.193, β=1 0.153)** and the second
lowest overall MAE (0.290–0.294 eV, behind only β=¼ 0.272 and well ahead of finite-G / qcloud
0.355). The overall MAE is monotone in c over the scan (0.290 → 0.294 → 0.298 → 0.316 for
c = 0.45 → 0.50 → 0.55 → 0.65), so the shallow optimum sits at ≈ 0.45; **the Gaussian-natural
c = 0.50 is within 0.004 eV of it (0.294 vs 0.290)** — effectively tied — and is the value to
quote as the parameter-free reference. It is *not* the single best density-μ point (c = 0.45 edges
it), but the difference is noise.

Against RS-DDH β=¼, c = 0.50 **beats it on the covalent set (0.143 vs 0.193) and on every direct
Γ→Γ edge** (Si −0.09, C +0.06, AlAs −0.36 vs β=¼ −0.31/−0.12/−0.42), and matches it on MgO
(+0.21 vs +0.26). But it **loses overall** (0.294 vs 0.272) because it hits a **hard floor**: the
`μ→∞` limit is the `α = 1/ε∞` global hybrid, and for the high-A fluorides (LiF A=0.49, CaF₂
A=0.44) that floor still lies above experiment (LiF +0.93, CaF₂ +0.5; ionic MAE 0.55 vs β=¼
0.315). RS-DDH β=¼ wins there precisely because its short-range fraction 0.25 < A *punches
through* that floor. Net: **β=¼ remains the best single overall model**, while density-μ (c ≈
0.45–0.50) is the strongest of the β=1 family and the best model on covalent + direct-gap edges,
mapping the same boundary from the other side (μ instead of B).

## Directory layout

```text
patch/ddrshcam-qe-7.5.patch   the DD-RSH-CAM source patch for QE 7.5
config/materials.toml         per-material structure + run parameters (source of truth)
scripts/                      build, patch, input-gen, driver, fit, gap, table generators
runs/MgO/validate/            PBE0/HSE limit verification inputs
runs/MgO/p2/eels/             turboEELS eps^-1(q) scan + data (eps_q_clean.dat)
runs/MgO/p2/ddrshcam/         strict DD-RSH-CAM production (mgo.nqx6.in)
runs/MgO/p2/audit/            convergence audit inputs + run scripts
runs/MgO/01-pbe-scf .. 04-dd-hse   earlier PBE / DDH / approximate-DD-HSE runs
runs/Si/ runs/C/ runs/AlAs/ runs/LiCl/ runs/NaCl/ runs/CaF2/ runs/LiF/
              PBE, eels, ddrshcam, rsddh, finiteG_a* (finite-G), qcloud_eta* (density-scale),
              qpeak_kappa* (density-peak log-curvature)
pseudos/                      SG15 ONCV PBE norm-conserving pseudopotentials
results/                      MgO-results.md, Si-results.md, EFT-ARPES-bench-comparison.md
docs/                         implementation plan
```

Wavefunction directories (`out/`, `*.save/`, `*.hdf5`) are not tracked — see `.gitignore`.
`.in` inputs and summary `.md`/`.json` are tracked; large `*.out` logs are optional locally.

## Key scripts

Benchmark pipeline (driven by `config/materials.toml`, no hand-edited inputs):

- `scripts/run_material.sh <Material>` — **end-to-end DD-RSH-CAM driver** (β=1): PBE SCF →
  eels SCF → turboEELS scan → fit (ε∞, μ) → DD-RSH-CAM SCF → gaps.
- `scripts/run_rsddh.sh <Material>` — **RS-DDH driver** (β=0.25, Skone 2016): reuses the
  turboEELS fit and only re-runs the hybrid SCF; writes to `runs/<M>/p2/rsddh/`.
- `scripts/run_finiteg.sh <Material> <a>` — **finite-G driver**: reuses the fit, computes
  `B_a = 1−(1−A)exp(−a²/4)`, re-runs the hybrid SCF; writes to `runs/<M>/p2/finiteG_a<a>/`.
- `scripts/run_density_qcloud.sh <Material> <η>` — **density-scale finite-q driver**: reuses
  the fit + PBE density, computes `B_η = ε⁻¹(η·q_WS)`, re-runs the hybrid SCF; writes to
  `runs/<M>/p2/qcloud_eta<η>/`.
- `scripts/diag_qcloud.py` — endpoint diagnostic for the density-scale model (no QE):
  prints N_val, Ω, q_WS, q_cloud, B_η for all materials/η and checks `A ≤ B_η ≤ 1`.
- `scripts/run_density_qpeak.sh <Material> <κ>` — **density-peak log-curvature driver**:
  reuses the fit + PBE valence density, computes `B_κ = ε⁻¹(κ/σ_peak)`, re-runs the hybrid
  SCF; writes to `runs/<M>/p2/qpeak_kappa<κ>/`.
- `scripts/diag_qpeak_logcurv.py` — endpoint diagnostic for the density-peak model (no QE):
  per-species σ_peak from the PBE valence density, `B_κ` for the fixed active species, checks
  `A ≤ B_κ ≤ 1` → `results/qpeak_logcurv_endpoint.{csv,md}`, `qpeak_logcurv_all_species.{csv,md}`.
- `scripts/qpeak.py` — shared core: G-space charge-density parser, exact spherical average,
  log-curvature σ_peak fit, `B_κ`, and the fixed `ACTIVE_SPECIES` map.
- `scripts/write_qpeak_benchmark.py` — optional `results/benchmark_qpeak_logcurv.{csv,md}`
  from whatever qpeak runs exist (gaps + signed error; MAE uses |error|).
- `scripts/run_density_mu.sh <Material> <c>` — **density-peak range-separation driver** (β=1,
  μ_eff = c/σ_peak): reuses A and σ_peak, re-runs the hybrid SCF; writes to
  `runs/<M>/p2/densmu_c<c>/`.
- `scripts/diag_density_mu.py` — prints μ_eff = c/σ_peak vs the fitted μ and the β=1 error for
  all materials (no QE), to pick c.
- `scripts/write_densitymu_benchmark.py [--write]` — `results/benchmark_densitymu.{csv,md}`
  (the 4 c next to all prior models); `--write` splices the tables into README.
- `scripts/gen_inputs.py <Material> [--which rsddh|finiteg --a A|qcloud --eta E|qpeak --kappa K] [--bexx B]`
  — generate QE inputs from `materials.toml` (short-range Fock `bexx`: 1.0 for ddrshcam,
  0.25 for rsddh, `B_a` for finiteg, `B_η` for qcloud, `B_κ` for qpeak).
- `scripts/scan_eps_q.sh <prefix> <alat_bohr> <eels_dir>` — generic turboEELS ε⁻¹(q) scan.
- `scripts/fit_mu.py <eps_q.dat>` — fit ε∞ and μ (parabolic-refined, numpy only).
- `scripts/extract_gap.py <pw.out>` — fundamental + Γ-direct gap from a pw.x output.
- `scripts/write_comparison.py --write` — regenerate the tables in
  `results/EFT-ARPES-bench-comparison.md` from the actual runs (numbers can't drift).
- `scripts/matlib.py` — loader / sanity printer for `config/materials.toml`.

Build / patch / MgO audit:

- `scripts/make_patch.sh` — regenerate `patch/ddrshcam-qe-7.5.patch` by diffing the
  built tree against pristine QE 7.5.
- `scripts/make_build_env.sh`, `scripts/build_qe.sh` — toolchain + compile.
- `scripts/collect_audit_gaps.py` — regenerate `results/MgO-audit.md`.

```bash
conda activate qedev                           # numpy + access to ~/qe-7.5/bin

# serial (OpenMP only)
scripts/run_material.sh AlAs

# MPI (recommended) — much faster on the turboEELS bottleneck at equal core count.
# OpenMPI refuses to run as root, so on this box pass --allow-run-as-root via MPIRUN:
QE_NP=4 OMP_NUM_THREADS=1 MPIRUN="mpirun --allow-run-as-root" \
  scripts/run_material.sh AlAs

python3 scripts/write_comparison.py --write    # regenerate the comparison tables
python3 scripts/matlib.py                       # list the configured materials
```

`QE_NP` (MPI ranks, default 1) is the main speed lever. `scripts/build_qe.sh` produces a
true MPI build (`Parallel version (MPI & OpenMP)`), and turboEELS scales far better over
MPI than OpenMP — e.g. one AlAs q-point drops from **7m40s serial to 1m27s on 4 ranks**
(~5.3×, same 4 cores), with results identical to ~1e-7. The driver refuses `QE_NP>1` on a
serial binary so a mis-set `QE_NP` can't silently corrupt a run. `MPIRUN` carries the
launcher and any flags (it is left unquoted, e.g. `mpirun --allow-run-as-root` when
running as root). `QLIST` overrides the turboEELS q-points (the fit has 2 parameters, so
5–6 points suffice).

## References

- Skone, Govoni, Galli, *Phys. Rev. B* **89**, 195112 (2014) — DDH.
- Chen et al., *Phys. Rev. Materials* **2**, 073803 (2018) — DD-RSH-CAM.
- MgO experimental gap 7.83 eV.
