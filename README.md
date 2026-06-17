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

| material | gap type | PBE | **DD-RSH-CAM** | expt | error | G₀W₀ | HSE06 | PBE0 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Si | indirect | 0.60 | **1.27** | 1.17 | +0.10 | 1.29 | 1.16 | 1.97 |
| Si | direct Γ | — | **3.28** | 3.40 | −0.12 | 3.35 | 3.32 | 3.96 |
| C (diamond) | indirect | 4.18 | **5.67** | 5.48 | +0.19 | 5.50 | 5.42 | 6.66 |
| C (diamond) | direct Γ | — | **7.50** | 7.30 | +0.20 | 7.50 | 7.04 | 8.40 |
| AlAs | indirect Γ→X | 1.43 | **2.19** | 2.23 | −0.04 | 2.18 | 2.04 | 2.86 |
| AlAs | direct Γ | — | **2.86** | 3.13 | −0.27 | 2.88 | 2.97 | 3.86 |
| LiCl | direct Γ | 6.43 | **9.61** | 9.40 | +0.21 | 9.1 | 7.80 | 9.0 |
| NaCl | direct Γ | 5.21 | **8.88** | 8.97 | −0.09 | 8.7 | 6.56 | 8.5 |
| MgO | direct Γ | 4.95 | **8.55** | 7.83 | +0.72 | 7.69 | 6.51 | 7.23 |
| CaF₂ | indirect W→Γ | 7.33 | **13.15** | 11.80 | +1.35 | ~11.4 | ~10.4 | ~11.0 |
| CaF₂ | direct Γ | — | **13.42** | 12.10 | +1.32 | ~11.8 | — | — |
| LiF | direct Γ | 9.15 | **15.90** | 14.20 | +1.70 | 14.3 | 11.50 | 14.7 |

**8 of 12 edges pass** their bench tolerance — **5 of 8 materials pass on every edge**.
Covalent / mid-gap solids and the III-V (Si, C, AlAs, LiCl, NaCl) land within ≤0.27 eV of
experiment — on top of G₀W₀, far better than PBE0's over-opening, for both indirect and
direct edges. The three smallest-ε∞ ionic crystals over-open as aexx = 1/ε∞ grows
(MgO +0.72, CaF₂ +1.35, LiF +1.70); LiF coincides with QSGW (15.9 eV), which also
overshoots before the e–h vertex. The PBE0/HSE limits remain bit-for-bit exact.

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
                              benchmark materials (PBE, eels, ddrshcam)
pseudos/                      SG15 ONCV PBE norm-conserving pseudopotentials
results/                      MgO-results.md, Si-results.md, EFT-ARPES-bench-comparison.md
docs/                         implementation plan
```

Wavefunction directories (`out/`, `*.save/`, `*.hdf5`) are not tracked — see `.gitignore`.
`.in` inputs and summary `.md`/`.json` are tracked; large `*.out` logs are optional locally.

## Key scripts

Benchmark pipeline (driven by `config/materials.toml`, no hand-edited inputs):

- `scripts/run_material.sh <Material>` — **end-to-end driver**: PBE SCF → eels SCF →
  turboEELS scan → fit (ε∞, μ) → DD-RSH-CAM SCF → gaps.
- `scripts/gen_inputs.py <Material>` — generate the 3 QE inputs from `materials.toml`.
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
