#!/usr/bin/env bash
set -uo pipefail

log() { echo "[install_qe] $*"; }

log "connectivity check"
for u in https://repo.anaconda.com https://conda.anaconda.org; do
  if curl -sI --max-time 12 "$u" >/dev/null 2>&1; then echo "  $u OK"; else echo "  $u FAIL"; fi
done

ARCH="$(uname -m)"
MF="$HOME/miniconda3"

if [ ! -x "$MF/bin/conda" ]; then
  log "downloading miniconda for $ARCH from repo.anaconda.com"
  curl -sSL -o /tmp/miniconda.sh "https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-${ARCH}.sh"
  log "installing miniconda to $MF"
  bash /tmp/miniconda.sh -b -p "$MF"
else
  log "miniconda already present at $MF"
fi

CONDA="$MF/bin/conda"
log "conda version: $($CONDA --version 2>/dev/null)"

if [ ! -x "$MF/envs/qe/bin/pw.x" ]; then
  log "creating qe env from conda-forge only (this can take several minutes)"
  "$CONDA" create -y -n qe --override-channels -c conda-forge qe
else
  log "qe env already present"
fi

echo "=== executables (.x) in qe env ==="
ls "$MF/envs/qe/bin" 2>/dev/null | grep -E '\.x$' | sort

echo "=== key binaries ==="
for b in pw.x epsilon.x ph.x pp.x; do
  if [ -x "$MF/envs/qe/bin/$b" ]; then echo "  $b: present"; else echo "  $b: MISSING"; fi
done

log "DONE"
