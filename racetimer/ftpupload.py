"""FTP-destination: Pi'en laver en færdig resultatside og uploader den.

Til almindelige webhoteller (fx klubbens hjemmeside), hvor man kun har FTP.
Der uploades:

* index.html          – selvstændig resultatside (dark mode, opdaterer sig selv)
* resultater.json     – samme data som JSON, hvis siden vil bruge dem selv
* slut-<løb>.html     – kopi af slutresultatet, når løbet er afsluttet

Adressen angives som ftps://vært/mappe (anbefalet, krypteret) eller ftp://vært/mappe.
Filer skrives først under et midlertidigt navn og omdøbes bagefter, så besøgende
aldrig ser en halvt uploadet side.
"""
import base64
import ftplib
import html
import os
import io
import json
import re
import ssl
import time
from urllib.parse import unquote, urlparse

LAP_TYPES = ("backyard", "backyard_custom", "timed", "record")



def _brand_header():
    """Klubbens logo indlejret i siden (så den kan uploades som én fil) – ellers klubnavnet som tekst."""
    from . import branding
    p = branding.logo_path()
    if p:
        ext = os.path.splitext(p)[1].lower()
        mime = branding.IMAGE_TYPES.get(ext, "image/png")
        with open(p, "rb") as f:
            src = f"data:{mime};base64," + base64.b64encode(f.read()).decode()
        return f'<img src="{src}" alt="{html.escape(branding.get()["name"])}">'
    return f'<span class="brand">{html.escape(branding.get()["name"])}</span>'


def _hms(sec, force_h=False):
    if sec is None:
        return "–"
    sec = int(max(0, sec))
    h, m, s = sec // 3600, sec % 3600 // 60, sec % 60
    return f"{h}:{m:02d}:{s:02d}" if h or force_h else f"{m}:{s:02d}"


def _km(v):
    return f"{(v or 0):.1f}".replace(".", ",")


def _clock(ts):
    return time.strftime("%H:%M", time.localtime(ts)) if ts else "–"


def _brand_name():
    from . import branding
    return branding.get()["name"]


def slug(name):
    s = re.sub(r"[^a-z0-9]+", "-", name.lower().replace("æ", "ae").replace("ø", "oe").replace("å", "aa"))
    return s.strip("-") or "loeb"


SPLASH_CSS = """
.teaser{position:absolute;bottom:6vh;left:50%;transform:translateX(-50%);width:min(92%,760px);padding:20px 28px;border-radius:20px;text-align:center;color:#fff;background:rgba(10,16,13,.74);border:1px solid rgba(255,255,255,.14);box-shadow:0 18px 60px rgba(0,0,0,.45)}
.splash.plain .teaser{position:static;transform:none;margin:22px auto 0}
.teaser .tk{color:var(--orange);font-weight:800;letter-spacing:.14em;text-transform:uppercase;font-size:13px}
.teaser .tn{font-weight:800;font-size:clamp(26px,5vw,52px);line-height:1.1;margin-top:4px}.teaser .tw{font-size:clamp(15px,2.2vw,22px);font-weight:600;opacity:.9;margin-top:6px}
.fb{width:1.15em;height:1.15em;vertical-align:-.22em}.teaser .tsu{margin-top:14px}.teaser .tsu a{display:inline-block;background:var(--orange);color:#fff;font-weight:700;padding:10px 22px;border-radius:12px;text-decoration:none}
.teaser .tc{font-size:clamp(26px,5vw,48px);font-weight:800;margin-top:6px;color:var(--cream);font-variant-numeric:tabular-nums}.teaser .ts{opacity:.75;margin-top:8px}
:root{--bg:#111814;--orange:#e5682a;--cream:#f6efe3}*{box-sizing:border-box}
body{margin:0;min-height:100vh;min-height:100dvh;display:flex;flex-direction:column;background:var(--bg);color:#fff;font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
header{background:var(--cream);border-bottom:3px solid var(--orange);padding:14px 20px}header img{height:40px;display:block}
.brand{font-weight:800;font-size:26px;color:#0c1b14;font-style:italic}
.splash{position:relative;flex:1;min-height:320px;background:#0c0e11 center/cover no-repeat;display:flex;align-items:flex-end}
.splash.plain{align-items:center;justify-content:center;flex-direction:column;text-align:center}
.splash.plain .pn{font-weight:800;font-style:italic;font-size:clamp(36px,8vw,110px);letter-spacing:-.03em;line-height:1.05;padding:0 5vw}
.txt{width:100%;padding:12vh 5vw 8vh;background:linear-gradient(to top,rgba(0,0,0,.78),rgba(0,0,0,.45) 55%,transparent);
  text-align:center;font-weight:800;font-size:clamp(24px,4.6vw,64px);line-height:1.12;white-space:pre-line;text-shadow:0 2px 18px rgba(0,0,0,.5)}
.splash.plain .txt{background:none;padding:18px 5vw 0;color:var(--orange);font-size:clamp(16px,2.4vw,30px);font-weight:600}
"""


DAGE = ("mandag", "tirsdag", "onsdag", "torsdag", "fredag", "lørdag", "søndag")
MDR = ("januar", "februar", "marts", "april", "maj", "juni", "juli", "august", "september", "oktober", "november", "december")


FB_ICON = ('<svg class="fb" viewBox="0 0 24 24" aria-label="Facebook" role="img"><circle cx="12" cy="12" r="12" fill="#1877F2"/><path fill="#fff" d="M15.1 12.5h-2.3V20H9.7v-7.5H8.2V9.8h1.5V8.1c0-1.4.7-3.3 3.3-3.3h2.3v2.6h-1.7c-.3 0-.8.2-.8.8v1.6h2.6z"/></svg>')


def signup_icon(url):
    """Facebooks logo ved et Facebook-link, ellers det almindelige ikon."""
    host = (urlparse(url or "").hostname or "").lower()
    return FB_ICON if re.search(r"(^|\.)(facebook\.com|fb\.com|fb\.me|fb\.watch)$", host) else "📝"


def _teaser_html(t):
    """Planlagt løb før indtjekningen: navn, starttid, nedtælling og antal tilmeldte – ingen deltagerliste."""
    e = html.escape
    start = t.get("start")
    if start:
        lt = time.localtime(start)
        when = f"{DAGE[lt.tm_wday].capitalize()} {lt.tm_mday}. {MDR[lt.tm_mon - 1]} kl. {time.strftime('%H.%M', lt)}"
    else:
        when = "Starttidspunktet kommer snart"
    sub = "  ·  ".join(x for x in (f"{t['count']} tilmeldte" if t.get("count") else "", " · ".join(e(d) for d in t.get("distances") or [])) if x)
    cd = (f'<div class="tc" data-start="{int(start)}"></div><script>(function(){{var el=document.querySelector(".teaser .tc"),s=+el.dataset.start;'
          'function p(n){return(n<10?"0":"")+n}function t(){var l=Math.max(0,Math.round(s-Date.now()/1000)),d=Math.floor(l/86400);'
          'el.textContent=l<=0?"":d>=1?"om "+d+(d===1?" dag":" dage"):p(Math.floor(l/3600))+":"+p(Math.floor(l%3600/60))+":"+p(l%60)}'
          't();setInterval(t,1000)})();</script>') if start else ""
    su = t.get("signup") or {}  # FTP-siden har ingen formular – kun et link andetsteds, fx en Facebook-begivenhed
    btn = (f'<div class="tsu"><a href="{e(su["url"])}" target="_blank" rel="noopener">{signup_icon(su["url"])} {e(su.get("text") or "Tilmeld dig")}</a></div>'
           if str(su.get("url") or "").startswith(("http://", "https://")) else "")
    return (f'<div class="teaser"><div class="tk">Næste løb</div><div class="tn">{e(t.get("name") or "")}</div><div class="tw">{e(when)}</div>'
            f'{cd}' + (f'<div class="ts">{sub}</div>' if sub else "") + btn + "</div>")


def render_splash_html(payload, image=None, refresh_sec=0, teaser=None):
    """Ingen aktive løb: splash-billede (eller klubnavnet) med den valgte tekst – evt. med en teaser om næste løb."""
    e = html.escape
    b = payload.get("branding") or {}
    text = b.get("splash_text") or ""
    refresh = f'<meta http-equiv="refresh" content="{int(refresh_sec)}">' if refresh_sec else ""
    tz = _teaser_html(teaser) if teaser else ""
    if image:
        # teaseren står i stedet for splash-teksten
        body = f'<div class="splash" style="background-image:url(\'{image}\')">{tz}' + (f'<div class="txt">{e(text)}</div>' if text and not tz else "") + "</div>"
    else:
        body = (f'<div class="splash plain"><div class="pn">{e(_brand_name())}</div>'
                + (tz or f'<div class="txt">{e(text or "Venter på næste løb")}</div>') + "</div>")
    return f"""<!doctype html>
<html lang="da"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
{refresh}<title>{e(_brand_name())}</title><style>{SPLASH_CSS}</style></head><body>
<header>{_brand_header()}</header>{body}</body></html>"""


COUNTDOWN_CSS = """
.cd{display:flex;align-items:center;gap:18px;background:var(--card);border:1px solid var(--line);border-radius:14px;padding:12px 18px;margin-bottom:14px}
.cd svg{width:72px;height:72px;transform:rotate(-90deg);flex:none}.cd circle{fill:none;stroke-width:10}.cd .bg{stroke:var(--line)}.cd .fg{stroke:#3fc56b;stroke-linecap:round}
.cdk{color:var(--muted);font-size:13px;font-weight:600;text-transform:uppercase;letter-spacing:.06em}.cdv{font-size:clamp(30px,6vw,52px);font-weight:700;font-variant-numeric:tabular-nums}
.cd.soon .fg{stroke:var(--orange)}.cd.soon .cdv{color:var(--orange)}.cd.last .fg{stroke:#ef5b5b}.cd.last .cdv{color:#ef5b5b}
"""
COUNTDOWN_JS = """<script>
document.querySelectorAll('.cd').forEach(function (el) {
  var end = +el.dataset.end, total = +el.dataset.total, C = 2 * Math.PI * 52, fg = el.querySelector('.fg');
  fg.style.strokeDasharray = C;
  function p(n) { return (n < 10 ? '0' : '') + n; }
  function tick() {
    var left = Math.max(0, end - Date.now() / 1000), s = Math.round(left), f = total ? Math.min(1, left / total) : 0;
    el.querySelector('.cdv').textContent = p(Math.floor(s / 3600)) + ':' + p(Math.floor(s % 3600 / 60)) + ':' + p(s % 60);
    fg.style.strokeDashoffset = C * (1 - f);
    el.className = 'cd' + (left <= Math.min(900, total * 0.05) ? ' last' : f <= 0.1 ? ' soon' : '');
  }
  tick(); setInterval(tick, 1000);
});
</script>"""


def _countdown(race, info, final):
    """Nedtæller med ring: tid tilbage af løbet (tidsløb / samlet tid) eller til næste yard (backyard)."""
    if final or info.get("phase") != "running":
        return ""
    if (race["type"] == "timed" or (info.get("continuous") and info.get("end_mode") == "duration")) and info.get("end_at"):
        label, end, total = "Tid tilbage", info["end_at"], info.get("duration_sec") or 0
    elif race["type"].startswith("backyard") and not info.get("continuous") and info.get("next_start"):
        label, end, total = "Næste start", info["next_start"], info.get("interval_sec") or 3600
    else:
        return ""
    return (f'<div class="cd" data-end="{float(end)}" data-total="{float(total)}"><svg viewBox="0 0 120 120" aria-hidden="true">'
            f'<circle class="bg" cx="60" cy="60" r="52"/><circle class="fg" cx="60" cy="60" r="52"/></svg>'
            f'<div><div class="cdk">{label}</div><div class="cdv">--:--:--</div></div></div>')


def render_html(payload, refresh_sec=0):
    race, info, rows = payload.get("race"), payload.get("info") or {}, payload.get("results") or []
    e = html.escape
    updated = time.strftime("%d.%m.%Y kl. %H:%M", time.localtime(payload["sent_at"]))
    final = payload["event"] == "final"
    if info.get("distances"):  # flere distancer: et afsnit med egen stilling pr. distance
        sections = "".join(
            f'<h2 class="dist">{e(d["name"])} <small>· {d.get("count", 0)} deltagere'
            f'{" · start " + _clock(d["started_at"]) if d.get("started_at") else ""}</small></h2>' +
            _section(race, d, [r for r in rows if r.get("distance") == d["id"]], final)
            for d in info["distances"])
    else:
        sections = _section(race, info, rows, final)
    refresh = f'<meta http-equiv="refresh" content="{int(refresh_sec)}">' if refresh_sec and not final else ""
    status = "Endelige resultater" if final else ("Live" if race["status"] == "running" else "Foreløbige resultater")
    return f"""<!doctype html>
<html lang="da"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
{refresh}<title>{e(race['name'])} – resultater</title>
<style>
:root{{--bg:#111814;--card:#1a231e;--head:#212c26;--line:#2e3a33;--text:#f3f1ec;--muted:#a2aca5;--dim:#6b766f;--orange:#e5682a;--cream:#f6efe3}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--text);font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}}
header{{background:var(--cream);border-bottom:3px solid var(--orange);padding:14px 20px}}header img{{height:40px;display:block}}.brand{{font-weight:800;font-size:26px;color:#0c1b14;font-style:italic}}
h1{{margin:0;font-size:28px}}.sub{{color:var(--muted);margin:6px 0 16px}}h2.dist{{margin:26px 0 10px;font-size:22px}}h2.dist small{{color:var(--muted);font-weight:500;font-size:14px}}
main{{max-width:1100px;margin:0 auto;padding:16px}}.pill{{display:inline-block;font-size:12px;font-weight:700;padding:3px 10px;border-radius:99px;background:{'#5aa3ff' if final else '#3fc56b'};color:#06121f;margin-right:8px}}
.sum{{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:14px 18px;margin-bottom:14px;font-size:20px;font-weight:600}}
.card{{background:var(--card);border:1px solid var(--line);border-radius:18px;overflow-x:auto}}
table{{width:100%;border-collapse:collapse}}th{{background:var(--head);color:var(--muted);text-align:left;padding:12px 14px;white-space:nowrap}}
td{{padding:11px 14px;border-top:1px solid var(--line);font-variant-numeric:tabular-nums}}td.r,th.r{{text-align:right;white-space:nowrap}}
td.name{{font-weight:600}}.bib{{color:var(--muted);font-weight:500;font-size:.85em;margin-right:.45em}}.club{{display:block;color:var(--muted);font-weight:400;font-size:.8em}}
td.st{{white-space:nowrap}}tr.out td{{color:var(--dim)}}.dot{{display:inline-block;width:.55em;height:.55em;border-radius:50%;margin-right:.5em;background:#8a9099}}
.dot.active{{background:#3fc56b}}.dot.resting{{background:#2bb3a3}}.dot.winner{{background:#f2c14e}}.dot.finished{{background:#5aa3ff}}.dot.rtc,.dot.dsq{{background:#ef5b5b}}
footer{{color:var(--muted);font-size:13px;padding:14px 4px}}
{COUNTDOWN_CSS}</style></head><body>
<header>{_brand_header()}</header>
<main><h1>{e(race['name'])}</h1><div class="sub"><span class="pill">{status}</span>{e(info.get('type_label', ''))} · start {_clock(race.get('started_at'))}</div>
{sections}
<footer>Opdateret {updated} · {e(_brand_name())}</footer></main>{COUNTDOWN_JS if 'class="cd"' in sections else ""}</body></html>"""


def _section(race, info, rows, final):
    """Opsummering, nedtæller og resultattabel – for hele løbet eller én distance."""
    e = html.escape
    typ = race["type"]
    lap = typ in LAP_TYPES

    summary = []
    if info.get("continuous"):
        goal = f"flest omgange på {_hms(info.get('duration_sec'), True)}" if info.get("end_mode") == "duration" \
            else f"først til {info.get('max_yards')} omgange"
        if info.get("phase") == "ended" and info.get("leader"):
            summary.append(f"🏁 Vinder: {e(info['leader'])} – {info.get('leader_laps')} omgange ({goal})")
        else:
            summary.append(f"{goal.capitalize()} · {info.get('on_course', 0)} på ruten")
    elif typ.startswith("backyard"):
        if info.get("winner"):
            summary.append(f"🏆 Vinder: {e(info['winner'])} – {info.get('completed_yards')} yards")
        elif info.get("no_winner"):
            summary.append(f"Løbet er slut – ingen vinder ({info.get('completed_yards')} yards)")
        elif info.get("phase") == "running":
            summary.append(f"Yard {info.get('yard')} · {info.get('runners_left')} tilbage")
    elif typ == "record":
        summary.append(f"{e(info.get('record_label') or 'Årets rekord')}: {_km(info.get('total_km'))} km")
    elif typ == "timed" and info.get("total_km") is not None:
        summary.append(f"Samlet distance: {_km(info.get('total_km'))} km")

    cont = bool(info.get("continuous"))
    head = ["#", "Navn", "Køn", "Status"] + (["Omgange", "Distance", "Sidste omg."] + (["Tid"] if cont else []) if lap else ["Tid"])
    body = []
    for r in rows:
        out = r["status"] in ("dnf", "rtc", "dsq", "dns")
        name = (f'<span class="bib">{r["bib"]}</span>' if r.get("bib") is not None else "") + e(r["name"])
        if r.get("club"):
            name += f'<span class="club">{e(r["club"])}</span>'
        if r.get("dogs"):
            name += f'<span class="club" style="color:var(--orange)">🐕 {" & ".join(e(d) for d in r["dogs"])}</span>'
        cells = [str(r["place"]) if r.get("place") is not None else "–", name, e(r.get("sex") or "") + (f' <span class="bib">{e(r["class"])}</span>' if r.get("class") else ""), f'<i class="dot {r["status"]}"></i>{e(r["status_label"])}']
        total = _hms(r.get("total_time"), True) if r.get("total_time") is not None else "–"
        cells += ([str(r["laps"]), f'{_km(r["distance_km"])} km', _hms(r.get("last_lap"))] + ([total] if cont else [])
                  if lap else [total])
        cls = ["", "name", "", "st"] + ["r"] * (len(cells) - 4)
        body.append(f'<tr class="{"out" if out else ""}">' +
                    "".join(f'<td class="{c}">{v}</td>' for c, v in zip(cls, cells)) + "</tr>")

    ths = "".join(f'<th class="{"r" if i > 3 else ""}">{h}</th>' for i, h in enumerate(head))
    return ("".join(f'<div class="sum">{x}</div>' for x in summary) + _countdown(race, info, final) +
            f'<div class="card"><table><thead><tr>{ths}</tr></thead>'
            f'<tbody>{"".join(body) or "<tr><td colspan=7>Ingen deltagere endnu</td></tr>"}</tbody></table></div>')


class _FTP_TLS(ftplib.FTP_TLS):
    """FTPS der genbruger TLS-sessionen på dataforbindelsen.

    Mange webhoteller (fx vsftpd med require_ssl_reuse) afviser ellers uploads
    med "522 SSL connection failed; session reuse required".
    """

    def ntransfercmd(self, cmd, rest=None):
        conn, size = ftplib.FTP.ntransfercmd(self, cmd, rest)
        if self._prot_p:
            conn = self.context.wrap_socket(conn, server_hostname=self.host, session=self.sock.session)
        return conn, size


def upload(dest, payload, splash_file=False):
    """Upload index.html + resultater.json (+ slut-kopi) til FTP/FTPS-destinationen.

    Uden aktivt løb er index.html en splash-side. splash_file=True uploader også splash-billedet
    (kun når udseendet er ændret – billedet kan være stort)."""
    from . import branding
    u = urlparse(dest["url"])
    if u.scheme not in ("ftp", "ftps") or not u.hostname:
        raise RuntimeError("FTP-adressen skal se sådan ud: ftps://ftp.example.dk/mappe")
    if u.scheme == "ftps":
        ftp = _FTP_TLS(timeout=20, context=ssl.create_default_context())
    else:
        ftp = ftplib.FTP(timeout=20)
    try:
        ftp.connect(u.hostname, u.port or 21)
        ftp.login(dest.get("username") or "anonymous", dest.get("key") or "")
        if u.scheme == "ftps":
            ftp.prot_p()  # krypter også selve filerne
        folder = unquote(u.path or "/")
        if folder not in ("", "/"):
            _cd_make(ftp, folder)
        refresh = int(dest.get("interval_sec") or 0)
        data = {k: v for k, v in payload.items() if k != "branding"}
        data["branding"] = {k: v for k, v in (payload.get("branding") or {}).items() if k != "images"}
        files = {"resultater.json": json.dumps(data, ensure_ascii=False, indent=1)}
        teaser = (payload.get("info") or {}).get("teaser") if payload.get("race") else None
        if payload.get("race") and not teaser:
            files["index.html"] = render_html(payload, refresh_sec=max(refresh, 15) if refresh else 0)
        else:
            image = None
            if (payload.get("branding") or {}).get("splash") == "image":
                path = branding.splash_path()
                image = "splash" + os.path.splitext(path)[1].lower()
                if splash_file:
                    with open(path, "rb") as f:
                        files[image] = f.read()
                image += f"?v={branding.get()['v']}"
            files["index.html"] = render_splash_html(payload, image, refresh_sec=max(refresh, 15) if refresh else 60, teaser=teaser)
        if payload["event"] == "final" and payload.get("race"):
            files[f"slut-{slug(payload['race']['name'])}.html"] = files["index.html"]
        for name, text in files.items():
            tmp = f".{name}.upload"
            ftp.storbinary(f"STOR {tmp}", io.BytesIO(text if isinstance(text, bytes) else text.encode("utf-8")))
            try:
                ftp.delete(name)
            except ftplib.error_perm:
                pass  # fandtes ikke i forvejen
            ftp.rename(tmp, name)
    except ssl.SSLCertVerificationError as e:
        raise RuntimeError(f"FTPS-certifikatet kunne ikke godkendes ({e.verify_message}). "
                           "Brug værtsnavnet fra dit webhotels certifikat.") from None
    except ftplib.error_perm as e:
        raise RuntimeError(f"FTP afviste: {e}") from None
    except OSError as e:
        raise RuntimeError(f"Ingen forbindelse til FTP: {e}") from None
    finally:
        try:
            ftp.quit()
        except Exception:  # noqa: BLE001
            ftp.close()


def _cd_make(ftp, folder):
    """Gå til mappen og opret undermapper, der mangler."""
    if folder.startswith("/"):
        ftp.cwd("/")
    for part in [p for p in folder.split("/") if p]:
        try:
            ftp.cwd(part)
        except ftplib.error_perm:
            ftp.mkd(part)
            ftp.cwd(part)
