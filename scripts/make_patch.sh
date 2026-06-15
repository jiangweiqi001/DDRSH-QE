#!/usr/bin/env bash
# Generate a unified patch of the DD-RSH-CAM (lmodelhf) modifications against a
# pristine Quantum ESPRESSO 7.5 source tree. Output: patch/ddrshcam-qe-7.5.patch
# Apply with:  cd q-e-qe-7.5 && patch -p1 < ddrshcam-qe-7.5.patch
set -euo pipefail

MOD="${QE_SRC:-$HOME/qe-7.5}"
PRISTINE="/tmp/qe-pristine"
TARBALL="/tmp/qe-7.5-pristine.tar.gz"
URL="https://gitlab.com/QEF/q-e/-/archive/qe-7.5/q-e-qe-7.5.tar.gz"
REPO="/home/footman/DDRSH"
OUT="$REPO/patch/ddrshcam-qe-7.5.patch"

FILES=(
  Modules/input_parameters.f90
  Modules/read_namelists.f90
  PW/src/input.f90
  PW/src/exx_base.f90
  PW/src/exx.f90
  XClib/dft_setting_params.f90
  XClib/dft_setting_routines.f90
  XClib/qe_drivers_lda_lsda.f90
  XClib/qe_drivers_gga.f90
  XClib/xc_lib.f90
)

if [ ! -d "$PRISTINE/PW/src" ]; then
  echo "[make_patch] downloading pristine QE 7.5"
  curl -sSL -o "$TARBALL" "$URL"
  mkdir -p "$PRISTINE"
  tar -xzf "$TARBALL" -C "$PRISTINE" --strip-components=1
fi

mkdir -p "$REPO/patch"
: > "$OUT"
for f in "${FILES[@]}"; do
  echo "[make_patch] diff $f"
  # label so that `patch -p1` works from the QE root
  diff -u "$PRISTINE/$f" "$MOD/$f" \
    --label "a/$f" --label "b/$f" >> "$OUT" || true
done

echo "[make_patch] wrote $OUT"
wc -l "$OUT"
grep -cE '^\+\+\+ ' "$OUT" | sed 's/^/files changed: /'
