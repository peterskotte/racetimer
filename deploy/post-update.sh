#!/bin/sh
# RaceTimer: alle installationstrin efter at ny kode er lagt i /opt/racetimer.
# Køres som root – af opdateringsknappen i admin (racetimer-update) og af deploy/update-pi.sh.
# Må køres igen og igen uden skade. Genstarter IKKE RaceTimer (det gør kalderen).
set -e
APP=/opt/racetimer
SVC_USER=$(systemctl show -p User --value racetimer 2>/dev/null); [ -n "$SVC_USER" ] || SVC_USER=root

chmod +x "$APP"/deploy/*.sh 2>/dev/null || true

# Python-pakker (kun når requirements.txt er ændret – kræver internet)
if ! cmp -s "$APP/requirements.txt" "$APP/.venv/.requirements" 2>/dev/null; then
  if "$APP/.venv/bin/pip" install -q -r "$APP/requirements.txt"; then
    cp "$APP/requirements.txt" "$APP/.venv/.requirements"
  else
    echo "  (kunne ikke tjekke Python-pakker – kræver internet; fortsætter med de installerede)"
  fi
fi

# Root-hjælpere (WiFi, fjernadgang, opdatering) – RaceTimer må kun kalde netop disse via sudo
install -m 755 -o root -g root "$APP/deploy/racetimer-wifi"   /usr/local/sbin/racetimer-wifi
install -m 755 -o root -g root "$APP/deploy/racetimer-tunnel" /usr/local/sbin/racetimer-tunnel
install -m 755 -o root -g root "$APP/deploy/racetimer-remote" /usr/local/sbin/racetimer-remote
install -m 755 -o root -g root "$APP/deploy/racetimer-update" /usr/local/sbin/racetimer-update
install -m 755 -o root -g root "$APP/deploy/racetimer-system" /usr/local/sbin/racetimer-system
install -m 644 "$APP/deploy/racetimer-tunnel.service" /etc/systemd/system/racetimer-tunnel.service
echo "$SVC_USER ALL=(root) NOPASSWD: /usr/local/sbin/racetimer-wifi, /usr/local/sbin/racetimer-tunnel, /usr/local/sbin/racetimer-remote, /usr/local/sbin/racetimer-update, /usr/local/sbin/racetimer-system" > /etc/sudoers.d/racetimer-wifi
chmod 440 /etc/sudoers.d/racetimer-wifi
visudo -cf /etc/sudoers.d/racetimer-wifi >/dev/null || rm -f /etc/sudoers.d/racetimer-wifi

# Udviklerens private signeringsnøgle må aldrig ligge på en Pi. Ældre versioner af
# update-pi.sh kopierede den med – fjern den, også fra gemte backups af tidligere versioner.
rm -rf "$APP/signing" "$APP/dist" /var/lib/racetimer-update/backup/*/signing /var/lib/racetimer-update/backup/*/dist

# Moduler: lyd via USB-højttaler (ALSA) – servicebrugeren skal i gruppen audio, og aplay skal findes
[ "$SVC_USER" = root ] || usermod -aG audio "$SVC_USER" 2>/dev/null || true
command -v aplay >/dev/null || apt-get install -y -qq alsa-utils >/dev/null 2>&1 \
  || echo "  (kunne ikke installere alsa-utils til højttaler-modulet – kræver internet)"

# Valgfrie programmer til fjernadgang – installeres slået fra (kræver internet)
if ! command -v cloudflared >/dev/null 2>&1; then
  ARCH=$(dpkg --print-architecture)
  if curl -fsSL -o /tmp/cloudflared.deb "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-$ARCH.deb"; then
    dpkg -i /tmp/cloudflared.deb >/dev/null && echo "  cloudflared installeret"
  else
    echo "  (kunne ikke hente cloudflared – fjernadgang via Cloudflare springes over)"
  fi
fi
if ! command -v tailscale >/dev/null 2>&1; then
  CODENAME=$(. /etc/os-release && echo "$VERSION_CODENAME")
  if curl -fsSL "https://pkgs.tailscale.com/stable/debian/$CODENAME.noarmor.gpg" > /usr/share/keyrings/tailscale-archive-keyring.gpg \
     && curl -fsSL "https://pkgs.tailscale.com/stable/debian/$CODENAME.tailscale-keyring.list" > /etc/apt/sources.list.d/tailscale.list \
     && apt-get update -qq && apt-get install -y -qq tailscale >/dev/null; then
    echo "  Tailscale installeret"
  else
    echo "  (kunne ikke installere Tailscale)"
  fi
fi
if ! command -v rpi-connect >/dev/null 2>&1; then
  apt-get install -y -qq rpi-connect >/dev/null 2>&1 && echo "  Raspberry Pi Connect installeret" || echo "  (kunne ikke installere Raspberry Pi Connect)"
fi

# Data bor i /var/lib/racetimer (adskilt fra programmet). Flyt én gang fra den gamle placering.
mkdir -p /var/lib/racetimer
if [ -f "$APP/data/racetimer.db" ] && [ ! -f /var/lib/racetimer/racetimer.db ]; then
  systemctl stop racetimer || true
  cp -a "$APP/data/." /var/lib/racetimer/
  echo "  data flyttet til /var/lib/racetimer (backup ligger stadig i $APP/data)"
fi
chown -R "$SVC_USER": /var/lib/racetimer
mkdir -p /etc/systemd/system/racetimer.service.d
printf "[Service]\nEnvironment=RACETIMER_DATA=/var/lib/racetimer\n" > /etc/systemd/system/racetimer.service.d/data.conf
systemctl daemon-reload
echo "  installationstrin færdige"
