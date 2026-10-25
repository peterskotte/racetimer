#!/bin/sh
# Samler browser-udgaven til en statisk hjemmeside (fx GitHub Pages eller klubbens webhotel).
# Resultatskærmen og stilarterne er de samme filer som på Pi'en.
#
# Brug:  sh tools/build-web.sh [mappe]   (standard: site/)
set -e
cd "$(dirname "$0")/.."
OUT="${1:-site}"
rm -rf "$OUT"
mkdir -p "$OUT/static/splash"
cp web/index.html web/lite.js web/engine.js web/outcome.js web/manifest.webmanifest web/sw.js "$OUT/"
cp racetimer/static/display.html "$OUT/display.html"
cp racetimer/static/style.css "$OUT/static/style.css"
cp racetimer/static/splash/racetiming.webp "$OUT/static/splash/"
echo "✓ Browser-udgaven ligger i $OUT/ – åbn $OUT/index.html via en webserver (fx python3 -m http.server -d $OUT)"
