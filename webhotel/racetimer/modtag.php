<?php
/*
 * RaceTimer → hjemmeside: modtager resultater fra Pi'en.
 *
 * 1. Skift nøglen herunder til din egen (samme nøgle skrives i RaceTimer under
 *    Synkronisering → destination af typen "Egen hjemmeside (JSON)").
 * 2. Upload denne fil + index.php til en mappe på webhotellet, fx /racetimer/
 * 3. Adressen i RaceTimer er så: https://ditdomæne.dk/racetimer/modtag.php
 *
 * Pi'en sender også klubbens logo, splash-billede og -tekst samt hvilke løb der er arkiveret.
 * index.php viser splash, når der ikke er et aktivt løb, og skjuler arkiverede løb.
 */
$RACETIMER_KEY = 'SKIFT-MIG-TIL-EN-LANG-HEMMELIG-NOEGLE';

header('Content-Type: application/json; charset=utf-8');
// Browser-udgaven af RaceTimer sender direkte fra browseren (fra en anden adresse). Det er sikkert at
// tillade, fordi hver forespørgsel stadig skal have den rigtige nøgle.
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type, X-RaceTimer-Key, Authorization');
if (($_SERVER['REQUEST_METHOD'] ?? '') === 'OPTIONS') {
    http_response_code(204);
    exit;
}

function svar($kode, $tekst, $ekstra = []) {
    http_response_code($kode);
    echo json_encode(['ok' => $kode === 200, 'besked' => $tekst] + $ekstra, JSON_UNESCAPED_UNICODE);
    exit;
}

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    svar(405, 'Denne adresse tager kun imod data fra RaceTimer (POST).');
}
if ($RACETIMER_KEY === 'SKIFT-MIG-TIL-EN-LANG-HEMMELIG-NOEGLE' || strlen($RACETIMER_KEY) < 12) {
    svar(500, 'Nøglen i modtag.php er ikke sat. Ret $RACETIMER_KEY øverst i filen.');
}

// Nøglen kan komme på flere måder – mange webhoteller fjerner Authorization-headeren
$auth = $_SERVER['HTTP_X_RACETIMER_KEY']
    ?? preg_replace('/^Bearer\s+/i', '', $_SERVER['HTTP_AUTHORIZATION'] ?? $_SERVER['REDIRECT_HTTP_AUTHORIZATION'] ?? '');
if (!hash_equals($RACETIMER_KEY, (string)$auth)) {
    svar(403, 'Forkert nøgle.');
}

$raw = file_get_contents('php://input');
$data = json_decode($raw, true);
if (!is_array($data) || !isset($data['event'])) {
    svar(400, 'Ugyldige data.');
}

$mappe = __DIR__ . '/data';
if (!is_dir($mappe) && !@mkdir($mappe, 0755)) {
    svar(500, 'Kan ikke oprette mappen data/ – giv webserveren skriveadgang til mappen.');
}
// Beskyt data-mappen mod mappevisning
if (!file_exists("$mappe/index.html")) {
    @file_put_contents("$mappe/index.html", '');
}

function gem($fil, $data) {
    $tmp = $fil . '.tmp';
    if (file_put_contents($tmp, json_encode($data, JSON_UNESCAPED_UNICODE)) === false || !rename($tmp, $fil)) {
        svar(500, 'Kunne ikke gemme ' . basename($fil) . ' – tjek skriveadgang til data/.');
    }
}

// Pi'en melder sin fjernadgangs-adresse (bruges af admin/index.php) – rører ikke resultaterne
if ($data['event'] === 'tunnel') {
    $url = $data['url'] ?? null;
    if ($url !== null && !preg_match('#^https://[a-z0-9-]+\.trycloudflare\.com$#', $url)) {
        svar(400, 'Ugyldig adresse.');
    }
    gem("$mappe/tunnel.json", ['url' => $url, 'modtaget' => time()]);
    svar(200, 'Adresse gemt');
}

// Udseende fra Pi'en: logo og splash-billede sendes kun, når de er ændret.
// udseende.json husker, hvilken version vi har – svaret fortæller Pi'en det, så den sender
// billederne igen, hvis de mangler (fx efter en udskiftning af denne fil).
$udseende = $data['branding'] ?? null;
$har_v = is_file("$mappe/udseende.json") ? (json_decode(file_get_contents("$mappe/udseende.json"), true)['v'] ?? null) : null;
if (is_array($udseende)) {
    $gemt = [];
    foreach (($udseende['images'] ?? []) as $slags => $billede) {
        if (!in_array($slags, ['logo', 'splash'], true) || !is_array($billede)) continue;
        $ext = strtolower($billede['ext'] ?? '');
        $bytes = base64_decode($billede['data'] ?? '', true);
        if (!in_array($ext, ['.png', '.jpg', '.jpeg', '.webp'], true) || $bytes === false
            || strlen($bytes) > 4 * 1024 * 1024 || !@getimagesizefromstring($bytes)) continue;
        foreach (glob("$mappe/$slags.*") ?: [] as $gammel) @unlink($gammel);
        if (file_put_contents("$mappe/$slags.tmp", $bytes) !== false && rename("$mappe/$slags.tmp", "$mappe/$slags$ext")) {
            $gemt[$slags] = true;
        }
    }
    $komplet = (!empty($gemt['splash']) || ($udseende['splash'] ?? '') === 'plain')
            && (!empty($gemt['logo']) || empty($udseende['logo']));
    if ($komplet && isset($udseende['v'])) {
        $har_v = $udseende['v'];
        file_put_contents("$mappe/udseende.json", json_encode(['v' => $har_v]));
    }
    if (empty($udseende['logo'])) {
        foreach (glob("$mappe/logo.*") ?: [] as $gammel) @unlink($gammel);
    }
    unset($data['branding']['images']);  // billederne ligger nu som filer
}

gem("$mappe/resultater.json", $data);

// Slutresultater gemmes også i et arkiv, så de bliver liggende efter næste løb
if ($data['event'] === 'final' && !empty($data['race']['id'])) {
    $navn = strtolower($data['race']['name'] ?? 'loeb');
    $navn = strtr($navn, ['æ' => 'ae', 'ø' => 'oe', 'å' => 'aa']);
    $navn = trim(preg_replace('/[^a-z0-9]+/', '-', $navn), '-') ?: 'loeb';
    $dato = date('Y-m-d', (int)($data['race']['started_at'] ?? time()));
    gem("$mappe/slut-$dato-$navn.json", $data);
}

svar(200, 'Gemt', ['brand_v' => $har_v]);
