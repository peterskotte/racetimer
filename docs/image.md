# RaceTimer-image til Raspberry Pi 3, 4 og 5

> Ny bruger? Start med [vejledning.md](vejledning.md), der går fra indkøb til første løb.

`racetimer-X.Y.Z-raspberrypi-arm64.img.xz` (hentes under [Releases](https://github.com/peterskotte/racetimer/releases/latest)) er et komplet SD-kort-image: Raspberry Pi OS (64-bit, med skrivebord) og RaceTimer, som er installeret og sat op. Du skal ikke installere noget og behøver ikke internet for at køre et løb.

## Hvad er sat op i imaget

| | |
|---|---|
| Værtsnavn | `racetimer` → `http://racetimer.local:8000` |
| Login på Pi'en | bruger **`racetimer`**, kode **`racetimer`**. Opsætningsguiden beder dig skifte den, og `sudo` kræver kode. |
| Admin i RaceTimer | **`admin`** og en tilfældig førstegangskode, som vises på Pi'ens skærm og ligger i `racetimer-kode.txt` på SD-kortet. Guiden beder dig skifte den. |
| Sprog / tastatur / tidszone | Dansk, dansk tastatur, Europe/Copenhagen, WiFi-land DK |
| SSH | Slået fra – slå det til med eget login under *Rediger indstillinger* i Raspberry Pi Imager |
| RaceTimer | Installeret i `/opt/racetimer` som systemd-service. Starter ved boot og genstarter ved fejl. |
| Skærm | Logger automatisk ind og åbner resultatskærmen i fuldskærm (kiosk). Skærmen slukker aldrig. |
| RFID-læsere | Adgang til USB-læsere (gruppen `input`) og serielle læsere (`dialout`) er klar. Vælg dem i admin. |

## 1. Skriv imaget til SD-kortet

1. Hent **Raspberry Pi Imager** fra raspberrypi.com/software og start den.
2. **Enhed:** jeres model (Raspberry Pi 3, 4 eller 5).
3. **Operativsystem:** rul ned til **"Brug brugerdefineret"** (Use custom) og vælg den hentede `racetimer-…-raspberrypi-arm64.img.xz`.
4. **Lager:** vælg SD-kortet (32 GB eller større anbefales).
5. Når Imager spørger, om du vil tilpasse indstillingerne, så vælg **Rediger indstillinger**. Her kan du lægge **WiFi** ind med netværksnavn, kode og land DK. Du kan også vælge **eget brugernavn og kode** til Pi'en. Lad værtsnavnet være `racetimer`.
6. Skriv kortet. Det tager 5-10 minutter.

Mere om WiFi, flere netværk og mobil-hotspot: [wifi.md](wifi.md).

## 2. Første opstart

1. Sæt kortet i Pi'en, og tilslut skærm (HDMI 0, nærmest strømstikket), RFID-læsere og strøm.
2. Første opstart tager 1-2 minutter, fordi Pi'en gør kortet større og lægger dine indstillinger ind. Derefter kommer skrivebordet, og resultatskærmen åbner af sig selv.
3. Fra en mobil eller bærbar på samme netværk åbner du `http://racetimer.local:8000/admin`. Virker `.local` ikke, så brug IP-adressen, som står nederst på resultatskærmen.
4. Log ind med `admin` og førstegangskoden fra Pi'ens skærm (eller fra `racetimer-kode.txt` på SD-kortet). En opsætningsguide fører dig igennem ny admin-kode, ny kode til Pi'en, navn og logo, splash-skærm, WiFi og RFID-læsere. Se [vejledning.md](vejledning.md#3-første-opstart-og-opsætningsguiden).

**Skift koden til Pi'en igen senere:** opsætningsguiden skifter standardkoden én gang. Vil du skifte den igen, så åbn en terminal på Pi'en, eller log ind via `ssh racetimer@racetimer.local`, og kør:

```bash
passwd
```

## 3. Daglig brug

- Tænd Pi'en. RaceTimer og resultatskærmen starter selv.
- Data ligger i `/var/lib/racetimer/`: databasen og en rå log over alle chip-læsninger. Programmet ligger i `/opt/racetimer/`.
- Afslut kiosk-visningen med **Alt+F4**, hvis du skal bruge skrivebordet. Den starter igen ved næste login eller genstart.
- Sluk pænt med strømknappen på Pi 5 (et kort tryk) eller med `sudo poweroff`. Data er sikret, også ved strømsvigt.

## Nyttige kommandoer (via SSH eller terminal)

Status og log:

```bash
systemctl status racetimer
```

```bash
journalctl -u racetimer -f
```

Genstart RaceTimer:

```bash
sudo systemctl restart racetimer
```

Tag en sikkerhedskopi af data til din computer (kør den på computeren):

```bash
scp -r racetimer@racetimer.local:/var/lib/racetimer ./racetimer-backup
```

## Opdatér RaceTimer

Under **Admin → ⚙ Opsætning → Opdatering** hentes og installeres nye versioner med ét tryk (Pi'en skal have internet). Løb og data røres ikke, og fejler den nye version, rulles der automatisk tilbage. Se [udgivelse.md](udgivelse.md) for hvordan det virker.

## Byg imaget selv igen

Det kræver en Mac eller PC med **Docker Desktop**. På en Mac med Apple Silicon tager det ca. 30-60 minutter. Kør fra projektmappen:

```bash
sh image/build.sh
```

Det færdige image lægges i `image/out/`. Login, sprog og værtsnavn ændres i `image/config`.
