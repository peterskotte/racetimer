"""Opdateringer fra GitHub Releases.

Udgiveren lægger to filer på hver release: racetimer-X.Y.Z.tar.gz og racetimer-X.Y.Z.tar.gz.sig
(lavet med tools/make-release.sh). Pi'en henter dem til datamappen, og root-hjælperen
deploy/racetimer-update kontrollerer signaturen og installerer.
"""
import json
import os
import re
import shlex
import subprocess
import time
import urllib.request

from . import db

HERE = os.path.dirname(__file__)
HELPER = "/usr/local/sbin/racetimer-update"
DOWNLOADS = os.environ.get("RACETIMER_UPDATE_DOWNLOADS", os.path.join(db.DATA_DIR, "update"))
API = os.environ.get("RACETIMER_UPDATE_API", "https://api.github.com")
_cache = {"t": 0, "v": None}


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
        with urllib.request.urlopen(req, timeout=15) as r:
            rel = json.loads(r.read())
    except OSError as e:
        return {"configured": True, "repo": repo, "current": current_version(), "error": f"Kunne ikke kontakte GitHub: {e}"}
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
        with urllib.request.urlopen(req, timeout=120) as r, open(dest, "wb") as f:
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
