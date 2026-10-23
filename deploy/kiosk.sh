#!/bin/sh
# Starter resultatskærmen i fuldskærm på Pi'ens skærm. Kaldes ved login (autostart).
exec 9>"/tmp/racetimer-kiosk-$(id -u).lock"
flock -n 9 || exit 0   # kun én kiosk ad gangen, selv om flere autostarts kalder scriptet
until curl -s -o /dev/null http://localhost:8000/; do sleep 1; done
BROWSER="$(command -v chromium || command -v chromium-browser)"
exec "$BROWSER" --kiosk --noerrdialogs --disable-infobars --incognito \
  --autoplay-policy=no-user-gesture-required --check-for-update-interval=31536000 \
  --password-store=basic "http://localhost:8000/?kiosk=1"
