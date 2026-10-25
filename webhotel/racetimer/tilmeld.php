<?php
/*
 * RaceTimer → hjemmeside: tilmelding til løb.
 * Hvilke løb der er åbne, bestemmes i RaceTimer (Deltagere → Tilmelding på hjemmesiden) og kommer
 * med Pi'ens næste afsendelse til modtag.php. Tilmeldingerne gemmes i data/tilmeld-<løb>.php, som
 * ikke kan læses udefra; Pi'en henter dem med nøglen og opretter deltagerne.
 * E-mail og fødselsår vises aldrig på siden. Kræver ingen opsætning ud over modtag.php.
 */
date_default_timezone_set('Europe/Copenhagen');
$mappe = __DIR__ . '/data';
$MAKS_PR_TIME = 10;  // tilmeldinger pr. IP-adresse pr. time (mod spam)

function e($s) { return htmlspecialchars((string)$s, ENT_QUOTES, 'UTF-8'); }
$info = is_file("$mappe/tilmelding.json") ? json_decode(file_get_contents("$mappe/tilmelding.json"), true) : null;
$alle = [];
foreach (($info['loeb'] ?? []) as $l) {
    // slettefristen er nået, selv om Pi'en ikke har været online: slet tilmeldingerne her og nu
    if (!empty($l['purge_at']) && $l['purge_at'] < time()) {
        @unlink("$mappe/tilmeld-" . (int)$l['id'] . '.php');
        continue;
    }
    $alle[(int)$l['id']] = $l;
}
$brand = $info['brand'] ?? 'Tilmelding';

function tilmeldinger($mappe, $lob) {
    $fil = "$mappe/tilmeld-" . (int)$lob . '.php';
    if (!is_file($fil)) return [];
    $ud = [];
    foreach (array_slice(file($fil, FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES), 1) as $linje) {
        $t = json_decode($linje, true);
        if (is_array($t)) $ud[] = $t;
    }
    return $ud;
}
function aaben($l) { return !empty($l['open']) && (empty($l['deadline']) || time() <= $l['deadline']); }
function dato($ts, $kl = false) { return $ts ? date($kl ? 'd.m.Y \k\l. H:i' : 'd.m.Y', (int)$ts) : ''; }
function distnavn($l, $id) {
    foreach ($l['distances'] ?? [] as $d) if ($d['id'] === $id) return $d['name'];
    return '';
}

// Bekræftelse på mail med startnummer. Afsenderen er noreply@<hjemmesidens domæne> (webhoteller kræver
// typisk en afsender på eget domæne); svar går til klubbens adresse fra RaceTimer. Returnerer true ved succes.
function send_bekraeftelse($lob, $t, $brand) {
    $enlinje = function ($s) { return trim(preg_replace('/[\r\n]+/', ' ', (string)$s)); };  // mod header-injektion
    $vaert = preg_replace('/^www\./', '', strtolower(preg_replace('/:\d+$/', '', $_SERVER['HTTP_HOST'] ?? 'localhost')));
    if (!preg_match('/^[a-z0-9.-]+$/', $vaert)) $vaert = 'localhost';
    $dist = $t['distance'] ? distnavn($lob, $t['distance']) : '';
    $emne = 'Tilmeldt: ' . $enlinje($lob['name']) . ($t['bib'] ? ' – startnummer ' . (int)$t['bib'] : '');
    $side = (!empty($_SERVER['HTTPS']) && $_SERVER['HTTPS'] !== 'off' ? 'https' : 'http') . '://' . ($_SERVER['HTTP_HOST'] ?? $vaert)
          . strtok($_SERVER['REQUEST_URI'] ?? '/tilmeld.php', '?') . '?lob=' . (int)$lob['id'];
    $tekst = "Hej " . $enlinje($t['name']) . "\n\n"
        . "Du er tilmeldt " . $enlinje($lob['name']) . ($dist !== '' ? ", $dist" : '') . ".\n"
        . "Dato: " . dato($lob['date'], true) . "\n"
        . ($t['bib'] ? "\nDit startnummer er: " . (int)$t['bib'] . "\n" : '')
        . (trim($lob['note'] ?? '') !== '' ? "\n" . trim($lob['note']) . "\n" : '')
        . "\nTilmeldingen: $side\n"
        . "\nHar du ikke selv tilmeldt dig, så svar på denne mail.\n\nVenlig hilsen\n" . $enlinje($brand) . "\n";
    $hoved = ['From: ' . mb_encode_mimeheader($enlinje($brand), 'UTF-8', 'Q') . " <noreply@$vaert>",
              'MIME-Version: 1.0', 'Content-Type: text/plain; charset=UTF-8', 'Content-Transfer-Encoding: 8bit',
              'Auto-Submitted: auto-generated'];
    $svar = $enlinje($lob['reply_to'] ?? '');
    if ($svar !== '' && filter_var($svar, FILTER_VALIDATE_EMAIL)) $hoved[] = "Reply-To: $svar";
    return @mail($t['email'], mb_encode_mimeheader($emne, 'UTF-8', 'Q'), $tekst, implode("\r\n", $hoved), "-fnoreply@$vaert");
}

// Spam-værn: højst $MAKS_PR_TIME tilmeldinger pr. IP pr. time (IP gemmes kun som hash og kun i en time)
function for_mange($mappe, $maks) {
    $fil = "$mappe/tilmeld-ip.php";
    $h = hash('sha256', ($_SERVER['REMOTE_ADDR'] ?? '') . date('Y-m-d') . __FILE__);
    $fp = fopen($fil, 'c+');
    if (!$fp) return false;
    flock($fp, LOCK_EX);
    $raw = stream_get_contents($fp);
    $liste = json_decode((string)substr($raw, strpos($raw, "\n") ?: 0), true) ?: [];
    $nu = time();
    foreach ($liste as $k => $tider) {
        $liste[$k] = array_values(array_filter($tider, function ($t) use ($nu) { return $t > $nu - 3600; }));
        if (!$liste[$k]) unset($liste[$k]);
    }
    $stop = count($liste[$h] ?? []) >= $maks;
    if (!$stop) $liste[$h][] = $nu;
    ftruncate($fp, 0); rewind($fp);
    fwrite($fp, "<?php http_response_code(404); exit; ?>\n" . json_encode($liste));
    flock($fp, LOCK_UN); fclose($fp);
    return $stop;
}

$lob_id = (int)($_GET['lob'] ?? $_POST['lob'] ?? 0);
if (!$lob_id && count($alle) === 1) $lob_id = array_key_first($alle);
$lob = $alle[$lob_id] ?? null;
$fejl = [];
$tak = null;
$mail = null;  // null = ingen bekræftelse, true = sendt, false = fejlede
$v = ['name' => '', 'sex' => '', 'birth_year' => '', 'club' => '', 'email' => '', 'distance' => ''];

if ($lob && ($_SERVER['REQUEST_METHOD'] ?? '') === 'POST') {
    foreach ($v as $k => $_) $v[$k] = trim((string)($_POST[$k] ?? ''));
    $nu = time();
    if (!aaben($lob)) $fejl[] = 'Tilmeldingen er lukket.';
    // robotter udfylder det skjulte felt eller sender formularen på under 3 sekunder
    if (($_POST['website'] ?? '') !== '' || $nu - (int)($_POST['t'] ?? 0) < 3) $fejl[] = 'Prøv igen om lidt.';
    if (mb_strlen($v['name']) < 2 || mb_strlen($v['name']) > 100) $fejl[] = 'Skriv dit fulde navn.';
    if (!in_array($v['sex'], ['Mand', 'Kvinde', 'Andet'], true)) $fejl[] = 'Vælg køn.';
    if (!filter_var($v['email'], FILTER_VALIDATE_EMAIL) || strlen($v['email']) > 200) $fejl[] = 'Skriv en gyldig e-mail.';
    $by = ($lob['birth_year'] ?? 'required');
    if ($by === 'off') $v['birth_year'] = '';
    elseif ($v['birth_year'] !== '' || $by === 'required') {
        $aar = (int)$v['birth_year'];
        if ($aar < 1900 || $aar > (int)date('Y')) $fejl[] = 'Skriv dit fødselsår (fx 1985).';
    }
    if (mb_strlen($v['club']) > 100) $fejl[] = 'Klubnavnet er for langt.';
    if (!empty($lob['distances']) && distnavn($lob, $v['distance']) === '') $fejl[] = 'Vælg distance.';
    if (empty($lob['distances'])) $v['distance'] = '';
    if (empty($_POST['samtykke'])) $fejl[] = 'Sæt flueben ved samtykket.';
    $alle_t = $fejl ? [] : tilmeldinger($mappe, $lob_id);
    foreach ($alle_t as $t) {
        if (mb_strtolower($t['email']) === mb_strtolower($v['email']) && mb_strtolower($t['name']) === mb_strtolower($v['name'])) {
            $fejl[] = 'Du er allerede tilmeldt.';
            break;
        }
    }
    if (!$fejl && for_mange($mappe, $MAKS_PR_TIME)) $fejl[] = 'For mange tilmeldinger fra din forbindelse – prøv igen senere.';
    if (!$fejl) {
        $fil = "$mappe/tilmeld-$lob_id.php";
        if (!is_dir($mappe)) @mkdir($mappe, 0755);
        $fp = @fopen($fil, 'c+');
        if (!$fp) {
            $fejl[] = 'Tilmeldingen kunne ikke gemmes. Kontakt arrangøren.';
        } else {
            flock($fp, LOCK_EX);
            $linjer = array_filter(explode("\n", stream_get_contents($fp)));
            $id = 0;
            // startnummer: næste efter det højeste, der er brugt – her eller på Pi'en
            $bib = null;
            if (!empty($lob['auto_bib'])) {
                $hoejeste = max(array_merge([(int)($lob['bib_from'] ?? 1) - 1], array_map('intval', $lob['taken_bibs'] ?? [])));
                foreach (array_slice($linjer, 1) as $l) $hoejeste = max($hoejeste, (int)(json_decode($l, true)['bib'] ?? 0));
                $bib = $hoejeste + 1;
            }
            foreach (array_slice($linjer, 1) as $l) $id = max($id, (int)(json_decode($l, true)['id'] ?? 0));
            // id stiger altid (også hvis filen er slettet og startet forfra), så Pi'en aldrig springer en over
            $t = ['id' => max($id + 1, (int)floor(microtime(true) * 1000)), 'ts' => time(), 'bib' => $bib, 'name' => $v['name'], 'sex' => $v['sex'],
                  'birth_year' => $v['birth_year'] !== '' ? (int)$v['birth_year'] : null, 'club' => $v['club'],
                  'email' => $v['email'], 'distance' => $v['distance'] ?: null];
            if (!$linjer) fwrite($fp, "<?php http_response_code(404); exit; ?>\n");
            fseek($fp, 0, SEEK_END);
            fwrite($fp, json_encode($t, JSON_UNESCAPED_UNICODE) . "\n");
            fflush($fp); flock($fp, LOCK_UN); fclose($fp);
            $tak = $t;
            $mail = !empty($lob['confirm_email']) ? send_bekraeftelse($lob, $t, $brand) : null;
        }
    }
}
$vis_liste = $lob && !empty($lob['public_list']);
$deltagere = $vis_liste ? tilmeldinger($mappe, $lob_id) : [];
usort($deltagere, function ($a, $b) { return strcoll(mb_strtolower($a['name']), mb_strtolower($b['name'])); });
?><!doctype html>
<html lang="da">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex">
<title><?= $lob ? 'Tilmelding: ' . e($lob['name']) : 'Tilmelding' ?></title>
<style>
:root{--bg:#111814;--card:#1a231e;--head:#212c26;--line:#2e3a33;--text:#f3f1ec;--muted:#a2aca5;--orange:#e5682a;--cream:#f6efe3;--green:#3fc56b;--red:#ef5b5b}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
header{background:var(--cream);border-bottom:3px solid var(--orange);padding:14px 20px;color:#0c1b14;font-weight:800;font-size:24px;font-style:italic}
main{max-width:720px;margin:0 auto;padding:16px}h1{margin:8px 0 4px;font-size:28px}.sub{color:var(--muted);margin-bottom:16px}
.card{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:18px;margin-bottom:16px}
label{display:block;font-weight:600;font-size:14px;margin-bottom:12px}label small{font-weight:400;color:var(--muted)}
input,select{display:block;width:100%;margin-top:6px;padding:11px 12px;border-radius:10px;border:1px solid var(--line);background:var(--bg);color:var(--text);font-size:16px}
.row{display:grid;grid-template-columns:1fr 1fr;gap:12px}@media(max-width:520px){.row{grid-template-columns:1fr}}
.chk{display:flex;gap:10px;align-items:flex-start;font-weight:400}.chk input{width:auto;margin-top:3px}
button{background:var(--orange);color:#fff;border:0;border-radius:12px;padding:13px 22px;font-size:17px;font-weight:700;cursor:pointer}
.fejl{background:#3a1414;border:1px solid var(--red);color:#ffc9c9;border-radius:12px;padding:12px 16px;margin-bottom:16px}
.ok{background:#12301d;border:1px solid var(--green);border-radius:12px;padding:16px;margin-bottom:16px}
.bib{font-size:20px;margin:10px 0 6px}.bib b{font-size:34px;color:var(--orange);margin-left:6px}.note{white-space:pre-line}.muted{color:var(--muted)}.hp{position:absolute;left:-9999px}
table{width:100%;border-collapse:collapse}th,td{text-align:left;padding:9px 8px;border-top:1px solid var(--line)}th{color:var(--muted);border-top:0}
a{color:var(--text)}ul.loeb{list-style:none;padding:0}ul.loeb li{margin:10px 0}
</style>
</head>
<body>
<header><?= e($brand) ?></header>
<main>
<?php if (!$lob): ?>
  <h1>Tilmelding</h1>
  <?php $aabne = array_filter($alle, 'aaben'); ?>
  <?php if (!$aabne): ?><p class="muted">Der er ingen løb med åben tilmelding lige nu.</p><?php else: ?>
  <ul class="loeb"><?php foreach ($aabne as $id => $l): ?>
    <li class="card"><a href="?lob=<?= (int)$id ?>"><b><?= e($l['name']) ?></b></a>
      <div class="muted"><?= dato($l['date']) ?><?= !empty($l['deadline']) ? ' · tilmelding senest ' . dato($l['deadline'], true) : '' ?></div></li>
  <?php endforeach; ?></ul>
  <?php endif; ?>
<?php else: ?>
  <h1><?= e($lob['name']) ?></h1>
  <div class="sub"><?= dato($lob['date'], true) ?><?= !empty($lob['deadline']) ? ' · tilmelding senest ' . dato($lob['deadline'], true) : '' ?></div>
  <?php if ($tak): ?>
    <div class="ok"><b>Tak, <?= e($tak['name']) ?> – du er tilmeldt<?= $tak['distance'] ? ' ' . e(distnavn($lob, $tak['distance'])) : '' ?>.</b>
      <?php if ($tak['bib']): ?><div class="bib">Dit startnummer er <b><?= (int)$tak['bib'] ?></b></div><?php endif; ?>
      <span class="muted"><?= $mail === true ? 'Vi har sendt en bekræftelse til ' . e($tak['email']) . '. Kig evt. i spam-mappen.'
        : ($mail === false ? 'Bekræftelsen kunne ikke sendes på mail' : 'Du får ikke en bekræftelse på mail')
          . ($tak['bib'] ? ', så skriv nummeret ned eller tag et billede af siden.' : '.') ?></span></div>
  <?php elseif (!aaben($lob)): ?>
    <div class="card">Tilmeldingen er lukket.</div>
  <?php else: ?>
    <?php if ($fejl): ?><div class="fejl"><?= implode('<br>', array_map('e', array_unique($fejl))) ?></div><?php endif; ?>
    <?php if (trim($lob['note'] ?? '') !== ''): ?><div class="card note"><?= e($lob['note']) ?></div><?php endif; ?>
    <form method="post" class="card" autocomplete="on">
      <input type="hidden" name="lob" value="<?= (int)$lob_id ?>">
      <input type="hidden" name="t" value="<?= time() ?>">
      <label class="hp" aria-hidden="true">Lad dette felt stå tomt<input name="website" tabindex="-1" autocomplete="off"></label>
      <label>Navn<input name="name" required maxlength="100" autocomplete="name" value="<?= e($v['name']) ?>"></label>
      <div class="row">
        <label>Køn<select name="sex" required><option value="">Vælg</option>
          <?php foreach (['Mand', 'Kvinde', 'Andet'] as $k): ?><option <?= $v['sex'] === $k ? 'selected' : '' ?>><?= $k ?></option><?php endforeach; ?></select></label>
        <?php if (($lob['birth_year'] ?? 'required') !== 'off'): ?>
        <label>Fødselsår<?= $lob['birth_year'] === 'optional' ? ' <small>(valgfrit)</small>' : '' ?>
          <input name="birth_year" inputmode="numeric" pattern="(19|20)[0-9]{2}" maxlength="4" placeholder="fx 1985"
                 <?= $lob['birth_year'] === 'required' ? 'required' : '' ?> value="<?= e($v['birth_year']) ?>"></label>
        <?php endif; ?>
      </div>
      <?php if (!empty($lob['distances'])): ?>
      <label>Distance<select name="distance" required><option value="">Vælg</option>
        <?php foreach ($lob['distances'] as $d): ?><option value="<?= e($d['id']) ?>" <?= $v['distance'] === $d['id'] ? 'selected' : '' ?>><?= e($d['name']) ?></option><?php endforeach; ?></select></label>
      <?php endif; ?>
      <label>Klub <small>(valgfrit)</small><input name="club" maxlength="100" value="<?= e($v['club']) ?>"></label>
      <label>E-mail<input name="email" type="email" required maxlength="200" autocomplete="email" value="<?= e($v['email']) ?>"></label>
      <label class="chk"><input type="checkbox" name="samtykke" value="1" required>
        <span>Jeg giver samtykke til, at mine oplysninger bruges til tidtagning og resultater for dette løb. Navn, køn, klub og
        <?= !empty($lob['distances']) ? 'distance' : 'resultat' ?> vises i resultatlisten<?= $vis_liste ? ' og på deltagerlisten herunder' : '' ?>.
        <?= !empty($lob['confirm_email']) ? 'Du får en bekræftelse på e-mail. ' : '' ?>E-mail og fødselsår vises aldrig offentligt og slettes fra hjemmesiden senest <?= (int)($lob['delete_days'] ?? 30) ?> dage efter løbet.</span></label>
      <button>Tilmeld</button>
    </form>
  <?php endif; ?>
  <?php if ($vis_liste): ?>
    <h2>Tilmeldte (<?= count($deltagere) ?>)</h2>
    <?php if ($deltagere): ?><div class="card" style="padding:6px 12px"><table>
      <tr><?= !empty($lob['auto_bib']) ? '<th>Nr</th>' : '' ?><th>Navn</th><th>Klub</th><?= !empty($lob['distances']) ? '<th>Distance</th>' : '' ?></tr>
      <?php foreach ($deltagere as $t): ?><tr><?= !empty($lob['auto_bib']) ? '<td class="muted">' . (int)($t['bib'] ?? 0) . '</td>' : '' ?><td><?= e($t['name']) ?></td><td class="muted"><?= e($t['club'] ?? '') ?></td>
        <?= !empty($lob['distances']) ? '<td>' . e(distnavn($lob, $t['distance'] ?? '')) . '</td>' : '' ?></tr><?php endforeach; ?>
    </table></div><?php else: ?><p class="muted">Ingen endnu – vær den første!</p><?php endif; ?>
  <?php endif; ?>
  <?php if (count(array_filter($alle, 'aaben')) > 1): ?><p><a href="?">← Andre løb</a></p><?php endif; ?>
<?php endif; ?>
</main>
</body>
</html>
