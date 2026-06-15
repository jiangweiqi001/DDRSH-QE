# DDRSH QE Approximate Reproduction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reproduce the MgO dielectric-dependent hybrid chain in Quantum ESPRESSO: PBE -> electronic epsilon_inf -> exx_fraction = 1/epsilon_inf -> global DDH (PBE0) gap, plus an approximate DD-HSE comparison.

**Architecture:** One directory per QE step. The primary, exactly reproducible target is global DDH (PBE0 with alpha = 1/epsilon_inf). DD-HSE is an approximate stand-in for the range-separated family and is documented as such. Strict DD-RSH-CAM requires patched QE and is out of scope.

**Tech Stack:** Quantum ESPRESSO (`pw.x`, `epsilon.x`), norm-conserving PBE pseudopotentials, Python 3 standard library.

---

### Task 1: Provide Pseudopotentials

**Files:**
- Create: `pseudos/Mg_ONCV_PBE-1.2.upf`
- Create: `pseudos/O_ONCV_PBE-1.2.upf`

- [ ] **Step 1: Download norm-conserving PBE UPF files**

Get ONCV SR PBE (standard) UPF for Mg and O from PseudoDojo and place them in `pseudos/`
with the names referenced in the inputs (or edit `ATOMIC_SPECIES` to match).

Expected: both UPF files exist in `pseudos/`.

### Task 2: Run PBE SCF

**Files:**
- Use: `runs/MgO/01-pbe-scf/mgo.scf.in`
- Create: `runs/MgO/01-pbe-scf/mgo.scf.out`

- [ ] **Step 1: Run SCF**

```bash
cd runs/MgO/01-pbe-scf
pw.x -in mgo.scf.in > mgo.scf.out
```

Expected: output contains `highest occupied, lowest unoccupied level (ev):`.

- [ ] **Step 2: Check the gap parser**

```bash
cd ../../..
python3 scripts/extract_qe_summary.py runs/MgO/01-pbe-scf/mgo.scf.out runs/MgO/02-eps/epsr.dat --json results/MgO-qe-summary.json
```

Expected: `pbe_gap.gap_eV` is populated (epsilon still pending until Task 3).

### Task 3: Compute Electronic epsilon_inf

**Files:**
- Use: `runs/MgO/02-eps/mgo.scf.in`, `runs/MgO/02-eps/mgo.nscf.in`, `runs/MgO/02-eps/mgo.eps.in`
- Create: `runs/MgO/02-eps/epsr.dat`

- [ ] **Step 1: Run scf + nscf + epsilon.x**

```bash
cd runs/MgO/02-eps
pw.x -in mgo.scf.in  > mgo.scf.out
pw.x -in mgo.nscf.in > mgo.nscf.out
epsilon.x -in mgo.eps.in > mgo.eps.out
```

Expected: `epsr.dat` exists with a static (low-energy) row.

- [ ] **Step 2: Extract epsilon_inf and exx_fraction**

```bash
cd ../../..
python3 scripts/extract_qe_summary.py runs/MgO/01-pbe-scf/mgo.scf.out runs/MgO/02-eps/epsr.dat --json results/MgO-qe-summary.json
```

Expected: `epsilon_inf` and `exx_fraction` are populated.

### Task 4: Propagate exx_fraction Into Hybrid Inputs

**Files:**
- Modify: `runs/MgO/03-ddh-pbe0/mgo.scf.in`
- Modify: `runs/MgO/04-dd-hse/mgo.scf.in`

- [ ] **Step 1: Update both inputs from the summary**

```bash
python3 scripts/update_exx_fraction.py --summary results/MgO-qe-summary.json runs/MgO/03-ddh-pbe0/mgo.scf.in runs/MgO/04-dd-hse/mgo.scf.in
```

Expected: both inputs show `exx_fraction = <1/epsilon_inf>`.

### Task 5: Run DDH (PBE0) and DD-HSE

**Files:**
- Create: `runs/MgO/03-ddh-pbe0/mgo.scf.out`
- Create: `runs/MgO/04-dd-hse/mgo.scf.out`

- [ ] **Step 1: Run the global DDH (primary target)**

```bash
cd runs/MgO/03-ddh-pbe0
pw.x -in mgo.scf.in > mgo.scf.out
```

Expected: gap near the literature DDH value of 7.70 eV.

- [ ] **Step 2: Run the approximate DD-HSE**

```bash
cd ../04-dd-hse
pw.x -in mgo.scf.in > mgo.scf.out
```

Expected: a gap that differs from DD-RSH-CAM because the long-range topology differs.

### Task 6: Build the Result Table and Error Analysis

**Files:**
- Modify: `results/MgO-ddrsh-summary.md`

- [ ] **Step 1: Generate the table**

```bash
cd ../../..
python3 scripts/write_results_table.py --material MgO \
  --summary results/MgO-qe-summary.json \
  --ddh-out runs/MgO/03-ddh-pbe0/mgo.scf.out \
  --hse-out runs/MgO/04-dd-hse/mgo.scf.out \
  --out results/MgO-ddrsh-summary.md
```

Expected: DDH and DD-HSE gaps are no longer `pending`.

- [ ] **Step 2: Record provenance and deviations**

Add QE version, pseudopotential files, `ecutwfc`/`ecutrho`/k-mesh/`nqx`, whether
epsilon_inf came from eps.x or a hybrid recompute, and that DD-HSE is approximate.

Reference values for comparison:

```text
PBE 4.79; HSE06 6.47; DDH 7.70; RS-DDH 7.88; DD0-RSH-CAM 8.32; Exp 7.83; ZPR 0.53
```
