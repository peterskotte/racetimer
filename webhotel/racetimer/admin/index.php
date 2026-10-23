<?php
/*
 * https://ditdomæne.dk/racetimer/admin  →  viderestiller til Pi'ens admin via fjernadgang.
 * Pi'en melder selv sin aktuelle adresse (Cloudflare-tunnel) til modtag.php hvert 5. minut.
 */
date_default_timezone_set('Europe/Copenhagen');
$fil = __DIR__ . '/../data/tunnel.json';
$t = is_file($fil) ? json_decode(file_get_contents($fil), true) : null;
$frisk = $t && !empty($t['url']) && time() - (int)$t['modtaget'] < 15 * 60;   // meldt inden for 15 min
if ($frisk) {
    header('Cache-Control: no-store');
    header('Location: ' . $t['url'] . '/admin', true, 302);
    exit;
}
$sidst = $t ? date('d.m.Y \k\l. H:i', (int)$t['modtaget']) : null;
?><!doctype html>
<html lang="da"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="refresh" content="30"><title>RaceTimer – admin</title>
<style>
body{margin:0;background:#111814;color:#f3f1ec;font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
header{background:#f6efe3;border-bottom:3px solid #e5682a;padding:14px 20px;font-weight:800;font-size:24px;color:#0c1b14}header img{height:40px;display:block}
main{max-width:640px;margin:40px auto;padding:0 20px}.card{background:#1a231e;border:1px solid #2e3a33;border-radius:16px;padding:22px}
h1{font-size:22px;margin:0 0 10px}p{color:#a2aca5;line-height:1.5}
</style></head><body>
<header><?= is_file(__DIR__ . '/../logo.png') ? '<img src="../logo.png" alt="Logo">' : 'RaceTimer' ?></header>
<main><div class="card">
  <h1>Admin er ikke tilgængelig lige nu</h1>
  <?php if ($t && empty($t['url'])): ?>
    <p>Fjernadgang er slået fra på Pi'en<?= $sidst ? " (meldt $sidst)" : '' ?>. Slå den til under <b>Synkronisering → Fjernadgang</b> i admin på stævnet.</p>
  <?php else: ?>
    <p>Pi'en har ikke meldt sig<?= $sidst ? " siden $sidst" : ' endnu' ?>. Den er måske slukket eller uden internet. Siden prøver igen automatisk hvert 30. sekund.</p>
  <?php endif; ?>
</div></main></body></html>
