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

echo "[build_qe] configuring with autotools"
./configure \
  --enable-parallel \
  --enable-openmp \
  MPIF90=mpif90 \
  F90=gfortran \
  CC=mpicc \
  BLAS_LIBS="-L$CONDA_BASE/envs/qedev/lib -lblas" \
  LAPACK_LIBS="-L$CONDA_BASE/envs/qedev/lib -llapack" \
  FFT_LIBS="-L$CONDA_BASE/envs/qedev/lib -lfftw3_omp -lfftw3"

# conda-forge provides libblas.so/liblapack.so (-> openblas) but no libopenblas.so symlink.
# QE configure sets LD to the raw `ld`, but conda LDFLAGS use compiler-driver
# (-Wl,...) options. Link through the gfortran driver instead.
sed -i 's|^LD             = x86_64-conda-linux-gnu-ld|LD             = x86_64-conda-linux-gnu-gfortran|' make.inc
# gfortran >=10 promotes argument-type mismatches (e.g. MPI calls) to errors.
sed -i 's|^FFLAGS         = |FFLAGS         = -fallow-argument-mismatch |' make.inc
# Select the FFTW3 backend (configure leaves DFLAGS empty when FFT_LIBS is forced).
sed -i 's|^DFLAGS         = $|DFLAGS         = -D__FFTW3|' make.inc
# Link OpenMP runtime (objects are compiled with -fopenmp; the link needs it too).
sed -i 's|^LDFLAGS        = -Wl,-O2|LDFLAGS        = -fopenmp -Wl,-O2|' make.inc

echo "[build_qe] building pw (this can take 10-20 minutes)"
make -j4 pw

echo "[build_qe] result:"
ls -l "$QE_SRC/bin/pw.x"
echo "[build_qe] DONE"
