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

Er der flere problemer på én gang, vises det vigtigste: rød ×1 → rød ×4 → gul ×2 → gul ×3. Uden net kan uret ikke stilles, så gul ×2 dækker også over gul ×3.

## Scanninger (forsiden)

| Lys | Scanning |
|---|---|
| 🟢 Grønt blink | Talt: omgang, mål, tjekket ind, afgang |
| 🟡 Gult blink | Læst, men tæller ikke (fx for tidligt eller allerede registreret) |
| 🔴 Rødt blink | Ukendt armbånd, kontakt en official |
| 🔵 Blåt blink | Chip tildelt under *Deltagere → Scan*, eller admin-armbånd scannet |
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

## Teknisk

- Lampen er en USB HID-enhed (`04D8:F372`). RaceTimer skriver direkte til `/dev/hidrawN` og har ingen ekstra pakker. Reglen `/etc/udev/rules.d/60-racetimer-luxafor.rules` giver gruppen `input` adgang.
- `racetimer-led.service` sætter hvid tidligt i opstarten og lilla ved nedlukning. `/usr/lib/systemd/system-shutdown/racetimer-led` slukker lampen helt til sidst.
- `racetimer-led-fail.service` startes af `OnFailure=` i `racetimer.service` og blinker rødt ×5, indtil RaceTimer starter igen.
- Alt installeres af opdateringen (`deploy/post-update.sh`).
