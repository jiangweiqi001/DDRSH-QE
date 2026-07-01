#!/usr/bin/env bash
# CALIBRATION: density-peak range-separation. Keep DD-RSH-CAM β=1 (short-range Fock = 1,
# long-range Fock A = 1/ε∞) but REPLACE the EELS-fitted screening μ by a density-derived one
#
#     μ_eff = c / σ_peak     (σ_peak = log-curvature width of the active species' PBE valence
#                             density peak; c is a single GLOBAL constant)
#
# Only `hfscreen` changes vs the β=1 production run; aexx = A and bexx = 1 are reused. Output
# goes to runs/<M>/p2/densmu_c<c>/ so the β=1 / β=¼ / finite-G / qcloud / qpeak runs are
# untouched. This is a calibration scan to find a global c, not a production model (yet).
#
# Prereq: scripts/run_material.sh <Material> has been run (eps_q_clean.dat + PBE save exist).
#
# Usage:   scripts/run_density_mu.sh <Material> <c>
# Env:     QE_BIN QE_NP MPIRUN OMP_NUM_THREADS  -- see run_material.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MAT="${1:?usage: run_density_mu.sh <Material> <c>}"
CVAL="${2:?usage: run_density_mu.sh <Material> <c>}"
BIN="${QE_BIN:-$HOME/qe-7.5/bin}"
PY="${PYTHON:-python3}"
QE_NP="${QE_NP:-1}"
MPIRUN="${MPIRUN:-mpirun}"
export OMP_NUM_THREADS="${OMP_NUM_THREADS:-4}"

run_qe() {
  if [ "$QE_NP" -gt 1 ]; then
    $MPIRUN -np "$QE_NP" "$@"
  else
    "$@"
  fi
}

if [ "$QE_NP" -gt 1 ]; then
  qe_banner="$(printf '' | "$BIN/pw.x" 2>&1 || true)"
  if ! printf '%s' "$qe_banner" | grep -q "Parallel version"; then
    echo "ERROR: QE_NP=$QE_NP but $BIN/pw.x is a serial (non-MPI) build." >&2
    exit 1
  fi
fi

PREFIX="$("$PY" -c "import sys; sys.path.insert(0, '$ROOT/scripts'); \
from matlib import load_materials; print(load_materials()['$MAT']['prefix'])")"
CTAG="$("$PY" -c "import sys; sys.path.insert(0, '$ROOT/scripts'); \
from matlib import kappa_tag; print(kappa_tag(float($CVAL)))")"
EELS_DIR="$ROOT/runs/$MAT/p2/eels"
DM_DIR="$ROOT/runs/$MAT/p2/densmu_c$CTAG"

test -f "$EELS_DIR/eps_q_clean.dat" \
  || { echo "ERROR: missing $EELS_DIR/eps_q_clean.dat — run run_material.sh $MAT first"; exit 1; }

echo "===================================================================="
echo " density-μ calibration (c=$CVAL, β=1): $MAT  (prefix=$PREFIX)"
echo "===================================================================="

FIT="$("$PY" "$ROOT/scripts/fit_mu.py" "$EELS_DIR/eps_q_clean.dat")"
AEXX="$(echo "$FIT" | awk '/AEXX=1\/eps_inf/{print $3}')"
MU_FIT="$(echo "$FIT" | awk '/^mu /{print $3}')"
[ -n "$AEXX" ] || { echo "ERROR: could not parse fit"; exit 1; }

MU_EFF="$("$PY" - "$MAT" "$CVAL" <<'PYEOF'
import sys
sys.path.insert(0, "scripts")
from matlib import load_materials
from qpeak import ACTIVE_SPECIES, species_sigma
name, c = sys.argv[1], float(sys.argv[2])
sp = ACTIVE_SPECIES[name]
fit = species_sigma(name, load_materials()[name]["prefix"])[sp]
if fit["sigma"] is None:
    sys.exit(f"ERROR: σ_peak fit failed for {name}/{sp}: {fit['status']}")
print(f"{c / fit['sigma']:.4f}")
PYEOF
)"
echo "    A=aexx=$AEXX  mu_fit=$MU_FIT  ->  mu_eff=c/sigma_peak=$MU_EFF  (bexx=1.0)"

mkdir -p "$DM_DIR"
"$PY" "$ROOT/scripts/gen_inputs.py" "$MAT" --which ddrshcam \
  --aexx "$AEXX" --hfscreen "$MU_EFF" --bexx 1.0 --stdout \
  | sed '1d' > "$DM_DIR/$PREFIX.dm.in"     # drop the "===== ddrshcam =====" banner line
( cd "$DM_DIR" && rm -rf out6 \
    && run_qe "$BIN/pw.x" -in "$PREFIX.dm.in" > "$PREFIX.dm.out" 2>&1 )

echo " $MAT density-μ (c=$CVAL, μ_eff=$MU_EFF) gaps:"
"$PY" "$ROOT/scripts/extract_gap.py" "$DM_DIR/$PREFIX.dm.out" | sed 's/^/    /'
echo "===================================================================="
