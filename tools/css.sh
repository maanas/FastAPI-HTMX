#!/bin/sh
# Build app/static/css/app.css with the Tailwind v4 standalone CLI (no Node needed).
# Usage: tools/css.sh [--watch]
# CSS_OUT=<file> writes there instead of app/static/css/app.css (the stale-CSS test uses it).
set -eu

VERSION="v4.3.3"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BIN_DIR="$ROOT/build/tailwind"
OUT="${CSS_OUT:-$ROOT/app/static/css/app.css}"

case "$(uname -s)-$(uname -m)" in
  Darwin-arm64)  ASSET="tailwindcss-macos-arm64";  SHA="cdf646702987a743464dff4d9c60fd4480d1c1e73dd819a9a67f1078815dce9d" ;;
  Darwin-x86_64) ASSET="tailwindcss-macos-x64";    SHA="7922e0953f2110c05976e3bf58f14e643d90427575e766b7d433f5f80cbee7e1" ;;
  Linux-x86_64)  ASSET="tailwindcss-linux-x64";    SHA="dc61b3ac6b8c9ca874c0cc4c57b2409791a64c5540404ca5f5367360babc313a" ;;
  Linux-aarch64|Linux-arm64) ASSET="tailwindcss-linux-arm64"; SHA="55fd0b241214eff3de1e8ee4f22796662f2d2e7a49bcfca7477cfd0bac398195" ;;
  *) echo "css.sh: no pinned Tailwind binary for $(uname -s)-$(uname -m)" >&2; exit 1 ;;
esac

BIN="$BIN_DIR/$ASSET-$VERSION"

sha256_of() {
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$1" | cut -d ' ' -f 1
  else
    shasum -a 256 "$1" | cut -d ' ' -f 1
  fi
}

if [ ! -x "$BIN" ]; then
  mkdir -p "$BIN_DIR"
  TMP="$BIN.part"
  curl -fsSL -o "$TMP" "https://github.com/tailwindlabs/tailwindcss/releases/download/$VERSION/$ASSET"
  if [ "$(sha256_of "$TMP")" != "$SHA" ]; then
    rm -f "$TMP"
    echo "css.sh: sha256 mismatch for $ASSET, download removed" >&2
    exit 1
  fi
  chmod +x "$TMP"
  mv "$TMP" "$BIN"
fi

if [ "${1:-}" = "--watch" ]; then
  exec "$BIN" -i "$ROOT/app/static/css/src/input.css" -o "$OUT" --watch
fi
"$BIN" -i "$ROOT/app/static/css/src/input.css" -o "$OUT" --minify
