# Fjernadgang til Pi'en

Under **Admin → ⚙ Opsætning → Fjernadgang** er der tre måder at nå Pi'en på, når du ikke er på stævnets netværk. Alle tre åbner forbindelsen **ud** fra Pi'en. Du skal ikke åbne porte i routeren, og det virker også på mobil-hotspot.

Alle tre installeres af opdateringsscriptet ("Opdater Pi.command"), men de er slået fra, indtil du logger ind. Pi'en skal have internet under opdateringen.

| | Hvem kan komme ind | Adresse | Til |
|---|---|---|---|
| **🔒 Tailscale** (anbefalet) | Kun dine egne enheder | Fast: `http://racetimer:8000/admin` | Admin under løbet |
| **🖥️ Raspberry Pi Connect** | Kun din Raspberry Pi-konto | connect.raspberrypi.com | Pi'ens skærm og terminal (opdateringer, fejlfinding) |
| **🌍 Cloudflare** | Alle med link + login | Skifter, men `ditdomæne.dk/racetimer/admin` følger med | Adgang fra en vilkårlig enhed |

---

## 🔒 Tailscale – privat

Pi'en kommer på dit private Tailscale-netværk, som er krypteret med WireGuard. Admin er **ikke** synlig på internettet. Kun dine egne enheder med Tailscale-appen kan nå den.

**Første gang:**
1. Opret en gratis konto på **tailscale.com**. Du kan logge ind med Google, Microsoft eller Apple.
2. Installér **Tailscale-appen** på din mobil og/eller Mac, og log ind med samme konto.
3. På Pi'en: **Admin → ⚙ Opsætning → Fjernadgang → Tailscale → Log ind / slå til**. Der vises et link.
4. Åbn linket, log ind og godkend Pi'en.
5. Efter få sekunder står der **Forbundet** og Pi'ens faste adresser:
   - `http://racetimer:8000/admin`
   - `http://racetimer.<dit-net>.ts.net:8000/admin`
   - `http://100.x.y.z:8000/admin`

Bagefter virker adressen fra dine enheder, uanset hvilket netværk Pi'en og du er på, også efter genstart. Tænd Tailscale i appen, når du skal bruge den.

Officials kan få adgang ved at blive inviteret til dit Tailscale-netværk (gratis for op til 3 brugere).

## 🖥️ Raspberry Pi Connect – skærm og terminal

Raspberry Pi's officielle tjeneste. Du ser Pi'ens skærm og kan bruge dens terminal direkte i browseren. Det er praktisk, hvis kiosk-vinduet er lukket, til opdateringer, eller hvis noget skal undersøges.

1. Opret en gratis **Raspberry Pi-konto** (id.raspberrypi.com).
2. På Pi'en: **Admin → ⚙ Opsætning → Fjernadgang → Raspberry Pi Connect → Log ind**. Åbn linket, og log ind.
3. Gå til **connect.raspberrypi.com**, og vælg Pi'en. Vælg *Screen sharing* (skærm) eller *Remote shell* (terminal).

## 🌍 Offentligt link via Cloudflare

Giver adgang fra en hvilken som helst enhed via **https://ditdomæne.dk/racetimer/admin**. Opsætningen står i [webhotel/LÆS-MIG.md](../webhotel/LÆS-MIG.md#fjernadgang-til-admin-via-hjemmesiden).

Admin er her åben på internettet, kun beskyttet af RaceTimers login:
- Standardkoden kan ikke bruges udefra.
- Login spærres i 15 min efter 5 forkerte forsøg.

Brug Tailscale, hvis det kun er dig og nogle få officials, der skal ind.
