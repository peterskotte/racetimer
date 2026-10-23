# RaceTimer

Et enkelt RFID-tidtagningssystem til løbetræning og løb, der kører på en Raspberry Pi 3, 4 eller 5.
Pi'en er både server, viser resultatskærmen og har en kodebeskyttet admin-side.

- **Resultatskærm** (dark mode): `http://<pi>:8000/` – virker på Pi-skærmen, en TV-skærm og på mobilen.
  `?kiosk=1` får lange lister til at rulle automatisk.
- **Admin**: `http://<pi>:8000/admin` – første login er `admin` / `admin`. Skift koden med det samme.

**Ny klub? Start med [Kom i gang-vejledningen](docs/vejledning.md)**: indkøb, SD-kort, opsætning, første løb og fejlfinding.

## Løbstyper

| Type | Sådan fungerer det |
|---|---|
| **Backyard Ultra (officiel)** | 6,7056 km, ny start hver hele time, advarsel 3-2-1 min (stor nedtælling på skærmen og bip). Løbere uden gyldig mållæsning inden timen er gået, bliver DNF. Vinderen er den sidste løber, der gennemfører én omgang mere end alle andre. Hvis ingen gennemfører den sidste omgang, er der ingen vinder. Parametrene er låst. |
| **Backyard Ultra (custom)** | Distance og minimumstid kan justeres, og du vælger, hvordan løbet slutter. **Sidste mand tilbage:** som officielt, med fælles start og 3-2-1-advarsler efter et valgfrit interval. **Samlet tid** (fx 3 timer): omgange løbes i træk uden fælles starter. Flest omgange vinder, og ved lige mange vinder den, der nåede sin sidste omgang først. **Cutoff** (fx 5 omgange): omgange løbes i træk, man er færdig efter sidste omgang, og hurtigste samlede tid vinder. |
| **Alm. tidtagning (A til B)** | Fælles start, som admin udløser med "Start nu" eller et planlagt tidspunkt. Måltiden er den første læsning efter minimumstiden. |
| **Rekordløb** | Tæller omgange pr. deltager og lægger alles distance sammen til en fælles total ("Årets rekord") med en fremskridtsbjælke mod rekorden. |
| **Tidsbaseret 6/12/24/48 t** | Flest omgange inden for tidsgrænsen vinder. Ved lige mange omgange vinder den, der nåede sin sidste omgang først. Læsninger efter slut tæller ikke. |
| **Intervalstart / enkeltstart** | Tre måder at starte på: *enkeltstart* med fast interval i startnummer-orden, *bølgestart* hvor startnummer-intervaller får hver sin forskydning, eller *chipstart* hvor første læsning er starttid. Hver løber kan desuden få en manuel startforskydning. |

**Indtjekning (alle løb med fælles start):** Hver løber skal scanne sin chip inden for **30 min før start**. Når løbet startes, starter alle indtjekkede på startskuddet, og hver stopper, når de selv scanner i mål. **Uden indtjekning tæller intet** for løberen: ingen omgange, ingen måltid, og i backyard er løberen ikke med i "sidste mand". En official kan trykke **✓ Tjek ind** i admin, fx hvis en løber har glemt at scanne. Så tæller løberens læsninger med det samme, også dem fra før indtjekningen. Før start viser skærmen og admin, hvor mange der er tjekket ind (fx 12/20), og hver løber står som *Tjekket ind* eller *Venter*. Vinduet kan ændres pr. løb (*Indtjekning: min. før start*, 0 = slået fra). Ved intervalstart med chipstart er startscanningen selve starten, så der er ingen særskilt indtjekning.

**🐕 Canicross:** A til B, rekordløb, tidsløb og intervalstart kan markeres som canicross, når løbet oprettes eller redigeres. Så skal hver deltager have **1 eller 2 hunde** med navn. Det kontrolleres ved manuel oprettelse, ved redigering og ved Excel-import (kolonnerne *Hunde, Hund 1, Hund 2*; antallet kan udelades og tælles så ud fra navnene). Hundenavnene vises under løberen på skærmen, på resultatsiderne og i CSV-filen. I admin vises, hvor mange deltagere der mangler hunde.

**Tidsvinduer i backyard** (i hver runde, officielle værdier):

| Minut i runden | Betydning |
|---|---|
| 0–3 | Afgang. Læsningen bekræfter start og vises som ✓ i kolonnen "Afgang" i admin. |
| 3–25 | Flagzone. Læsningen tæller **ikke**, men vises under **⚑ Til vurdering** i admin, hvor en official godkender den som runde eller afviser den (fx sen start eller en løber, der har vendt om). |
| 25–60 | Målvindue. Første læsning = runden er klaret. Ekstra passager i samme runde ignoreres. |

Samme chip inden for 30 sek. tæller kun én gang (debounce, kan ændres i admin). En manuel passage fra admin tæller altid, fordi den er officialens egen registrering.

Når klokken slår, gælder: har en løber ingen mållæsning i runden, er løberen ude, og runderne gemmes. Er der **2 eller flere** aktive, fortsætter løbet. Er der **1 med flest runder**, er det vinderen. Er der **1 med lige mange runder** (den næstsidste meldte fra i startfeltet efter en gennemført runde), skal den sidste løbe én runde alene for at vinde. Det viser skærmen. Er der **0** aktive, er alle DNF. Melder en løber fra (RTC) i hvilepausen, vises det med det samme.

**Minimumstiden** findes for de øvrige typer. Læsninger tættere på start eller på forrige omgang end den ignoreres. Det beskytter mod dobbeltlæsninger og mod løbere, der står og venter ved læseren i startboksen.

## Hardware

| Del | Anbefaling |
|---|---|
| Computer | Raspberry Pi 5 (4 eller 8 GB) anbefales; Pi 4 og Pi 3 (B/B+) virker også. Brug den officielle strømforsyning og et godt SD-kort eller en NVMe-disk |
| **Ur** | **Officielt Pi 5 RTC-batteri** (lille knapcelle-stik). Uden det mister Pi'en tiden ved strømsvigt, hvis der ikke er internet. |
| RFID-læsere (2 stk.) | **To ens USB HID-læsere til 13,56 MHz** ("keyboard emulation", MIFARE/NTAG). Driverfrie, billige, robuste og de mest udbredte. Brug samme model til primær og backup, så chip-ID'et har samme format. |
| Armbånd | Silikone-armbånd med MIFARE Classic 1K eller NTAG213. ID'et kan tjekkes med en mobil med NFC. 125 kHz EM4100-armbånd + 125 kHz-læsere virker også. |
| Strøm i felten | UPS-HAT eller powerbank med pass-through. Databasen er crash-sikker, men skærmen skal også have strøm. |

**Placering:** Sæt de to læsere ca. 30 cm fra hinanden ved målet, mærket "1" og "2". Hvis de står helt tæt, kan 13,56 MHz-felterne forstyrre hinanden. Løberen holder armbåndet mod læser 1. Hvis den ikke bipper, bruger løberen læser 2. Hvis begge læsere ser samme chip inden for dublet-vinduet (10 sek. som standard), tæller det kun én gang. Dublet-vinduet kan ændres i admin.

> Har du brug for at løberne bliver registreret *uden* at stoppe (fx store A-B-løb), kræver det UHF-læsere med antennemåtter. De er markant dyrere. Koden understøtter læsere, der sender chip-ID som tekstlinjer over seriel/USB (`serial:/dev/serial/by-id/...`), så en UHF-læser i "ASCII output"-tilstand kan sættes ind uden kodeændringer.

## Installation på Pi'en

**Nemmest:** hent det færdige SD-kort-image `racetimer-X.Y.Z-raspberrypi-arm64.img.xz` under **[Releases](https://github.com/peterskotte/racetimer/releases/latest)**, og skriv det til et SD-kort med Raspberry Pi Imager (virker på Raspberry Pi 3, 4 og 5). Så er alt sat op, og første gang du åbner admin, guider opsætningen dig igennem. Se [docs/image.md](docs/image.md).

Eller installér på en Pi, der allerede kører Raspberry Pi OS:

```bash
git clone https://github.com/peterskotte/racetimer.git ~/racetimer
cd ~/racetimer
sh deploy/install.sh
sudo reboot
```

Skal Pi'en på WiFi først, så følg [docs/wifi.md](docs/wifi.md).

Scriptet:

- installerer afhængigheder
- opretter en systemd-service, der starter ved boot og genstarter ved fejl
- giver brugeren adgang til `/dev/input`
- starter Chromium i kiosk-tilstand på skærmen

Bagefter vælger du læserne i **Admin → Rediger aktivt løb → Læsere**. Listen viser stabile `/dev/input/by-id/...`-stier, så primær og backup ikke bytter plads efter en genstart.

## Opdateringer

Under **Admin → Opdatering** kan man se den installerede version, få besked om nye versioner (med ændringsliste) og opdatere med ét tryk:
- Pakkerne er **digitalt signeret**, og en pakke, der ikke er fra udgiveren, installeres aldrig.
- Starter en ny version ikke, **rulles der automatisk tilbage**. Man kan også selv rulle tilbage.
- Løb og indstillinger røres ikke.

Sådan udgiver man en ny version: [docs/udgivelse.md](docs/udgivelse.md).

## Første opstart (ny installation)

Første gang du åbner `http://racetimer.local:8000/admin`, logger du ind med **admin / admin**. Derefter fører en opsætningsguide dig igennem:

1. **Ny admin-kode.** Skal vælges, før noget andet virker.
2. **Navn og logo.** Vises på resultatskærmen og hjemmesiden.
3. **Splash-skærm.** Vælg et medfølgende billede eller upload jeres eget.
4. **WiFi** (valgfrit). Flere netværk kan tilføjes senere under fanen *WiFi*.
5. **RFID-læsere.** Vælg primær/backup og test med en chip.
6. **Kontrol.** Tjek af Pi'ens ur og en kort opsummering.

En ny installation indeholder ét **demoløb** med 3 testløbere (chip `DEMO01`–`DEMO03`), så du kan prøve alt med *Test uden hardware*. Slet det, når I opretter jeres eget løb. Alt fra guiden kan ændres senere, fx navn, logo og splash under fanen **Udseende**.

## Sådan bruges det på løbsdagen

1. **Tilføj nyt løb**: vælg type, navn og eventuelt planlagt start.
2. **Deltagerregistrering**:
   - Importér fra Excel (hent skabelonen; kolonnerne er *Startnr, Navn, Køn, Klub, Chip* og ved canicross *Hunde, Hund 1, Hund 2*) eller tilføj deltagere manuelt.
   - Tryk **📡 Scan** ud for en deltager og hold armbåndet mod en læser. Så er chippen tildelt. Under scanning tæller læsningen ikke i løbet.
3. **Rediger aktivt løb**:
   - **Start nu** eller **Start kl.** (Backyard: start på et helt klokkeslæt).
   - Undervejs kan du markere RTC/DNS/DSQ og ignorere eller gendanne fejllæsninger.
   - **Hvis RFID fejler:** **+ Nu** registrerer en passage med klokken lige nu. **⏱ Tid** åbner en dialog, hvor du indtaster tiden som klokkeslæt (med sekunder) eller som løbstid fra start:
     - **Omgange / mellemtid** (backyard, tidsløb, rekordløb): hver tid tæller som en omgang. Den sidste omgang er sluttiden.
     - **Sluttid** (A til B, intervalstart): erstatter en eventuel forkert mållæsning. Den gamle læsning ignoreres og kan gendannes i loggen.
     - **Starttid** (intervalstart med chipstart): hvis løberen ikke blev læst ved start.
     - Manuelle tider er officialens afgørelse og tæller derfor også i backyards flagzone. De vises som "Manuel" i loggen og kan ignoreres der.
   - **Resultater (CSV)** henter resultatlisten.
4. **Arkivér** løbet bagefter med **🗄 Arkivér**, så løbslisten ikke bliver lang. Under fanen **Arkiv** kan gamle løb søges frem, ses, hentes som CSV eller gendannes. Intet slettes ved arkivering.

## Driftssikkerhed

- Hver læsning skrives til SQLite (WAL, `synchronous=FULL`), før den behandles, og desuden til en rå tekstlog `data/reads.log`.
- Stillingen gemmes ikke. Den **genberegnes ud fra læsningerne** ved hvert opslag. Genstarter Pi'en midt i et 48-timers løb, er alt som før.
- Intet slettes permanent fra admin. "Ignorér" og "Nulstil" markerer kun læsninger, så de kan gendannes.
- Hvis en læser mister forbindelsen (kablet trækkes ud), forbinder den automatisk igen. Status vises i admin og som små prikker på resultatskærmen.

## Send resultater til en webserver

Alt kører på Pi'en, også uden internet. Under **Admin → Synkronisering** bestemmer du, hvor resultaterne sendes hen, og hvornår.

```
[læsere] → Raspberry Pi (tidtagning, admin, skærm) ──når der er net──▶ webserver(e)
```

Du kan oprette flere **destinationer**. For hver vælger du:

| Indstilling | Valg |
|---|---|
| **Type** | *RaceTimer-spejlserver*: viser den samme resultatskærm offentligt. *Egen hjemmeside (JSON)*: din side modtager stillingen og viser den selv. *FTP-upload*: Pi'en laver en færdig resultatside og lægger den på dit webhotel. |
| **Send automatisk** | Kun manuelt, hvert 10./30. sek., hvert 1./5./15. minut eller hver time |
| **Ved afslutning** | Send de endelige resultater automatisk, når løbet afsluttes. Det sker præcis én gang, og Pi'en prøver igen hvert 30. sek., indtil det lykkes. |
| **Send nu** | Knap til manuel afsendelse. Er løbet afsluttet, sendes resultaterne som endelige. |

Status for hver destination viser seneste afsendelse, eventuel fejl, næste planlagte afsendelse, og for spejlservere hvor mange læsninger der venter. **Chip-ID'er sendes aldrig.**

**Fjernadgang:** under **Admin → Fjernadgang** kan Pi'en nås udefra på tre måder uden åbne porte:
- **Tailscale:** privat, kun dine egne enheder, fast adresse `http://racetimer:8000/admin`.
- **Raspberry Pi Connect:** Pi'ens skærm og terminal i browseren.
- **Cloudflare:** offentligt link via **https://ditdomæne.dk/racetimer/admin**.

Se [docs/fjernadgang.md](docs/fjernadgang.md).

WiFi på Pi'en: op til 5 faste netværk under **Admin → WiFi**, som Pi'en selv forbinder til. Se [docs/wifi.md](docs/wifi.md).

### A) RaceTimer-spejlserver

En webserver kører RaceTimer i spejl-tilstand. Den har ingen admin og intet login, og den viser kun det, Pi'en sender.

- Kun nye eller ændrede læsninger sendes (komprimeret), så det er billigt over mobilnet.
- Efter et netudfald sendes det, der mangler. Mister serveren sine data, sender Pi'en hele løbet igen.
- Serveren bruger Pi'ens ur til nedtællinger, så "næste start" passer med stævnet.
- Har den ikke hørt fra Pi'en i over 30 sek., viser siden et banner om, at den viser de seneste data.

Opsætning på en Linux-server, fx en lille VPS med Ubuntu:

```bash
sudo useradd -r -m -d /opt/racetimer racetimer
sudo -u racetimer git clone https://github.com/peterskotte/racetimer.git /opt/racetimer
cd /opt/racetimer
sudo -u racetimer python3 -m venv .venv
sudo -u racetimer .venv/bin/pip install -r requirements.txt
python3 -c "import secrets; print(secrets.token_urlsafe(32))"   # din nøgle
sudo cp deploy/racetimer-mirror.service /etc/systemd/system/      # indsæt nøglen i filen
sudo systemctl enable --now racetimer-mirror
sudo apt install caddy && sudo cp deploy/Caddyfile /etc/caddy/Caddyfile   # ret domænet
sudo systemctl reload caddy
```

Opret derefter en destination på Pi'en med typen *RaceTimer-spejlserver*, adressen `https://dit-domæne` og samme nøgle.

### B) Egen hjemmeside (JSON)

Pi'en sender en `POST` med JSON til den adresse, du angiver. Nøglen sendes som `Authorization: Bearer <nøgle>`.

```json
{
  "event": "update",            // eller "final", når løbet er afsluttet
  "sent_at": 1792572000.0,
  "race": {"id": 3, "name": "Rold Skov Backyard", "type": "backyard", "status": "running", "started_at": ...},
  "info": {"yard": 12, "next_start": ..., "runners_left": 9, ...},
  "results": [
    {"place": 1, "bib": 4, "name": "Mads Hansen", "sex": "Mand", "club": "", "status": "resting",
     "status_label": "I mål", "laps": 12, "distance_km": 80.467, "total_time": 34211.0,
     "last_lap": 2890.0, "best_lap": 2701.0}
  ]
}
```

**Færdig løsning til webhotellet:** mappen [`webhotel/racetimer/`](webhotel/) indeholder `modtag.php` (modtager) og `index.php` (resultatside med arkiv). Opsætningen står i [webhotel/LÆS-MIG.md](webhotel/LÆS-MIG.md). Adressen i RaceTimer skal pege på selve scriptet, fx `https://ditdomæne.dk/racetimer/modtag.php`. Nøglen sendes både som `Authorization: Bearer …` og som `X-RaceTimer-Key`, fordi mange webhoteller fjerner Authorization-headeren.

Tider er i sekunder, og tidspunkter er Unix-tid. Vil du skrive din egen modtager, er her et minimalt PHP-script, der gemmer de seneste resultater som `resultater.json`:

```php
<?php // modtag.php
$key = 'din-hemmelige-nøgle';
if (($_SERVER['HTTP_X_RACETIMER_KEY'] ?? '') !== $key) { http_response_code(403); exit; }
$data = json_decode(file_get_contents('php://input'), true);
if (!$data) { http_response_code(400); exit; }
file_put_contents(__DIR__ . '/resultater.json', json_encode($data, JSON_UNESCAPED_UNICODE));
if ($data['event'] === 'final') {   // gem en kopi af slutresultatet
    file_put_contents(__DIR__ . '/slut-' . $data['race']['id'] . '.json', json_encode($data, JSON_UNESCAPED_UNICODE));
}
echo '{"ok":true}';
```

### C) FTP-upload til webhotel

Har du kun FTP-adgang til klubbens webhotel, laver Pi'en selv resultatsiden og uploader den. Der skal ikke installeres noget på webhotellet.

- **Adresse:** `ftps://ftp.ditwebhotel.dk/public_html/resultater`. Mappen oprettes, hvis den ikke findes. Brug `ftps://` (krypteret), hvis webhotellet understøtter det. `ftp://` virker også, men sender koden ukrypteret.
- **Brugernavn og adgangskode:** dit FTP-login fra webhotellet.
- **Filer, der uploades:**
  - `index.html`: en færdig resultatside i samme mørke stil. Den genindlæser sig selv med samme interval, som Pi'en sender.
  - `resultater.json`: samme data som JSON.
  - `slut-<løbsnavn>.html`: kopi af slutresultatet, når løbet er afsluttet, så den bliver liggende, når næste løb begynder.
- Filerne uploades først under et midlertidigt navn og omdøbes bagefter, så besøgende aldrig ser en halv side.
- FTPS kræver et gyldigt certifikat. Brug det værtsnavn, som står i webhotellets vejledning; ellers får du en tydelig fejl i status. SFTP (over SSH) understøttes ikke.

> Brug altid `https://`-adresser. Nøglen sendes i hver forespørgsel og må ikke gå ukrypteret over nettet.

## Udvikling (Mac/PC uden læsere)

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn racetimer.app:app --reload
python scripts/demo.py          # opretter et demo-backyardløb i yard 41
python -m pytest tests/         # tester løbsmotoren
```

Synkroniseringen kan prøves lokalt med en spejlserver på port 8001:

```bash
RACETIMER_MODE=mirror RACETIMER_DB=data-mirror/racetimer.db RACETIMER_MIRROR_KEY=dev-noegle-123 \
  .venv/bin/uvicorn racetimer.app:app --port 8001
```

Opret en destination under Synkronisering med adressen `http://127.0.0.1:8001` og nøglen `dev-noegle-123`.

Under **Admin → Rediger aktivt løb → Test uden hardware** kan du simulere chip-læsninger.

## Struktur

```
racetimer/
  app.py       FastAPI: API, login, import, chip-scan, læsning → database
  engine.py    Løbsmotor: rene funktioner pr. løbstype (al regellogik)
  readers.py   USB HID (evdev) + seriel læser, auto-genforbindelse
  sync.py      Sender resultater til webservere (interval, manuelt, ved afslutning)
  db.py        SQLite-skema, brugere (PBKDF2), sessioner
  static/      display.html (resultatskærm), admin.html, style.css
deploy/        install.sh, systemd-services (Pi + spejlserver), kiosk-script, Caddyfile
docs/          vejledning.md (kom i gang), image.md, wifi.md, fjernadgang.md, udgivelse.md
tests/         test af løbsmotoren
```
