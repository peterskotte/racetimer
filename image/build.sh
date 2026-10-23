#!/bin/sh
# Byg et komplet Raspberry Pi-image (Raspberry Pi OS + RaceTimer) med pi-gen i Docker.
# Kræver Docker Desktop. Resultat: image/out/racetimer-*.img.xz
set -e
cd "$(dirname "$0")"
PIGEN_BRANCH="${PIGEN_BRANCH:-arm64}"   # arm64-grenen bygger 64-bit Raspberry Pi OS

[ -d pi-gen ] || git clone --depth 1 --branch "$PIGEN_BRANCH" https://github.com/RPi-Distro/pi-gen.git pi-gen

# Vores stage + config ind i pi-gen
rm -rf pi-gen/stage-racetimer
cp -R stage-racetimer pi-gen/
cp config pi-gen/config
touch pi-gen/stage2/SKIP_IMAGES   # vi vil kun have det færdige image, ikke også en Lite-udgave

# Selve appen (uden lokale data, venvs og byggefiler)
APP=pi-gen/stage-racetimer/00-racetimer/files/racetimer
mkdir -p "$APP"
rsync -a --delete --chmod=Du=rwx,Dgo=rx,Fu=rw,Fgo=r \
  --exclude .git --exclude .venv --exclude .deps --exclude data --exclude data-mirror \
  --exclude __pycache__ --exclude .claude --exclude image --exclude '*.pyc' \
  --exclude branding-local --exclude '*.command' \
  ../ "$APP/"

cd pi-gen
# CONTINUE=1 genbruger en tidligere afbrudt build-container
CONTINUE="${CONTINUE:-0}" ./build-docker.sh

mkdir -p ../out
cp deploy/*.img.xz ../out/ 2>/dev/null || cp deploy/*.zip ../out/
ls -lh ../out
