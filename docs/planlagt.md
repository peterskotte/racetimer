# Planlagt til næste opdateringer

Noter fra Peter, 24. oktober 2026. Intet af dette er bygget endnu.

## 1. Visuel nedtælling ved tidsbegrænsede løb ✅ bygget (25.10.2026)

Ved løb med en fast varighed skal skærmen vise **hvor meget tid der er tilbage** med en bar, en cirkel eller lignende, så det kan aflæses på afstand.

Gælder:
- **Tidsbaseret** (6/12/24/48 t)
- **Backyard custom** med *samlet tid*
- Evt. en lille ring om hver backyard-yard (tid til næste start)

Idéer:
- **Stor nedtæller (countdown) `00:00:00`**, der tæller ned til løbet slutter. Kan stå alene eller sammen med ringen/baren.
- Stor fremskridtsring eller -bar ved siden af *Tid tilbage* i toppen af resultatskærmen.
- Farven skifter mod slutningen, fx orange de sidste 10 % og rød det sidste kvarter.
- Samme visning på hjemmesiden (PHP/FTP/spejl) og i admin.

## 2. Browser-udgave til små løb (uden Pi og RFID) ✅ bygget (25.10.2026) – se [browser.md](browser.md)

En **billig udgave, der kun kræver en browser**: ingen Raspberry Pi, ingen RFID-læsere eller andet hardware. Til klubber og enkeltpersoner med små løb.

**Besluttet (Peter, 24.10.2026):**
- **Kun en browser-version.** Den åbnes som en almindelig hjemmeside på en bærbar, tablet eller mobil. Der skal ikke installeres noget.
- **Kun race director tager tid, manuelt:** op til **12 deltagere**, hver med et **stort felt/knap**. RD trykker på feltet, hver gang løberen passerer. Fortryd-knap og mulighed for at rette en tid.
- **Resten er som i den rigtige RaceTimer:** løbstyper og regler, resultatskærm (dark mode, top 4, scan-besked), splash med egen tekst, udseende/logo, testløb, arkiv og resultater til hjemmesiden.

**Konsekvenser, der skal løses ved bygningen:**
- **Løbsmotoren skal også findes i JavaScript.** Den kører i dag i Python på Pi'en, og de samme tests skal køres mod begge versioner, så reglerne ikke glider fra hinanden.
- **Data gemmes i browseren** (IndexedDB) og overlever genindlæsning og strømsvigt. Der skal være eksport/import af en sikkerhedskopi, og en advarsel om ikke at rydde browserdata midt i et løb.
- **Resultatskærm:** et ekstra vindue på samme enhed (fx på en ekstern skærm eller et TV via HDMI), som opdateres live fra RD-vinduet.
- **Resultater til hjemmesiden:** via den eksisterende `modtag.php` (JSON), som så skal tillade kald fra browseren (CORS). FTP kan ikke bruges fra en browser.
- **Hosting:** en statisk side, fx på GitHub Pages eller klubbens eget webhotel, der også virker offline, når den først er åbnet (PWA).
- **Ikke med:** RFID-læsere, moduler/højttaler, WiFi, fjernadgang og opdateringsknap, som alle kræver Pi'en.
