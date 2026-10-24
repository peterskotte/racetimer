#!/bin/bash -e
# Lægger RaceTimer ind i imaget: app i /opt/racetimer, systemd-service, kiosk-skærm ved login.

install -d "${ROOTFS_DIR}/opt/racetimer"
cp -a files/racetimer/. "${ROOTFS_DIR}/opt/racetimer/"
install -m 644 files/racetimer.service "${ROOTFS_DIR}/etc/systemd/system/racetimer.service"
install -d "${ROOTFS_DIR}/etc/xdg/autostart"
install -m 644 files/racetimer-kiosk.desktop "${ROOTFS_DIR}/etc/xdg/autostart/racetimer-kiosk.desktop"

on_chroot << 'CHROOT'
set -e
# Chromium hedder chromium-browser på Bookworm og chromium på nyere udgaver
command -v chromium >/dev/null || command -v chromium-browser >/dev/null || \
	apt-get install -y chromium-browser || apt-get install -y chromium

id racetimer-svc >/dev/null 2>&1 || \
	useradd --system --home-dir /opt/racetimer --shell /usr/sbin/nologin --user-group racetimer-svc
usermod -aG input,dialout,audio racetimer-svc

python3 -m venv --system-site-packages /opt/racetimer/.venv
/opt/racetimer/.venv/bin/pip install --no-cache-dir -r /opt/racetimer/requirements.txt

install -d -o racetimer-svc -g racetimer-svc /var/lib/racetimer
chmod +x /opt/racetimer/deploy/*.sh
systemctl enable racetimer

# WiFi-hjælper til admin-fanen WiFi (op til 5 netværk)
install -m 755 -o root -g root /opt/racetimer/deploy/racetimer-wifi /usr/local/sbin/racetimer-wifi

# Fjernadgang til admin (Cloudflare quick tunnel) – installeret, men slået fra
curl -fsSL -o /tmp/cloudflared.deb "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64.deb"
dpkg -i /tmp/cloudflared.deb && rm -f /tmp/cloudflared.deb
install -m 644 /opt/racetimer/deploy/racetimer-tunnel.service /etc/systemd/system/racetimer-tunnel.service
install -m 755 -o root -g root /opt/racetimer/deploy/racetimer-tunnel /usr/local/sbin/racetimer-tunnel
# Privat fjernadgang: Tailscale + Raspberry Pi Connect (slået fra, indtil man logger ind i admin)
CODENAME=$(. /etc/os-release && echo "$VERSION_CODENAME")
curl -fsSL "https://pkgs.tailscale.com/stable/debian/$CODENAME.noarmor.gpg" > /usr/share/keyrings/tailscale-archive-keyring.gpg
curl -fsSL "https://pkgs.tailscale.com/stable/debian/$CODENAME.tailscale-keyring.list" > /etc/apt/sources.list.d/tailscale.list
apt-get update -qq && apt-get install -y tailscale rpi-connect
install -m 755 -o root -g root /opt/racetimer/deploy/racetimer-remote /usr/local/sbin/racetimer-remote
install -m 755 -o root -g root /opt/racetimer/deploy/racetimer-update /usr/local/sbin/racetimer-update
install -m 755 -o root -g root /opt/racetimer/deploy/racetimer-system /usr/local/sbin/racetimer-system
# Pi-brugeren har en kendt standardkode: markér det, så opsætningsguiden beder om en ny (én gang).
# sudo kræver kode – også standardkoden – i stedet for Raspberry Pi OS' "NOPASSWD".
install -d -m 755 /etc/racetimer
echo "Pi-brugeren har stadig standardkoden fra RaceTimer-imaget" > /etc/racetimer/default-pi-password
rm -f /etc/sudoers.d/010_pi-nopasswd
echo "racetimer-svc ALL=(root) NOPASSWD: /usr/local/sbin/racetimer-wifi, /usr/local/sbin/racetimer-tunnel, /usr/local/sbin/racetimer-remote, /usr/local/sbin/racetimer-update, /usr/local/sbin/racetimer-system" > /etc/sudoers.d/racetimer-wifi
chmod 440 /etc/sudoers.d/racetimer-wifi

# Kiosk via labwc's egen autostart også (kiosk.sh sikrer at kun én kører)
if [ -f /etc/xdg/labwc/autostart ] && ! grep -q kiosk.sh /etc/xdg/labwc/autostart; then
	echo "/opt/racetimer/deploy/kiosk.sh &" >> /etc/xdg/labwc/autostart
fi

# Start skrivebordet med automatisk login, og sluk aldrig skærmen
raspi-config nonint do_boot_behaviour B4 || true
raspi-config nonint do_blanking 1 || true
CHROOT
