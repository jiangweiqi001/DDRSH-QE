# Strict DD-RSH-CAM in Quantum ESPRESSO (source patch) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`).

**Goal:** Implement a strict dielectric-dependent range-separated hybrid (DD-RSH-CAM / RS-DDH, VASP `LMODELHF` form) in Quantum ESPRESSO 7.5 by patching the source, then determine the screening parameter mu nonempirically from the fitted inverse dielectric function.

**Architecture:** Build a patched `pw.x` from QE 7.5 source in a user-space conda toolchain (no sudo). The functional is defined by a two-fraction range-separated Fock kernel plus the matching semilocal (PBE) complement. mu is obtained by fitting epsilon^-1(q) to the model function. Validation is by reduction to PBE0 and HSE, which the existing conda QE already reproduces.

**Tech Stack:** QE 7.5 (Fortran), conda-forge toolchain (gfortran, openmpi, fftw, openblas, scalapack, libxc, hdf5), Python 3 for parsing and fitting.

---

## Background: the target functional

Reciprocal-space exact-exchange kernel (q2 = |q+G|^2):

```
V(q) = (4*pi*e2 / q2) * [ a_SR - (a_SR - a_LR) * exp(-q2 / (4*mu^2)) ]
```

- short range (q2 -> infinity): V -> a_SR * 4*pi*e2/q2   (BEXX, full Fock = 1.0)
- long range  (q2 -> 0):        V -> a_LR * 4*pi*e2/q2   (AEXX, screened Fock = 1/eps_inf)

Decomposition into kernels QE already has:

```
V_DDRSH = a_LR * V_bare(PBE0)  +  (a_SR - a_LR) * V_erfc(HSE short range)
```

Semilocal (PBE) exchange complement, using QE's `pbex` (full) and `pbexsr` (short range):

```
E_x^DFT = (1 - a_LR) * E_x^PBE  -  (a_SR - a_LR) * E_x^PBE,SR(mu)
```

DD-RSH-CAM parameters for MgO (phase 1, literature): a_SR = 1.0, a_LR = 1/eps_inf, mu = 0.63 bohr^-1.

---

## Phase 0: Toolchain and vanilla build (de-risk) -- DONE

### Task 0.1: Create build toolchain -- DONE
- Use: `scripts/make_build_env.sh` (conda env `qedev`: gfortran 14.3, openmpi, fftw, openblas, libxc, hdf5)

### Task 0.2: Get QE 7.5 source -- DONE
- Use: `scripts/get_qe_src.sh` -> `~/qe-7.5`
- Submodules (mbd, devxlib, fox) via `scripts/get_qe_submodules.sh`. NOTE: github git
  protocol is blocked here, but codeload.github.com HTTPS tarballs and gitlab git work,
  so submodules are fetched as tarballs/clones at the exact pinned commits, with `.git`
  marker dirs added so QE's `update_submodule` macro skips re-cloning.

### Task 0.3: Build vanilla pw.x -- DONE (autotools, not CMake)
- Use: `scripts/build_qe.sh` -> `~/qe-7.5/bin/pw.x`
- CMake was abandoned because it clones wannier90 from the blocked github at configure
  time. Autotools `./configure && make pw` does not. Required make.inc fixes (all baked
  into build_qe.sh):
  - `LD` -> gfortran driver (conda LDFLAGS use -Wl, options)
  - `FFLAGS += -fallow-argument-mismatch` (gfortran 14 strictness)
  - `DFLAGS = -D__FFTW3` (select FFT backend)
  - BLAS/LAPACK: `-lblas -llapack` (no libopenblas.so symlink in conda env)
  - `LDFLAGS += -fopenmp`; `FFT_LIBS = -lfftw3_omp -lfftw3` (OpenMP + threaded FFTW)
- Also: a stale empty `MBD/` dir and a stale `install/libcuda_devxlib` marker can skip the
  mbd/devxlib builds; remove them if `*.mod` are missing.

### Task 0.4: Baseline validation -- DONE
- Self-built pw.x on MgO PBE SCF gives HOMO 9.0027 / LUMO 13.9551 -> gap 4.952 eV,
  matching the conda build exactly. Toolchain is correct; safe to patch.

---

## Phase 1: DD-RSH-CAM functional patch

> Read the actual source before editing. The exact variable names and call sites must be
> taken from `~/qe-7.5`, not assumed. Target files (verify on read):
> - `PW/src/exx_base.f90` (subroutine `g2_convolution`, the kernel factor `fac`)
> - `Modules/funct.f90` or `XClib/` (functional setup; `erfc_scrlen`, `gau_scrlen`, exx fractions)
> - `Modules/read_input.f90`, `Modules/input_parameters.f90`, `PW/src/input.f90` (new namelist vars)
> - `PW/src/exx.f90` (energy/potential assembly, where `exxalfa` scales the Fock term)

### Task 1.1: Add input variables
- [ ] Add `lmodelhf` (logical), `aexx`, `bexx`, `hfscreen` (reals) to the `system` namelist:
  declare in `input_parameters.f90`, read in `read_input.f90`, propagate in `PW/src/input.f90`
  into the EXX module variables. Mirror how `exx_fraction` and `screening_parameter` are handled.

### Task 1.2: Patch the Fock kernel
- [ ] In `g2_convolution`, add a branch active when `lmodelhf` is true:

```fortran
! pseudo-code; adapt names to the real file
fac(ig) = e2 * fpi / qq * ( bexx - (bexx - aexx) * EXP( -qq / (4.0_dp*hfscreen**2) ) )
```

  applied with the same `grid_factor`, `on_double_grid`, and q=G=0 (exxdiv) handling that
  the existing erfc/erf branches use. Ensure the global `exxalfa` does not double-scale this
  branch (set `exxalfa = 1` for `lmodelhf` and bake fractions into `fac`).

### Task 1.3: Patch the semilocal complement
- [ ] Configure the GGA exchange so the total semilocal exchange equals
  `(1 - aexx) * pbex - (bexx - aexx) * pbexsr(mu)`. Reuse the HSE short-range exchange
  routine (`pbexsr`) that QE already calls; add the `(1 - aexx)` full-PBE term and the
  `-(bexx - aexx)` short-range term with `mu = hfscreen`.

### Task 1.4: Build patched pw.x
- [ ] `cmake --build build -j4 --target pw` and confirm it links.

### Task 1.5: Limit-check validation (critical)
- [ ] PBE0 check: set `lmodelhf=.true., aexx=0.25, bexx=0.25, hfscreen=<any>`; gap must match
  native `input_dft='pbe0', exx_fraction=0.25`.
- [ ] HSE check: set `aexx=0.0, bexx=0.25, hfscreen=0.106`; gap must match native
  `input_dft='hse'`. (HSE has full Fock at short range, zero at long range.)
- [ ] If both match within ~1 meV, the kernel and complement are correct.

### Task 1.6: DD-RSH-CAM run (literature mu)
- Create: `runs/MgO/05-dd-rsh-cam/mgo.scf.in`
- [ ] Run with `aexx = 1/eps_inf`, `bexx = 1.0`, `hfscreen = 0.63`; record the gap and
  compare with paper DD0-RSH-CAM 8.32 eV and experiment 7.83 eV.

---

## Phase 2: Nonempirical mu from epsilon^-1(q)

### Methodology decision (toolchain-constrained)
- eps^-1(q) is computed with **turbo_eels.x** (TDDFPT-Lanczos, RPA + crystal local fields)
  at the **PBE** level: for each q (along [100], units 2pi/a) take the omega=0 value of
  Re(eps) / Re(1/eps) from `mgo.plot_eps.dat`. This is the inverse macroscopic dielectric
  function including local fields = the (0,0) head of the inverse dielectric matrix, exactly
  the quantity the DD-RSH-CAM model targets.
- Both eps_inf AND mu are fit from this single consistent dataset.
- **Limitation**: QE DFPT/turboEELS only run at the semilocal level, so the q-dependent
  dielectric (hence mu) is taken at PBE-RPA. mu is transferable. eps_inf self-consistency at
  the hybrid level is done with **epsilon.x (IPA)** on the DD-RSH-CAM wavefunctions (the only
  hybrid-capable dielectric tool in base QE; no local fields -> documented caveat).

### Task 2.1: Compute epsilon^-1(q)  [DONE]
- `runs/MgO/p2/eels/scan_q.sh` scans q in {0.10..1.70} (2pi/a). Clean data in `eps_q_clean.dat`
  (q1=1.00 dropped: stale turbo_spectrum file). PBE epsilon.x IPA cross-check: eps_inf=3.98.

### Task 2.2: Fit the model  [DONE]
- `scripts/fit_mu.py` (numpy-only: 1-D scan over mu, linear solve for amplitude each step).
- Result: **eps_inf = 3.092, mu = 0.726 bohr^-1, AEXX = 0.323, RMSE = 0.006.**

### Task 2.3: One-shot run + self-consistent loop  [IN PROGRESS]
- One-shot DD-RSH-CAM (k 6x6x6, nqx 3x3x3): gap = 8.67 eV (HOMO 6.21 / LUMO 14.88).
  -> checking nqx convergence (nqx=6) since coarse q-grid likely inflates the gap.
- Create: `scripts/run_ddrshcam_sc.sh`
- [ ] Iterate: run DD-RSH-CAM -> recompute eps_inf (epsilon.x IPA) -> update aexx ->
  rerun, until eps_inf is converged. Record the converged gap.

### Task 2.4: Final comparison
- Modify: `results/MgO-ddrsh-summary.md` (extend generator)
- [ ] Add the strict DD-RSH-CAM row (self-consistent) alongside DDH and DD-HSE, with
  deviations vs paper and experiment.

---

## Validation summary

The patch is trusted only after Task 1.5 passes (PBE0 and HSE reproduced by the new code
path). The physical result is trusted after Phase 2 converges and the DD-RSH-CAM gap is
within an explainable range of the paper and experiment.
