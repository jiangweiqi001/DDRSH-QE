#!/usr/bin/env bash
# Finite-G dielectric-dependent hybrid for one material at a global constant `a`.
#
# Same kernel as DD-RSH-CAM / RS-DDH (single μ, long-range Fock A = 1/ε∞), but the
# short-range Fock endpoint is the dielectric function at finite wavevector G = a·μ:
#
#     B_a = ε⁻¹(a·μ) = 1 − (1 − A)·exp(−a²/4)        (A = aexx = 1/ε∞)
#
# `a` is a global parameter (same for every material); B_a is material-dependent through A.
# The dielectric input (ε∞, μ) is functional-independent, so this REUSES the DD-RSH-CAM
# turboEELS fit and only re-runs the final hybrid SCF. Output goes to
# runs/<M>/p2/finiteG_a<a>/ so the DD-RSH-CAM and RS-DDH results are left untouched.
#
# Prereq: scripts/run_material.sh <Material> has been run (eps_q_clean.dat exists).
#
# Usage:   scripts/run_finiteg.sh <Material> <a>
# Env:     QE_BIN QE_NP MPIRUN OMP_NUM_THREADS  -- see run_material.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MAT="${1:?usage: run_finiteg.sh <Material> <a>}"
AVAL="${2:?usage: run_finiteg.sh <Material> <a>}"
BIN="${QE_BIN:-$HOME/qe-7.5/bin}"
PY="${PYTHON:-python3}"
QE_NP="${QE_NP:-1}"
MPIRUN="${MPIRUN:-mpirun}"
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
ADIR="$("$PY" -c "print(f'finiteG_a{float($AVAL):.1f}')")"
EELS_DIR="$ROOT/runs/$MAT/p2/eels"
FG_DIR="$ROOT/runs/$MAT/p2/$ADIR"

test -f "$EELS_DIR/eps_q_clean.dat" \
  || { echo "ERROR: missing $EELS_DIR/eps_q_clean.dat — run run_material.sh $MAT first"; exit 1; }

echo "===================================================================="
echo " finite-G (a=$AVAL) pipeline: $MAT  (prefix=$PREFIX, bin=$BIN)"
echo "===================================================================="

echo "[1/3] reuse turboEELS fit (eps_inf, mu)"
FIT="$("$PY" "$ROOT/scripts/fit_mu.py" "$EELS_DIR/eps_q_clean.dat")"
echo "$FIT" | sed 's/^/    /'
AEXX="$(echo "$FIT" | awk '/AEXX=1\/eps_inf/{print $3}')"
MU="$(echo "$FIT" | awk '/^mu /{print $3}')"
[ -n "$AEXX" ] && [ -n "$MU" ] || { echo "ERROR: could not parse fit"; exit 1; }

BA="$("$PY" -c "import math; A=$AEXX; a=$AVAL; print(f'{1-(1-A)*math.exp(-a*a/4):.4f}')")"
echo "[2/3] finite-G SCF  (aexx=$AEXX, a=$AVAL -> bexx=B_a=$BA, hfscreen=$MU)"
"$PY" "$ROOT/scripts/gen_inputs.py" "$MAT" --which finiteg \
  --aexx "$AEXX" --hfscreen "$MU" --a "$AVAL"
( cd "$FG_DIR" && rm -rf out_fg \
    && run_qe "$BIN/pw.x" -in "$PREFIX.fg.in" > "$PREFIX.fg.out" 2>&1 )

echo "===================================================================="
echo " $MAT finite-G (a=$AVAL, B_a=$BA) gaps:"
"$PY" "$ROOT/scripts/extract_gap.py" "$FG_DIR/$PREFIX.fg.out" | sed 's/^/    /'
echo "===================================================================="
