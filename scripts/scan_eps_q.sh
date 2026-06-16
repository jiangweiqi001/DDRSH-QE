#!/bin/bash
# Generic turboEELS eps^-1(q) q-scan at omega=0 (PBE, RPA + crystal local fields).
# Usage: scan_eps_q.sh <prefix> <alat_bohr> <workdir>
# The workdir must already contain a converged SCF save in ./out (self-built
# QE 7.5, charge-density.dat) with the given prefix.
set -uo pipefail

PREFIX="$1"; ALAT="$2"; WORKDIR="$3"
BIN="${QE_BIN:-$HOME/qe-7.5/bin}"
export OMP_NUM_THREADS="${OMP_NUM_THREADS:-4}"

cd "$WORKDIR"
TPA=$(python3 -c "import math;print(2*math.pi/${ALAT})")   # 2pi/alat in bohr^-1
OUT=eps_q.dat
echo "# q[2pi/a]   q[bohr^-1]   eps_M(q,0)   eps^-1(q,0)" > "$OUT"

for q in 0.10 0.20 0.30 0.45 0.60 0.80 1.00 1.30 1.70; do
  cat > scan.eels.in <<EOF
&lr_input
  prefix = '${PREFIX}'
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
  prefix = '${PREFIX}'
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
  # Drop stale outputs so a failed turbo_eels can't leave turbo_spectrum
  # regenerating the previous q's spectrum from old Lanczos coefficients.
  rm -f ${PREFIX}.plot_eps.dat out/${PREFIX}.beta_gamma_z.* out/${PREFIX}.save/*.beta_gamma_z.*
  if ! "$BIN/turbo_eels.x" -in scan.eels.in > scan.eels.q${q}.out 2>&1; then
    echo "q=${q}  SKIPPED (turbo_eels failed: e.g. minus_q symmetry bug)"
    continue
  fi
  "$BIN/turbo_spectrum.x" -in scan.pp.in > scan.pp.q${q}.out 2>&1
  if [ ! -f ${PREFIX}.plot_eps.dat ]; then
    echo "q=${q}  SKIPPED (no plot_eps.dat; turbo_spectrum failed for this q)"
    continue
  fi
  line=$(grep -v '^#' ${PREFIX}.plot_eps.dat | head -1)
  reps=$(echo "$line" | awk '{print $4}')
  rinv=$(echo "$line" | awk '{print $2}')
  qbohr=$(python3 -c "print(${q}*${TPA})")
  echo "${q}  ${qbohr}  ${reps}  ${rinv}" >> "$OUT"
  echo "q=${q} (2pi/a)  qbohr=${qbohr}  eps=${reps}  epsinv=${rinv}"
  cp ${PREFIX}.plot_eps.dat plot_eps.q${q}.dat
done
echo "=== eps_q.dat ==="
cat "$OUT"
echo DONE
