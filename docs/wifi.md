# Forbind Raspberry Pi'en til WiFi

RaceTimer kører fint uden internet. WiFi bruges kun til tre ting: at sende resultater til en webserver, at åbne admin fra en mobil eller bærbar, og at stille uret.

Vejledningen gælder Raspberry Pi OS Bookworm, som er standard på en Pi 5.

---

## Op til 5 faste netværk fra admin (anbefalet)

Når Pi'en først er på nettet én gang, kan du lægge op til **5 netværk** ind under **Admin → ⚙ Opsætning → WiFi**. Det kan fx være klubhuset, hjemme, din mobils hotspot og en reservemobil. Pi'en forbinder automatisk til det første netværk i listen, der er inden for rækkevidde, og den bliver ved med at prøve, også efter genstart. Ude ved løbet skal du ikke røre noget.

- **Rækkefølgen er prioriteten.** Nr. 1 vælges før nr. 2 osv. Flyt med ↑ ↓. Koderne følger med.
- **Netværk inden for rækkevidde** vises nederst. Tryk **+ Tilføj** for at sætte et netværk ind.
- **Tom kode** betyder, at den gemte kode beholdes. Sæt flueben i **Åbent** for netværk uden kode og i **Skjult** for netværk, der ikke viser deres navn.
- **Forbind** skifter til netværket med det samme. Er du selv på WiFi til Pi'en, kan admin miste forbindelsen et øjeblik.
- Koderne gemmes i Pi'ens netværksopsætning, som kun root kan læse, og ikke i RaceTimers database.
- Netværk fra Raspberry Pi Imager bliver ikke rørt. De står som "andre gemte netværk" og bruges, når ingen af de 5 er i nærheden.

> Tip: Læg mobil-hotspottet ind hjemmefra, inden du tager ud til løbet. Så er Pi'en online, så snart du tænder hotspottet.

## 1. Første gang: indstil WiFi, når SD-kortet laves

1. Hent **Raspberry Pi Imager** på din computer (raspberrypi.com/software).
2. Vælg *Raspberry Pi 5* → *Raspberry Pi OS (64-bit)* → dit SD-kort.
3. Når Imager spørger *"Vil du bruge tilpassede indstillinger?"*, så tryk **Rediger indstillinger** og udfyld:
   - **Værtsnavn:** `racetimer`
   - **Brugernavn og adgangskode:** vælg dine egne
   - **Konfigurér trådløst LAN:** netværksnavn (SSID) og kode
   - **Trådløst LAN-land:** `DK` (vigtigt – uden land er WiFi slået fra)
   - Under fanen *Tjenester*: slå **SSH** til
4. Skriv kortet, sæt det i Pi'en og tænd. Efter 1-2 minutter er den på nettet.

## 2. På Pi'en med skærm og mus

Klik på **netværksikonet** øverst til højre → vælg netværket → skriv koden. Pi'en husker netværket og forbinder automatisk næste gang.

Siger ikonet, at WiFi er slået fra, så vælg *Indstillinger → Raspberry Pi-konfiguration → Lokalisering → WLAN-land → DK*.

## 3. Fra terminal eller SSH

Brug en menu:

```bash
sudo nmtui
```

Vælg *Activate a connection* → netværket → skriv koden.

Eller direkte med kommandoer. Først en liste over netværk i nærheden:

```bash
nmcli device wifi list
```

Forbind derefter (ret navn og kode):

```bash
sudo nmcli device wifi connect "Netværksnavn" password "kode"
```

## 4. Flere netværk: klubhus, hjemme og mobil-hotspot

Pi'en husker alle netværk, du har forbundet til, og vælger selv et, der er i nærheden. Til løb i skoven er en **mobil-hotspot** det mest praktiske. Opret den hjemme på forhånd, så Pi'en kender den:

1. Tænd hotspot på mobilen. Giv den et fast navn og en fast kode.
   - **iPhone:** *Indstillinger → Personligt hotspot*. Slå **"Maksimer kompatibilitet"** til, så den bruger 2,4 GHz, som rækker længere.
   - **Android:** *Indstillinger → Hotspot og internetdeling*. Vælg 2,4 GHz.
2. Forbind Pi'en til den én gang (punkt 2 eller 3).
3. Hvis Pi'en skal foretrække hotspot frem for andre netværk, så giv den højere prioritet:

```bash
sudo nmcli connection modify "Mobilens navn" connection.autoconnect-priority 10
```

Se hvilke netværk Pi'en kender:

```bash
nmcli connection show
```

Glem et netværk:

```bash
sudo nmcli connection delete "Navn"
```

## 5. Find Pi'en og åbn admin

Når mobil eller bærbar er på **samme netværk** som Pi'en, åbner du `http://racetimer.local:8000/admin`.

Virker `.local` ikke (det sker på nogle Android-telefoner), så find IP-adressen på Pi'en:

```bash
hostname -I
```

og brug fx `http://192.168.1.42:8000/admin`.

## 6. Tjek at alt virker

Er der internet?

```bash
ping -c 3 1.1.1.1
```

Er uret stillet? Linjen *System clock synchronized* skal sige **yes**:

```bash
timedatectl
```

Admin → **Synkronisering** viser også, om den seneste afsendelse til webserveren lykkedes.

> **Uret er vigtigt.** Pi'en stiller selv uret, når den har internet. Monter det officielle RTC-batteri, så den også har korrekt tid efter en genstart uden net. Kontrollér altid klokken på resultatskærmen inden start.

## 7. Uden netværk på stedet

Er der hverken WiFi eller mobildækning, kan Pi'en selv lave et lille WiFi-net, som admin-mobilen forbinder til:

```bash
sudo nmcli device wifi hotspot ifname wlan0 ssid RaceTimer password "vælg-en-kode"
```

Admin findes derefter på `http://10.42.0.1:8000/admin`. Mens hotspottet kører, kan Pi'en ikke selv være på et andet WiFi. Resultaterne kan sendes til webserveren bagefter: forbind til et netværk igen, og tryk **Send nu** under Synkronisering.

Stop hotspottet igen:

```bash
sudo nmcli connection down Hotspot
```

## Fejlfinding

| Problem | Løsning |
|---|---|
| WiFi-ikonet er gråt eller slået fra | Sæt WLAN-land til DK (punkt 2), eller kør `sudo rfkill unblock wifi` |
| Netværket vises ikke | Pi'en er for langt væk, eller nettet kører kun 5 GHz. Brug 2,4 GHz på hotspot/router |
| "Secrets were required" | Forkert kode. Slet forbindelsen (punkt 4) og prøv igen |
| `racetimer.local` virker ikke | Brug IP-adressen fra `hostname -I` |
| Synkronisering siger "Ingen forbindelse" | Tjek med `ping` (punkt 6). Tidtagningen kører videre, og alt sendes, når nettet er tilbage |
