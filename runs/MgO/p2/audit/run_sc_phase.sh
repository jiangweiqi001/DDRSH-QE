#!/bin/bash
# Resume audit from Phase C (SC iter1) after hybrid convergence runs completed.
set -euo pipefail
source /home/footman/miniconda3/etc/profile.d/conda.sh
conda activate qedev
export OMP_NUM_THREADS=4

AUDIT=/home/footman/DDRSH/runs/MgO/p2/audit
BIN=/home/footman/qe-7.5/bin
ROOT=/home/footman/DDRSH
cd "$AUDIT"

log() { echo "[sc $(date +%H:%M:%S)] $*"; }

run_pw() {
  local tag="$1" infile="$2"
  log "START $tag"
  "$BIN/pw.x" -in "$infile" > "${infile%.in}.out" 2>&1
  log "DONE  $tag exit=$?"
  grep -E 'highest occupied' "${infile%.in}.out" | tail -1 || true
}

if [ ! -d ../ddrshcam/out6/mgo6.save ]; then
  log "ERROR: missing ../ddrshcam/out6/mgo6.save"
  exit 1
fi

log "NSCF (k666, nqx666, nbnd=16 — must match nqx6 SCF for ACE)"
run_pw "SC NSCF" sc_nscf.in

log "epsilon.x IPA"
"$BIN/epsilon.x" -in sc_eps.in > sc_eps.out 2>&1
log "epsilon exit=$?"
if ! grep -q "JOB DONE" sc_eps.out; then
  log "WARNING: epsilon.x failed — SC iter1 skipped (see sc_eps.out)"
  python3 "$ROOT/scripts/collect_audit_gaps.py"
  log "SC_PHASE_COMPLETE (partial)"
  exit 0
fi

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
print(f"{1.0/float('$EPS_INF'):.6f}")
PY
)

log "IPA eps_inf=$EPS_INF  AEXX $AEXX_BEFORE -> $AEXX_AFTER"

python3 - <<PY
import json
from pathlib import Path
Path("sc_meta.json").write_text(json.dumps({
    "epsilon_inf_ipa": float("$EPS_INF"),
    "aexx_before": float("$AEXX_BEFORE"),
    "aexx_after": float("$AEXX_AFTER"),
}, indent=2))
PY

sed -i "s/^[[:space:]]*aexx[[:space:]]*=.*/  aexx             = $AEXX_AFTER/" sc_iter1.in
run_pw "SC iter1" sc_iter1.in

python3 "$ROOT/scripts/collect_audit_gaps.py"
log "SC_PHASE_COMPLETE"
