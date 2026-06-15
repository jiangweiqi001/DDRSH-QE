#!/usr/bin/env bash
# Run the full MgO QE DDRSH-approximation chain end to end.
# Requires the conda `qe` env created by scripts/install_qe.sh and the
# pseudopotentials in pseudos/.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONDA_BASE="${CONDA_BASE:-$HOME/miniconda3}"
QE="$CONDA_BASE/bin/conda run -n qe"
THREADS="${OMP_NUM_THREADS:-4}"

run_pw() {
  local dir="$1" infile="$2" outfile="$3"
  echo "[run_all] pw.x: $dir/$infile"
  ( cd "$ROOT/$dir" && OMP_NUM_THREADS="$THREADS" $QE pw.x -in "$infile" > "$outfile" 2>&1 )
}

echo "[run_all] 1/6 PBE SCF"
run_pw runs/MgO/01-pbe-scf mgo.scf.in mgo.scf.out

echo "[run_all] 2/6 epsilon_inf via DFPT (scf + ph.x epsil)"
run_pw runs/MgO/02-eps mgo.scf.in mgo.scf.out
( cd "$ROOT/runs/MgO/02-eps" && OMP_NUM_THREADS="$THREADS" $QE ph.x -in mgo.ph.in > mgo.ph.out 2>&1 )

echo "[run_all] 3/6 extract gap + epsilon_inf"
python3 "$ROOT/scripts/extract_qe_summary.py" \
  "$ROOT/runs/MgO/01-pbe-scf/mgo.scf.out" \
  "$ROOT/runs/MgO/02-eps/mgo.ph.out" \
  --json "$ROOT/results/MgO-qe-summary.json"

echo "[run_all] 4/6 propagate exx_fraction into hybrid inputs"
python3 "$ROOT/scripts/update_exx_fraction.py" \
  --summary "$ROOT/results/MgO-qe-summary.json" \
  "$ROOT/runs/MgO/03-ddh-pbe0/mgo.scf.in" \
  "$ROOT/runs/MgO/04-dd-hse/mgo.scf.in"

echo "[run_all] 5/6 DDH (PBE0) and DD-HSE"
run_pw runs/MgO/03-ddh-pbe0 mgo.scf.in mgo.scf.out
run_pw runs/MgO/04-dd-hse   mgo.scf.in mgo.scf.out

echo "[run_all] 6/6 write results table"
python3 "$ROOT/scripts/write_results_table.py" --material MgO \
  --summary "$ROOT/results/MgO-qe-summary.json" \
  --ddh-out "$ROOT/runs/MgO/03-ddh-pbe0/mgo.scf.out" \
  --hse-out "$ROOT/runs/MgO/04-dd-hse/mgo.scf.out" \
  --out "$ROOT/results/MgO-ddrsh-summary.md"

echo "[run_all] DONE -> results/MgO-ddrsh-summary.md"
