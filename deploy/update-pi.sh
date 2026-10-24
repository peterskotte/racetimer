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
# tar over SSH i stedet for rsync: macOS 26 har skiftet rsync ud med openrsync, der fejler
# ("unexpected end of file") mod den rigtige rsync på Pi'en. På Pi'en bruges rsync som før.
# signing/ (den private nøgle) og dist/ må aldrig forlade udviklerens computer.
COPYFILE_DISABLE=1 tar -czf - \
  --exclude ./.git --exclude ./.venv --exclude ./.deps --exclude ./data --exclude ./data-mirror \
  --exclude ./image --exclude ./signing --exclude ./dist --exclude ./.claude --exclude ./.github \
  --exclude '__pycache__' --exclude '*.pyc' --exclude '*.command' --exclude '.DS_Store' --exclude '._*' \
  . | ssh $SSH_OPTS "$PI_USER@$HOST" \
  'rm -rf /tmp/racetimer-ny && mkdir -p /tmp/racetimer-ny && tar -xzf - -C /tmp/racetimer-ny --no-same-owner --warning=no-unknown-keyword'

echo "→ Lægger filerne på plads og genstarter RaceTimer …"
ssh -t $SSH_OPTS "$PI_USER@$HOST" '
  set -e
  sudo rsync -a --chmod=Dgo+rx,Fgo+r --exclude data --exclude .venv /tmp/racetimer-ny/ /opt/racetimer/
  sudo rm -rf /opt/racetimer/signing /opt/racetimer/dist /tmp/racetimer-ny  # rester fra ældre versioner af scriptet
  sudo sh /opt/racetimer/deploy/post-update.sh
  sudo systemctl restart racetimer
  sleep 2
  systemctl is-active --quiet racetimer && echo "✓ RaceTimer kører med den nye version ($(cat /opt/racetimer/racetimer/VERSION))" || { echo "✗ RaceTimer startede ikke:"; sudo journalctl -u racetimer -n 20 --no-pager; exit 1; }
'
ssh -O exit $SSH_OPTS "$PI_USER@$HOST" 2>/dev/null || true
echo "Tryk F5 på Pi-skærmen (eller genstart Pi'en), så resultatskærmen henter de nye sider."
