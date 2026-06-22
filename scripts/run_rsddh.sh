#!/usr/bin/env bash
# Skone 2016 RS-DDH (short-range Fock bexx=0.25) for one material.
#
# The dielectric input (eps_inf, mu) is functional-independent (PBE-level turboEELS),
# so this REUSES the fit produced by the DD-RSH-CAM pipeline and only re-runs the final
# hybrid SCF with bexx=0.25 instead of 1.0. PBE / eels / turboEELS are NOT recomputed.
# Output goes to runs/<M>/p2/rsddh/ so the Chen 2018 DD-RSH-CAM results are left untouched.
#
# Prereq: scripts/run_material.sh <Material> has been run (eps_q_clean.dat exists).
#
# Usage:   scripts/run_rsddh.sh <Material>
# Env:
#   QE_BIN   QE bin dir (default ~/qe-7.5/bin)
#   QE_NP    MPI ranks (default 1 = serial). >1 needs an MPI build (scripts/build_qe.sh).
#   MPIRUN   MPI launcher, may carry flags (default mpirun). As root use
#            MPIRUN="mpirun --allow-run-as-root".
#   BEXX     short-range Fock fraction (default 0.25 = RS-DDH)
#   OMP_NUM_THREADS  threads per rank (default 4)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MAT="${1:?usage: run_rsddh.sh <Material>}"
BIN="${QE_BIN:-$HOME/qe-7.5/bin}"
PY="${PYTHON:-python3}"
QE_NP="${QE_NP:-1}"
MPIRUN="${MPIRUN:-mpirun}"
BEXX="${BEXX:-0.25}"
export OMP_NUM_THREADS="${OMP_NUM_THREADS:-4}"

run_qe() {
  if [ "$QE_NP" -gt 1 ]; then
    # MPIRUN is intentionally unquoted so it can carry flags, e.g.
    #   MPIRUN="mpirun --allow-run-as-root"  (needed when running as root)
    $MPIRUN -np "$QE_NP" "$@"
  else
    "$@"
  fi
}

# Guard: mpirun on a serial (non-MPI) QE binary launches N independent rank-0 copies
# that clobber each other's outputs and silently corrupt results. Refuse it.
# pw.x exits non-zero on empty input (MPI_ABORT), so capture the banner first (|| true)
# to keep `set -o pipefail` from masking the grep result.
if [ "$QE_NP" -gt 1 ]; then
  qe_banner="$(printf '' | "$BIN/pw.x" 2>&1 || true)"
  if ! printf '%s' "$qe_banner" | grep -q "Parallel version"; then
    echo "ERROR: QE_NP=$QE_NP but $BIN/pw.x is a serial (non-MPI) build." >&2
    echo "       Rebuild with MPI (scripts/build_qe.sh) or unset QE_NP." >&2
    exit 1
  fi
fi

PREFIX="$("$PY" -c "import sys; sys.path.insert(0, '$ROOT/scripts'); \
from matlib import load_materials; print(load_materials()['$MAT']['prefix'])")"
EELS_DIR="$ROOT/runs/$MAT/p2/eels"
RS_DIR="$ROOT/runs/$MAT/p2/rsddh"

test -f "$EELS_DIR/eps_q_clean.dat" \
  || { echo "ERROR: missing $EELS_DIR/eps_q_clean.dat — run run_material.sh $MAT first"; exit 1; }

echo "===================================================================="
echo " RS-DDH (Skone 2016, bexx=$BEXX) pipeline: $MAT  (prefix=$PREFIX, bin=$BIN)"
echo "===================================================================="

echo "[1/3] reuse turboEELS fit (eps_inf, mu)"
FIT="$("$PY" "$ROOT/scripts/fit_mu.py" "$EELS_DIR/eps_q_clean.dat")"
echo "$FIT" | sed 's/^/    /'
AEXX="$(echo "$FIT" | awk '/AEXX=1\/eps_inf/{print $3}')"
MU="$(echo "$FIT" | awk '/^mu /{print $3}')"
[ -n "$AEXX" ] && [ -n "$MU" ] || { echo "ERROR: could not parse fit"; exit 1; }

echo "[2/3] RS-DDH SCF  (aexx=$AEXX, bexx=$BEXX, hfscreen=$MU)"
"$PY" "$ROOT/scripts/gen_inputs.py" "$MAT" --which rsddh \
  --aexx "$AEXX" --hfscreen "$MU" --bexx "$BEXX"
( cd "$RS_DIR" && rm -rf out_rs \
    && run_qe "$BIN/pw.x" -in "$PREFIX.rsddh.in" > "$PREFIX.rsddh.out" 2>&1 )

echo "===================================================================="
echo " $MAT RS-DDH gaps:"
"$PY" "$ROOT/scripts/extract_gap.py" "$RS_DIR/$PREFIX.rsddh.out" | sed 's/^/    /'
echo "===================================================================="
