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

## Directory layout

```text
patch/ddrshcam-qe-7.5.patch   the DD-RSH-CAM source patch for QE 7.5
scripts/                      build, patch, dielectric-fit, audit collector
runs/MgO/validate/            PBE0/HSE limit verification inputs
runs/MgO/p2/eels/             turboEELS eps^-1(q) scan + data (eps_q_clean.dat)
runs/MgO/p2/ddrshcam/         strict DD-RSH-CAM production (mgo.nqx6.in)
runs/MgO/p2/audit/            convergence audit inputs + run scripts
runs/MgO/01-pbe-scf .. 04-dd-hse   earlier PBE / DDH / approximate-DD-HSE runs
pseudos/                      SG15 ONCV PBE norm-conserving pseudopotentials
results/                      MgO-results.md (main), MgO-audit.md, JSON summaries
docs/                         implementation plan
```

Wavefunction directories (`out/`, `*.save/`, `*.hdf5`) are not tracked — see `.gitignore`.
`.in` inputs and summary `.md`/`.json` are tracked; large `*.out` logs are optional locally.

## Key scripts

- `scripts/make_patch.sh` — regenerate `patch/ddrshcam-qe-7.5.patch` by diffing the
  built tree against pristine QE 7.5.
- `scripts/make_build_env.sh`, `scripts/build_qe.sh` — toolchain + compile.
- `scripts/fit_mu.py` — fit ε∞ and μ from `eps_q.dat` (numpy only).
- `scripts/collect_audit_gaps.py` — regenerate `results/MgO-audit.md`.

```bash
python3 scripts/fit_mu.py runs/MgO/p2/eels/eps_q_clean.dat
python3 scripts/collect_audit_gaps.py
```

## References

- Skone, Govoni, Galli, *Phys. Rev. B* **89**, 195112 (2014) — DDH.
- Chen et al., *Phys. Rev. Materials* **2**, 073803 (2018) — DD-RSH-CAM.
- MgO experimental gap 7.83 eV.
