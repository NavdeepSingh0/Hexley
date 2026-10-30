#!/usr/bin/env bash
# scripts/copy-mascot.sh
# Copies sentinel-mascot.js from design/mascot/ into extension/.
# Run this after pulling changes to design/mascot/sentinel-mascot.js.
# Never edit extension/sentinel-mascot.js directly — edit the source and re-run this.

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
SRC="$REPO_ROOT/design/mascot/sentinel-mascot.js"
DST="$REPO_ROOT/extension/sentinel-mascot.js"

if [ ! -f "$SRC" ]; then
  echo "Error: source not found at $SRC" >&2
  exit 1
fi

cp "$SRC" "$DST"
echo "Copied sentinel-mascot.js → extension/sentinel-mascot.js"
