#!/usr/bin/env bash
# End-to-end non-empirical DD-RSH-CAM pipeline for one material.
#
#   PBE SCF  ->  eels SCF  ->  turboEELS eps^-1(q) scan  ->  fit (eps_inf, mu)
#            ->  DD-RSH-CAM SCF (aexx=1/eps_inf, hfscreen=mu)  ->  gaps
#
# All inputs are generated from config/materials.toml; nothing is hand-edited.
#
# Usage:   scripts/run_material.sh <Material>           (e.g. Si, AlAs, CaF2)
# Needs:   a Python env with numpy active (for gen_inputs/fit), and the self-built
#          patched QE 7.5 at $QE_BIN (default ~/qe-7.5/bin) which writes
#          charge-density.dat that turbo_eels.x can read.
#
# Env:     QE_BIN, OMP_NUM_THREADS (default 4).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MAT="${1:?usage: run_material.sh <Material>}"
BIN="${QE_BIN:-$HOME/qe-7.5/bin}"
PY="${PYTHON:-python3}"
export OMP_NUM_THREADS="${OMP_NUM_THREADS:-4}"

eval "$($PY - <<EOF
import sys; sys.path.insert(0, "$ROOT/scripts")
from matlib import load_materials
m = load_materials()["$MAT"]
print(f"PREFIX={m['prefix']}")
print(f"ALAT={m['celldm1']}")
EOF
)"

PBE_DIR="$ROOT/runs/$MAT/01-pbe-scf"
EELS_DIR="$ROOT/runs/$MAT/p2/eels"
DDH_DIR="$ROOT/runs/$MAT/p2/ddrshcam"

echo "===================================================================="
echo " DD-RSH-CAM pipeline: $MAT  (prefix=$PREFIX, alat=$ALAT bohr, bin=$BIN)"
echo "===================================================================="

echo "[1/6] generate PBE + eels inputs"
"$PY" "$ROOT/scripts/gen_inputs.py" "$MAT" --which pbe
"$PY" "$ROOT/scripts/gen_inputs.py" "$MAT" --which eels

echo "[2/6] PBE SCF"
( cd "$PBE_DIR" && rm -rf out && "$BIN/pw.x" -in "$PREFIX.scf.in" > "$PREFIX.scf.out" 2>&1 )
echo "  PBE gap:"
"$PY" "$ROOT/scripts/extract_gap.py" "$PBE_DIR/$PREFIX.scf.out" | sed 's/^/    /'

echo "[3/6] eels SCF (-> charge-density.dat)"
( cd "$EELS_DIR" && rm -rf out && "$BIN/pw.x" -in "$PREFIX.scf.in" > "$PREFIX.scf.out" 2>&1 )
test -f "$EELS_DIR/out/$PREFIX.save/charge-density.dat" \
  || { echo "ERROR: no charge-density.dat (need self-built QE, not HDF5 build)"; exit 1; }

echo "[4/6] turboEELS eps^-1(q) scan"
QE_BIN="$BIN" bash "$ROOT/scripts/scan_eps_q.sh" "$PREFIX" "$ALAT" "$EELS_DIR"
cp "$EELS_DIR/eps_q.dat" "$EELS_DIR/eps_q_clean.dat"

echo "[5/6] fit (eps_inf, mu)"
FIT="$("$PY" "$ROOT/scripts/fit_mu.py" "$EELS_DIR/eps_q_clean.dat")"
echo "$FIT" | sed 's/^/    /'
AEXX="$(echo "$FIT" | awk -F'=' '/AEXX=1\/eps_inf/{gsub(/ /,"",$2);print $2}')"
MU="$(echo "$FIT" | awk '/^mu /{print $3}')"
[ -n "$AEXX" ] && [ -n "$MU" ] || { echo "ERROR: could not parse fit"; exit 1; }

echo "[6/6] DD-RSH-CAM SCF  (aexx=$AEXX, hfscreen=$MU)"
"$PY" "$ROOT/scripts/gen_inputs.py" "$MAT" --which ddrshcam --aexx "$AEXX" --hfscreen "$MU"
( cd "$DDH_DIR" && rm -rf out6 && "$BIN/pw.x" -in "$PREFIX.ddrshcam.in" > "$PREFIX.ddrshcam.out" 2>&1 )

echo "===================================================================="
echo " $MAT DD-RSH-CAM gaps:"
"$PY" "$ROOT/scripts/extract_gap.py" "$DDH_DIR/$PREFIX.ddrshcam.out" | sed 's/^/    /'
echo " (regenerate the comparison table with: scripts/write_comparison.py)"
echo "===================================================================="
