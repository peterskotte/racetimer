#!/bin/sh
# Opdatér RaceTimer på en Raspberry Pi med den kode, der ligger i denne mappe.
# Data (database, læsninger, brugere, indstillinger) på Pi'en røres ikke.
#
# Brug:  sh deploy/update-pi.sh racetimer.local [brugernavn]   (eller Pi'ens IP-adresse)
set -e
HOST="${1:?Angiv adressen paa din Pi, fx: sh deploy/update-pi.sh racetimer.local}"
PI_USER="${2:-racetimer}"
cd "$(dirname "$0")/.."

# Én SSH-forbindelse til hele opdateringen → du skal kun skrive koden én gang (+ sudo-koden)
SSH_OPTS="-o ControlMaster=auto -o ControlPath=/tmp/racetimer-ssh-%r@%h -o ControlPersist=60"

echo "→ Kopierer filer til $PI_USER@$HOST …"
rsync -az --delete --chmod=Du=rwx,Dgo=rx,Fu=rw,Fgo=r -e "ssh $SSH_OPTS" \
  --exclude .git --exclude .venv --exclude .deps --exclude data --exclude data-mirror \
  --exclude image --exclude __pycache__ --exclude .claude --exclude '*.pyc' --exclude '*.command' \
  ./ "$PI_USER@$HOST:/tmp/racetimer-ny/"

echo "→ Lægger filerne på plads og genstarter RaceTimer …"
ssh -t $SSH_OPTS "$PI_USER@$HOST" '
  set -e
  sudo rsync -a --chmod=Dgo+rx,Fgo+r --exclude data --exclude .venv /tmp/racetimer-ny/ /opt/racetimer/
  sudo sh /opt/racetimer/deploy/post-update.sh
  sudo systemctl restart racetimer
  sleep 2
  systemctl is-active --quiet racetimer && echo "✓ RaceTimer kører med den nye version ($(cat /opt/racetimer/racetimer/VERSION))" || { echo "✗ RaceTimer startede ikke:"; sudo journalctl -u racetimer -n 20 --no-pager; exit 1; }
'
ssh -O exit $SSH_OPTS "$PI_USER@$HOST" 2>/dev/null || true
echo "Tryk F5 på Pi-skærmen (eller genstart Pi'en), så resultatskærmen henter de nye sider."
