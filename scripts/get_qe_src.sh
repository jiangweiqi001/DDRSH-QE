#!/usr/bin/env bash
# Download and extract the Quantum ESPRESSO 7.5 source tree to $HOME/qe-7.5.
set -euo pipefail

DEST="${QE_SRC:-$HOME/qe-7.5}"
TARBALL="/tmp/qe-7.5.tar.gz"
URL="https://gitlab.com/QEF/q-e/-/archive/qe-7.5/q-e-qe-7.5.tar.gz"

if [ -d "$DEST/PW/src" ]; then
  echo "[get_qe_src] source already present at $DEST"
  exit 0
fi

echo "[get_qe_src] downloading QE 7.5 source"
curl -sSL -o "$TARBALL" "$URL"

echo "[get_qe_src] extracting"
mkdir -p "$DEST"
tar -xzf "$TARBALL" -C "$DEST" --strip-components=1

echo "[get_qe_src] done -> $DEST"
ls "$DEST" | head -20
