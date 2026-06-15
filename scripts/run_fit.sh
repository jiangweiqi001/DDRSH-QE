#!/bin/bash
source /home/footman/miniconda3/etc/profile.d/conda.sh
conda activate qedev
cd /home/footman/DDRSH
echo "=== fit eps_inf AND mu (free) ==="
python3 scripts/fit_mu.py runs/MgO/p2/eels/eps_q_clean.dat
