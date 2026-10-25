# Vis RaceTimer-resultater på din hjemmeside (JSON)

Mappen `racetimer/` her lægges op på webhotellet. Den indeholder to filer:

| Fil | Hvad den gør |
|---|---|
| `modtag.php` | Tager imod resultater fra Pi'en og gemmer dem i `data/` |
| `index.php` | Viser resultaterne som en side, med arkiv over tidligere løb |
| `tilmeld.php` | Tilmelding til løb, som er åbnet for tilmelding i RaceTimer (se nedenfor) |
| `logo.png` *(valgfri)* | Reserve-logo. Normalt sender Pi'en selv logoet fra **Admin → ⚙ Opsætning → Udseende** |
| `admin/index.php` | Gør, at `…/racetimer/admin` viderestiller til Pi'ens admin via fjernadgang (se nedenfor) |

Det kræver kun et almindeligt webhotel med PHP 7.4 eller nyere. Der skal ikke bruges en database.

## Opsætning

1. **Lav en nøgle.** Kør denne kommando på Mac'en, eller find selv på en lang, tilfældig tekst:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(24))"
```

2. **Sæt nøglen ind i `modtag.php`.** Ret linjen øverst:

   ```php
   $RACETIMER_KEY = 'din-nøgle-her';
   ```

3. **Upload mappen.** Læg `modtag.php` og `index.php` (og evt. jeres eget `logo.png`) i mappen `/racetimer/` på webhotellet med FTP eller webhotellets filhåndtering. Webserveren skal kunne skrive i mappen, fordi `modtag.php` opretter undermappen `data/` første gang.

4. **Opret destinationen i RaceTimer** under **Admin → ⚙ Opsætning → Synkronisering**:
   - **Type:** Egen hjemmeside (JSON)
   - **Adresse:** `https://ditdomæne.dk/racetimer/modtag.php` ← **med `modtag.php` til sidst**
   - **Nøgle:** samme nøgle som i trin 2
   - **Send automatisk** og **endelige resultater** efter ønske

5. Tryk **Send nu**. Status skal vise "Sendt …".

6. **Se resultaterne** på `https://ditdomæne.dk/racetimer/`. Siden opdaterer sig selv hvert 30. sekund, mens et løb kører.

**Hvad siden viser:**
- **Det løb, der vises på Pi'ens skærm**, med live- eller slutresultater.
- **Splash, når der ikke er et aktivt løb:** samme billede og tekst som på Pi'en. De vælges under **Admin → ⚙ Opsætning → Udseende**, og Pi'en sender selv logo og splash-billede (højst 4 MB), når de ændres.
- **Tidligere resultater** som en liste under splash eller tabellen.
- **Arkiverede løb vises ikke.** Arkiverer du et løb i RaceTimer, forsvinder det fra siden med det samme. Gendanner du det, kommer det tilbage.

> **Browser-udgaven** af RaceTimer (uden Pi) sender til den samme `modtag.php`. Det kræver den nyeste version, som tillader afsendelse fra en browser.

> Har du en ældre version af `modtag.php` og `index.php` på webhotellet, så upload de nye. Ellers vises arkiverede løb stadig, og splash mangler. Husk at sætte din nøgle i den nye `modtag.php`.

## Tilmelding på hjemmesiden

Med `tilmeld.php` kan løbere tilmelde sig direkte på hjemmesiden:

1. Læg `tilmeld.php` i samme mappe som `modtag.php`. Der skal ikke sættes noget op i filen.
2. I RaceTimer: **Deltagere → 🌐 Tilmelding på hjemmesiden** → sæt flueben i *Åben for tilmelding*, vælg frist m.m. og tryk **Gem tilmelding**. Pi'en sender med det samme løbets navn, dato, frist og distancer til hjemmesiden.
3. Tilmeldingssiden er `https://ditdomæne.dk/racetimer/tilmeld.php` (adressen står også i RaceTimer). `index.php` viser et link, så længe tilmeldingen er åben.
4. Pi'en henter nye tilmeldinger hvert minut, når den er på nettet, og opretter dem som deltagere (med startnummer, hvis det er valgt).

**Persondata:**
- Tilmeldingerne gemmes i `data/tilmeld-<løb>.php`. Filen starter med en PHP-linje, så webserveren svarer *404* og viser intet, hvis nogen prøver at åbne den. Den kan kun hentes af Pi'en med nøglen.
- E-mail og fødselsår vises aldrig på hjemmesiden. Deltagerlisten på tilmeldingssiden (kan slås fra) viser kun navn, klub og distance.
- Tilmeldingerne slettes automatisk fra webhotellet det valgte antal dage efter løbet (standard 30), og med det samme, hvis løbet slettes i RaceTimer.
- Formularen kræver samtykke og har værn mod spam: et skjult felt for robotter og højst 10 tilmeldinger i timen pr. forbindelse (IP-adresser gemmes kun som hash og kun i en time).
- Siden sender ikke mails. Hold hjemmesiden på **https**, så oplysningerne er krypteret undervejs.

Vil du vise resultaterne inde på en eksisterende side (fx i WordPress), kan du indsætte dem med en iframe:

```html
<iframe src="https://ditdomæne.dk/racetimer/" style="width:100%;height:900px;border:0"></iframe>
```

## Fejl i status i RaceTimer

| Status | Betyder | Løsning |
|---|---|---|
| `HTTP 403 … Forbidden` (Apache-side) | Adressen peger på mappen, ikke på scriptet | Tilføj `/modtag.php` til adressen |
| `HTTP 403 … "Forkert nøgle."` | Nøglen i RaceTimer og i `modtag.php` er forskellige | Skriv den samme nøgle begge steder |
| `HTTP 500 … "Nøglen i modtag.php er ikke sat"` | Trin 2 mangler | Ret `$RACETIMER_KEY` |
| `HTTP 500 … skriveadgang` | Webserveren må ikke skrive i mappen | Giv mappen skriveadgang (fx 755/775) i webhotellets filhåndtering |
| `HTTP 404` | Filen ligger et andet sted | Tjek stien i adressen |
| `HTTP 403` uden Apache-side, eller "Not Acceptable" | Webhotellets firewall (ModSecurity) blokerer | Bed webhotellet om at tillade POST til `/racetimer/modtag.php`, eller brug **FTP-upload** i stedet |

## Fjernadgang til admin via hjemmesiden

Pi'en kan åbne en krypteret tunnel ud til Cloudflare. Det kræver ingen konto, ingen DNS-ændring og ingen åbne porte, og det virker også på mobil-hotspot. Tunnelen får en tilfældig adresse (`https://….trycloudflare.com`), som skifter, når Pi'en genstarter. Pi'en melder derfor selv sin aktuelle adresse til `modtag.php`, og `admin/index.php` viderestiller dertil.

1. Upload **`modtag.php`** (ny version) og mappen **`admin/`** med `index.php` til `/racetimer/` på webhotellet.
2. På Pi'en: **Admin → ⚙ Opsætning → Brugere**. Skift koden for `admin`. Standardkoden kan ikke bruges udefra.
3. **Admin → ⚙ Opsætning → Synkronisering → (jeres JSON-destination) → Rediger**. Sæt flueben i **"Meld admin-adressen (fjernadgang)"**, og tryk **Gem**.
4. **Admin → ⚙ Opsætning → Synkronisering → Fjernadgang til admin → Slå fjernadgang til.** Efter få sekunder vises adressen.
5. Åbn **https://ditdomæne.dk/racetimer/admin** fra en hvilken som helst enhed.

Sikkerhed:
- Fjernadgang er slået fra som standard og kan kun slås fra på stævnets netværk, så man ikke lukker sig selv ude.
- Al trafik går over HTTPS.
- Login spærres i 15 min efter 5 forkerte forsøg.
- Er Pi'en slukket eller offline, viser siden, hvornår den sidst meldte sig.
