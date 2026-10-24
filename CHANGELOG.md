# Ændringer

Hver udgivelse har et afsnit her. Teksten under versionsnummeret vises i admin under **Opdatering → Hvad er nyt** og på GitHub-udgivelsen.

## [Ikke udgivet]

- **Rettet:** med to ens læsere (samme model) blev kun den ene vist i læserlisten. Ens læsere vises nu med deres USB-port, og samme læser kan ikke vælges som både primær og backup.
- **Scan-besked:** stor grøn, gul eller rød bjælke på resultatskærmen, hver gang et armbånd scannes. Den viser, om scanningen talte, og hvorfor ikke. Slås til og fra under *Udseende*.
- **Moduler** (*⚙ Opsætning → Moduler*): eksterne enheder på USB, der reagerer på scanninger og nedtælling. Første modul er **USB-højttaler** med valgfri lyd pr. hændelse, lydstyrke og læser. Moduler påvirker aldrig tidtagningen.
- Hver læsning vurderes nu (talt, ignoreret med årsag, eller ukendt). Det bruges af scan-beskeden og modulerne.
- Menuen i admin er samlet: løbsfanerne (*Aktivt løb, Nyt løb, Deltagere, Arkiv*) står forrest, og resten ligger under **⚙ Opsætning**, grupperet i *Skærm og web*, *Udstyr* (RFID-læsere og moduler), *Netværk* og *System*. Læserne vælges nu under *⚙ Opsætning → RFID-læsere*, og *Aktivt løb* viser deres status. Menuen og toppen af siden passer nu også på mobil.
- Ur-tjek: admin viser, om Pi'ens ur er stillet via internettet, og om det passer med din mobil/computer. Går uret forkert, eller er det ikke stillet siden opstart, advares der tydeligt, når løbet startes.

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
