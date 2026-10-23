# Udgiv en ny version (for udvikleren)

Alle installerede RaceTimer-enheder kan opdateres fra **Admin → ⚙ Opsætning → Opdatering**. De henter nye versioner fra GitHub Releases og installerer **kun** pakker, der er signeret med udgiverens private nøgle.

## Signeringsnøglen

| Fil | Hvad | Hvor |
|---|---|---|
| `signing/racetimer-signing-key.pem` | **Privat** nøgle – signerer udgivelser | Kun hos dig + som GitHub Secret `RACETIMER_SIGNING_KEY`. **Aldrig i repoet** (`signing/` er i `.gitignore`) |
| `racetimer/release.json` → `pubkey` | Offentlig nøgle – Pi'erne kontrollerer med den | I repoet og på alle enheder |

> **Tag en sikker backup af den private nøgle** (fx i en password-manager). Mister du den, kan eksisterende enheder ikke opdateres automatisk længere. De kan stadig opdateres manuelt, fx med et nyt SD-kort-image eller `deploy/update-pi.sh`.

## Sådan udgiver du

1. Lav og test ændringerne. Kør `sh deploy/update-pi.sh racetimer.local` mod din egen test-Pi.
2. Byg en signeret pakke med et nyt versionsnummer (X.Y.Z, højere end det nuværende):

```bash
sh tools/make-release.sh 1.1.0
```

   Scriptet opdaterer `racetimer/VERSION` og laver `dist/racetimer-1.1.0.tar.gz` + `.sig`. Det kontrollerer også selv signaturen, før det melder ✓.
3. Opret en **GitHub Release** med tag `v1.1.0`. Skriv ændringerne i beskrivelsen; de vises i admin under "Hvad er nyt". Vedhæft de to filer fra `dist/`.
   (Med GitHub Actions sker punkt 2–3 automatisk, når du pusher et tag. Se `.github/workflows/`.)
4. Enhederne viser nu "Version 1.1.0 er klar" under **Admin → ⚙ Opsætning → Opdatering**.

## Hvad sker der på enheden

1. Pakke og signatur hentes til `/var/lib/racetimer/update/`.
2. Root-hjælperen `racetimer-update` kopierer dem til en mappe, kun root kan skrive i, og **kontrollerer signaturen** med den offentlige nøgle, der allerede er installeret. Passer den ikke, stopper alt.
3. Den nuværende version gemmes som backup (de seneste 3 gemmes). Den nye kode lægges i `/opt/racetimer`. Data (`/var/lib/racetimer`), Python-miljøet og `branding-local/` røres aldrig.
4. `deploy/post-update.sh` kører: hjælpere, services, Python-pakker og datamappe.
5. RaceTimer genstartes, og der laves et sundhedstjek. Svarer den nye version ikke inden for ca. 90 sek., **rulles der automatisk tilbage**.
6. Under **Admin → ⚙ Opsætning → Opdatering** kan man følge loggen og selv rulle tilbage til forrige version.

Er et løb i gang, advares man, før opdateringen starter.
