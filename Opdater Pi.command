#!/bin/sh
# Dobbeltklik for at opdatere RaceTimer på Pi'en med koden i denne mappe.
# Ret adressen/brugernavnet herunder, hvis din Pi får en anden adresse.
PI_ADRESSE=racetimer.local
PI_BRUGER=racetimer

cd "$(dirname "$0")"
echo "Opdaterer RaceTimer på $PI_ADRESSE …"
echo "Du bliver spurgt om koden til Pi'en (1–2 gange)."
echo
sh deploy/update-pi.sh "$PI_ADRESSE" "$PI_BRUGER"
echo
printf "Tryk Enter for at lukke vinduet … "
read _
