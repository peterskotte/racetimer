# Ændringer

Hver udgivelse har et afsnit her. Teksten under versionsnummeret vises i admin under **Opdatering → Hvad er nyt** og på GitHub-udgivelsen.

## [Ikke udgivet]

**Sikkerhed**
- **Eduroam og andre netværk med brugernavn (WPA2-Enterprise):** Pi'en tjekker nu netværkets servercertifikat mod et domæne (udfyldes fra brugernavnet, fx navn@aau.dk → aau.dk, eller skrives i det nye felt). Før kunne en falsk adgang med samme navn opsnappe brugernavn og kode. Netværk, der allerede er gemt, får tjekket, næste gang WiFi-listen gemmes – gem den igen efter opdateringen.
- **Ingen ukrypteret afsendelse over internettet:** destinationer og løbsportaler skal bruge https:// (og FTP ftps://). http:// og ftp:// virker kun på det lokale net (fx en spejlserver i klubhuset), så nøgler, koder og tilmeldinger aldrig sendes i klartekst.
- **Skift af kode logger andre ud:** når en admin-kode skiftes, lukkes alle andre login-sessioner for brugeren.
- **Resultat-CSV:** navne og klubber, der starter med = + - @, får et ' foran, så Excel ikke tolker dem som formler.
- **E-mail slettes på Pi'en efter løbet:** når slettefristen efter løbet er nået (standard 30 dage), slettes deltagernes e-mail – og fødselsår, hvis løbet ikke har aldersklasser. Navne og tider bliver.
- **Opdateringshjælperen** (kører som root) følger ikke længere symlinks, når den skriver sin statusfil.
- **Advarsel ved WiFi uden kode:** er Pi'en på et åbent WiFi, viser admin en advarsel, fordi koden ellers kan aflures (admin er http på det lokale net). Brug et WiFi med kode, kabel eller Tailscale.
- **Sikkerhedsheadere:** browseren må ikke gætte filtyper, og admin kan ikke lægges i en ramme på en anden side. Resultatskærmen kan stadig indlejres.
- **Tilmelding på hjemmesiden (tilmeld.php):** navne med links eller adresser afvises, og der sendes højst 100 bekræftelsesmails i timen i alt, så siden ikke kan bruges til at sende spam fra klubbens mail. Upload den nye `tilmeld.php` til webhotellet.

**Rettet**
- **Ens RFID-læsere i andre USB-porte:** to ens læsere kendes på USB-porten. Flyttes de, fx til en USB-hub, blinkede statuslampen rød ×1, selvom begge sad i. Nu finder RaceTimer dem selv i de nye porte (samme model, læser 1 i den første port), og klar-tjekket og admin viser, at de er flyttet. Sættes de tilbage, bruges de gemte porte igen.
- Hver læser stod to gange i listen over læsere på Pi 5 (samme port har to navne).

**Nyt**
- **🎲 Demoløb af alle løbstyper:** under *Nyt løb* oprettes et færdigt testløb af en valgfri løbstype med tilfældige deltagere (også canicross med hunde). Simulerede løbere scanner af sig selv i hurtig tid, så man kan se tidtagning, stilling og skærm uden læsere, armbånd eller tilmelding. Backyard ender altid med én vinder. Chipstart og callout virker også. Demoløb sendes aldrig ud og kan slettes alle på én gang.
- **Ændringer fra løbsportalen:** rettede og afmeldte tilmeldinger hentes også (afmeldte uden tider fjernes), og **⟳ Opdater** overfører navn, starttid og nye distancer til et løb, der allerede er hentet. Deltagere, som arrangøren tilføjer eller importerer på portalen, hentes som alle andre.
- **⇩ Hent løb fra portalen:** løb med flueben i *Må hentes til RaceTimer* på løbsportalen kan hentes til RaceTimer med ét tryk. Navn, starttid og distancer (med starttider) oprettes, løbet kobles, og de tilmeldte hentes.
- **Chipstart i A til B:** hver løbers tid starter ved første scanning efter start og stopper ved næste scanning efter minimumstiden. Virker også med flere distancer og ruter i træk (fx Nytårsløbet), og i browser-udgaven (første tryk).
- **Browser-udgaven og løbsportalen:** RaceTimer i browseren (iPad, iPhone, Android) kan forbindes til en løbsportal med en kode, koble et løb, hente de tilmeldte og sende live-resultater og endelige resultater. Anonyme løbere forbliver anonyme på portalen.
- **Omgangstider sendes med:** hjemmesider og løbsportalen får hver løbers omgangstider (og tiden for hver rute ved flere ruter i træk). På løbsportalen kan man folde dem ud ved hver løber, og Excel-filen har en kolonne pr. omgang.
- **Lampe ved læseren (blink(1) mk3):** en lille USB-lampe ved hver RFID-læser blinker grønt, gult eller rødt, så løberen kan se, om scanningen talte. Med to læsere vælges, hvilken læser hver lampe sidder ved. Lamperne tilføjes af sig selv under Moduler.
- **📣 Callout:** kan slås til i A til B, intervalstart, tidsløb og rekordløb. Løberen scanner sin chip ved start, løbslederen tæller ned fra 15 sekunder, og løberens tid starter ved 0. Nedtællingen vises stort i admin, højttaleren bipper de sidste sekunder, og statuslampen lyser grønt ved start.
- **Sådan scannes chippen:** indstillingerne for hvert løb viser, hvornår løberne skal scanne (ved start, ved hver omgang, i mål osv.), ud fra løbstype og indstillinger.
- **Pi'ens skærm slukker af sig selv:** efter 5 minutter uden aktivitet slukker en tilsluttet skærm helt (også baggrundslyset). Et tryk på skærmen, et armbånd ved læseren eller admin-armbåndet tænder den igen. Det første tryk vækker kun skærmen og trykker ikke på noget. Mens et løb kører, slukker skærmen ikke. Tiden kan ændres eller slås fra under Opsætning → Udseende → Pi'ens skærm.
- **Løbsportal (fx rebildtrail.dk):** Pi'en kan forbindes til en WordPress-side med pluginet RaceTimer Portal under ⚙ Opsætning → Synkronisering → Løbsportal, med en kode fra portalen. Et løb kobles under Deltagere → 🌐 Tilmelding → Løbsportal. Så hentes de tilmeldte automatisk og får startnummer på Pi'en, og resultaterne vises live på portalen. Løb, der allerede findes på Pi'en, kan overføres, og afholdte løb får de endelige resultater med. Skabelonerne sendes også, så løb kan oprettes ud fra dem på portalen. Portalen får aldrig Pi'ens mailopsætning.
- **Vejledningen som HTML og PDF** til klubbens webhotel (`webhotel/racetimer/vejledning/`), bygget fra `docs/vejledning.md` med `tools/build-guide.py`. Alle screenshots er taget igen, og der er nye af klar-tjek, offline-tilstand og admin-armbånd.
- **Klar-tjek ved opstart:** har Pi'en en skærm, starter den på et klar-tjek i stedet for resultatskærmen. Netværk, ur, RFID-læsere, moduler, hjemmeside og løbet vises med grøn, gul eller rød, og de kan rettes direkte fra touchskærmen eller et tastatur: vælg WiFi (med skærmtastatur til koden), vælg og test læsere, tilføj og test højttaler og statuslampe, se hjemmesidens seneste afsendelse eller fejl og tryk *Send nu*, og vælg løbet. **START** skifter til splash eller det aktive løb, og ⚙ på resultatskærmen fører tilbage. En ny Pi viser førstegangskoden her. Klar-tjekket virker kun på Pi'ens egen skærm (ikke via netværket eller fjernadgang).
- **Offline-tilstand** i klar-tjekket: til løb uden WiFi. "Intet netværk" er så ikke en advarsel, og statuslampen lyser fast orange, når læsere, database og ur er i orden. Resultaterne sendes, når der er net igen.
- **Uret kan stilles manuelt** i klar-tjekket – kun i offline-tilstand og ikke mens et løb kører. Med net stilles uret automatisk.
- **Admin-armbånd:** scan et admin-armbånd ved læseren for at skifte Pi'ens skærm til klar-tjekket og tilbage igen. Sættes op under *Opsætning → Brugere*. Armbåndet tæller aldrig i et løb og kan ikke tildeles en løber; statuslampen blinker blåt.

**Ændret**
- **Splash fylder hele browservinduet** på hjemmesiden (`index.php` og FTP-siden), også på mobil. Listen over tidligere resultater ligger nedenunder.

**Nyt**
- **Statuslampe (Luxafor Flag):** sæt lampen i USB, så viser den Pi'ens tilstand – også uden skærm og net. Hvid = Pi'en starter, blå pulserende = RaceTimer starter, blåt blink = søger netværk, grøn = klar. Ved problemer blinker den en kode (N blink og pause): gul ×2 intet netværk, gul ×3 uret er ikke stillet, rød ×1 læser ikke tilsluttet, rød ×4 databasefejl, rød ×5 RaceTimer kunne ikke starte. Lilla ved nedlukning, slukket når strømmen kan fjernes. Forsiden blinker grønt/gult/rødt ved scanninger. Lampen tilføjes af sig selv under *⚙ Opsætning → Moduler*. Se [docs/statuslampe.md](docs/statuslampe.md).
- **Tilmelding vælges pr. løb:** når et løb oprettes (og senere under *Deltagere*), vælges *Ingen tilmelding*, *Formular på hjemmesiden* eller *Link andetsteds* (fx en Facebook-begivenhed).
  - **Formular:** vælg for køn, fødselsår, klub og e-mail, om feltet skal udfyldes, er valgfrit eller ikke er med. Navn er altid med, og distance, når løbet har flere. Samtykketeksten på siden følger de valgte felter.
  - **Link:** linket (og en valgfri linktekst) vises på hjemmesiden og som knap i teaseren om løbet, indtil løbet starter eller fristen er nået. Resultatskærmen skriver, hvor man tilmelder sig. Går linket til Facebook, vises Facebooks logo, ellers 📝.
  - **Aktivt løb** viser løbets tilmelding med en *ret*-knap, der hopper direkte til indstillingen under Deltagere.
  - Upload den nye `index.php` og `tilmeld.php`.

## [1.4.2] – 2026-10-26

**Til eksisterende installationer:** upload den nye `index.php` til webhotellet, så hjemmesiden viser teaseren.

**Nyt**
- **Teaser for planlagte løb:** et løb med planlagt starttidspunkt viser ikke længere deltagerlisten på skærm og hjemmeside, før indtjekningen åbner. I stedet vises splash med en teaser: navn, dato, nedtælling, antal tilmeldte og distancer. Teaseren står i stedet for jeres splash-tekst (fx *Venter på næste løb*). Startlisten kommer frem, når indtjekningen åbner (eller 30 min før start uden indtjekning), og navnene sendes heller ikke til hjemmesiden før. Admin viser, hvornår det sker. Upload den nye `index.php`.
- **Tidsløbets varighed i headeren:** resultatskærm, admin og hjemmeside viser fx *Tidsbaseret · 6 timer* i stedet for *Tidsbaseret (6/12/24/48 t)*.
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
