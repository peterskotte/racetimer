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

> **Har I ikke en Raspberry Pi?** Til små løb (op til 12 deltagere) kan I bruge [browser-udgaven](browser.md), hvor race director tager tid ved at trykke på en skærm.

## 1. Det skal I bruge

| Del | Krav | Bemærk |
|---|---|---|
| **Raspberry Pi** | Pi 5 (anbefalet), Pi 4 eller Pi 3 (B/B+) | Pi 3 klarer tidtagningen fint, men skærmen er langsommere. Brug den officielle strømforsyning. |
| **SD-kort** | 32 GB eller større, gerne "A2"/"Application class" | Et godt mærkekort holder længere. |
| **Skærm** *(valgfri)* | Alm. skærm eller TV med HDMI | **Ikke nødvendig for at tage tid.** Resultater og admin kan ses på mobil, tablet eller bærbar (se [Uden skærm](#uden-skærm)). Pi 4/5 har micro-HDMI, så I skal bruge et kabel eller en adapter. |
| **RFID-læser** | 1 eller 2 USB-læsere, 13,56 MHz, "keyboard emulation" | Driverfri, billig og den mest udbredte type. Med 2 af samme model har I en backup. |
| **Armbånd/chips** | MIFARE Classic 1K eller NTAG213 | Køb et par ekstra til glemte og defekte chips. |
| **Ur (kun Pi 5)** | Officielt RTC-batteri | Holder uret, når Pi'en er slukket og uden internet. Pi 3/4 har ikke batteristik. De stiller selv uret, så snart de har internet, så giv dem net et par minutter, inden løbet startes (mobil-hotspot er nok). |
| Til ude i skoven | Powerbank med pass-through eller UPS | Uden skærm rækker en almindelig powerbank længe. Med skærm skal den også have strøm. |
| *Valgfrit:* højttaler | En USB-højttaler ved læseren | Lyd, når der scannes, så løberen kan høre, om omgangen talte. Se afsnit 7. |

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

1. Sæt kortet i Pi'en. Tilslut evt. en skærm (på Pi 4/5 HDMI 0, porten nærmest strømstikket), RFID-læsere og til sidst strøm.
2. Første opstart tager 1–2 minutter. Derefter åbner resultatskærmen af sig selv og viser **Pi'ens adresse** nederst, fx `http://192.168.1.23:8000`.
3. På en mobil eller bærbar **på samme netværk** åbner I adressen med `/admin` bagefter, fx `http://192.168.1.23:8000/admin`. `http://racetimer.local:8000/admin` virker også på de fleste netværk.
   Er Pi'en ikke på et netværk endnu, kan I åbne `http://localhost:8000/admin` på Pi'en selv med mus og tastatur. Luk kiosk-visningen med **Alt+F4**.
4. Log ind med brugernavnet **admin** og **førstegangskoden**. Det er en tilfældig kode som `K7PQ-M2XD-9HTA`, som hver Pi laver selv ved første opstart, så ingen andre kender den.
   - **Med skærm:** koden står stort på Pi'ens skærm, sammen med adressen.
   - **Uden skærm:** sluk Pi'en, sæt SD-kortet i en computer, og åbn filen `racetimer-kode.txt` på kortet. Filen forsvinder af sig selv, når koden er skiftet.

   Opsætningsguiden starter:

| Trin | Hvad sker der |
|---|---|
| 1. **Admin-kode** | Vælg jeres egen kode på mindst 10 tegn. Førstegangskoden holder op med at virke. |
| 2. **Pi'ens kode** | Selve Raspberry Pi'en leveres med en kendt kode (bruger `racetimer`, kode `racetimer`). Vælg en ny på mindst 10 tegn. Den bruges til skrivebordet, SSH og administrator-rettigheder (sudo). Gem den sikkert. |
| 3. **Navn og logo** | Klubbens eller løbets navn og eventuelt et logo (PNG/JPG/WebP, gerne med gennemsigtig baggrund). Vises øverst på skærmen og på resultatsiderne. |
| 4. **Splash-skærm** | Billedet, der vises, når der ikke kører et løb, og en valgfri tekst (fx "Næste løb: lørdag kl. 10"). Vises både på skærmen og på hjemmesiden. |
| 5. **WiFi** (valgfrit) | Op til 5 netværk, som Pi'en selv forbinder til, fx klubhus og en mobil-hotspot. Eduroam og andre netværk med brugernavn virker også. |
| 6. **RFID-læsere** | Vælg primær og evt. backup. Hold en chip mod læseren, og se den dukke op. |
| 7. **Færdig** | Tjekker, at Pi'ens ur passer med jeres mobil/computer, og viser en opsummering. |

Alt kan ændres senere: navn, logo og splash under **⚙ Opsætning → Udseende**, netværk under **⚙ Opsætning → WiFi** og læsere under **⚙ Opsætning → RFID-læsere**.

**Menuen i admin** er delt i to. Det, I bruger på løbsdagen, står i menuen foroven, og resten ligger under **⚙ Opsætning**. På en computer er ⚙ Opsætning et panel i højre side, hvor hver sektion klappes ud for sig, så du kan rette indstillinger og samtidig se løbet. På mobil og tablet er ⚙ Opsætning en fane i menuen.

| Løb | ⚙ Opsætning |
|---|---|
| **Aktivt løb**: start, stilling, manuelle tider, læserstatus | *Skærm og web:* **Udseende**, **Synkronisering** |
| **Nyt løb** | *Udstyr:* **RFID-læsere**, **Moduler**, **Udstyrstest** |
| **Deltagere**: import og chip-scanning | *Netværk:* **WiFi**, **Fjernadgang** |
| **Arkiv**: gamle løb | *System:* **Brugere**, **Opdatering** |

> **Flere officials?** Opret en bruger til hver under **⚙ Opsætning → Brugere**, så ingen deler kode. Alle koder skal være mindst 10 tegn, og det offentlige link kan først slås til, når alle administratorer har en kode på mindst 10 tegn.

### Uden skærm

En skærm er rar at have ved målet, men **RaceTimer kører fuldt ud uden**. Pi'en tager tid, gemmer læsninger og sender til hjemmesiden, uanset om der er en skærm.

- **Find Pi'en:** på samme netværk er adressen `http://racetimer.local:8000`. Med Tailscale er den `http://racetimer:8000`, uanset netværk. Ellers kan IP-adressen findes i routerens liste over enheder eller i mobil-hotspottets liste over forbundne enheder.
- **Admin:** `http://racetimer.local:8000/admin` på en mobil eller bærbar.
- **Resultatskærm:** `http://racetimer.local:8000/` virker på enhver mobil, tablet, bærbar eller smart-TV med browser, og flere kan se med på én gang. Tilføj `?kiosk=1` på en tablet eller et TV ved målet, så ruller listen af sig selv.
- **Scan-bekræftelse uden skærm:** sæt en **USB-højttaler** i (se afsnit 7). Så kan løberen høre, om scanningen talte. Læserens eget bip fortæller kun, at armbåndet er læst.
- **Første opstart uden skærm:** læg WiFi ind i Raspberry Pi Imager, når kortet skrives (afsnit 2), så Pi'en kommer på nettet af sig selv. Opsætningsguiden køres derefter fra mobilen.

## 4. Prøv det med demoløbet

En ny installation har ét demoløb, *Demoløb (kan slettes)*, med tre testløbere (chip `DEMO01`–`DEMO03`).

1. Gå til **Aktivt løb**, og tryk **Start nu**.
2. Under **Test uden hardware** kan I "scanne" en testchip og se omgangene komme på skærmen.
3. Prøv også jeres rigtige læser: tildel jeres egen chip til en testløber under **Deltagere → 📡 Scan**, og hold den mod læseren.
4. Afslut demoløbet, og slet det, når I er trygge ved systemet.

> **Prøv løbstypen først:** sæt flueben i **🧪 Testløb** under *Nyt løb*, og vælg fx *60× hurtigere*. Så varer en backyard-time 1 minut, og du kan øve hele forløbet med rigtige armbånd på få minutter. Testløb sendes ikke til hjemmesiden.

## 5. Opret jeres eget løb

Under **Nyt løb** vælger I type, navn og eventuelt et planlagt starttidspunkt.

| I vil lave … | Vælg |
|---|---|
| Et backyard-løb efter de officielle regler | **Backyard Ultra (officiel)** |
| Et kortere backyard, fx træningsløb, med egen distance eller et fast antal omgange eller timer | **Backyard Ultra (custom)** |
| Et løb fra start til mål med fælles start, fx 5 km eller trail | **Alm. tidtagning (A til B)** |
| Flest omgange på 6, 12, 24 eller 48 timer | **Tidsbaseret** |
| Fælles mål, hvor alle omgange lægges sammen (fx "Årets rekord") | **Rekordløb** |
| Enkeltstart, bølgestart eller start på chip | **Intervalstart** |
| Canicross | Vælg A til B, tidsløb, rekordløb eller intervalstart, og sæt flueben i **Canicross** |

**Flere distancer i samme løb** (fx Nytårsløbet med 5, 10 og 15 km): vælg *Alm. tidtagning (A til B)*, og opret under **Distancer**:
1. **Ruterne** med navn, km og minimumstid, fx *Kort* 5 km / 15 min og *Lang* 10 km / 30 min.
2. **Distancerne**, der hver består af en eller flere ruter i træk, fx *5 km* = Kort, *10 km* = Lang og *15 km* = Kort → Lang. Ved 15 km er løberen i mål efter anden passage.
3. **Start + min** giver en distance sin egen start, fx 30 min efter løbets start. Startknappen starter løbet, og senere distancer starter selv.

Hver deltager vælger distance i deltagerlisten (eller kolonnen *Distance* i Excel). Stilling, resultatskærm, hjemmeside og CSV deles op pr. distance, og resultatskærmen skifter selv mellem distancerne hvert 15. sekund. Alle bruger de samme læsere. *Tidsbaseret* kan på samme måde have flere varigheder, fx 6 og 12 timer.

**Tæller:** vælg **📶 Armbånd**, når løberne har RFID-armbånd, eller **👆 Manuel**, når der ikke er læsere, fx til en lille træning. Ved *Manuel* viser **Aktivt løb** et felt pr. løber, og I trykker på feltet, hver gang løberen passerer (et nyt tryk inden for 3 sekunder tæller ikke, og **↶ Fortryd sidste tryk** fjerner det seneste). Der kan skiftes mellem de to når som helst, også under løbet, fx hvis en læser fejler. Resultatskærm og hjemmeside virker ens for begge.

Reglerne for hver type og backyards tidsvinduer står i [README](../README.md#løbstyper).

**Indtjekning:** Ved fælles start skal hver løber scanne sin chip inden for 30 minutter før start. Ellers tæller løberens læsninger ikke. Glemmer en løber det, kan en official trykke **✓ Tjek ind** i admin. Vinduet kan ændres pr. løb, og 0 slår det fra.

## 6. Deltagere og chips

**Excel-import (hurtigst ved mange deltagere)**
1. Under **Deltagere** henter I skabelonen.
2. Udfyld *Startnr, Navn, Køn, Klub* og eventuelt *Chip*. Ved canicross også *Hunde, Hund 1, Hund 2*.
3. Importér filen. CSV virker også, fx eksporteret fra jeres tilmeldingssystem.

**Tildel chips ved at scanne**
Tryk **📡 Scan** ud for en deltager, og hold armbåndet mod en læser. Så er chippen tildelt. Scanninger her tæller ikke i løbet. Det er nemt at gøre ved udleveringen af startnumre.

**Manuelt:** Tilføj enkelte deltagere med formularen, fx eftertilmeldinger på dagen.

## 7. På løbsdagen

**Før start**
- [ ] Tænd Pi'en i god tid. Under **Aktivt løb** står det, om uret er i orden (🕐 ✓). Står der en advarsel, så giv Pi'en internet et par minutter, inden løbet startes.
- [ ] Kør **⚙ Opsætning → Udstyrstest**. Den beder dig holde et armbånd mod læser 1 og læser 2, og den tester højttalere og resultatskærm. Scanninger under testen tæller ikke. Læserne vælges under **⚙ Opsætning → RFID-læsere**.
- [ ] Placér læserne ved målet, ca. 30 cm fra hinanden, og mærk dem "1" og "2". Har I to ens læsere, kendes de på USB-porten, så sæt dem i de samme porte hver gang (mærk gerne portene).
- [ ] Bed løberne scanne for at tjekke ind. Skærmen viser, hvor mange der er tjekket ind, fx 18/20.
- [ ] Hav en mobil med admin åben, så I kan rette undervejs.

**Under løbet**
- Løberen holder armbåndet mod læser 1. Bipper den ikke, bruges læser 2. Samme chip på begge læsere tæller kun én gang.
- **Fejler RFID**, kan I skifte **Tæller** til **👆 Manuel** og trykke på løbernes felter, eller registrere tider ud for løberen: **+ Nu** registrerer en passage med klokken lige nu, og **⏱ Tid** lader jer skrive tiden ind bagefter.
- Udgår en løber, trykker I **RTC** (udgået) ud for løberen. **DNS** er for en løber, der ikke startede, og **DSQ** for diskvalifikation.
- En forkert læsning kan ignoreres og gendannes igen i loggen. Intet slettes.
- I backyard viser **⚑ Til vurdering** læsninger i flagzonen, som en official skal godkende eller afvise.
- **Løberen kan se, om scanningen talte.** En stor bjælke på skærmen er grøn, når den talte, gul, når den ikke talte (med årsagen), og rød ved et ukendt armbånd. Med en **USB-højttaler** ved læseren kan det også høres: sæt den i, og tilføj den under **⚙ Opsætning → Moduler**. Tryk **▶ Test** for at høre den.

**Efter løbet**
- Afslut løbet, og hent resultaterne som **CSV** (åbnes i Excel).
- Tryk **🗄 Arkivér**, når I er færdige med løbet. Det forsvinder fra løbslisten, skærmen og hjemmesiden, men ligger under fanen **Arkiv**, hvor det kan ses, hentes som CSV og gendannes.
- Uden aktivt løb viser skærm og hjemmeside splash med jeres tekst. Skift teksten under **⚙ Opsætning → Udseende**, fx til næste løbs dato.
- Har I sat synkronisering op, sendes de endelige resultater til hjemmesiden automatisk.

> **Strømsvigt eller genstart midt i løbet?** Alle læsninger gemmes med det samme, og stillingen regnes ud fra dem. Tænd Pi'en igen, så er alt som før.

## 8. Resultater på nettet

RaceTimer kører fint helt uden internet. Har Pi'en net (fx via mobil-hotspot), kan den sende resultaterne videre under **⚙ Opsætning → Synkronisering**:

| Har I … | Vælg |
|---|---|
| Kun FTP-adgang til klubbens webhotel | **FTP-upload**: Pi'en laver selv en færdig resultatside |
| Et webhotel med PHP | **Egen hjemmeside (JSON)** med de færdige filer i [`webhotel/`](../webhotel/LÆS-MIG.md) |
| En lille Linux-server | **RaceTimer-spejlserver**: præcis samme live-skærm offentligt |

Vælg hvor ofte der sendes, fx hvert minut, og sæt flueben i *ved afslutning*. Detaljer i [README](../README.md#send-resultater-til-en-webserver).

**Adgang til admin hjemmefra eller over mobilnet:** se [fjernadgang.md](fjernadgang.md). Tailscale er det nemmeste og sikreste for en lille gruppe officials.

## 9. Opdateringer og sikkerhedskopi

**Opdateringer:** Under **Admin → ⚙ Opsætning → Opdatering** står den installerede version, og om der er en nyere. Tryk **Opdatér**, så hentes og installeres den nye version. Pi'en skal have internet.
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
| **Jeg kan ikke finde Pi'ens adresse** | Den står nederst på resultatskærmen. Prøv også `http://racetimer.local:8000/admin`. Mobil og Pi skal være på samme netværk. Uden skærm kan du se den i routerens eller mobil-hotspottets liste over forbundne enheder, eller bruge `http://racetimer:8000` via Tailscale. |
| **Sort skærm / resultatskærmen er lukket** | Genstart Pi'en, eller log ud og ind på skrivebordet. Kiosk-visningen starter af sig selv. |
| **Læseren reagerer ikke** | Tjek at den er valgt under *⚙ Opsætning → RFID-læsere*, og at prikken er grøn. Prøv en anden USB-port. Bipper læseren, men intet sker, så hold chippen mod læseren under **📡 Scan** for at se, om den læses. |
| **En løbers omgange tæller ikke** | Er løberen tjekket ind? Har løberen den rigtige chip? Er omgangen hurtigere end minimumstiden? Se loggen under *Seneste læsninger*. |
| **Uret går forkert** | Pi'en stiller selv uret, så snart den har internet. Pi 3/4 og Pi 5 uden RTC-batteri skal derfor have net et par minutter, *inden* løbet startes (mobil-hotspot er nok). Får den først net midt i løbet, hopper uret, og tiderne bliver forkerte. Admin advarer ved start. |
| **WiFi vil ikke forbinde** | Tjek koden. Fejlbeskeden står under **⚙ Opsætning → WiFi**. Mobil-hotspots skal være synlige, og iPhone skal have "Maksimer kompatibilitet" slået til. |
| **Glemt admin-kode** | En anden administrator kan sætte en ny under **⚙ Opsætning → Brugere**. Er der ingen, så kontakt udgiveren via GitHub. |
| **Opdateringen fejlede** | Pi'en kører videre på den gamle version. Loggen står under **⚙ Opsætning → Opdatering**. |

Finder I en fejl eller mangler en funktion, så opret en sag under **[Issues](https://github.com/peterskotte/racetimer/issues)** på GitHub. Skriv versionsnummeret (står under *Opdatering*), løbstype, og hvad der skete.
