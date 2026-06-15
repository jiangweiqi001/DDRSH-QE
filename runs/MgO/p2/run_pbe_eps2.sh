#!/bin/bash
source /home/footman/miniconda3/etc/profile.d/conda.sh
conda activate qedev
export OMP_NUM_THREADS=4
cd /home/footman/DDRSH/runs/MgO/p2
BIN=/home/footman/qe-7.5/bin
echo "cores=$(nproc)"
echo "=== NSCF (40 bands, nosym) ==="
"$BIN/pw.x" -in pbe.nscf.in > pbe.nscf.out 2>&1
echo "  pw exit $?"
grep -E 'highest occupied' pbe.nscf.out | tail -1
echo "=== epsilon.x (IPA) ==="
"$BIN/epsilon.x" -in pbe.eps.in > pbe.eps.out 2>&1
echo "  epsilon exit $?"
echo "--- epsr.dat head (energy  eps_x  eps_y  eps_z) ---"
head -5 epsr.dat 2>/dev/null
echo DONE
