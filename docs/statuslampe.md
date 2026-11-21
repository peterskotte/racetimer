# Statuslampe (Luxafor Flag)

En **Luxafor Flag** i USB viser, hvad Pi'en laver, fra den tændes, til den er klar. Det virker uden skærm og uden net. Så kan man se, om Pi'en er kommet på WiFi, og om læserne er sat i.

Lampen har 3 LED'er på **forsiden** og 3 på **bagsiden**:
- **Bagsiden** (vend den mod dig) viser altid Pi'ens tilstand.
- **Forsiden** (vend den mod løberne) viser det samme, men blinker kort ved hver scanning.

## Opstart

| Lys | Betyder |
|---|---|
| ⚪ Hvid | Pi'en er tændt og starter |
| 🔵 Blå, pulserende | RaceTimer starter |
| 🔵 Blå, blinker roligt | Søger netværk (op til 2 minutter efter opstart) |
| 🟢 Grøn | **Klar.** Læsere, netværk og ur er i orden |
| 🟠 Orange (fast lys) | **Klar uden netværk.** Offline-tilstand er slået til i klar-tjekket, og læsere, database og ur er i orden |

## Blinkkoder

Lampen blinker et antal gange, holder en pause og gentager. Tæl blinkene.

| Kode | Hvad er galt | Tidtagningen virker? | Hvad gør jeg? |
|---|---|---|---|
| 🔴 ×1 | En valgt RFID-læser er ikke tilsluttet | **Nej**, ikke på den læser | Tjek USB-stikket. Under *Aktivt løb → Læsere* kan du se hvilken. |
| 🟡 ×2 | Intet netværk | Ja | Pi'en kan ikke finde et af de gemte WiFi-net. Tænd mobilens hotspot eller sæt et netværkskabel i. Se [wifi.md](wifi.md). |
| 🟡 ×3 | Uret er ikke stillet | Ja, men tiderne kan være forkerte | Pi'en har net, men har ikke kunnet stille uret endnu. Vent et par minutter. |
| 🔴 ×4 | Databasen kan ikke læses | **Nej** | Genstart Pi'en. Fortsætter det, er SD-kortet måske fyldt eller defekt. |
| 🔴 ×5 | RaceTimer kunne ikke starte | **Nej** | Genstart Pi'en. Fortsætter det, så kør opdateringen igen eller skriv et nyt SD-kort. |

Ved gule koder er forsiden stadig grøn. Tidtagningen virker, kun bagsiden advarer. Ved røde koder blinker begge sider.

Er der flere problemer på én gang, vises det vigtigste: rød ×1 → rød ×4 → gul ×2 → gul ×3. Uden net kan uret ikke stilles, så gul ×2 dækker også over gul ×3. I offline-tilstand vises gul ×3 dog, indtil uret er stillet manuelt i klar-tjekket, og røde koder vises som altid.

Orange er altid fast lys, gul blinker altid. Det er sådan, man kender dem fra hinanden.

## Scanninger (forsiden)

| Lys | Scanning |
|---|---|
| 🟢 Grønt blink | Talt: omgang, mål, tjekket ind, afgang |
| 🟡 Gult blink | Læst, men tæller ikke (fx for tidligt eller allerede registreret) |
| 🔴 Rødt blink | Ukendt armbånd, kontakt en official |
| 🔵 Blåt blink | Chip tildelt under *Deltagere → Scan*, eller admin-armbånd scannet |
| 🔵 Blåt blink, så hvide blink, så grønt | Callout: løberen har scannet. Hvide blink ved 10, 5, 3, 2 og 1 sekund og grønt, når løberens tid starter |
| ⚪ Hvide blink ×3, ×2, ×1 | Nedtælling 3-2-1 minutter |
| 🟢 Grønt lys i 3 sek. | Start |

## Nedlukning

| Lys | Betyder |
|---|---|
| 🟣 Lilla | Pi'en lukker ned. **Tag ikke strømmen endnu.** |
| Slukket | Nu kan strømmen fjernes |

## Indstillinger

Lampen tilføjes af sig selv under **⚙ Opsætning → Moduler**, første gang den sættes i. Her kan du vælge:
- **Læser:** hvilke læseres scanninger lampen blinker ved
- **Lysstyrke**
- **Scanninger vises på:** forsiden, begge sider, eller slet ikke (så viser lampen kun status)

**Test** får lampen til at skifte mellem alle farver i 3 sekunder. Under status står, hvad den viser lige nu, fx *Forside: grøn · bagside: gul ×2*.

Fjerner du lampen i admin, bliver den ikke tilføjet igen. Den kan altid tilføjes fra listen over fundne enheder. Hvide, lilla og røde ×5 lys kommer fra opstarten og nedlukningen af Pi'en og vises altid, når lampen er sat i.

## Lampe ved læseren (blink(1) mk3)

En lille [blink(1) mk3](https://shop.thingm.com/products/blink1mk3) kan sidde ved hver RFID-læser, så løberen kan se, om scanningen talte. Den blinker med de samme farver som forsiden på statuslampen: grønt = talt, gult = læst, men tæller ikke, rødt = ukendt armbånd, blåt = callout eller chip tildelt. Mellem scanningerne lyser den grønt, når Pi'en er klar, og viser de røde koder ved fejl.

Lamperne tilføjes af sig selv under **⚙ Opsætning → Moduler**, når de sættes i. Med to læsere og to lamper skal hver lampe have sin læser:
- **Sidder ved læser:** *Læser 1 (primær)* eller *Læser 2 (backup)*. Så blinker lampen kun ved sin egen læser. *Begge læsere* passer, når der kun er én lampe.
- **Lysstyrke:** standard er fuld styrke, fordi lampen er lille.
- **Mellem scanninger:** grøn, når Pi'en er klar, eller slukket, så den kun lyser ved scanninger. Røde fejlkoder vises altid.

Brug **Test** for at se, hvilken lampe der er hvilken. blink(1) lyser svagere end Luxafor Flag og ses bedst i skygge. Lamperne lyser ikke under opstart og nedlukning af Pi'en, det gør kun Luxafor-lampen.

## Teknisk

- Lampen er en USB HID-enhed (`04D8:F372`). RaceTimer skriver direkte til `/dev/hidrawN` og har ingen ekstra pakker. Reglen `/etc/udev/rules.d/60-racetimer-luxafor.rules` giver gruppen `input` adgang.
- `racetimer-led.service` sætter hvid tidligt i opstarten og lilla ved nedlukning. `/usr/lib/systemd/system-shutdown/racetimer-led` slukker lampen helt til sidst.
- `racetimer-led-fail.service` startes af `OnFailure=` i `racetimer.service` og blinker rødt ×5, indtil RaceTimer starter igen.
- Alt installeres af opdateringen (`deploy/post-update.sh`).
- blink(1) styres med HID feature reports (`ioctl HIDIOCSFEATURE`) på `/dev/hidrawN` (`27B8:01ED`). Samme udev-regel giver adgang (`racetimer/modules/blink1.py`).
