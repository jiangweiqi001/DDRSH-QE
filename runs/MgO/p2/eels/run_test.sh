#!/bin/bash
source /home/footman/miniconda3/etc/profile.d/conda.sh
conda activate qedev
export OMP_NUM_THREADS=4
cd /home/footman/DDRSH/runs/MgO/p2/eels
BIN=/home/footman/qe-7.5/bin
echo "=== SCF ==="
"$BIN/pw.x" -in mgo.scf.in > mgo.scf.out 2>&1
echo "  pw exit $?"
grep -E 'highest occupied' mgo.scf.out | tail -1
echo "=== turbo_eels q1=0.5 ==="
"$BIN/turbo_eels.x" -in test.eels.in > test.eels.out 2>&1
echo "  eels exit $?"
tail -3 test.eels.out
echo "=== turbo_spectrum ==="
"$BIN/turbo_spectrum.x" -in test.pp.in > test.pp.out 2>&1
echo "  pp exit $?"
echo "--- dat files produced ---"
ls -t *.dat *.plot* 2>/dev/null | head
echo DONE
