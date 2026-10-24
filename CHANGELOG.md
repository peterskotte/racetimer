# Ændringer

Hver udgivelse har et afsnit her. Teksten under versionsnummeret vises i admin under **Opdatering → Hvad er nyt** og på GitHub-udgivelsen.

## [1.3.0] – 2026-10-24

**Til eksisterende installationer:** jeres admin-kode virker som før. Er den kortere end 10 tegn, skal den skiftes under *⚙ Opsætning → Brugere*, før det offentlige link kan bruges. Pi'er installeret før denne version kan ikke få Pi'ens kode skiftet fra RaceTimer – brug `passwd` på Pi'en.

**Sikkerhed**
- **Tilfældig førstegangskode:** nye installationer starter ikke længere med admin/admin. Hver Pi laver sin egen kode, som kun vises på Pi'ens egen skærm og ligger i `racetimer-kode.txt` på SD-kortet. Indtil guiden er kørt, kan andre på netværket altså ikke overtage den.
- **Pi'ens egen kode:** opsætningsguiden (og *⚙ Opsætning → Brugere*) skifter Pi-brugerens kendte standardkode `racetimer`, og derefter kræver `sudo` kode. Imaget kræver kode til `sudo` fra start. RaceTimer kan kun skifte koden én gang, fra standardkoden.
- **Stærkere koder:** admin-koder skal være mindst 10 tegn. Det offentlige link (Cloudflare) kan kun slås til, når alle administratorer har en kode på mindst 10 tegn, og kortere koder kan ikke bruges udefra. Brugere med kort kode er markeret under *Brugere*.
- Spærringen efter 5 forkerte login kunne omgås på det lokale net med en falsk Cloudflare-header. Headeren bruges nu kun, når den kommer fra tunnelen på Pi'en selv.
- Et forkert login frøs hele serveren i 1 sekund (også resultatskærmen), så mange forsøg kunne lamme den. Ventetiden blokerer nu kun det ene login-forsøg.
- Udviklerens signeringsnøgle kan ikke længere komme med i et lokalt bygget image, og rester af den fjernes fra Pi'en og dens gemte backups ved opdatering.

## [1.2.1] – 2026-10-24

**Rettet**
- **Splash på hjemmesiden:** splash-billede og logo nåede ikke frem, hvis de var sendt, før den nye `modtag.php` blev lagt op. `modtag.php` fortæller nu Pi'en, hvilke billeder den har, og Pi'en sender dem igen, hvis de mangler. **Upload den nye `modtag.php` til webhotellet** (husk at sætte jeres nøgle i den).
- **Opdateringer:** tjekket gav op med *timed out* på nogle netværk. Det prøver nu igen over IPv4, og fejlbeskeden siger, om Pi'en mangler internet, eller om det kun er GitHub, der ikke svarer.

**Ændret**
- Admin-adresse, IP og WiFi vises kun på Pi'ens egen skærm, ikke når resultatsiden åbnes på mobiler, via Tailscale eller via det offentlige link. Splash med jeres tekst vises stadig overalt.
- Teksten ved testløb beskriver den orange ramme på resultatskærmen.

## [1.2.0] – 2026-10-24

**Nyt**
- **Ny admin:** på computer ligger ⚙ Opsætning som panel i højre side med sektioner, der klappes ud, mens løbet vises til venstre. Admin er gjort mobilvenlig: på mobil og tablet er Opsætning en fane, og stillingen vises som kompakte kort.
- **Scan-besked:** stor grøn, gul eller rød bjælke på resultatskærmen, hver gang et armbånd scannes. Den viser, om scanningen talte, og hvorfor ikke (fx dublet, for tidligt, ikke tjekket ind). Slås til og fra under *Udseende*.
- **Moduler** (*⚙ Opsætning → Moduler*): eksterne enheder på USB, der reagerer på scanninger og nedtælling. Første modul er **USB-højttaler** med valgfri lyd pr. hændelse, lydstyrke og læser.
- **Udstyrstest** (*⚙ Opsætning → Udstyrstest*): beder om et armbånd mod læser 1 og læser 2 (og advarer om byttede USB-stik) og tester højttalere og resultatskærm. Scanninger under testen tæller ikke.
- **Testløb:** alle løbstyper kan køres som test med hurtigere tid (10×, 60×, 120×) og uden minimumstid, indtjekning eller dublet-filter. Testløb får orange ramme på skærmen og sendes aldrig til hjemmesiden.
- **Ur-tjek:** admin viser, om Pi'ens ur er stillet og passer med din mobil, og advarer, før løbet startes.
- RFID-læsere vælges nu under *⚙ Opsætning → RFID-læsere*, og *Aktivt løb* viser deres status.
- Linjen med Pi'ens adresse viser også, hvilket WiFi Pi'en er forbundet til.

**Rettet**
- Med to ens læsere (samme model) blev kun den ene vist. Ens læsere vises nu med deres USB-port. **Har du to ens læsere, så vælg primær og backup igen efter opdateringen.**
- Højttalerens startsignal spillede ikke ved hver ny backyard-time.

## [1.1.0] – 2026-10-23

- Arkiv: afsluttede løb kan arkiveres med **🗄 Arkivér**. De forsvinder fra løbslisten, men kan søges frem, ses, hentes som CSV, gendannes eller slettes under den nye fane **Arkiv**.
- Arkiverede løb vises ikke længere på hjemmesiden (JSON/PHP). Opdatér `modtag.php` og `index.php` på webhotellet.
- Egen tekst på splash-skærmen (**Udseende** og opsætningsguiden), fx "Næste løb: lørdag kl. 10".
- Uden aktivt løb viser hjemmesiden splash med billede og tekst. Det gælder PHP-siden, FTP-siden og spejlserveren. Pi'en sender selv logo og splash-billede, når de ændres.
- Ændringer af aktivt løb, arkiv og udseende sendes til hjemmesiden med det samme.

## [1.0.0] – 2026-10-23

Første offentlige udgivelse.

- RFID-tidtagning med 1–2 almindelige USB- eller serielle læsere (primær og backup, dubletfiltrering)
- Løbstyper: Backyard Ultra (officiel og custom: sidste mand, cutoff eller samlet tid), A til B, rekordløb, tidsløb (6/12/24/48 t) og intervalstart (interval, bølger eller chipstart)
- Backyard efter de officielle tidsvinduer: afgang, flagzone til official og målvindue; solo-runde
- Indtjekning før start, manuelle tider (omgang, sluttid, starttid), RTC/DNS/DSQ og canicross (1–2 hunde)
- Resultatskærm i dark mode med top 4, kiosk-tilstand, splash-skærm og 3-2-1-advarsler
- Admin med opsætningsguide, deltager-import fra Excel, chip-scanning og brugerstyring
- Udseende: klubnavn, logo og splash kan vælges
- Synkronisering til hjemmeside (RaceTimer-spejl, JSON/PHP eller FTP) med interval, manuelt og ved afslutning
- WiFi med op til 5 faste netværk (også brugernavn+kode som eduroam)
- Fjernadgang: Tailscale, Raspberry Pi Connect og offentligt link via Cloudflare
- Opdateringer fra admin med digital signatur og automatisk tilbagerulning
- Færdigt SD-kort-image til Raspberry Pi 3, 4 og 5 (64-bit)
