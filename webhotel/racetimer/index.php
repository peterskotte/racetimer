<?php
/*
 * RaceTimer → hjemmeside: viser de seneste resultater, som modtag.php har gemt.
 * Åbn https://ditdomæne.dk/racetimer/ – eller vis den i en iframe på en anden side.
 * Tidligere slutresultater vises i en liste under tabellen.
 * Er der ikke et aktivt løb på Pi'en, vises splash-billedet med den tekst, der er valgt i RaceTimer.
 * Løb, der er arkiveret i RaceTimer, vises ikke.
 */
date_default_timezone_set('Europe/Copenhagen');
$mappe = __DIR__ . '/data';

// Den seneste besked fra Pi'en bestemmer udseende, og hvilke løb der er arkiveret
$seneste = is_file("$mappe/resultater.json") ? json_decode(file_get_contents("$mappe/resultater.json"), true) : null;
$udseende = $seneste['branding'] ?? [];
$arkiveret = array_map('intval', $seneste['archived'] ?? []);
$skjult = function ($d) use ($arkiveret) { return in_array((int)($d['race']['id'] ?? 0), $arkiveret, true); };

$arkiv = [];
foreach (glob("$mappe/slut-*.json") ?: [] as $a) {
    $d = json_decode(file_get_contents($a), true);
    if ($d && !$skjult($d)) $arkiv[basename($a)] = $d;
}
krsort($arkiv);

$vis = $_GET['vis'] ?? '';
$data = $seneste;
if ($vis !== '' && isset($arkiv[$vis])) {
    $data = $arkiv[$vis];
} else {
    $vis = '';
}
// Intet aktivt løb (eller det er arkiveret) → splash
$splash = $vis === '' && (!$data || empty($data['race']) || $skjult($data));

function e($s) { return htmlspecialchars((string)$s, ENT_QUOTES, 'UTF-8'); }
function datafil($navn) {
    foreach (['webp', 'png', 'jpg', 'jpeg'] as $x) {
        if (is_file(__DIR__ . "/data/$navn.$x")) return "data/$navn.$x?v=" . filemtime(__DIR__ . "/data/$navn.$x");
    }
    return null;
}
// Logo: det, Pi'en har sendt – ellers evt. et logo.png i samme mappe – ellers klubnavnet som tekst
$brand = $udseende['name'] ?? $seneste['brand'] ?? 'Resultater';
$logofil = datafil('logo') ?? (is_file(__DIR__ . '/logo.png') ? 'logo.png' : null);
$logo = $logofil
    ? '<img src="' . e($logofil) . '" alt="' . e($brand) . '">'
    : '<span class="brand">' . e($brand) . '</span>';
$splashfil = ($udseende['splash'] ?? 'image') === 'image' ? datafil('splash') : null;
$splashtekst = trim($udseende['splash_text'] ?? '');
// Løb med åben tilmelding (tilmeld.php) – vises som et link øverst
$tilm = is_file("$mappe/tilmelding.json") ? json_decode(file_get_contents("$mappe/tilmelding.json"), true) : null;
$aabne = array_filter($tilm['loeb'] ?? [], function ($l) {
    return !empty($l['open']) && (empty($l['deadline']) || time() <= $l['deadline']);
});
$tilmlink = $aabne ? '<div class="tilm">📝 Tilmelding er åben: ' . implode(' · ', array_map(function ($l) {
    return '<a href="tilmeld.php?lob=' . (int)$l['id'] . '">' . e($l['name']) . '</a>'
        . (!empty($l['deadline']) ? ' <span>(senest ' . date('d.m', (int)$l['deadline']) . ')</span>' : '');
}, $aabne)) . '</div>' : '';
function hms($sek, $tvungen = false) {
    if ($sek === null) return '–';
    $sek = max(0, (int)$sek);
    $h = intdiv($sek, 3600); $m = intdiv($sek % 3600, 60); $s = $sek % 60;
    return ($h || $tvungen) ? sprintf('%d:%02d:%02d', $h, $m, $s) : sprintf('%d:%02d', $m, $s);
}
function km($v) { return number_format((float)$v, 1, ',', '.'); }

$race = $data['race'] ?? null;
$info = $data['info'] ?? [];
$rows = $data['results'] ?? [];
$final = ($data['event'] ?? '') === 'final';
$omgang = $race && in_array($race['type'], ['backyard', 'backyard_custom', 'timed', 'record'], true);
$medtid = $omgang && !empty($info['continuous']);
// Planlagt løb, hvor indtjekningen ikke er åbnet: splash med en teaser om løbet – ingen deltagerliste
$teaser = (!$splash && $vis === '' && !empty($info['teaser'])) ? $info['teaser'] : null;
if ($teaser) $splash = true;
function teaser_html($t) {
    $dage = ['søndag', 'mandag', 'tirsdag', 'onsdag', 'torsdag', 'fredag', 'lørdag'];
    $mdr = ['januar', 'februar', 'marts', 'april', 'maj', 'juni', 'juli', 'august', 'september', 'oktober', 'november', 'december'];
    $start = !empty($t['start']) ? (int)$t['start'] : null;
    $hvornaar = $start ? ucfirst($dage[(int)date('w', $start)]) . ' ' . date('j', $start) . '. ' . $mdr[(int)date('n', $start) - 1]
        . ' kl. ' . date('H.i', $start) : 'Starttidspunktet kommer snart';
    $info = array_filter([!empty($t['count']) ? (int)$t['count'] . ' tilmeldte' : '', implode(' · ', array_map('e', $t['distances'] ?? []))]);
    return '<div class="teaser"><div class="tk">Næste løb</div><div class="tn">' . e($t['name'] ?? '') . '</div><div class="tw">' . e($hvornaar) . '</div>'
        . ($start ? '<div class="tc" data-start="' . $start . '" data-now="' . time() . '"></div>' : '')
        . ($info ? '<div class="ts">' . implode('  ·  ', $info) . '</div>' : '') . '</div>'
        . ($start ? '<script>(function(){var el=document.querySelector(".teaser .tc"),s=+el.dataset.start,off=+el.dataset.now-Date.now()/1000;'
        . 'function p(n){return(n<10?"0":"")+n}function t(){var l=Math.max(0,Math.round(s-(Date.now()/1000+off))),d=Math.floor(l/86400);'
        . 'el.textContent=l<=0?"":d>=1?"om "+d+(d===1?" dag":" dage"):p(Math.floor(l/3600))+":"+p(Math.floor(l%3600/60))+":"+p(l%60)}t();setInterval(t,1000)})();</script>' : '');
}
$live = !$splash && $race && !$final && ($race['status'] ?? '') === 'running' && $vis === '';
?>
<?php
// Opsummering, nedtæller og resultattabel – for hele løbet eller én distance
function sektion($race, $info, $rows, $final) {
    $omgang = in_array($race['type'], ['backyard', 'backyard_custom', 'timed', 'record'], true);
    $medtid = $omgang && !empty($info['continuous']);

    $sum = '';
if (!empty($info['continuous'])) {
    $maal = ($info['end_mode'] ?? '') === 'duration' ? 'flest omgange på ' . hms($info['duration_sec'] ?? 0, true) : 'først til ' . (int)$info['max_yards'] . ' omgange';
    $sum = (($info['phase'] ?? '') === 'ended' && !empty($info['leader']))
        ? '🏁 Vinder: ' . e($info['leader']) . ' – ' . (int)$info['leader_laps'] . " omgange ($maal)"
        : ucfirst($maal) . ' · ' . (int)($info['on_course'] ?? 0) . ' på ruten';
} elseif (strpos($race['type'], 'backyard') === 0) {
    if (!empty($info['winner'])) $sum = '🏆 Vinder: ' . e($info['winner']) . ' – ' . (int)$info['completed_yards'] . ' yards';
    elseif (!empty($info['no_winner'])) $sum = 'Løbet er slut – ingen vinder';
    elseif (($info['phase'] ?? '') === 'running') $sum = 'Yard ' . (int)$info['yard'] . ' · ' . (int)$info['runners_left'] . ' tilbage';
} elseif ($race['type'] === 'record') {
    $sum = e($info['record_label'] ?? 'Årets rekord') . ': ' . km($info['total_km'] ?? 0) . ' km';
} elseif ($race['type'] === 'timed' && isset($info['total_km'])) {
    $sum = 'Samlet distance: ' . km($info['total_km']) . ' km';
}
if ($sum) echo "<div class=\"sum\">$sum</div>";

// Nedtæller med ring: tid tilbage af løbet (tidsløb / samlet tid) eller til næste yard (backyard)
$cd = null;
if (!$final && ($info['phase'] ?? '') === 'running') {
    if (($race['type'] === 'timed' || (!empty($info['continuous']) && ($info['end_mode'] ?? '') === 'duration')) && !empty($info['end_at']))
        $cd = ['Tid tilbage', $info['end_at'], $info['duration_sec'] ?? 0];
    elseif (strpos($race['type'], 'backyard') === 0 && empty($info['continuous']) && !empty($info['next_start']))
        $cd = ['Næste start', $info['next_start'], $info['interval_sec'] ?? 3600];
}
if ($cd): ?>
<div class="cd" data-end="<?= (float)$cd[1] ?>" data-total="<?= (float)$cd[2] ?>" data-now="<?= time() ?>">
  <svg viewBox="0 0 120 120" aria-hidden="true"><circle class="bg" cx="60" cy="60" r="52"/><circle class="fg" cx="60" cy="60" r="52"/></svg>
  <div><div class="cdk"><?= e($cd[0]) ?></div><div class="cdv">--:--:--</div></div>
</div>
<?php endif; ?>
<div class="card"><table>
<thead><tr><th>#</th><th>Navn</th><th>Køn</th><th>Status</th>
<?php if ($omgang): ?><th class="r">Omgange</th><th class="r">Distance</th><th class="r">Sidste omg.</th><?php if ($medtid): ?><th class="r">Tid</th><?php endif; ?><?php else: ?><th class="r">Tid</th><?php endif; ?>
</tr></thead><tbody>
<?php if (!$rows): ?><tr><td colspan="7" class="tom">Ingen deltagere endnu</td></tr><?php endif; ?>
<?php foreach ($rows as $r): $ude = in_array($r['status'], ['dnf', 'rtc', 'dsq', 'dns'], true); ?>
<tr class="<?= $ude ? 'ude' : '' ?>">
  <td><?= $r['place'] !== null ? (int)$r['place'] : '–' ?></td>
  <td class="navn"><?= $r['bib'] !== null ? '<span class="nr">' . (int)$r['bib'] . '</span>' : '' ?><?= e($r['name']) ?><?= !empty($r['club']) ? '<span class="klub">' . e($r['club']) . '</span>' : '' ?><?= !empty($r['dogs']) ? '<span class="klub" style="color:var(--orange)">🐕 ' . e(implode(' & ', $r['dogs'])) . '</span>' : '' ?></td>
  <td><?= e($r['sex'] ?? '') ?><?= !empty($r['class']) ? ' <span class="nr">' . e($r['class']) . '</span>' : '' ?></td>
  <td style="white-space:nowrap"><i class="dot <?= e($r['status']) ?>"></i><?= e($r['status_label']) ?></td>
<?php if ($omgang): ?>
  <td class="r"><?= (int)$r['laps'] ?></td><td class="r"><?= km($r['distance_km']) ?> km</td><td class="r"><?= hms($r['last_lap']) ?></td>
  <?php if ($medtid): ?><td class="r"><?= $r['total_time'] !== null ? hms($r['total_time'], true) : '–' ?></td><?php endif; ?>
<?php else: ?>
  <td class="r"><?= $r['total_time'] !== null ? hms($r['total_time'], true) : '–' ?></td>
<?php endif; ?>
</tr>
<?php endforeach; ?>
</tbody></table></div>
<?php
}
?>
<!doctype html>
<html lang="da">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<?php if ($live): ?><meta http-equiv="refresh" content="30"><?php elseif ($splash): ?><meta http-equiv="refresh" content="60"><?php endif; ?>
<title><?= !$splash && $race ? e($race['name']) . ' – resultater' : e($brand) ?></title>
<style>
:root{--bg:#111814;--card:#1a231e;--head:#212c26;--line:#2e3a33;--text:#f3f1ec;--muted:#a2aca5;--dim:#6b766f;--orange:#e5682a;--cream:#f6efe3}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
header{background:var(--cream);border-bottom:3px solid var(--orange);padding:14px 20px}header img{height:40px;display:block}
.brand{font-weight:800;font-size:26px;color:#0c1b14;font-style:italic}
h1{margin:0;font-size:28px}h2.dist{margin:26px 0 10px;font-size:22px}h2.dist small{color:var(--muted);font-weight:500;font-size:14px}.sub{color:var(--muted);margin:6px 0 16px}
main{max-width:1100px;margin:0 auto;padding:16px}
.pill{display:inline-block;font-size:12px;font-weight:700;padding:3px 10px;border-radius:99px;margin-right:8px;color:#06121f}
.pill.live{background:#3fc56b}.pill.final{background:#5aa3ff}.pill.prel{background:#9aa1ab}
.sum{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:14px 18px;margin-bottom:14px;font-size:20px;font-weight:600}
.card{background:var(--card);border:1px solid var(--line);border-radius:18px;overflow-x:auto}
table{width:100%;border-collapse:collapse}th{background:var(--head);color:var(--muted);text-align:left;padding:12px 14px;white-space:nowrap}
td{padding:11px 14px;border-top:1px solid var(--line);font-variant-numeric:tabular-nums}.r{text-align:right;white-space:nowrap}
td.navn{font-weight:600}.nr{color:var(--muted);font-weight:500;font-size:.85em;margin-right:.45em}.klub{display:block;color:var(--muted);font-weight:400;font-size:.8em}
tr.ude td{color:var(--dim)}.dot{display:inline-block;width:.55em;height:.55em;border-radius:50%;margin-right:.5em;background:#8a9099}
.active{background:#3fc56b}.resting{background:#2bb3a3}.winner{background:#f2c14e}.finished{background:#5aa3ff}.rtc,.dsq{background:#ef5b5b}
.tilm{background:var(--orange);color:#fff;padding:10px 20px;font-weight:600}.tilm a{color:#fff}.tilm span{font-weight:400;opacity:.85}
.arkiv{margin-top:22px}.arkiv a{color:var(--text)}.arkiv li{margin:6px 0}
footer{color:var(--muted);font-size:13px;padding:14px 4px}.tom{padding:40px;text-align:center;color:var(--muted)}
.cd{display:flex;align-items:center;gap:18px;background:var(--card);border:1px solid var(--line);border-radius:14px;padding:12px 18px;margin-bottom:14px}
.cd svg{width:72px;height:72px;transform:rotate(-90deg);flex:none}.cd circle{fill:none;stroke-width:10}.cd .bg{stroke:var(--line)}.cd .fg{stroke:#3fc56b;stroke-linecap:round}
.cdk{color:var(--muted);font-size:13px;font-weight:600;text-transform:uppercase;letter-spacing:.06em}.cdv{font-size:clamp(30px,6vw,52px);font-weight:700;font-variant-numeric:tabular-nums}
.cd.soon .fg{stroke:var(--orange)}.cd.soon .cdv{color:var(--orange)}.cd.last .fg{stroke:#ef5b5b}.cd.last .cdv{color:#ef5b5b}
.splash{position:relative;min-height:70vh;background:#0c0e11 center/cover no-repeat;display:flex;align-items:flex-end}
.splash.plain{align-items:center;justify-content:center;flex-direction:column;text-align:center}
.splash .pn{font-weight:800;font-style:italic;font-size:clamp(36px,8vw,110px);letter-spacing:-.03em;line-height:1.05;padding:0 5vw}
.splash .txt{width:100%;padding:12vh 5vw 8vh;background:linear-gradient(to top,rgba(0,0,0,.78),rgba(0,0,0,.45) 55%,transparent);color:#fff;
  text-align:center;font-weight:800;font-size:clamp(24px,4.6vw,64px);line-height:1.12;white-space:pre-line;text-shadow:0 2px 18px rgba(0,0,0,.5)}
.teaser{position:absolute;bottom:6vh;left:50%;transform:translateX(-50%);width:min(92%,760px);padding:20px 28px;border-radius:20px;text-align:center;color:#fff;
  background:rgba(10,16,13,.74);border:1px solid rgba(255,255,255,.14);box-shadow:0 18px 60px rgba(0,0,0,.45);backdrop-filter:blur(10px)}
.splash.plain .teaser{position:static;transform:none;margin:22px auto 0}
.teaser .tk{color:var(--orange);font-weight:800;letter-spacing:.14em;text-transform:uppercase;font-size:13px}
.teaser .tn{font-weight:800;font-size:clamp(26px,5vw,52px);line-height:1.1;margin-top:4px}.teaser .tw{font-size:clamp(15px,2.2vw,22px);font-weight:600;opacity:.9;margin-top:6px}
.teaser .tc{font-size:clamp(26px,5vw,48px);font-weight:800;margin-top:6px;color:var(--cream);font-variant-numeric:tabular-nums}.teaser .ts{opacity:.75;margin-top:8px}
.splash.plain .txt{background:none;padding:18px 5vw 0;color:var(--orange);font-size:clamp(16px,2.4vw,30px);font-weight:600}
</style>
</head>
<body>
<?php if ($splash): ?>
<header><?= $logo ?></header><?= $tilmlink ?>
<?php if ($splashfil): ?>
<div class="splash" style="background-image:url('<?= e($splashfil) ?>')"><?= $teaser ? teaser_html($teaser) : '' ?><?php if ($splashtekst !== '' && !$teaser): ?><div class="txt"><?= e($splashtekst) ?></div><?php endif; ?></div>
<?php else: ?>
<div class="splash plain"><div class="pn"><?= e($brand) ?></div><?= $teaser ? teaser_html($teaser) : '<div class="txt">' . e($splashtekst !== '' ? $splashtekst : 'Venter på næste løb') . '</div>' ?></div>
<?php endif; ?>
<main>
<?php else: ?>
<header><?= $logo ?></header><?= $tilmlink ?>
<main>
  <h1><?= e($race['name']) ?></h1>
  <div class="sub">
    <span class="pill <?= $final ? 'final' : ($live ? 'live' : 'prel') ?>"><?= $final ? 'Endelige resultater' : ($live ? 'Live' : 'Foreløbige resultater') ?></span>
    <?= e($info['type_label'] ?? '') ?><?= !empty($race['started_at']) ? ' · start ' . date('d.m.Y H:i', (int)$race['started_at']) : '' ?>
  </div>
<?php if (!empty($info['distances'])): foreach ($info['distances'] as $d): ?>
<h2 class="dist"><?= e($d['name']) ?> <small>· <?= (int)($d['count'] ?? 0) ?> deltagere<?= !empty($d['started_at']) ? ' · start ' . date('H:i', (int)$d['started_at']) : '' ?></small></h2>
<?php sektion($race, $d, array_values(array_filter($rows, function ($r) use ($d) { return ($r['distance'] ?? null) === $d['id']; })), $final); endforeach;
else: sektion($race, $info, $rows, $final); endif;
if (!$final): ?>
<script>
(function () {  // tæller ned hvert sekund mellem opdateringerne (webhotellets ur bruges som reference)
  document.querySelectorAll('.cd').forEach(function (el) {
  var end = +el.dataset.end, total = +el.dataset.total,
      off = +el.dataset.now - Date.now() / 1000, C = 2 * Math.PI * 52, fg = el.querySelector('.fg');
  fg.style.strokeDasharray = C;
  function p(n) { return (n < 10 ? '0' : '') + n; }
  function tick() {
    var left = Math.max(0, end - (Date.now() / 1000 + off)), s = Math.round(left), f = total ? Math.min(1, left / total) : 0;
    el.querySelector('.cdv').textContent = p(Math.floor(s / 3600)) + ':' + p(Math.floor(s % 3600 / 60)) + ':' + p(s % 60);
    fg.style.strokeDashoffset = C * (1 - f);
    el.className = 'cd' + (left <= Math.min(900, total * 0.05) ? ' last' : f <= 0.1 ? ' soon' : '');
  }
  tick(); setInterval(tick, 1000);
  });
})();
</script>
<?php endif; ?>
<footer>Opdateret <?= date('d.m.Y \k\l. H:i', (int)$data['sent_at']) ?><?= $live ? ' · siden opdaterer sig selv hvert 30. sekund' : '' ?></footer>
<?php endif; ?>

<?php if ($arkiv): ?>
<div class="arkiv"><h3>Tidligere resultater</h3><ul>
<?php if ($vis !== ''): ?><li><a href="?">← Seneste løb</a></li><?php endif; ?>
<?php foreach ($arkiv as $b => $d): ?>
  <li><a href="?vis=<?= e($b) ?>"><?= e($d['race']['name'] ?? $b) ?></a> <span style="color:var(--muted)">· <?= !empty($d['race']['started_at']) ? date('d.m.Y', (int)$d['race']['started_at']) : '' ?></span></li>
<?php endforeach; ?>
</ul></div>
<?php endif; ?>
</main>
</body>
</html>
