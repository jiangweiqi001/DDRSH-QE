#!/usr/bin/env bash
# Density-scale finite-q dielectric-dependent hybrid for one material at a global η.
#
# Same kernel as DD-RSH-CAM / RS-DDH / finite-G (single μ, long-range Fock A = 1/ε∞), but
# the short-range Fock endpoint is the dielectric function at a DENSITY-derived wavevector
# q_cloud = η·q_WS, where q_WS is set by the cell's average valence density:
#
#     q_WS    = (4π n_v / 3)^(1/3),   n_v = N_val / Ω        (bohr⁻¹; Ω, N_val from PBE out)
#     B_η     = ε⁻¹(q_cloud) = 1 − (1 − A)·exp[ −(η·q_WS)² / (4 μ²) ],   A = 1/ε∞
#
# η is a global parameter (same for every material — no per-material / no gap fitting);
# B_η is material-dependent through A, μ and the density. The dielectric input (ε∞, μ) is
# functional-independent, so this REUSES the DD-RSH-CAM turboEELS fit and only re-runs the
# final hybrid SCF. Output goes to runs/<M>/p2/qcloud_eta<η>/ so the β=1 / β=¼ / finite-G
# results are left untouched.
#
# Prereq: scripts/run_material.sh <Material> has been run (eps_q_clean.dat + PBE out exist).
#
# Usage:   scripts/run_density_qcloud.sh <Material> <eta>
# Env:     QE_BIN QE_NP MPIRUN OMP_NUM_THREADS  -- see run_material.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MAT="${1:?usage: run_density_qcloud.sh <Material> <eta>}"
ETA="${2:?usage: run_density_qcloud.sh <Material> <eta>}"
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
EDIR="$("$PY" -c "import sys; sys.path.insert(0, '$ROOT/scripts'); \
from matlib import eta_tag; print(f'qcloud_eta{eta_tag(float($ETA))}')")"
EELS_DIR="$ROOT/runs/$MAT/p2/eels"
QC_DIR="$ROOT/runs/$MAT/p2/$EDIR"

test -f "$EELS_DIR/eps_q_clean.dat" \
  || { echo "ERROR: missing $EELS_DIR/eps_q_clean.dat — run run_material.sh $MAT first"; exit 1; }

echo "===================================================================="
echo " density-scale finite-q (η=$ETA) pipeline: $MAT  (prefix=$PREFIX, bin=$BIN)"
echo "===================================================================="

echo "[1/3] reuse turboEELS fit (eps_inf, mu) + cell density (N_val, Ω)"
FIT="$("$PY" "$ROOT/scripts/fit_mu.py" "$EELS_DIR/eps_q_clean.dat")"
echo "$FIT" | sed 's/^/    /'
AEXX="$(echo "$FIT" | awk '/AEXX=1\/eps_inf/{print $3}')"
MU="$(echo "$FIT" | awk '/^mu /{print $3}')"
[ -n "$AEXX" ] && [ -n "$MU" ] || { echo "ERROR: could not parse fit"; exit 1; }

# Echo the density quantities + endpoint so the run log is self-documenting.
"$PY" - "$MAT" "$AEXX" "$MU" "$ETA" <<'PYEOF'
import sys
sys.path.insert(0, "scripts")
from gen_inputs import q_ws, qcloud_bexx
from matlib import load_materials, pbe_density
name, aexx, mu, eta = sys.argv[1], float(sys.argv[2]), float(sys.argv[3]), float(sys.argv[4])
m = load_materials()[name]
nval, vol = pbe_density(name, m)
qws = q_ws(nval, vol)
B = qcloud_bexx(aexx, mu, qws, eta)
print(f"    N_val={nval:g}  Omega={vol:.3f} bohr^3  n_v={nval/vol:.5f}  "
      f"q_WS={qws:.4f}  q_cloud=eta*q_WS={eta*qws:.4f}  bohr^-1")
print(f"    A=aexx={aexx:.4f}  mu={mu:.4f}  ->  bexx=B_eta={B:.4f}")
PYEOF

echo "[2/3] density-scale hybrid SCF"
"$PY" "$ROOT/scripts/gen_inputs.py" "$MAT" --which qcloud \
  --aexx "$AEXX" --hfscreen "$MU" --eta "$ETA"
( cd "$QC_DIR" && rm -rf out_qc \
    && run_qe "$BIN/pw.x" -in "$PREFIX.qc.in" > "$PREFIX.qc.out" 2>&1 )

echo "===================================================================="
echo " $MAT density-scale finite-q (η=$ETA) gaps:"
"$PY" "$ROOT/scripts/extract_gap.py" "$QC_DIR/$PREFIX.qc.out" | sed 's/^/    /'
echo "===================================================================="
