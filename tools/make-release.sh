#!/bin/sh
# Lav en signeret opdateringspakke:  sh tools/make-release.sh 1.1.0
#
# Resultat i dist/: racetimer-1.1.0.tar.gz + racetimer-1.1.0.tar.gz.sig
# Læg begge filer på en GitHub Release med tag "v1.1.0" – så tilbyder alle Pi'er opdateringen.
#
# Signeringsnøglen læses fra signing/racetimer-signing-key.pem – eller fra miljøvariablen
# RACETIMER_SIGNING_KEY (bruges af GitHub Actions). Den private nøgle må ALDRIG i repoet.
set -e
VERSION="${1:?Angiv version, fx: sh tools/make-release.sh 1.1.0}"
echo "$VERSION" | grep -Eq '^[0-9]+\.[0-9]+\.[0-9]+$' || { echo "Version skal være X.Y.Z"; exit 1; }
cd "$(dirname "$0")/.."

# OpenSSL 3 (Ed25519-signering). På Mac bruges Homebrews udgave.
OSSL=openssl
for c in /opt/homebrew/opt/openssl@3/bin/openssl /usr/local/opt/openssl@3/bin/openssl; do [ -x "$c" ] && OSSL="$c" && break; done
"$OSSL" version | grep -q "^OpenSSL [3-9]" || { echo "Kræver OpenSSL 3 (brew install openssl@3)"; exit 1; }

KEY=signing/racetimer-signing-key.pem
if [ -n "$RACETIMER_SIGNING_KEY" ]; then
  KEY=$(mktemp); printf '%s\n' "$RACETIMER_SIGNING_KEY" > "$KEY"; trap 'rm -f "$KEY"' EXIT
fi
[ -f "$KEY" ] || { echo "Mangler signeringsnøgle ($KEY)"; exit 1; }

echo "$VERSION" > racetimer/VERSION
STAGE=$(mktemp -d)
mkdir -p "$STAGE/racetimer-$VERSION" dist
rsync -a --chmod=Du=rwx,Dgo=rx,Fu=rw,Fgo=r \
  --exclude .git --exclude .venv --exclude .deps --exclude data --exclude data-mirror --exclude image \
  --exclude __pycache__ --exclude '*.pyc' --exclude .claude --exclude branding-local --exclude signing \
  --exclude dist --exclude '*.command' --exclude .DS_Store \
  ./ "$STAGE/racetimer-$VERSION/"
chmod 755 "$STAGE/racetimer-$VERSION"/deploy/racetimer-* "$STAGE/racetimer-$VERSION"/deploy/*.sh
TAR="dist/racetimer-$VERSION.tar.gz"
COPYFILE_DISABLE=1 tar -czf "$TAR" -C "$STAGE" "racetimer-$VERSION"
rm -rf "$STAGE"
"$OSSL" pkeyutl -sign -inkey "$KEY" -rawin -in "$TAR" -out "$TAR.sig"

# kontrol med den offentlige nøgle, der følger med programmet
python3 -c "import json;print(json.load(open('racetimer/release.json'))['pubkey'])" > dist/.pub.pem
"$OSSL" pkeyutl -verify -pubin -inkey dist/.pub.pem -rawin -in "$TAR" -sigfile "$TAR.sig" >/dev/null
rm -f dist/.pub.pem
echo "✓ $TAR ($(du -h "$TAR" | cut -f1)) + signatur – klar til GitHub Release v$VERSION"
