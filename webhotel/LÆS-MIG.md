# Vis RaceTimer-resultater på din hjemmeside (JSON)

Mappen `racetimer/` her lægges op på webhotellet. Den indeholder to filer:

| Fil | Hvad den gør |
|---|---|
| `modtag.php` | Tager imod resultater fra Pi'en og gemmer dem i `data/` |
| `index.php` | Viser resultaterne som en side, med arkiv over tidligere løb |
| `logo.png` *(valgfri)* | Jeres logo øverst på siden – uden den vises klubnavnet som tekst |
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

4. **Opret destinationen i RaceTimer** under **Admin → Synkronisering**:
   - **Type:** Egen hjemmeside (JSON)
   - **Adresse:** `https://ditdomæne.dk/racetimer/modtag.php` ← **med `modtag.php` til sidst**
   - **Nøgle:** samme nøgle som i trin 2
   - **Send automatisk** og **endelige resultater** efter ønske

5. Tryk **Send nu**. Status skal vise "Sendt …".

6. **Se resultaterne** på `https://ditdomæne.dk/racetimer/`. Siden opdaterer sig selv hvert 30. sekund, mens et løb kører.

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
2. På Pi'en: **Admin → Brugerstyring**. Skift koden for `admin`. Standardkoden kan ikke bruges udefra.
3. **Admin → Synkronisering → (jeres JSON-destination) → Rediger**. Sæt flueben i **"Meld admin-adressen (fjernadgang)"**, og tryk **Gem**.
4. **Admin → Synkronisering → Fjernadgang til admin → Slå fjernadgang til.** Efter få sekunder vises adressen.
5. Åbn **https://ditdomæne.dk/racetimer/admin** fra en hvilken som helst enhed.

Sikkerhed:
- Fjernadgang er slået fra som standard og kan kun slås fra på stævnets netværk, så man ikke lukker sig selv ude.
- Al trafik går over HTTPS.
- Login spærres i 15 min efter 5 forkerte forsøg.
- Er Pi'en slukket eller offline, viser siden, hvornår den sidst meldte sig.
