#!/bin/bash
source /home/footman/miniconda3/etc/profile.d/conda.sh
conda activate qedev
cd /home/footman/DDRSH/runs/MgO/p2
BIN=/home/footman/qe-7.5/bin
echo "=== PBE SCF ==="
"$BIN/pw.x" -in pbe.scf.in > pbe.scf.out 2>&1
echo "  pw exit $?"
grep -E '!.*total energy' pbe.scf.out | tail -1
grep -E 'highest occupied' pbe.scf.out | tail -1
echo "=== DFPT eps_inf ==="
"$BIN/ph.x" -in pbe.eps.ph.in > pbe.eps.ph.out 2>&1
echo "  ph exit $?"
grep -A4 'Dielectric constant in cartesian axis' pbe.eps.ph.out | tail -6
echo DONE
