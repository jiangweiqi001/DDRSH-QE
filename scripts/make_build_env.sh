#!/usr/bin/env bash
# Create a user-space conda env with the toolchain to build QE 7.5 from source.
set -euo pipefail

CONDA_BASE="${CONDA_BASE:-$HOME/miniconda3}"
CONDA="$CONDA_BASE/bin/conda"

if [ -x "$CONDA_BASE/envs/qedev/bin/mpif90" ] || [ -x "$CONDA_BASE/envs/qedev/bin/gfortran" ]; then
  echo "[make_build_env] qedev already present"
  exit 0
fi

echo "[make_build_env] creating qedev (compilers, MPI, math libs) from conda-forge"
"$CONDA" create -y -n qedev --override-channels -c conda-forge \
  fortran-compiler c-compiler cxx-compiler \
  openmpi \
  fftw libopenblas liblapack scalapack libxc hdf5 \
  make cmake git pkg-config

echo "[make_build_env] toolchain binaries:"
for b in gfortran mpif90 mpicc make cmake; do
  if [ -x "$CONDA_BASE/envs/qedev/bin/$b" ]; then echo "  $b: present"; else echo "  $b: MISSING"; fi
done
echo "[make_build_env] DONE"
