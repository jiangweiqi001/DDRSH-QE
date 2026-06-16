#!/bin/bash
# MgO DD-RSH-CAM systematic audit (convergence + lattice + SC iter1).
set -euo pipefail
source /home/footman/miniconda3/etc/profile.d/conda.sh
conda activate qedev
export OMP_NUM_THREADS=4

AUDIT=/home/footman/DDRSH/runs/MgO/p2/audit
BIN=/home/footman/qe-7.5/bin
ROOT=/home/footman/DDRSH
cd "$AUDIT"

log() { echo "[audit $(date +%H:%M:%S)] $*"; }

run_pw() {
  local tag="$1" infile="$2"
  log "START $tag ($infile)"
  "$BIN/pw.x" -in "$infile" > "${infile%.in}.out" 2>&1
  local ec=$?
  log "DONE  $tag exit=$ec"
  grep -E 'highest occupied' "${infile%.in}.out" | tail -1 || true
  grep -E 'PWSCF.*WALL' "${infile%.in}.out" | tail -1 || true
  return 0
}

log "=== Phase A/B: PBE + hybrid audit runs ==="
run_pw "PBE a=4.148" pbe_4148.in
run_pw "fitted a=4.148" fit_4148.in
run_pw "lit a=4.148" lit_4148.in
run_pw "fitted k888" fit_k888.in
run_pw "fitted nqx8" fit_nqx8.in

log "=== Phase C: SC iteration 1 (epsilon.x IPA on nqx6 hybrid WFN) ==="
if [ ! -d ../ddrshcam/out6/mgo6.save ]; then
  log "ERROR: missing ../ddrshcam/out6/mgo6.save — run nqx6 first"
  exit 1
fi

log "NSCF on hybrid WFN (8x8x8, nosym)"
"$BIN/pw.x" -in sc_nscf.in > sc_nscf.out 2>&1
log "NSCF exit=$?"

log "epsilon.x IPA"
"$BIN/epsilon.x" -in sc_eps.in > sc_eps.out 2>&1
log "epsilon exit=$?"

EPS_INF=$(python3 - <<'PY'
from pathlib import Path
p = Path("epsr.dat")
for line in p.read_text().splitlines():
    if line.startswith("#"):
        continue
    parts = line.split()
    if len(parts) >= 4 and float(parts[0]) == 0.0:
        vals = [float(parts[i]) for i in (1, 2, 3)]
        print(sum(vals) / 3.0)
        break
PY
)
AEXX_BEFORE=0.3234
AEXX_AFTER=$(python3 - <<PY
eps = float("$EPS_INF")
print(f"{1.0/eps:.6f}")
PY
)

log "IPA eps_inf=$EPS_INF  AEXX $AEXX_BEFORE -> $AEXX_AFTER"

python3 - <<PY
import json
from pathlib import Path
meta = {
    "epsilon_inf_ipa": float("$EPS_INF"),
    "aexx_before": float("$AEXX_BEFORE"),
    "aexx_after": float("$AEXX_AFTER"),
}
Path("sc_meta.json").write_text(json.dumps(meta, indent=2))
PY

sed -i "s/^[[:space:]]*aexx[[:space:]]*=.*/  aexx             = $AEXX_AFTER/" sc_iter1.in

run_pw "SC iter1" sc_iter1.in

log "=== Collect report ==="
python3 "$ROOT/scripts/collect_audit_gaps.py"
log "AUDIT_COMPLETE"
