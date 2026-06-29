#!/usr/bin/env bash
# Density-peak log-curvature finite-q dielectric-dependent hybrid for one material at global κ.
#
# Same kernel as DD-RSH-CAM / RS-DDH / finite-G / qcloud (single μ, long-range Fock A = 1/ε∞),
# but the short-range Fock endpoint is the dielectric function at a wavevector set by the LOCAL
# valence electron-cloud size of the active species, q_peak = κ/σ_peak:
#
#     ln ρ̄_s(r) ≈ c₀ + c₁(r−r₀) + c₂(r−r₀)²,   σ_peak = sqrt(−1/(2 c₂))   (PBE valence density)
#     B_κ      = ε⁻¹(q_peak) = 1 − (1 − A)·exp[ −q_peak² / (4 μ²) ],   q_peak = κ/σ_peak
#
# κ is a GLOBAL constant (same for every material — no per-material / no gap fitting); B_κ is
# material-dependent through A, μ and σ_peak. The active species is fixed in qpeak.ACTIVE_SPECIES.
# The dielectric input (ε∞, μ) is functional-independent, so this REUSES the DD-RSH-CAM turboEELS
# fit and only re-runs the final hybrid SCF. Output goes to runs/<M>/p2/qpeak_kappa<κ>/ so the
# β=1 / β=¼ / finite-G / qcloud results are left untouched.
#
# Prereq: scripts/run_material.sh <Material> has been run (eps_q_clean.dat + PBE save exist).
#
# Usage:   scripts/run_density_qpeak.sh <Material> <kappa>
# Env:     QE_BIN QE_NP MPIRUN OMP_NUM_THREADS  -- see run_material.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MAT="${1:?usage: run_density_qpeak.sh <Material> <kappa>}"
KAPPA="${2:?usage: run_density_qpeak.sh <Material> <kappa>}"
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
from matlib import kappa_tag; print(f'qpeak_kappa{kappa_tag(float($KAPPA))}')")"
EELS_DIR="$ROOT/runs/$MAT/p2/eels"
QP_DIR="$ROOT/runs/$MAT/p2/$EDIR"

test -f "$EELS_DIR/eps_q_clean.dat" \
  || { echo "ERROR: missing $EELS_DIR/eps_q_clean.dat — run run_material.sh $MAT first"; exit 1; }

echo "===================================================================="
echo " density-peak log-curvature finite-q (κ=$KAPPA): $MAT  (prefix=$PREFIX, bin=$BIN)"
echo "===================================================================="

echo "[1/3] reuse turboEELS fit (eps_inf, mu) + PBE valence-density σ_peak (active species)"
FIT="$("$PY" "$ROOT/scripts/fit_mu.py" "$EELS_DIR/eps_q_clean.dat")"
echo "$FIT" | sed 's/^/    /'
AEXX="$(echo "$FIT" | awk '/AEXX=1\/eps_inf/{print $3}')"
MU="$(echo "$FIT" | awk '/^mu /{print $3}')"
[ -n "$AEXX" ] && [ -n "$MU" ] || { echo "ERROR: could not parse fit"; exit 1; }

# Echo σ_peak + endpoint so the run log is self-documenting.
"$PY" - "$MAT" "$AEXX" "$MU" "$KAPPA" <<'PYEOF'
import sys
sys.path.insert(0, "scripts")
from qpeak import ACTIVE_SPECIES, qpeak_bexx, species_sigma
name, aexx, mu, kappa = sys.argv[1], float(sys.argv[2]), float(sys.argv[3]), float(sys.argv[4])
sp = ACTIVE_SPECIES[name]
fit = species_sigma(name, __import__("matlib").load_materials()[name]["prefix"])[sp]
if fit["sigma"] is None:
    sys.exit(f"ERROR: σ_peak fit failed for {name}/{sp}: {fit['status']}")
q, B = qpeak_bexx(aexx, mu, fit["sigma"], kappa)
print(f"    active_species={sp}  r0={fit['r0']:.3f}  sigma_peak={fit['sigma']:.4f} bohr  "
      f"R2={fit['R2']:.4f}")
print(f"    q_peak=kappa/sigma={q:.4f} bohr^-1  q_peak/mu={q/mu:.3f}")
print(f"    A=aexx={aexx:.4f}  mu={mu:.4f}  ->  bexx=B_kappa={B:.4f}")
if not (aexx <= B <= 1.0):
    print(f"    WARNING: B_kappa={B:.4f} outside [A={aexx:.3f}, 1]")
PYEOF

echo "[2/3] density-peak log-curvature hybrid SCF"
"$PY" "$ROOT/scripts/gen_inputs.py" "$MAT" --which qpeak \
  --aexx "$AEXX" --hfscreen "$MU" --kappa "$KAPPA"
( cd "$QP_DIR" && rm -rf out_qp \
    && run_qe "$BIN/pw.x" -in "$PREFIX.qp.in" > "$PREFIX.qp.out" 2>&1 )

echo "===================================================================="
echo " $MAT density-peak log-curvature finite-q (κ=$KAPPA) gaps:"
"$PY" "$ROOT/scripts/extract_gap.py" "$QP_DIR/$PREFIX.qp.out" | sed 's/^/    /'
echo "===================================================================="
