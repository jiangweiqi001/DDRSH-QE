#!/bin/bash
set -e
source /home/footman/miniconda3/etc/profile.d/conda.sh
conda activate qedev
cd /home/footman/DDRSH/runs/MgO/validate
PW=/home/footman/qe-7.5/bin/pw.x
for c in pbe0_native pbe0_model hse_native hse_model; do
  echo "=== $c ==="
  "$PW" -in "$c.in" > "$c.out" 2>&1 || echo "  (pw.x exit $?)"
  grep -E '!.*total energy' "$c.out" | tail -1
  grep -E 'convergence has been achieved' "$c.out" | tail -1
done
echo DONE
