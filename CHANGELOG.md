# Ændringer

Hver udgivelse har et afsnit her. Teksten under versionsnummeret vises i admin under **Opdatering → Hvad er nyt** og på GitHub-udgivelsen.

## [Ikke udgivet]

**Nyt**
- **Teaser for planlagte løb:** et løb med planlagt starttidspunkt viser ikke længere deltagerlisten på skærm og hjemmeside, før indtjekningen åbner. I stedet vises splash med en teaser: navn, dato, nedtælling, antal tilmeldte og distancer. Startlisten kommer frem, når indtjekningen åbner (eller 30 min før start uden indtjekning), og navnene sendes heller ikke til hjemmesiden før. Admin viser, hvornår det sker. Upload den nye `index.php`.
- **Vejledningen har screenshots** af admin, resultatskærm og hjemmeside.

## [1.4.1] – 2026-10-25

**Til eksisterende installationer:** upload den nye `mailer.php` og de nye `tilmeld.php` og `modtag.php` til webhotellet (husk jeres nøgle i `modtag.php`). Sæt derefter klubbens mailkonto op under *⚙ Opsætning → Synkronisering*, og send en testmail.

**Nyt**
- **Mailkonto til bekræftelser:** under *⚙ Opsætning → Synkronisering → ✉ Mail til tilmeldinger* kan klubbens mailkonto (SMTP, fx Simply, One.com eller Gmail med app-adgangskode) sættes op, så bekræftelserne kommer frem i stedet for at blive afvist eller havne i spam. **✉ Send testmail** viser med det samme, om det virker, eller hvorfor ikke (fx forkert adgangskode). Pi'en sender opsætningen til hjemmesiden, som gemmer den i en fil, der ikke kan læses udefra; adgangskoden vises aldrig i admin. Kræver den nye `mailer.php` og `modtag.php` på webhotellet.
- **Bekræftelse på e-mail:** tilmeldte får en mail med løb, distance, startnummer og jeres tekst (fx pris og betaling). Mailen sendes fra webhotellet (`noreply@` jeres domæne), og svar går til klubbens adresse, som vælges i RaceTimer. Kvitteringen på siden fortæller, om mailen blev sendt. Kan slås fra.

**Ændret**
- **Startnummer ved online tilmelding:** hjemmesiden giver startnummeret i selve tilmeldingen og viser det på kvitteringen og deltagerlisten. Pi'en sender de numre, den allerede har brugt, så de ikke gives igen, og beholder hjemmesidens nummer, når tilmeldingen hentes. Er nummeret alligevel optaget (fx givet manuelt på Pi'en i samme minut), får løberen et nyt, og admin får en advarsel. Upload den nye `tilmeld.php`.

## [1.4.0] – 2026-10-25

**Til eksisterende installationer:** upload `tilmeld.php` og de nye `index.php` og `modtag.php` til webhotellet (husk jeres nøgle i `modtag.php`). Uden dem virker resultaterne som før, men hjemmesiden viser ikke distancer, nedtæller og tilmelding.

**Nyt**
- **Tilmelding på hjemmesiden:** åbn et løb for tilmelding under *Deltagere*. Den nye `tilmeld.php` på webhotellet viser formularen (navn, køn, fødselsår, klub, e-mail, distance og samtykke) og en valgfri liste over tilmeldte. Pi'en henter nye tilmeldinger hvert minut og opretter dem som deltagere, evt. med startnummer. Persondata kan ikke læses udefra på webhotellet, e-mail og fødselsår vises aldrig offentligt, og tilmeldingerne slettes automatisk efter løbet. **Upload `tilmeld.php` og de nye `modtag.php` og `index.php`** (husk nøglen i `modtag.php`).
- **Aldersklasser:** 5- eller 10-års klasser ud fra køn og fødselsår, i resultater og CSV. Deltagere har fået felterne fødselsår og e-mail (også i Excel-importen).
- **Byg selv og skabeloner:** *Nyt løb* kan starte fra en guide, der ud fra et par spørgsmål vælger løbstype og indstillinger, eller fra en skabelon. Der er indbyggede eksempler (Nytårsløb 5/10/15 km, 6- og 12-timersløb, trailløb med cutoff, klubtræning uden armbånd), og et løbs opsætning kan gemmes som egen skabelon, hentes som fil og importeres på en anden Pi.
- **Cutoff:** A til B og intervalstart kan have en maksimal tid – også pr. distance. Ikke i mål inden da = *DNF · over tid*. Virker også i browser-udgaven.
- **Flere distancer i samme løb:** A til B og tidsbaserede løb kan have flere distancer med fælles læsere, fx Nytårsløbet med 5, 10 og 15 km. Opret ruter (km og minimumstid) og saml distancerne af dem – en lang distance kan være flere ruter i træk (kort + lang = 15 km, i mål efter 2. passage). Hver distance kan have sin egen start, og tidsløb kan have hver sin varighed (fx 6 og 12 timer). Deltagere vælger distance (også i Excel), og stilling, resultatskærm, hjemmeside, FTP-side og CSV deles op pr. distance. Upload den nye `index.php` til webhotellet.
- **Manuel tidtagning på Pi'en:** hvert løb har en **Tæller**: *📶 Armbånd* eller *👆 Manuel*. Vælg den, når løbet oprettes, og skift når som helst, også under løbet. Ved *Manuel* trykker race director på løberens felt i admin ved hver passage, med samme regler, resultatskærm og hjemmeside som med armbånd. Dobbelttryk inden for 3 sek. tæller ikke, og sidste tryk kan fortrydes.
- **Browser-udgave til små løb uden Pi og RFID** ([docs/browser.md](docs/browser.md)): race director trykker på løberens felt. Vælg antal løbere (1–12) med ét tryk, og felterne fylder skærmen, så få løbere giver store felter. Samme løbstyper, regler, resultatskærm, splash, testløb, arkiv og hjemmeside som på Pi'en. Data gemmes i browseren med sikkerhedskopi, og den virker offline. Løbsmotoren findes nu også i JavaScript, og en test tjekker, at begge regner ens.
- `modtag.php` tillader afsendelse fra browser-udgaven (CORS). Nøglen kræves stadig.
- Resultatskærmen kan få sine data fra et andet browservindue (`display.html?local=1`).
- **Nedtæller med ring:** tidsløb og custom backyard med samlet tid viser *Tid tilbage* som en stor `00:00:00`-nedtæller med en ring, der tømmes. Backyard viser det samme for tiden til næste start. Ringen bliver orange de sidste 10 % og rød det sidste kvarter. Nedtælleren vises også på hjemmesiden (PHP og FTP) og spejlserveren. Upload den nye `index.php` til webhotellet.

**Rettet**
- Teksten under *Offentligt link* nævnte stadig admin/admin. Den siger nu, at login udefra kræver en kode på mindst 10 tegn.
- Løbsmotoren lægger tider og km sammen ens i alle Python-versioner og i browser-udgaven (testene fejlede på Python 3.11).

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
