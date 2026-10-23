<?php
/*
 * RaceTimer → hjemmeside: viser de seneste resultater, som modtag.php har gemt.
 * Åbn https://ditdomæne.dk/racetimer/ – eller vis den i en iframe på en anden side.
 * Tidligere slutresultater vises i en liste under tabellen.
 */
date_default_timezone_set('Europe/Copenhagen');
$mappe = __DIR__ . '/data';

$arkiv = glob("$mappe/slut-*.json") ?: [];
rsort($arkiv);

$vis = $_GET['vis'] ?? '';
$fil = "$mappe/resultater.json";
if ($vis !== '' && preg_match('/^slut-[a-z0-9-]+\.json$/', $vis) && is_file("$mappe/$vis")) {
    $fil = "$mappe/$vis";
}
$data = is_file($fil) ? json_decode(file_get_contents($fil), true) : null;

function e($s) { return htmlspecialchars((string)$s, ENT_QUOTES, 'UTF-8'); }
// Logo: læg evt. jeres eget logo.png i samme mappe – ellers vises klubnavnet som tekst
$brand = $data['brand'] ?? 'Resultater';
$logo = is_file(__DIR__ . '/logo.png')
    ? '<img src="logo.png" alt="' . e($brand) . '">'
    : '<span class="brand">' . e($brand) . '</span>';
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
$live = $race && !$final && ($race['status'] ?? '') === 'running' && $vis === '';
?><!doctype html>
<html lang="da">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<?php if ($live): ?><meta http-equiv="refresh" content="30"><?php endif; ?>
<title><?= $race ? e($race['name']) . ' – resultater' : 'Resultater' ?></title>
<style>
:root{--bg:#111814;--card:#1a231e;--head:#212c26;--line:#2e3a33;--text:#f3f1ec;--muted:#a2aca5;--dim:#6b766f;--orange:#e5682a;--cream:#f6efe3}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
header{background:var(--cream);border-bottom:3px solid var(--orange);padding:14px 20px}header img{height:40px;display:block}
.brand{font-weight:800;font-size:26px;color:#0c1b14;font-style:italic}
h1{margin:0;font-size:28px}.sub{color:var(--muted);margin:6px 0 16px}
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
.arkiv{margin-top:22px}.arkiv a{color:var(--text)}.arkiv li{margin:6px 0}
footer{color:var(--muted);font-size:13px;padding:14px 4px}.tom{padding:40px;text-align:center;color:var(--muted)}
</style>
</head>
<body>
<?php if (!$race): ?>
<header><?= $logo ?></header>
<main><h1>Resultater</h1><div class="card tom" style="margin-top:16px">Der er ingen resultater endnu.</div>
<?php else: ?>
<header><?= $logo ?></header>
<main>
  <h1><?= e($race['name']) ?></h1>
  <div class="sub">
    <span class="pill <?= $final ? 'final' : ($live ? 'live' : 'prel') ?>"><?= $final ? 'Endelige resultater' : ($live ? 'Live' : 'Foreløbige resultater') ?></span>
    <?= e($info['type_label'] ?? '') ?><?= !empty($race['started_at']) ? ' · start ' . date('d.m.Y H:i', (int)$race['started_at']) : '' ?>
  </div>
<?php
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
?>
<div class="card"><table>
<thead><tr><th>#</th><th>Navn</th><th>Køn</th><th>Status</th>
<?php if ($omgang): ?><th class="r">Omgange</th><th class="r">Distance</th><th class="r">Sidste omg.</th><?php if ($medtid): ?><th class="r">Tid</th><?php endif; ?><?php else: ?><th class="r">Tid</th><?php endif; ?>
</tr></thead><tbody>
<?php if (!$rows): ?><tr><td colspan="7" class="tom">Ingen deltagere endnu</td></tr><?php endif; ?>
<?php foreach ($rows as $r): $ude = in_array($r['status'], ['dnf', 'rtc', 'dsq', 'dns'], true); ?>
<tr class="<?= $ude ? 'ude' : '' ?>">
  <td><?= $r['place'] !== null ? (int)$r['place'] : '–' ?></td>
  <td class="navn"><?= $r['bib'] !== null ? '<span class="nr">' . (int)$r['bib'] . '</span>' : '' ?><?= e($r['name']) ?><?= !empty($r['club']) ? '<span class="klub">' . e($r['club']) . '</span>' : '' ?><?= !empty($r['dogs']) ? '<span class="klub" style="color:var(--orange)">🐕 ' . e(implode(' & ', $r['dogs'])) . '</span>' : '' ?></td>
  <td><?= e($r['sex'] ?? '') ?></td>
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
<footer>Opdateret <?= date('d.m.Y \k\l. H:i', (int)$data['sent_at']) ?><?= $live ? ' · siden opdaterer sig selv hvert 30. sekund' : '' ?></footer>
<?php endif; ?>

<?php if ($arkiv): ?>
<div class="arkiv"><h3>Tidligere resultater</h3><ul>
<?php if ($vis !== ''): ?><li><a href="?">← Seneste løb</a></li><?php endif; ?>
<?php foreach ($arkiv as $a): $d = json_decode(file_get_contents($a), true); $b = basename($a); ?>
  <li><a href="?vis=<?= e($b) ?>"><?= e($d['race']['name'] ?? $b) ?></a> <span style="color:var(--muted)">· <?= !empty($d['race']['started_at']) ? date('d.m.Y', (int)$d['race']['started_at']) : '' ?></span></li>
<?php endforeach; ?>
</ul></div>
<?php endif; ?>
</main>
</body>
</html>
