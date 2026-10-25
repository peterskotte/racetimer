<?php
/*
 * RaceTimer → hjemmeside: afsendelse af mails (bekræftelse på tilmelding).
 * Bruges af tilmeld.php og modtag.php – gør intet, hvis den åbnes direkte.
 *
 * Er der en mailkonto (SMTP) i data/mail.php, sendes der via den. Opsætningen laves i RaceTimer under
 * ⚙ Opsætning → Synkronisering → ✉ Mail til tilmeldinger og sendes hertil af Pi'en. Ellers bruges
 * webhotellets mail(), som mange modtagere afviser eller lægger i spam.
 */

function rt_mail_fil($mappe) { return "$mappe/mail.php"; }

// Mailopsætningen ligger efter en PHP-linje, så webserveren svarer 404, hvis nogen prøver at åbne filen
function rt_mail_opsaetning($mappe) {
    $fil = rt_mail_fil($mappe);
    if (!is_file($fil)) return null;
    $raw = file_get_contents($fil);
    $cfg = json_decode((string)substr($raw, strpos($raw, "\n") + 1), true);
    return is_array($cfg) && !empty($cfg['host']) ? $cfg : null;
}

function rt_gem_mail_opsaetning($mappe, $cfg) {
    $fil = rt_mail_fil($mappe);
    if ($cfg === null) return !is_file($fil) || @unlink($fil);
    $tmp = "$fil.tmp";
    return file_put_contents($tmp, "<?php http_response_code(404); exit; ?>\n" . json_encode($cfg, JSON_UNESCAPED_UNICODE)) !== false
        && rename($tmp, $fil);
}

function rt_enlinje($s) { return trim(preg_replace('/[\r\n]+/', ' ', (string)$s)); }  // mod header-injektion

function rt_vaert() {
    $v = preg_replace('/^www\./', '', strtolower(preg_replace('/:\d+$/', '', $_SERVER['HTTP_HOST'] ?? 'localhost')));
    return preg_match('/^[a-z0-9.-]+$/', $v) ? $v : 'localhost';
}

/*
 * Send en mail (ren tekst, UTF-8). Returnerer true – eller en fejltekst, der kan vises til admin.
 */
function rt_send_mail($mappe, $til, $emne, $tekst, $afsender_navn, $svar_til = '') {
    $til = rt_enlinje($til);
    if (!filter_var($til, FILTER_VALIDATE_EMAIL)) return 'Ugyldig modtager';
    $cfg = rt_mail_opsaetning($mappe);
    $fra = $cfg && filter_var($cfg['from_email'] ?? '', FILTER_VALIDATE_EMAIL) ? $cfg['from_email'] : 'noreply@' . rt_vaert();
    $navn = rt_enlinje(($cfg['from_name'] ?? '') ?: $afsender_navn);
    $svar_til = rt_enlinje($svar_til);
    $hoved = ['From: ' . mb_encode_mimeheader($navn, 'UTF-8', 'Q') . " <$fra>",
              'MIME-Version: 1.0', 'Content-Type: text/plain; charset=UTF-8', 'Content-Transfer-Encoding: 8bit',
              'Auto-Submitted: auto-generated'];
    if ($svar_til !== '' && filter_var($svar_til, FILTER_VALIDATE_EMAIL)) $hoved[] = "Reply-To: $svar_til";
    $emne = mb_encode_mimeheader(rt_enlinje($emne), 'UTF-8', 'Q');
    if (!$cfg) {
        return @mail($til, $emne, $tekst, implode("\r\n", $hoved), "-f$fra") ? true : 'Webhotellet afviste afsendelsen (mail())';
    }
    return rt_smtp($cfg, $fra, $til, $emne, $tekst, $hoved);
}

function rt_smtp($cfg, $fra, $til, $emne, $tekst, $hoved) {
    $sikker = $cfg['security'] ?? 'starttls';
    $port = (int)($cfg['port'] ?? 587);
    $host = rt_enlinje($cfg['host']);
    $fejl = null;
    $s = @stream_socket_client(($sikker === 'ssl' ? 'ssl://' : 'tcp://') . "$host:$port", $nr, $fejltekst, 15);
    if (!$s) return "Kan ikke forbinde til $host:$port ($fejltekst)";
    stream_set_timeout($s, 15);
    $svar = function () use ($s) {
        $alt = '';
        while (($l = fgets($s, 1024)) !== false) {
            $alt .= $l;
            if (strlen($l) < 4 || $l[3] !== '-') break;
        }
        return $alt;
    };
    $kmd = function ($linje, $forvent) use ($s, $svar) {
        if ($linje !== null) fwrite($s, $linje . "\r\n");
        $r = $svar();
        return in_array(substr($r, 0, 3), (array)$forvent, true) ? true : (trim($r) !== '' ? trim($r) : 'intet svar');
    };
    $trin = function ($r, $hvad) { return $r === true ? null : "$hvad: $r"; };
    $ehlo = 'EHLO ' . rt_vaert();
    $fejl = $trin($kmd(null, '220'), 'Forbindelse')
        ?? $trin($kmd($ehlo, '250'), 'EHLO');
    if (!$fejl && $sikker === 'starttls') {
        $fejl = $trin($kmd('STARTTLS', '220'), 'STARTTLS');
        if (!$fejl && !@stream_socket_enable_crypto($s, true, STREAM_CRYPTO_METHOD_TLS_CLIENT)) $fejl = 'TLS kunne ikke startes';
        if (!$fejl) $fejl = $trin($kmd($ehlo, '250'), 'EHLO');
    }
    if (!$fejl && ($cfg['user'] ?? '') !== '') {
        $fejl = $trin($kmd('AUTH LOGIN', '334'), 'Login')
            ?? $trin($kmd(base64_encode($cfg['user']), '334'), 'Login (brugernavn)')
            ?? $trin($kmd(base64_encode($cfg['password'] ?? ''), '235'), 'Login (adgangskode)');
    }
    if (!$fejl) {
        $fejl = $trin($kmd("MAIL FROM:<$fra>", '250'), 'Afsender')
            ?? $trin($kmd("RCPT TO:<$til>", ['250', '251']), 'Modtager')
            ?? $trin($kmd('DATA', '354'), 'DATA');
    }
    if (!$fejl) {
        $msg = array_merge(['Date: ' . date('r'), "To: <$til>", "Subject: $emne",
                            'Message-ID: <' . bin2hex(random_bytes(12)) . '@' . rt_vaert() . '>'], $hoved);
        $krop = preg_replace('/^\./m', '..', str_replace(["\r\n", "\r"], "\n", $tekst));  // linjer med punktum først
        fwrite($s, implode("\r\n", $msg) . "\r\n\r\n" . str_replace("\n", "\r\n", $krop) . "\r\n.\r\n");
        $fejl = $trin($kmd(null, '250'), 'Afsendelse');
    }
    @fwrite($s, "QUIT\r\n");
    fclose($s);
    return $fejl ?? true;
}
