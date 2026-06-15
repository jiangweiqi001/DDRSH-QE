#!/usr/bin/env bash
# Populate QE external/ submodules from tarballs at the exact commits pinned by
# qe-7.5. We use tarball downloads because the git protocol to github is blocked
# here (codeload.github.com HTTPS works; gitlab git works).
set -euo pipefail

QE_SRC="${QE_SRC:-$HOME/qe-7.5}"
EXT="$QE_SRC/external"

# Pinned commits (from gitlab API tree of QEF/q-e @ qe-7.5, path=external).
MBD_SHA="89a3cc199c0a200c9f0f688c3229ef6b9a8d63bd"
DEVXLIB_SHA="a6b89ef77b1ceda48e967921f1f5488d2df9226d"
FOX_SHA="3453648e6837658b747b895bb7bef4b1ed2eac40"

# Download a github tarball (codeload HTTPS works even though git protocol is blocked).
fetch_tar() {
  local name="$1" url="$2" sha="$3"
  local dest="$EXT/$name"
  if [ -f "$dest/.populated_$sha" ]; then
    echo "[submods] $name already populated ($sha)"; return 0
  fi
  echo "[submods] fetching $name @ $sha (tarball)"
  rm -rf "$dest"; mkdir -p "$dest"
  curl -sSL --max-time 180 -o "/tmp/$name.tar.gz" "$url"
  tar -xzf "/tmp/$name.tar.gz" -C "$dest" --strip-components=1
  touch "$dest/.populated_$sha"
  echo "[submods] $name done -> $(ls "$dest" | head -5 | tr '\n' ' ')"
}

# Clone from gitlab and checkout an exact commit (gitlab archive endpoint 403s,
# but the git protocol works).
fetch_git() {
  local name="$1" url="$2" sha="$3"
  local dest="$EXT/$name"
  if [ -f "$dest/.populated_$sha" ]; then
    echo "[submods] $name already populated ($sha)"; return 0
  fi
  echo "[submods] cloning $name @ $sha (git)"
  rm -rf "$dest"
  git clone --quiet "$url" "$dest"
  ( cd "$dest" && git checkout --quiet "$sha" )
  rm -rf "$dest/.git"
  touch "$dest/.populated_$sha"
  echo "[submods] $name done -> $(ls "$dest" | head -5 | tr '\n' ' ')"
}

fetch_tar mbd     "https://codeload.github.com/libmbd/libmbd/tar.gz/$MBD_SHA"        "$MBD_SHA"
fetch_git devxlib "https://gitlab.com/max-centre/components/devicexlib.git"          "$DEVXLIB_SHA"
fetch_tar fox     "https://codeload.github.com/pietrodelugas/fox/tar.gz/$FOX_SHA"     "$FOX_SHA"

# QE's update_submodule macro re-clones (from the blocked github) unless a
# `.git` marker exists in each submodule dir. Create empty markers so it skips.
for s in mbd devxlib fox; do mkdir -p "$EXT/$s/.git"; done

echo "[submods] ALL DONE"
