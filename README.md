# Strict DD-RSH-CAM in Quantum ESPRESSO (patched) — MgO reproduction

This project implements the **dielectric-dependent range-separated hybrid
DD-RSH-CAM** functional in **Quantum ESPRESSO 7.5** by patching the source
(QE has no native functional with independent short- and long-range exact-exchange
fractions), and runs the **full non-empirical pipeline** for MgO:
`turboEELS ε⁻¹(q) → fit (ε∞, μ) → DD-RSH-CAM SCF → gap`.

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
configures and compiles. The patch was developed against that environment.

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
3. **Run** — DD-RSH-CAM SCF with the fitted parameters (`runs/MgO/p2/ddrshcam/`).

### Results (MgO)

| method | gap (eV) |
| --- | ---: |
| PBE (this build) | 4.95 |
| approximate DD-HSE (long-range Fock removed) | 5.23 |
| **strict DD-RSH-CAM (this work, q-converged)** | **8.55** |
| paper RS-DDH | 7.88 |
| paper DD0-RSH-CAM | 8.32 |
| experiment | 7.83 |

The strict gap (8.55 eV) lands in the paper's DD-RSH-CAM family (8.32 eV), **not**
the approximate DD-HSE (5.23 eV) — confirming that keeping the long-range screened
Fock is what matters. Residual vs paper: parameter source (paper ε∞=2.81), lattice
constant (4.186 Å here vs 4.148 Å), pseudopotentials, and k/q convergence.

> Toolchain limitation: QE DFPT/turboEELS run only at the semilocal level, so μ is
> taken at PBE-RPA (transferable). A self-consistent hybrid ε∞ would use `epsilon.x`
> (IPA, no local fields) and increase the gap further.

## Directory layout

```text
patch/ddrshcam-qe-7.5.patch   the DD-RSH-CAM source patch for QE 7.5
scripts/                      build, patch, dielectric-fit, and helper scripts
runs/MgO/validate/            PBE0/HSE limit verification inputs+outputs
runs/MgO/p2/eels/             turboEELS eps^-1(q) scan + data (eps_q_clean.dat)
runs/MgO/p2/ddrshcam/         strict DD-RSH-CAM production runs (nqx 3 and 6)
runs/MgO/01-pbe-scf .. 04-dd-hse   earlier PBE / DDH / approximate-DD-HSE runs
pseudos/                      SG15 ONCV PBE norm-conserving pseudopotentials
results/MgO-ddrsh-summary.md  summary table and provenance
docs/                         implementation plan
```

QE run outputs (`out/`, wavefunctions, `*.hdf5`) are not tracked — see `.gitignore`.

## Key scripts

- `scripts/make_patch.sh` — regenerate `patch/ddrshcam-qe-7.5.patch` by diffing the
  built tree against pristine QE 7.5.
- `scripts/make_build_env.sh`, `scripts/build_qe.sh` — toolchain + compile.
- `scripts/fit_mu.py` — fit ε∞ and μ from `eps_q.dat` (numpy only).
```bash
python3 scripts/fit_mu.py runs/MgO/p2/eels/eps_q_clean.dat
```

## References

- Skone, Govoni, Galli, *Phys. Rev. B* **89**, 195112 (2014) — DDH.
- Chen, Pasquarello et al., dielectric-dependent range-separated hybrids (DD-RSH-CAM).
- MgO experimental gap 7.83 eV.
