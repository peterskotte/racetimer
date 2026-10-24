"""Opdateringer fra GitHub Releases.

Udgiveren lægger to filer på hver release: racetimer-X.Y.Z.tar.gz og racetimer-X.Y.Z.tar.gz.sig
(lavet med tools/make-release.sh). Pi'en henter dem til datamappen, og root-hjælperen
deploy/racetimer-update kontrollerer signaturen og installerer.
"""
import json
import os
import re
import shlex
import socket
import subprocess
import threading
import time
import urllib.request

from . import db

HERE = os.path.dirname(__file__)
HELPER = "/usr/local/sbin/racetimer-update"
DOWNLOADS = os.environ.get("RACETIMER_UPDATE_DOWNLOADS", os.path.join(db.DATA_DIR, "update"))
API = os.environ.get("RACETIMER_UPDATE_API", "https://api.github.com")
_cache = {"t": 0, "v": None}
_v4_lock = threading.Lock()


def _urlopen(req, timeout):
    """urlopen, der prøver igen kun over IPv4, hvis forbindelsen hænger.

    Et net med halvt fungerende IPv6 (fx nogle mobil-hotspots) er en klassisk årsag til timeouts.
    """
    try:
        return urllib.request.urlopen(req, timeout=timeout)
    except OSError as e:
        if "timed out" not in str(e) and not isinstance(e, TimeoutError):
            raise
    with _v4_lock:
        orig = socket.getaddrinfo
        socket.getaddrinfo = lambda host, port, family=0, *a, **k: orig(host, port, socket.AF_INET, *a, **k)
        try:
            return urllib.request.urlopen(req, timeout=timeout)
        finally:
            socket.getaddrinfo = orig


def _net_error(e):
    """Forståelig fejl: har Pi'en slet ikke internet, eller er det kun GitHub, der ikke svarer?"""
    try:
        socket.create_connection(("1.1.1.1", 443), timeout=4).close()
        online = True
    except OSError:
        online = False
    if not online:
        return "Pi'en har ikke forbindelse til internettet. Tjek WiFi under ⚙ Opsætning → WiFi, og prøv igen."
    return (f"Pi'en har internet, men GitHub svarer ikke ({e}). Prøv igen om lidt. "
            "Fortsætter det, blokerer netværket måske github.com – prøv et andet net, fx et mobil-hotspot.")


def current_version():
    with open(os.path.join(HERE, "VERSION")) as f:
        return f.read().strip()


def release_config():
    with open(os.path.join(HERE, "release.json")) as f:
        return json.load(f)


def _ver(s):
    return tuple(int(x) for x in re.findall(r"\d+", s)[:3]) or (0,)


def check(force=False):
    """Seneste udgivelse på GitHub (caches i 30 min.)."""
    repo = (os.environ.get("RACETIMER_UPDATE_REPO") or release_config().get("repo") or "").strip()
    if not repo:
        return {"configured": False, "current": current_version()}
    if not force and _cache["v"] and time.time() - _cache["t"] < 1800:
        return _cache["v"]
    req = urllib.request.Request(f"{API}/repos/{repo}/releases/latest",
                                 headers={"Accept": "application/vnd.github+json", "User-Agent": "RaceTimer"})
    try:
        with _urlopen(req, 20) as r:
            rel = json.loads(r.read())
    except OSError as e:
        return {"configured": True, "repo": repo, "current": current_version(), "error": _net_error(e)}
    latest = (rel.get("tag_name") or "").lstrip("v")
    assets = {a["name"]: a["browser_download_url"] for a in rel.get("assets", [])}
    tar = f"racetimer-{latest}.tar.gz"
    out = {"configured": True, "repo": repo, "current": current_version(), "latest": latest,
           "notes": (rel.get("body") or "")[:4000], "published": rel.get("published_at"), "url": rel.get("html_url"),
           "available": _ver(latest) > _ver(current_version()),
           "package": assets.get(tar), "signature": assets.get(tar + ".sig")}
    _cache.update(t=time.time(), v=out)
    return out


def download(info):
    """Hent pakke og signatur til datamappen. Selve kontrollen sker i root-hjælperen."""
    if not info.get("package") or not info.get("signature"):
        raise RuntimeError("Udgivelsen mangler pakke eller signatur")
    os.makedirs(DOWNLOADS, exist_ok=True)
    for f in os.listdir(DOWNLOADS):
        os.remove(os.path.join(DOWNLOADS, f))
    paths = []
    for url, name in ((info["package"], "pakke.tar.gz"), (info["signature"], "pakke.tar.gz.sig")):
        dest = os.path.join(DOWNLOADS, name)
        req = urllib.request.Request(url, headers={"User-Agent": "RaceTimer"})
        with _urlopen(req, 120) as r, open(dest, "wb") as f:
            while True:
                chunk = r.read(65536)
                if not chunk:
                    break
                f.write(chunk)
                if f.tell() > 200 * 1024 * 1024:
                    raise RuntimeError("Pakken er for stor")
        paths.append(dest)
    return paths


def helper(*args):
    """Kald root-hjælperen (RACETIMER_UPDATE_CMD kan overstyre ved test)."""
    base = shlex.split(os.environ.get("RACETIMER_UPDATE_CMD", "")) or ["sudo", "-n", HELPER]
    if not os.environ.get("RACETIMER_UPDATE_CMD") and not os.path.exists(HELPER):
        raise RuntimeError("Opdatering via admin virker kun på en installeret Pi (hjælperen mangler – kør opdateringen én gang)")
    r = subprocess.run(base + list(args), capture_output=True, text=True, timeout=60)
    try:
        out = json.loads(r.stdout or "{}")
    except ValueError:
        raise RuntimeError((r.stderr or r.stdout or "Ukendt fejl").strip()[:300]) from None
    if not out.get("ok"):
        raise RuntimeError(out.get("error") or "Fejl i opdateringshjælperen")
    return out
