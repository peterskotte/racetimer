# Planlagt til næste opdateringer

Noter fra Peter, 24. oktober 2026. Intet af dette er bygget endnu.

## 1. Visuel nedtælling ved tidsbegrænsede løb

Ved løb med en fast varighed skal skærmen vise **hvor meget tid der er tilbage** med en bar, en cirkel eller lignende, så det kan aflæses på afstand.

Gælder:
- **Tidsbaseret** (6/12/24/48 t)
- **Backyard custom** med *samlet tid*
- Evt. en lille ring om hver backyard-yard (tid til næste start)

Idéer:
- Stor fremskridtsring eller -bar ved siden af *Tid tilbage* i toppen af resultatskærmen.
- Farven skifter mod slutningen, fx orange de sidste 10 % og rød det sidste kvarter.
- Samme visning på hjemmesiden (PHP/FTP/spejl) og i admin.

## 2. Webbaseret udgave til små løb (uden Pi og RFID)

En enkel udgave til klubber og enkeltpersoner, der ikke har en Raspberry Pi med RFID-læsere.

- **Op til 12 deltagere**, der hver har et **stort felt/knap** på race director-siden.
- RD **trykker på løberens felt**, hver gang løberen passerer. Det registrerer en omgang eller målpassage.
- Fortryd-knap og mulighed for at rette en tid.
- Samme løbstyper og regler som den rigtige RaceTimer, hvor det giver mening, fx backyard, tidsløb og A til B.

Åbne spørgsmål:
- **Hvor skal den køre?** Kun i browseren, så den også virker offline (fx som en side på GitHub Pages), eller på klubbens webhotel (PHP)?
- **Flere enheder:** skal en tilskuerskærm eller mobil kunne følge med live, eller er én enhed nok?
- **Resultater:** eksport som CSV og/eller upload til hjemmesiden som i den rigtige udgave?
- **Genbrug:** løbsmotoren findes i Python på Pi'en. Den webbaserede udgave skal enten have sin egen JavaScript-version eller køre en server.
