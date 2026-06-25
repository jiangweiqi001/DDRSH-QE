# DD-RSH-CAM (β=1) and RS-DDH (β=¼) vs experiment — EFT-ARPES-bench subset

Two non-empirical dielectric-dependent range-separated hybrids (patched QE 7.5) applied
to a subset of the [EFT-ARPES-bench](https://github.com/kunyuan/EFT-ARPES-bench) set.
Each material runs the same pipeline with **no empirical parameters**:

```
PBE SCF  →  turboEELS ε⁻¹(q)  →  fit (ε∞, μ)  →  hybrid SCF  →  gap
```

Both functionals share the long-range Fock fraction `aexx = 1/ε∞` and the screening
`μ = hfscreen` from the *same* turboEELS fit; they differ only in the **short-range**
Fock fraction `bexx`:

- **DD-RSH-CAM** (Chen 2018): `bexx = 1` — full short-range Fock.
- **RS-DDH** (Skone 2016): `bexx = 0.25` — PBE0-like short-range fraction.

Fock q-grid nqx 6×6×6, `exxdiv = gygi-baldereschi`, SG15 ONCV PBE norm-conserving
pseudopotentials, experimental lattice constants from the bench TOMLs. Because the
dielectric input (ε∞, μ) is PBE-level and functional-independent, RS-DDH reuses the
DD-RSH-CAM fit and only re-runs the final hybrid SCF (`scripts/run_rsddh.sh`).

8 materials, spanning covalent semiconductors, a III-V, alkali halides, and ionic
wide-gap oxide/fluoride.

> The tables below are **auto-generated** from the actual run outputs by
> `scripts/write_comparison.py --write` (structure/run params from
> `config/materials.toml`, reference values from `scripts/literature.py`, fits and gaps
> reparsed from `runs/`). Do not edit them by hand — rerun the script.

## Non-empirical parameters (from turboEELS fit)

<!-- BEGIN:params -->
| material | structure | a (bohr) | ecut (Ry) | ε∞ (fit) | ε∞ (expt) | μ (bohr⁻¹) | aexx = 1/ε∞ |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Si | diamond | 10.263 | 60 | 10.95 | ~11.7 | 0.657 | 0.091 |
| C (diamond) | diamond | 6.741 | 80 | 5.40 | ~5.7 | 0.901 | 0.185 |
| AlAs | zincblende | 10.696 | 60 | 8.03 | ~8.16 | 0.605 | 0.125 |
| MgO | rocksalt | 7.9104 | 80 | 3.09 | ~2.96 | 0.726 | 0.323 |
| LiCl | rocksalt | 9.649 | 50 | 2.97 | ~2.75 | 0.633 | 0.337 |
| NaCl | rocksalt | 10.573 | 50 | 2.53 | ~2.34 | 0.594 | 0.395 |
| CaF₂ | fluorite | 10.323 | 80 | 2.25 | ~2.04 | 0.714 | 0.443 |
| LiF | rocksalt | 7.605 | 80 | 2.04 | ~1.9 | 0.725 | 0.490 |
<!-- END:params -->

## Band gaps vs experiment (eV)

<!-- BEGIN:gaps -->
| material | gap type | PBE | **DD-RSH-CAM** (β=1) | RS-DDH (β=¼) | expt | err DDH | err RS | G₀W₀ | HSE06 | PBE0 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Si | indirect | 0.60 | **1.27** | 1.15 | 1.17 | +0.10 | −0.02 | 1.29 | 1.16 | 1.97 |
| Si | direct Γ→Γ | 2.56 | **3.28** | 3.09 | 3.40 | −0.12 | −0.31 | 3.35 | 3.32 | 3.96 |
| C (diamond) | indirect | 4.18 | **5.67** | 5.60 | 5.48 | +0.19 | +0.12 | 5.5 | 5.42 | 6.66 |
| C (diamond) | direct Γ→Γ | 5.60 | **7.50** | 7.18 | 7.30 | +0.20 | −0.12 | 7.5 | 7.04 | 8.4 |
| AlAs | indirect Γ→X | 1.43 | **2.19** | 2.05 | 2.23 | −0.04 | −0.18 | 2.18 | 2.04 | 2.86 |
| AlAs | direct Γ→Γ | 2.04 | **2.86** | 2.71 | 3.13 | −0.27 | −0.42 | 2.88 | 2.97 | 3.86 |
| MgO | direct Γ→Γ | 4.95 | **8.55** | 8.09 | 7.83 | +0.72 | +0.26 | 7.69 | 6.51 | 7.23 |
| LiCl | direct Γ→Γ | 6.43 | **9.61** | 9.16 | 9.40 | +0.21 | −0.24 | 9.1 | 7.8 | 9.0 |
| NaCl | direct Γ→Γ | 5.21 | **8.88** | 8.36 | 8.97 | −0.09 | −0.61 | 8.7 | 6.56 | 8.5 |
| CaF₂ | indirect W→Γ | 7.33 | **13.15** | 12.03 | 11.80 | +1.35 | +0.23 | ~11.4 | ~10.4 | ~11.0 |
| CaF₂ | direct Γ→Γ | 7.59 | **13.42** | 12.31 | 12.10 | +1.32 | +0.21 | ~11.8 | — | — |
| LiF | direct Γ→Γ | 9.15 | **15.90** | 14.76 | 14.20 | +1.70 | +0.56 | 14.3 | 11.5 | 14.7 |
<!-- END:gaps -->

(G₀W₀/HSE06/PBE0 columns are literature values from the bench TOMLs; MgO row from
`results/MgO-results.md`. CaF₂ hybrid/GW literature is sparse — those entries are the
bench-TOML estimates, marked `~`.)

## Verdict against the benchmark tolerances

<!-- BEGIN:verdict -->
| material | gap type | tol (eV) | DD-RSH-CAM err | pass? | RS-DDH err | pass? |
| --- | --- | ---: | ---: | :--: | ---: | :--: |
| Si | indirect | 0.30 | +0.10 | ✅ | −0.02 | ✅ |
| Si | direct Γ→Γ | 0.30 | −0.12 | ✅ | −0.31 | ❌ (over) |
| C (diamond) | indirect | 0.40 | +0.19 | ✅ | +0.12 | ✅ |
| C (diamond) | direct Γ→Γ | 0.40 | +0.20 | ✅ | −0.12 | ✅ |
| AlAs | indirect Γ→X | 0.30 | −0.04 | ✅ | −0.18 | ✅ |
| AlAs | direct Γ→Γ | 0.30 | −0.27 | ✅ | −0.42 | ❌ (over) |
| MgO | direct Γ→Γ | 0.50 | +0.72 | ❌ (over) | +0.26 | ✅ |
| LiCl | direct Γ→Γ | 0.40 | +0.21 | ✅ | −0.24 | ✅ |
| NaCl | direct Γ→Γ | 0.40 | −0.09 | ✅ | −0.61 | ❌ (over) |
| CaF₂ | indirect W→Γ | 0.50 | +1.35 | ❌ (over) | +0.23 | ✅ |
| CaF₂ | direct Γ→Γ | 0.50 | +1.32 | ❌ (over) | +0.21 | ✅ |
| LiF | direct Γ→Γ | 0.50 | +1.70 | ❌ (over) | +0.56 | ❌ (over) |

**DD-RSH-CAM: 8 of 12 edges within tolerance; RS-DDH (β=¼): 8 of 12.**
<!-- END:verdict -->

Both functionals pass **8 of 12 edges**, but on *complementary* materials. DD-RSH-CAM
(β=1) nails the covalent / III-V / chloride edges (Si, C, AlAs, LiCl, NaCl) and
over-opens the small-ε∞ fluorides + oxide (MgO, CaF₂, LiF). Cutting the short-range Fock
to β=¼ (RS-DDH) removes most of that over-opening — MgO +0.72→+0.26, CaF₂ +1.3→+0.2,
LiF +1.70→+0.56, so **MgO and both CaF₂ edges now pass** — but it under-opens the more
covalent direct edges (Si/AlAs Γ→Γ, NaCl). The short-range Fock fraction is the knob that
trades **ionic over-opening (favours β=¼)** against **covalent under-opening (favours
β=1)**.

## What the numbers say

- **Covalent / mid-gap (Si, C, AlAs, LiCl, NaCl): excellent.** All within ≤0.27 eV of
  experiment, essentially on top of G₀W₀ and far better than PBE0's systematic
  over-opening. The non-empirical 1/ε∞ + screened long-range Fock recipe works cleanly
  here, for both indirect (Si, C, AlAs Γ→X) and direct (Γ→Γ) edges.
- **AlAs is a clean two-edge test.** The same single parameter set reproduces *both* the
  indirect X minimum (2.19 vs 2.23) and the Γ direct gap (2.86 vs 3.13), landing right on
  G₀W₀ (2.18 / 2.88) — it is fitting the physics, not one number.
- **LiCl confirms the alkali-halide trend.** Same Li 1s core as LiF but Cl 3p valence and
  a smaller gap: 9.61 vs 9.40 eV, essentially exact and matching DD-PBEH (9.49), where
  HSE06 falls 1.6 eV short.
- **`must_open_gap` passes everywhere.** Every material opens from the PBE value to near
  experiment (NaCl 5.21 → 8.88, LiCl 6.43 → 9.61, C 4.18 → 5.67) without the empirical
  25% mixing of PBE0.
- **The smallest-ε∞ ionic crystals over-open (MgO +0.72, CaF₂ +1.35, LiF +1.70).** As ε∞
  drops (aexx → 0.44–0.49) strict DD-RSH-CAM with full short-range Fock (`bexx = 1`)
  overshoots, monotonically with 1/ε∞. LiF lands on **QSGW (15.9)**, which also overshoots
  before the electron–hole vertex brings it back to ~14.5. This is a real physical trend
  (more screening error where ε∞ is smallest), not a code defect: the PBE0/HSE limits are
  still reproduced bit-for-bit (see `results/MgO-results.md`).
- **RS-DDH (β=¼) is the better choice for these ionic wide-gap crystals.** Reducing the
  short-range Fock to the PBE0-like 0.25 (Skone 2016) brings MgO (8.09), CaF₂ (12.0/12.3)
  and LiF (14.76) back toward experiment — MgO and CaF₂ now pass — confirming the
  over-opening is a *short-range* exchange effect, not the long-range 1/ε∞ tail. The price
  is mild under-opening of the covalent direct edges (Si Γ −0.31, AlAs Γ −0.42, NaCl
  −0.61), where the full short-range Fock of β=1 was doing useful work. No single β is best
  everywhere; the two columns bracket the experimental gaps.

## Coverage map

```
ε∞ large ───────────────────────────────────────────────────► ε∞ small
        Si     AlAs   C        MgO    LiCl   NaCl    CaF₂     LiF
        0.091  0.125  0.185    0.323  0.337  0.395   0.443    0.490   ← aexx = 1/ε∞
β=1  :  ✅✅   ✅✅   ✅✅      ❌     ✅     ✅      ❌❌     ❌      ← DD-RSH-CAM
β=¼  :  ✅❌   ✅❌   ✅✅      ✅     ✅     ❌      ✅✅     ❌      ← RS-DDH
        └──── covalent: β=1 wins ────┘       └─ ionic wide-gap: β=¼ wins ─┘
```

(Pairs are indirect/direct where a material has two edges; single mark = one edge.)

## Finite-G model (third class: material-dependent short-range endpoint)

`bexx = 1` (DD-RSH-CAM) and `bexx = ¼` (RS-DDH) are the two *fixed* short-range endpoints.
The finite-G model keeps the same single-μ kernel (long-range Fock `aexx = 1/ε∞`,
screening `μ = hfscreen`), but sets the short-range Fock endpoint to the **dielectric
function evaluated at a finite wavevector** `G = a·μ`:

```
B_a = ε⁻¹(G = a·μ) = 1 − (1 − A)·exp(−a²/4),     A = aexx = 1/ε∞
```

`a` is a single **global** constant (the same for every material — no per-material
tuning); `B_a` is then a **material-dependent** effective short-range endpoint, set by each
material's own A. The limits make the interpolation explicit: `a→0 ⇒ B_a→1` (DD-RSH-CAM)
and `a→∞ ⇒ B_a→A` (a global hybrid with a single fraction 1/ε∞). For finite `a`,
`A ≤ B_a ≤ 1`, and larger `a` means *less* short-range Fock. The dielectric input is
functional-independent, so each `a` reuses the DD-RSH-CAM fit and only re-runs the hybrid
SCF (`scripts/run_finiteg.sh <M> <a>`); results live in `runs/<M>/p2/finiteG_a<a>/` and do
not touch the β=1 / β=¼ runs.

Endpoints actually used (derived from each material's A):

<!-- BEGIN:fgparams -->
| material | A = 1/ε∞ | B (a=0.5) | B (a=1.0) | B (a=2.0) |
| --- | ---: | ---: | ---: | ---: |
| Si | 0.091 | 0.146 | 0.292 | 0.666 |
| C (diamond) | 0.185 | 0.234 | 0.365 | 0.700 |
| AlAs | 0.125 | 0.178 | 0.318 | 0.678 |
| MgO | 0.323 | 0.364 | 0.473 | 0.751 |
| LiCl | 0.337 | 0.377 | 0.483 | 0.756 |
| NaCl | 0.395 | 0.432 | 0.529 | 0.778 |
| CaF₂ | 0.443 | 0.477 | 0.567 | 0.795 |
| LiF | 0.490 | 0.521 | 0.603 | 0.812 |
<!-- END:fgparams -->

Band gaps for the three global `a` values, next to the two fixed-β models (eV):

<!-- BEGIN:finiteg -->
| material | gap type | expt | **DD-RSH-CAM** (β=1) | RS-DDH (β=¼) | finite-G a=0.5 | finite-G a=1.0 | finite-G a=2.0 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Si | indirect | 1.17 | **1.27** | 1.15 | 1.13 | 1.16 | 1.22 |
| Si | direct Γ→Γ | 3.40 | **3.28** | 3.09 | 3.07 | 3.10 | 3.20 |
| C (diamond) | indirect | 5.48 | **5.67** | 5.60 | 5.59 | 5.61 | 5.64 |
| C (diamond) | direct Γ→Γ | 7.30 | **7.50** | 7.18 | 7.17 | 7.23 | 7.37 |
| AlAs | indirect Γ→X | 2.23 | **2.19** | 2.05 | 2.04 | 2.06 | 2.13 |
| AlAs | direct Γ→Γ | 3.13 | **2.86** | 2.71 | 2.70 | 2.73 | 2.80 |
| MgO | direct Γ→Γ | 7.83 | **8.55** | 8.09 | 8.16 | 8.22 | 8.39 |
| LiCl | direct Γ→Γ | 9.40 | **9.61** | 9.16 | 9.24 | 9.30 | 9.46 |
| NaCl | direct Γ→Γ | 8.97 | **8.88** | 8.36 | 8.49 | 8.55 | 8.73 |
| CaF₂ | indirect W→Γ | 11.80 | **13.15** | 12.03 | 12.36 | 12.49 | 12.84 |
| CaF₂ | direct Γ→Γ | 12.10 | **13.42** | 12.31 | 12.64 | 12.77 | 13.11 |
| LiF | direct Γ→Γ | 14.20 | **15.90** | 14.76 | 15.16 | 15.29 | 15.61 |
<!-- END:finiteg -->

Mean absolute error by model (overall and by material class):

<!-- BEGIN:mae -->
| model | MAE all (eV) | MAE ionic¹ | MAE covalent² |
| --- | ---: | ---: | ---: |
| DD-RSH-CAM (β=1) | 0.525 | 1.272 | 0.153 |
| RS-DDH (β=¼) | 0.272 | 0.315 | 0.193 |
| finite-G a=0.5 | 0.355 | 0.596 | 0.205 |
| finite-G a=1.0 | 0.369 | 0.709 | 0.179 |
| finite-G a=2.0 | 0.435 | 1.002 | 0.152 |

¹ ionic = MgO, CaF₂, LiF (low-ε∞ strong-ionic wide-gap). ² covalent = Si, C, AlAs (covalent / III–V). MAE is over all listed edges (fundamental + direct Γ→Γ) where a value exists.
<!-- END:mae -->

<!-- BEGIN:fganalysis -->
All 24 runs (8 materials × 3 `a`) completed; **no failures**. Gaps increase monotonically
with `a` for every material (larger `a` ⇒ larger `B_a` ⇒ more short-range Fock ⇒ wider
gap), so the three values cleanly bracket the fixed-β results.

**Which `a` has the smallest overall MAE?** `a = 0.5` (0.355 eV), then `a = 1.0` (0.369),
then `a = 2.0` (0.435). All three sit *between* DD-RSH-CAM (0.525) and RS-DDH (0.272): the
flat β=¼ is still the best single model overall, and no global `a` beats it (see the
mechanism note below).

**Which `a` helps the low-ε∞ ionic crystals (MgO, CaF₂, LiF) most?** `a = 0.5`, by a clear
margin: ionic MAE 0.596 (a=0.5) < 0.709 (a=1.0) < 1.002 (a=2.0). Smaller `a` ⇒ smaller
`B_a` ⇒ less short-range Fock ⇒ less over-opening, monotonically.

**Do they relieve the β=1 over-opening?** Yes — all three reduce it, most at `a = 0.5`
(ionic MAE 1.272 → 0.596). Per edge at `a = 0.5`: MgO +0.72 → +0.33, CaF₂ direct
+1.32 → +0.54, CaF₂ indirect +1.35 → +0.56, LiF +1.70 → +0.96. The relief shrinks as `a`
grows (LiF +0.96 → +1.09 → +1.41), since larger `a` pushes `B_a` back toward 1.

**Do they under-open the covalent edges (Si, C, AlAs) less than β=¼?** Yes — best at
`a = 2.0`, which restores most of the short-range Fock: covalent MAE 0.152 (a=2.0) vs 0.193
(β=¼), matching β=1's 0.153. Per direct edge vs β=¼: Si Γ −0.31 → −0.20, AlAs Γ
−0.42 → −0.33, C Γ −0.12 → +0.07.

**Why no global `a` beats the flat β=¼.** `B_a = ε⁻¹(a·μ)` rises with `A = 1/ε∞`, so the
finite-G prescription hands the *most* short-range Fock to the *most ionic* materials
(at a=0.5: Si B=0.15 vs LiF B=0.52) — exactly the materials that over-open and want *less*.
The material dependence is physically motivated (it is the literal dielectric screening at
G = a·μ) but runs opposite to what the gap errors prefer, so it cannot simultaneously
fix ionic over-opening and covalent under-opening with one constant. The practical takeaway
is an interpolation knob: `a → small` reproduces β=¼-like (ionic-friendly) behaviour,
`a → large` reproduces β=1-like (covalent-friendly) behaviour, and `a ≈ 0.5` is the best
single compromise across this 8-material set.
<!-- END:fganalysis -->

## Reproduce

```bash
conda activate qedev                       # numpy + access to ~/qe-7.5/bin
scripts/run_material.sh AlAs               # DD-RSH-CAM (β=1) full pipeline (serial)
QE_NP=4 OMP_NUM_THREADS=1 MPIRUN="mpirun --allow-run-as-root" \
  scripts/run_material.sh AlAs             #   ... the same under MPI (as root)
scripts/run_rsddh.sh AlAs                  # RS-DDH (β=¼): reuses the fit, reruns hybrid SCF
scripts/run_finiteg.sh AlAs 0.5            # finite-G (B_a = ε⁻¹(0.5·μ)); repeat for 1.0, 2.0
python3 scripts/write_comparison.py --write  # regenerate the tables above
```

## Files

```text
config/materials.toml             per-material structure + run parameters (source of truth)
runs/Si/  runs/C/  runs/AlAs/  runs/MgO/  runs/LiCl/  runs/NaCl/  runs/CaF2/  runs/LiF/
                                  PBE, eels, ddrshcam (β=1), rsddh (β=¼), finiteG_a{0.5,1.0,2.0}
scripts/run_material.sh           DD-RSH-CAM driver (PBE→eels→scan→fit→ddrshcam)
scripts/run_rsddh.sh              RS-DDH (β=0.25) driver — reuses the fit, reruns hybrid SCF
scripts/run_finiteg.sh            finite-G driver (B_a = ε⁻¹(a·μ)) — reuses the fit, per `a`
scripts/gen_inputs.py             generate the QE inputs from materials.toml (--which finiteg --a)
scripts/scan_eps_q.sh             generic turboEELS ε⁻¹(q) q-scan
scripts/fit_mu.py                 fit (ε∞, μ) from eps_q.dat with parabolic refinement
scripts/extract_gap.py            fundamental + Γ-direct gap from a pw.x .out
scripts/write_comparison.py       regenerate the tables in this file
results/Si-results.md             Si detail
results/MgO-results.md            MgO detail (PBE0/HSE limit checks)
```

> Toolchain notes: all QE steps use the self-built patched `~/qe-7.5/bin` (writes
> `charge-density.dat`; the conda `qe` build writes HDF5 that self-built `turbo_eels.x`
> cannot read). turboEELS fails at q=1.00 (2π/a) with a `minus_q` symmetry bug, so it is
> omitted from the default q-list in `scan_eps_q.sh` (a skip-on-failure guard remains for
> any other failure). Cutoffs: soft alkali halides (LiCl, NaCl) converge at 50 Ry; Si and
> AlAs at 60 Ry; the harder/semicore solids (C, MgO, LiF, CaF₂) use 80 Ry. Set `QE_NP` to
> run pw.x/turbo_eels.x under MPI (near-linear speedup). Ge and GaAs (3d-in-valence,
> 28/18 e per cell) are left out here — too expensive in serial; rerun with `QE_NP` (MPI)
> to make them feasible.
