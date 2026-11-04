#!/bin/sh
# Dobbeltklik for at opdatere RaceTimer på Pi'en med koden i denne mappe.
# Adresserne prøves i rækkefølge: Tailscale-navnet og det lokale netværk (racetimer.local).
# Ret listen herunder, hvis din Pi har andre adresser.
PI_ADRESSER="racetimer racetimer.local"
PI_BRUGER=racetimer

cd "$(dirname "$0")"
PI_ADRESSE=""
for a in $PI_ADRESSER; do
  if nc -z -G 3 "$a" 22 >/dev/null 2>&1; then PI_ADRESSE="$a"; break; fi
done
if [ -z "$PI_ADRESSE" ]; then
  echo "✗ Kan ikke finde Pi'en på: $PI_ADRESSER"
  echo "  Er Pi'en tændt og på samme WiFi som denne Mac? Eller er Tailscale slået til på Mac'en?"
  printf "Tryk Enter for at lukke vinduet … "; read _; exit 1
fi
echo "Opdaterer RaceTimer på $PI_ADRESSE …"
echo "Du bliver spurgt om koden til Pi'en (1–2 gange)."
echo
sh deploy/update-pi.sh "$PI_ADRESSE" "$PI_BRUGER"
echo
printf "Tryk Enter for at lukke vinduet … "
read _
