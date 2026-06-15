#!/bin/bash
source /home/footman/miniconda3/etc/profile.d/conda.sh
conda activate qedev
export OMP_NUM_THREADS=4
cd /home/footman/DDRSH/runs/MgO/p2/ddrshcam
BIN=/home/footman/qe-7.5/bin
echo "=== DD-RSH-CAM SCF nqx=6x6x6 (converged q-grid) ==="
"$BIN/pw.x" -in mgo.nqx6.in > mgo.nqx6.out 2>&1
echo "  pw exit $?"
grep -E '!.*total energy' mgo.nqx6.out | tail -1
grep -E 'highest occupied' mgo.nqx6.out | tail -1
echo DONE_NQX6
