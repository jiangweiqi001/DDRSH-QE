#!/usr/bin/env bash
# Build pw.x from the QE 7.5 source tree using the qedev conda toolchain.
# Uses autotools (./configure + make pw) which does NOT fetch the wannier90
# github submodule (CMake does, and github is unreachable here).
set -euo pipefail

CONDA_BASE="${CONDA_BASE:-$HOME/miniconda3}"
QE_SRC="${QE_SRC:-$HOME/qe-7.5}"

source "$CONDA_BASE/etc/profile.d/conda.sh"
conda activate qedev

if [ ! -f "$QE_SRC/PW/src/exx_base.f90" ]; then
  echo "[build_qe] QE source not found at $QE_SRC (run scripts/get_qe_src.sh first)" >&2
  exit 1
fi

cd "$QE_SRC"

# Clean any partial CMake build artifacts from a previous attempt.
rm -rf build external/wannier90 2>/dev/null || true

# A stale serial config.cache makes configure re-pick plain gfortran for MPIF90; clear it.
rm -f config.cache install/config.cache

echo "[build_qe] configuring with autotools (MPI + OpenMP)"
./configure \
  --enable-parallel \
  --enable-openmp \
  MPIF90="$(command -v mpif90)" \
  CC=mpicc \
  BLAS_LIBS="-L$CONDA_BASE/envs/qedev/lib -lblas" \
  LAPACK_LIBS="-L$CONDA_BASE/envs/qedev/lib -llapack" \
  FFT_LIBS="-L$CONDA_BASE/envs/qedev/lib -lfftw3_omp -lfftw3"

# QE's configure cannot link-test the conda mpif90 wrapper, so it silently falls back to
# a serial build (MPIF90 -> plain gfortran, DFLAGS without -D__MPI). We verified mpif90
# compiles and runs MPI programs, so force the MPI toolchain into make.inc directly.
MPIF90BIN="$(command -v mpif90)"
sed -i "s|^MPIF90 .*|MPIF90         = $MPIF90BIN|" make.inc
# Link through mpif90 so the MPI runtime is pulled in (raw conda `ld` can't take -Wl).
sed -i "s|^LD .*|LD             = $MPIF90BIN|" make.inc
# gfortran >=10 promotes argument-type mismatches (e.g. MPI calls) to errors.
sed -i 's|^FFLAGS         = |FFLAGS         = -fallow-argument-mismatch |' make.inc
# Enable MPI (-D__MPI) and select the FFTW3 backend (configure leaves DFLAGS empty when
# FFT_LIBS is forced).
sed -i 's|^DFLAGS .*|DFLAGS         = -D__MPI -D__FFTW3|' make.inc
# Link the OpenMP runtime (objects are compiled with -fopenmp; the link needs it too).
sed -i 's|^LDFLAGS        = |LDFLAGS        = -fopenmp |' make.inc

echo "[build_qe] make.inc MPI settings:"
grep -E "^MPIF90|^DFLAGS|^LD " make.inc | sed 's/^/  /'

echo "[build_qe] building pw + ph + tddfpt (turbo_eels/turbo_spectrum); 20-40 minutes"
make -j4 pw ph tddfpt

echo "[build_qe] result:"
ls -l "$QE_SRC/bin/"{pw.x,turbo_eels.x,turbo_spectrum.x}
echo "[build_qe] checking parallel banner:"
printf '' | "$QE_SRC/bin/pw.x" 2>&1 | grep -iE "parallel|serial" | head -1
echo "[build_qe] DONE"
