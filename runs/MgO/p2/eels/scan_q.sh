#!/bin/bash
# Scan turboEELS over q to get eps^-1(q) at omega=0 (PBE, RPA+local fields).
source /home/footman/miniconda3/etc/profile.d/conda.sh
conda activate qedev
export OMP_NUM_THREADS=4
cd /home/footman/DDRSH/runs/MgO/p2/eels
BIN=/home/footman/qe-7.5/bin
ALAT=7.9104
TPA=$(python3 -c "import math;print(2*math.pi/${ALAT})")   # 2pi/alat in bohr^-1

OUT=eps_q.dat
echo "# q[2pi/a]   q[bohr^-1]   eps_M(q,0)   eps^-1(q,0)" > "$OUT"

for q in 0.10 0.20 0.30 0.45 0.60 0.80 1.00 1.30 1.70; do
  cat > scan.eels.in <<EOF
&lr_input
  prefix = 'mgo'
  outdir = './out'
  restart_step = 250
  restart = .false.
/
&lr_control
  itermax = 300
  q1 = ${q}
  q2 = 0.0
  q3 = 0.0
  approximation = 'TDDFT'
/
EOF
  cat > scan.pp.in <<EOF
&lr_input
  prefix = 'mgo'
  outdir = './out'
  eels = .true.
  itermax0 = 300
  itermax  = 6000
  extrapolation = "osc"
  epsil = 0.02
  units = 1
  start = 0.0
  end   = 5.0
  increment = 0.05
/
EOF
  "$BIN/turbo_eels.x" -in scan.eels.in > scan.eels.q${q}.out 2>&1
  "$BIN/turbo_spectrum.x" -in scan.pp.in > scan.pp.q${q}.out 2>&1
  # first data line of plot_eps.dat = omega=0 : cols: w  Re(1/eps)  -Im(1/eps)  Re(eps)  Im(eps)
  line=$(grep -v '^#' mgo.plot_eps.dat | head -1)
  reps=$(echo "$line" | awk '{print $4}')
  rinv=$(echo "$line" | awk '{print $2}')
  qbohr=$(python3 -c "print(${q}*${TPA})")
  echo "${q}  ${qbohr}  ${reps}  ${rinv}" >> "$OUT"
  echo "q=${q} (2pi/a)  qbohr=${qbohr}  eps=${reps}  epsinv=${rinv}"
  cp mgo.plot_eps.dat plot_eps.q${q}.dat
done
echo "=== eps_q.dat ==="
cat "$OUT"
echo DONE
