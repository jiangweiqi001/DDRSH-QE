#!/bin/bash
source /home/footman/miniconda3/etc/profile.d/conda.sh
conda activate qedev
export OMP_NUM_THREADS=4
cd /home/footman/DDRSH/runs/MgO/p2/ddrshcam
BIN=/home/footman/qe-7.5/bin
echo "=== DD-RSH-CAM SCF, LITERATURE params (eps_inf=2.81 -> aexx=0.3559, mu=0.63), nqx=6 ==="
"$BIN/pw.x" -in mgo.litparams.in > mgo.litparams.out 2>&1
echo "  pw exit $?"
grep -E '!.*total energy' mgo.litparams.out | tail -1
grep -E 'highest occupied' mgo.litparams.out | tail -1
echo DONE_LITPARAMS
