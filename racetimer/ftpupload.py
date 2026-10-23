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
:root{--bg:#111814;--orange:#e5682a;--cream:#f6efe3}*{box-sizing:border-box}
body{margin:0;min-height:100vh;display:flex;flex-direction:column;background:var(--bg);color:#fff;font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
header{background:var(--cream);border-bottom:3px solid var(--orange);padding:14px 20px}header img{height:40px;display:block}
.brand{font-weight:800;font-size:26px;color:#0c1b14;font-style:italic}
.splash{position:relative;flex:1;min-height:60vh;background:#0c0e11 center/cover no-repeat;display:flex;align-items:flex-end}
.splash.plain{align-items:center;justify-content:center;flex-direction:column;text-align:center}
.splash.plain .pn{font-weight:800;font-style:italic;font-size:clamp(36px,8vw,110px);letter-spacing:-.03em;line-height:1.05;padding:0 5vw}
.txt{width:100%;padding:12vh 5vw 8vh;background:linear-gradient(to top,rgba(0,0,0,.78),rgba(0,0,0,.45) 55%,transparent);
  text-align:center;font-weight:800;font-size:clamp(24px,4.6vw,64px);line-height:1.12;white-space:pre-line;text-shadow:0 2px 18px rgba(0,0,0,.5)}
.splash.plain .txt{background:none;padding:18px 5vw 0;color:var(--orange);font-size:clamp(16px,2.4vw,30px);font-weight:600}
"""


def render_splash_html(payload, image=None, refresh_sec=0):
    """Ingen aktive løb: splash-billede (eller klubnavnet) med den valgte tekst."""
    e = html.escape
    b = payload.get("branding") or {}
    text = b.get("splash_text") or ""
    refresh = f'<meta http-equiv="refresh" content="{int(refresh_sec)}">' if refresh_sec else ""
    if image:
        body = f'<div class="splash" style="background-image:url(\'{image}\')">' + (f'<div class="txt">{e(text)}</div>' if text else "") + "</div>"
    else:
        body = f'<div class="splash plain"><div class="pn">{e(_brand_name())}</div><div class="txt">{e(text or "Venter på næste løb")}</div></div>'
    return f"""<!doctype html>
<html lang="da"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
{refresh}<title>{e(_brand_name())}</title><style>{SPLASH_CSS}</style></head><body>
<header>{_brand_header()}</header>{body}</body></html>"""


def render_html(payload, refresh_sec=0):
    race, info, rows = payload.get("race"), payload.get("info") or {}, payload.get("results") or []
    e = html.escape
    updated = time.strftime("%d.%m.%Y kl. %H:%M", time.localtime(payload["sent_at"]))
    final = payload["event"] == "final"
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
        cells = [str(r["place"]) if r.get("place") is not None else "–", name, e(r.get("sex") or ""), f'<i class="dot {r["status"]}"></i>{e(r["status_label"])}']
        total = _hms(r.get("total_time"), True) if r.get("total_time") is not None else "–"
        cells += ([str(r["laps"]), f'{_km(r["distance_km"])} km', _hms(r.get("last_lap"))] + ([total] if cont else [])
                  if lap else [total])
        cls = ["", "name", "", "st"] + ["r"] * (len(cells) - 4)
        body.append(f'<tr class="{"out" if out else ""}">' +
                    "".join(f'<td class="{c}">{v}</td>' for c, v in zip(cls, cells)) + "</tr>")

    refresh = f'<meta http-equiv="refresh" content="{int(refresh_sec)}">' if refresh_sec and not final else ""
    status = "Endelige resultater" if final else ("Live" if race["status"] == "running" else "Foreløbige resultater")
    return f"""<!doctype html>
<html lang="da"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
{refresh}<title>{e(race['name'])} – resultater</title>
<style>
:root{{--bg:#111814;--card:#1a231e;--head:#212c26;--line:#2e3a33;--text:#f3f1ec;--muted:#a2aca5;--dim:#6b766f;--orange:#e5682a;--cream:#f6efe3}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--text);font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}}
header{{background:var(--cream);border-bottom:3px solid var(--orange);padding:14px 20px}}header img{{height:40px;display:block}}.brand{{font-weight:800;font-size:26px;color:#0c1b14;font-style:italic}}
h1{{margin:0;font-size:28px}}.sub{{color:var(--muted);margin:6px 0 16px}}
main{{max-width:1100px;margin:0 auto;padding:16px}}.pill{{display:inline-block;font-size:12px;font-weight:700;padding:3px 10px;border-radius:99px;background:{'#5aa3ff' if final else '#3fc56b'};color:#06121f;margin-right:8px}}
.sum{{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:14px 18px;margin-bottom:14px;font-size:20px;font-weight:600}}
.card{{background:var(--card);border:1px solid var(--line);border-radius:18px;overflow-x:auto}}
table{{width:100%;border-collapse:collapse}}th{{background:var(--head);color:var(--muted);text-align:left;padding:12px 14px;white-space:nowrap}}
td{{padding:11px 14px;border-top:1px solid var(--line);font-variant-numeric:tabular-nums}}td.r,th.r{{text-align:right;white-space:nowrap}}
td.name{{font-weight:600}}.bib{{color:var(--muted);font-weight:500;font-size:.85em;margin-right:.45em}}.club{{display:block;color:var(--muted);font-weight:400;font-size:.8em}}
td.st{{white-space:nowrap}}tr.out td{{color:var(--dim)}}.dot{{display:inline-block;width:.55em;height:.55em;border-radius:50%;margin-right:.5em;background:#8a9099}}
.dot.active{{background:#3fc56b}}.dot.resting{{background:#2bb3a3}}.dot.winner{{background:#f2c14e}}.dot.finished{{background:#5aa3ff}}.dot.rtc,.dot.dsq{{background:#ef5b5b}}
footer{{color:var(--muted);font-size:13px;padding:14px 4px}}
</style></head><body>
<header>{_brand_header()}</header>
<main><h1>{e(race['name'])}</h1><div class="sub"><span class="pill">{status}</span>{e(info.get('type_label', ''))} · start {_clock(race.get('started_at'))}</div>{''.join(f'<div class="sum">{x}</div>' for x in summary)}
<div class="card"><table><thead><tr>{''.join(f'<th class="{"r" if i > 3 else ""}">{h}</th>' for i, h in enumerate(head))}</tr></thead>
<tbody>{''.join(body) or '<tr><td colspan="7">Ingen deltagere endnu</td></tr>'}</tbody></table></div>
<footer>Opdateret {updated} · {e(_brand_name())}</footer></main></body></html>"""


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
        if payload.get("race"):
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
            files["index.html"] = render_splash_html(payload, image, refresh_sec=max(refresh, 15) if refresh else 60)
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
