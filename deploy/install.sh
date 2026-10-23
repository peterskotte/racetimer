#!/bin/sh
# Installér RaceTimer på Raspberry Pi OS (Bookworm, 64-bit) på en Raspberry Pi 5.
# Kør fra projektmappen:  sh deploy/install.sh
set -e
DIR="$(cd "$(dirname "$0")/.." && pwd)"
USER_NAME="$(id -un)"

sudo apt-get update
sudo apt-get install -y python3-venv python3-evdev python3-serial chromium-browser curl

# venv med adgang til apt-pakkerne (evdev/pyserial)
python3 -m venv --system-site-packages "$DIR/.venv"
"$DIR/.venv/bin/pip" install -r "$DIR/requirements.txt"

# RFID-læsere er /dev/input-enheder → brugeren skal være i gruppen 'input'
sudo usermod -aG input "$USER_NAME"

# systemd-service (starter automatisk ved boot og genstarter ved fejl)
sed -e "s#__USER__#$USER_NAME#g" -e "s#__DIR__#$DIR#g" "$DIR/deploy/racetimer.service" \
  | sudo tee /etc/systemd/system/racetimer.service >/dev/null
sudo systemctl daemon-reload
sudo systemctl enable --now racetimer

# WiFi-hjælper til admin-fanen WiFi (op til 5 netværk)
sudo install -m 755 -o root -g root "$DIR/deploy/racetimer-wifi" /usr/local/sbin/racetimer-wifi

# Fjernadgang til admin (Cloudflare quick tunnel) – installeret, men slået fra
if ! command -v cloudflared >/dev/null 2>&1; then
  curl -fsSL -o /tmp/cloudflared.deb "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-$(dpkg --print-architecture).deb"
  sudo dpkg -i /tmp/cloudflared.deb
fi
sudo install -m 644 "$DIR/deploy/racetimer-tunnel.service" /etc/systemd/system/racetimer-tunnel.service
sudo install -m 755 -o root -g root "$DIR/deploy/racetimer-tunnel" /usr/local/sbin/racetimer-tunnel
sudo systemctl daemon-reload
  # Privat fjernadgang: Tailscale (officielt pakkearkiv) + Raspberry Pi Connect – installeres, men er slået fra
  if ! command -v tailscale >/dev/null 2>&1; then
    CODENAME=$(. /etc/os-release && echo "$VERSION_CODENAME")
    if curl -fsSL "https://pkgs.tailscale.com/stable/debian/$CODENAME.noarmor.gpg" | sudo tee /usr/share/keyrings/tailscale-archive-keyring.gpg >/dev/null \
       && curl -fsSL "https://pkgs.tailscale.com/stable/debian/$CODENAME.tailscale-keyring.list" | sudo tee /etc/apt/sources.list.d/tailscale.list >/dev/null \
       && sudo apt-get update -qq && sudo apt-get install -y -qq tailscale >/dev/null; then
      echo "  Tailscale installeret"
    else
      echo "  (kunne ikke installere Tailscale – kræver internet)"
    fi
  fi
  if ! command -v rpi-connect >/dev/null 2>&1; then
    sudo apt-get install -y -qq rpi-connect >/dev/null 2>&1 && echo "  Raspberry Pi Connect installeret" || echo "  (kunne ikke installere Raspberry Pi Connect)"
  fi
  sudo install -m 755 -o root -g root "$DIR/deploy/racetimer-remote" /usr/local/sbin/racetimer-remote
sudo install -m 755 -o root -g root "$DIR/deploy/racetimer-update" /usr/local/sbin/racetimer-update
echo "$USER_NAME ALL=(root) NOPASSWD: /usr/local/sbin/racetimer-wifi, /usr/local/sbin/racetimer-tunnel, /usr/local/sbin/racetimer-remote, /usr/local/sbin/racetimer-update" | sudo tee /etc/sudoers.d/racetimer-wifi >/dev/null
sudo chmod 440 /etc/sudoers.d/racetimer-wifi

# Kiosk-skærm ved login (Raspberry Pi OS bruger labwc som skrivebord)
chmod +x "$DIR/deploy/kiosk.sh"
mkdir -p "$HOME/.config/labwc"
grep -q kiosk.sh "$HOME/.config/labwc/autostart" 2>/dev/null || echo "$DIR/deploy/kiosk.sh &" >> "$HOME/.config/labwc/autostart"

echo
echo "Færdig. Genstart Pi'en (sudo reboot) så gruppe-rettigheder og kiosk træder i kraft."
echo "Admin: http://$(hostname -I | awk '{print $1}'):8000/admin  (admin / admin – skift koden!)"
