# RaceTimer i browseren: manuel tidtagning uden Pi

En billig udgave til **små løb med op til 12 deltagere**, fx klubtræning eller et lille motionsløb. Der skal **ingen Raspberry Pi, RFID-læsere eller andet udstyr** til, kun en bærbar, tablet eller mobil med en browser.

Race director **trykker på løberens felt**, hver gang løberen passerer. Resten er som i den rigtige RaceTimer: de samme løbstyper og regler, den samme resultatskærm med top 4, scan-besked og nedtælling, splash med jeres tekst, testløb, arkiv og resultater til hjemmesiden.

## Kom i gang

1. Åbn browser-udgaven på **[rebildtrail.dk/tidtagning](https://rebildtrail.dk/tidtagning/)**. Den følger med løbsportalens plugin (version 0.16 eller nyere), så enhver portal med pluginnet har den på `/tidtagning/`. Den kan også lægges på klubbens eget webhotel, se nederst.
2. **Opsæt løb:** vælg navn og løbstype. Indtjekning er slået fra som standard, undtagen i det officielle backyard. Sæt evt. flueben i *🧪 Testløb* for at øve.
3. **Deltagere:** vælg **antal løbere (1–12)**, og tryk **Lav felterne**. Felterne hedder Løber 1, Løber 2 … Ret navne og startnumre direkte i listen, eller lad dem stå. Du kan også tilføje løbere én ad gangen med køn, klub og hundenavne ved canicross.
4. **Løb → ▶ Start nu**, og tryk på løberens felt ved hver passage.
5. **🖥️ Resultatskærm** åbner resultatskærmen i et nyt vindue. Træk det over på en ekstern skærm eller et TV (HDMI), og sæt det i fuld skærm.

> **🎲 Prøv en løbstype:** under *Opsæt løb* opretter **🎲 Opret demoløb** et færdigt testløb med op til 12 tilfældige løbere (også canicross med hunde) i hurtig tid, fx en backyard-runde pr. minut. Tryk selv på felterne, eller sæt flueben i *Simulerede løbere*, så passagerne kommer af sig selv. Simuleringen kan stoppes og startes igen med knappen i løbets top. Demoløb sendes aldrig til hjemmesiden eller portalen, og **Slet alle demoløb** fjerner dem igen.

## Under løbet

| Handling | Sådan |
|---|---|
| Felterne | Fylder skærmen: få løbere giver store felter (fx 4 løbere = 2×2), 12 løbere giver 4×3 (på en mobil 2–3 kolonner). |
| Passage | Tryk på løberens felt. Feltet blinker grønt (*✓ Omgang 3*) eller gult med årsagen (fx *For tidligt*). |
| Dobbelttryk | Et nyt tryk på samme løber inden for 3 sekunder tæller ikke (*Allerede registreret*). |
| Fortryd | **↶ Fortryd sidste** fjerner det seneste tryk, der talte. |
| Glemt tryk | **⋯ → ⏱ Indtast tid**: løbstid fra start (fx `1:23:45`) eller klokkeslæt (`kl 14:05:30`). |
| Udgået, ikke startet, diskvalificeret | **⋯ → RTC / DNS / DSQ** |
| Resultater | **⬇ CSV**, eller arkivér løbet og hent det senere under **Arkiv** |

## Hvor gemmes data?

**Alt gemmes kun i browseren på den enhed, du bruger** (localStorage). Det overlever genindlæsning, nedlukning og strømsvigt, men:
- **Ryd ikke browserdata** (cookies og webstedsdata) midt i en sæson.
- Brug **⚙ Indstillinger → Sikkerhedskopi** før og efter løb. Filen kan indlæses igen på samme eller en anden enhed.
- Private vinduer (inkognito) gemmer intet, når de lukkes.

Når siden først er åbnet, **virker den også uden internet**. Kun afsendelse til hjemmesiden kræver net.

## Resultater på hjemmesiden

Under **⚙ Indstillinger → Hjemmeside** skriver du adressen til `modtag.php` og nøglen. Det er de samme filer som til RaceTimer på Pi'en, se [webhotel/LÆS-MIG.md](../webhotel/LÆS-MIG.md). Browser-udgaven kræver den **nyeste** `modtag.php`, som tillader afsendelse fra en browser. Uden aktivt løb viser hjemmesiden jeres splash med tekst. Testløb sendes aldrig.

FTP og spejlserver kan ikke bruges fra en browser.

## Løbsportal (fx rebildtrail.dk)

Browser-udgaven kan forbindes til en løbsportal med pluginet RaceTimer Portal, ligesom RaceTimer på Pi'en:

1. Opret løbet på portalen, og lav en **forbindelseskode** under *For arrangører → Mine RaceTimere*.
2. Opret løbet her under **Opsæt løb**. Gå til **⚙ Indstillinger → 🌍 Løbsportal**, skriv portalens adresse og koden, og tryk **Forbind**.
3. Vælg løbet på portalen, og tryk **Kobl**. De tilmeldte hentes med det samme. Felter med *Løber N* uden tider bliver udfyldt først, og der er plads til 12. Indtil start hentes nye tilmeldte hvert minut, og **⬇ Hent tilmeldte nu** henter med det samme.
4. Under løbet sendes resultaterne til portalen hvert 15. sekund (med omgangstider), og de endelige resultater, når løbet afsluttes. Uden net prøver den igen, når der er forbindelse.

Løbere, der har valgt at være anonyme på portalen, står med navn her, men som *Anonym løber* på portalen. Testløb sendes aldrig. Portalen skal have version 0.10 eller nyere (den tillader kald fra en browser).

## Forskelle fra RaceTimer på Pi'en

| | Browser | Raspberry Pi |
|---|---|---|
| Tidtagning | RD trykker manuelt | Armbånd (RFID) eller manuelle tryk, valgt pr. løb |
| Deltagere | Op til 12 | Ubegrænset, med Excel-import |
| Resultatskærm | Ekstra vindue på samme enhed | Pi'ens skærm og alle enheder på netværket |
| Data | I browseren på én enhed | På Pi'en, med flere administratorer |
| Løbsportal | ✓ Tilmeldte (op til 12) og live-resultater | ✓ Tilmeldte, live-resultater, overførsel af løb og skabeloner |
| Højttaler, LED, læsere, WiFi, fjernadgang, opdateringer | – | ✓ |

## Læg den på jeres egen hjemmeside

```bash
sh tools/build-web.sh
```

Upload indholdet af mappen `site/` til en mappe på webhotellet, fx `/racetimer-lite/`. Det er almindelige filer, så der skal ikke installeres noget. Den skal ligge på `https://`, ellers virker offline-funktionen ikke.
