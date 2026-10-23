# Kom i gang: RaceTimer i jeres klub

Denne vejledning er til klubber og arrangører, der vil bruge RaceTimer til egne løb. Den går fra indkøb til første løb. Du skal ikke kunne programmere, og en Raspberry Pi kan sættes op på en aften.

**Indhold**
1. [Det skal I bruge](#1-det-skal-i-bruge)
2. [Skriv SD-kortet](#2-skriv-sd-kortet)
3. [Første opstart og opsætningsguiden](#3-første-opstart-og-opsætningsguiden)
4. [Prøv det med demoløbet](#4-prøv-det-med-demoløbet)
5. [Opret jeres eget løb](#5-opret-jeres-eget-løb)
6. [Deltagere og chips](#6-deltagere-og-chips)
7. [På løbsdagen](#7-på-løbsdagen)
8. [Resultater på nettet](#8-resultater-på-nettet)
9. [Opdateringer og sikkerhedskopi](#9-opdateringer-og-sikkerhedskopi)
10. [Fejlfinding](#10-fejlfinding)

---

## 1. Det skal I bruge

| Del | Krav | Bemærk |
|---|---|---|
| **Raspberry Pi** | Pi 5 (anbefalet), Pi 4 eller Pi 3 (B/B+) | Pi 3 klarer tidtagningen fint, men skærmen er langsommere. Brug den officielle strømforsyning. |
| **SD-kort** | 32 GB eller større, gerne "A2"/"Application class" | Et godt mærkekort holder længere. |
| **Skærm** | Alm. skærm eller TV med HDMI | Pi 4/5 har micro-HDMI, så I skal bruge et kabel eller en adapter. |
| **RFID-læser** | 1 eller 2 USB-læsere, 13,56 MHz, "keyboard emulation" | Driverfri, billig og den mest udbredte type. Med 2 af samme model har I en backup. |
| **Armbånd/chips** | MIFARE Classic 1K eller NTAG213 | Køb et par ekstra til glemte og defekte chips. |
| **Ur (kun Pi 5)** | Officielt RTC-batteri | Holder uret, når Pi'en er slukket og uden internet. Pi 3/4 har ikke batteristik, så de skal have internet ved opstart (mobil-hotspot er nok). |
| Til ude i skoven | Powerbank med pass-through eller UPS | Skærmen skal også have strøm. |

> **Tip:** Køb læseren før armbåndene, og test med de armbånd, der fulgte med. Læseren skal kunne læse jeres chip-type.

## 2. Skriv SD-kortet

1. Hent det nyeste image under **[Releases](https://github.com/peterskotte/racetimer/releases/latest)**. Filen hedder `racetimer-X.Y.Z-raspberrypi-arm64.img.xz` og fylder ca. 1 GB. Den skal ikke pakkes ud.
2. Hent og start **Raspberry Pi Imager** fra [raspberrypi.com/software](https://www.raspberrypi.com/software/).
3. **Enhed:** vælg jeres Pi-model.
4. **Operativsystem:** rul ned til **Brug brugerdefineret** (*Use custom*), og vælg den hentede fil.
5. **Lager:** vælg SD-kortet.
6. Når Imager spørger om tilpasning, kan I vælge **Rediger indstillinger** og lægge **WiFi** ind (netværk, kode og land DK). Det er valgfrit, for WiFi kan også sættes op i guiden bagefter. Lad værtsnavnet være `racetimer`.
7. Skriv kortet. Det tager 5–10 minutter.

Imaget indeholder Raspberry Pi OS, RaceTimer og ét demoløb. Der er ingen netværk, koder eller klubdata i det.

> **Login på selve Pi'en** er `racetimer` / `racetimer`. SSH er slået fra, fordi koden er offentligt kendt. Har I brug for SSH, så vælg eget brugernavn og kode og slå SSH til under *Rediger indstillinger* i Imager.

## 3. Første opstart og opsætningsguiden

1. Sæt kortet i Pi'en. Tilslut skærm (på Pi 4/5 HDMI 0, porten nærmest strømstikket), RFID-læsere og til sidst strøm.
2. Første opstart tager 1–2 minutter. Derefter åbner resultatskærmen af sig selv og viser **Pi'ens adresse** nederst, fx `http://192.168.1.23:8000`.
3. På en mobil eller bærbar **på samme netværk** åbner I adressen med `/admin` bagefter, fx `http://192.168.1.23:8000/admin`. `http://racetimer.local:8000/admin` virker også på de fleste netværk.
   Er Pi'en ikke på et netværk endnu, kan I åbne `http://localhost:8000/admin` på Pi'en selv med mus og tastatur. Luk kiosk-visningen med **Alt+F4**.
4. Log ind med **admin / admin**. Opsætningsguiden starter:

| Trin | Hvad sker der |
|---|---|
| 1. **Admin-kode** | Vælg en ny kode. Standardkoden kan ikke bruges, efter I har skiftet den. |
| 2. **Navn og logo** | Klubbens eller løbets navn og eventuelt et logo (PNG/JPG/WebP, gerne med gennemsigtig baggrund). Vises øverst på skærmen og på resultatsiderne. |
| 3. **Splash-skærm** | Billedet, der vises, når der ikke kører et løb. Vælg et medfølgende, eller upload jeres eget. |
| 4. **WiFi** (valgfrit) | Op til 5 netværk, som Pi'en selv forbinder til, fx klubhus og en mobil-hotspot. Eduroam og andre netværk med brugernavn virker også. |
| 5. **RFID-læsere** | Vælg primær og evt. backup. Hold en chip mod læseren, og se den dukke op. |
| 6. **Færdig** | Tjekker, at Pi'ens ur passer med jeres mobil/computer, og viser en opsummering. |

Alt kan ændres senere: navn, logo og splash under **Udseende**, netværk under **WiFi** og læsere under **Rediger aktivt løb → Læsere**.

> **Flere officials?** Opret en bruger til hver under **Brugerstyring**, så ingen deler kode.

## 4. Prøv det med demoløbet

En ny installation har ét demoløb, *Demoløb (kan slettes)*, med tre testløbere (chip `DEMO01`–`DEMO03`).

1. Gå til **Rediger aktivt løb**, og tryk **Start nu**.
2. Under **Test uden hardware** kan I "scanne" en testchip og se omgangene komme på skærmen.
3. Prøv også jeres rigtige læser: tildel jeres egen chip til en testløber under **Deltagerregistrering → 📡 Scan**, og hold den mod læseren.
4. Afslut demoløbet, og slet det, når I er trygge ved systemet.

## 5. Opret jeres eget løb

Under **Tilføj nyt løb** vælger I type, navn og eventuelt et planlagt starttidspunkt.

| I vil lave … | Vælg |
|---|---|
| Et backyard-løb efter de officielle regler | **Backyard Ultra (officiel)** |
| Et kortere backyard, fx træningsløb, med egen distance eller et fast antal omgange eller timer | **Backyard Ultra (custom)** |
| Et løb fra start til mål med fælles start, fx 5 km eller trail | **Alm. tidtagning (A til B)** |
| Flest omgange på 6, 12, 24 eller 48 timer | **Tidsbaseret** |
| Fælles mål, hvor alle omgange lægges sammen (fx "Årets rekord") | **Rekordløb** |
| Enkeltstart, bølgestart eller start på chip | **Intervalstart** |
| Canicross | Vælg A til B, tidsløb, rekordløb eller intervalstart, og sæt flueben i **Canicross** |

Reglerne for hver type og backyards tidsvinduer står i [README](../README.md#løbstyper).

**Indtjekning:** Ved fælles start skal hver løber scanne sin chip inden for 30 minutter før start. Ellers tæller løberens læsninger ikke. Glemmer en løber det, kan en official trykke **✓ Tjek ind** i admin. Vinduet kan ændres pr. løb, og 0 slår det fra.

## 6. Deltagere og chips

**Excel-import (hurtigst ved mange deltagere)**
1. Under **Deltagerregistrering** henter I skabelonen.
2. Udfyld *Startnr, Navn, Køn, Klub* og eventuelt *Chip*. Ved canicross også *Hunde, Hund 1, Hund 2*.
3. Importér filen. CSV virker også, fx eksporteret fra jeres tilmeldingssystem.

**Tildel chips ved at scanne**
Tryk **📡 Scan** ud for en deltager, og hold armbåndet mod en læser. Så er chippen tildelt. Scanninger her tæller ikke i løbet. Det er nemt at gøre ved udleveringen af startnumre.

**Manuelt:** Tilføj enkelte deltagere med formularen, fx eftertilmeldinger på dagen.

## 7. På løbsdagen

**Før start**
- [ ] Tænd Pi'en i god tid. Tjek at klokken øverst på resultatskærmen passer med din mobil.
- [ ] Tjek at læserne står som forbundet under **Rediger aktivt løb → Læsere** (grøn prik).
- [ ] Placér læserne ved målet, ca. 30 cm fra hinanden, og mærk dem "1" og "2".
- [ ] Bed løberne scanne for at tjekke ind. Skærmen viser, hvor mange der er tjekket ind, fx 18/20.
- [ ] Hav en mobil med admin åben, så I kan rette undervejs.

**Under løbet**
- Løberen holder armbåndet mod læser 1. Bipper den ikke, bruges læser 2. Samme chip på begge læsere tæller kun én gang.
- **Fejler RFID**, kan I registrere tider manuelt: **+ Nu** registrerer en passage med klokken lige nu, og **⏱ Tid** lader jer skrive tiden ind bagefter.
- Udgår en løber, trykker I **RTC** (udgået) ud for løberen. **DNS** er for en løber, der ikke startede, og **DSQ** for diskvalifikation.
- En forkert læsning kan ignoreres og gendannes igen i loggen. Intet slettes.
- I backyard viser **⚑ Til vurdering** læsninger i flagzonen, som en official skal godkende eller afvise.

**Efter løbet**
- Afslut løbet, og hent resultaterne som **CSV** (åbnes i Excel).
- Tryk **🗄 Arkivér**, når I er færdige med løbet. Det forsvinder fra løbslisten og skærmen, men ligger under fanen **Arkiv**, hvor det kan ses, hentes som CSV og gendannes.
- Har I sat synkronisering op, sendes de endelige resultater til hjemmesiden automatisk.

> **Strømsvigt eller genstart midt i løbet?** Alle læsninger gemmes med det samme, og stillingen regnes ud fra dem. Tænd Pi'en igen, så er alt som før.

## 8. Resultater på nettet

RaceTimer kører fint helt uden internet. Har Pi'en net (fx via mobil-hotspot), kan den sende resultaterne videre under **Synkronisering**:

| Har I … | Vælg |
|---|---|
| Kun FTP-adgang til klubbens webhotel | **FTP-upload**: Pi'en laver selv en færdig resultatside |
| Et webhotel med PHP | **Egen hjemmeside (JSON)** med de færdige filer i [`webhotel/`](../webhotel/LÆS-MIG.md) |
| En lille Linux-server | **RaceTimer-spejlserver**: præcis samme live-skærm offentligt |

Vælg hvor ofte der sendes, fx hvert minut, og sæt flueben i *ved afslutning*. Detaljer i [README](../README.md#send-resultater-til-en-webserver).

**Adgang til admin hjemmefra eller over mobilnet:** se [fjernadgang.md](fjernadgang.md). Tailscale er det nemmeste og sikreste for en lille gruppe officials.

## 9. Opdateringer og sikkerhedskopi

**Opdateringer:** Under **Admin → Opdatering** står den installerede version, og om der er en nyere. Tryk **Opdatér**, så hentes og installeres den nye version. Pi'en skal have internet.
- Kun pakker signeret af udgiveren installeres.
- Starter den nye version ikke, går Pi'en automatisk tilbage til den gamle. I kan også selv rulle tilbage.
- Løb, deltagere og indstillinger røres ikke.
- Opdatér ikke midt i et løb. Admin advarer, hvis et løb er i gang.

**Sikkerhedskopi:** Hent resultaterne som CSV efter hvert løb. Vil I gemme hele databasen, ligger den i `/var/lib/racetimer/` på Pi'en. Med SSH slået til kan den kopieres til en computer:

```bash
scp -r racetimer@racetimer.local:/var/lib/racetimer ./racetimer-backup
```

## 10. Fejlfinding

| Problem | Løsning |
|---|---|
| **Jeg kan ikke finde Pi'ens adresse** | Den står nederst på resultatskærmen. Prøv også `http://racetimer.local:8000/admin`. Mobil og Pi skal være på samme netværk. |
| **Sort skærm / resultatskærmen er lukket** | Genstart Pi'en, eller log ud og ind på skrivebordet. Kiosk-visningen starter af sig selv. |
| **Læseren reagerer ikke** | Tjek at den er valgt under *Læsere*, og at prikken er grøn. Prøv en anden USB-port. Bipper læseren, men intet sker, så hold chippen mod læseren under **📡 Scan** for at se, om den læses. |
| **En løbers omgange tæller ikke** | Er løberen tjekket ind? Har løberen den rigtige chip? Er omgangen hurtigere end minimumstiden? Se loggen under *Seneste læsninger*. |
| **Uret går forkert** | Pi 3/4 og Pi 5 uden RTC-batteri har brug for internet ved opstart for at stille uret. Forbind til en mobil-hotspot i et par minutter. |
| **WiFi vil ikke forbinde** | Tjek koden. Fejlbeskeden står under **WiFi**. Mobil-hotspots skal være synlige, og iPhone skal have "Maksimer kompatibilitet" slået til. |
| **Glemt admin-kode** | En anden administrator kan sætte en ny under **Brugerstyring**. Er der ingen, så kontakt udgiveren via GitHub. |
| **Opdateringen fejlede** | Pi'en kører videre på den gamle version. Loggen står under **Opdatering**. |

Finder I en fejl eller mangler en funktion, så opret en sag under **[Issues](https://github.com/peterskotte/racetimer/issues)** på GitHub. Skriv versionsnummeret (står under *Opdatering*), løbstype, og hvad der skete.
