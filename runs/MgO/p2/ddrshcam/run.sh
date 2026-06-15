#!/bin/bash
source /home/footman/miniconda3/etc/profile.d/conda.sh
conda activate qedev
export OMP_NUM_THREADS=4
cd /home/footman/DDRSH/runs/MgO/p2/ddrshcam
BIN=/home/footman/qe-7.5/bin
echo "=== DD-RSH-CAM SCF (aexx=0.3234, bexx=1.0, mu=0.7257) ==="
"$BIN/pw.x" -in mgo.ddrshcam.in > mgo.ddrshcam.out 2>&1
echo "  pw exit $?"
grep -E 'DD-RSH-CAM|AEXX' mgo.ddrshcam.out | head -3
grep -E '!.*total energy' mgo.ddrshcam.out | tail -1
grep -E 'highest occupied' mgo.ddrshcam.out | tail -1
echo DONE
