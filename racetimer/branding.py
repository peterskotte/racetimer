"""Udseende: klubnavn, logo og splash-skærm – vælges i admin (og i opsætningsguiden).

Uploadede filer ligger i datamappen (DATA_DIR/assets), så de overlever opdateringer.
Medfølgende splash-billeder ligger i static/splash/.

Har en installation en mappe "branding-local/" ved siden af programmet (ikke med i det
offentlige repo), importeres dens navn, logo og splash automatisk første gang.
"""
import json
import os
import shutil
import time

from . import db

HERE = os.path.dirname(__file__)
ASSETS = os.path.join(db.DATA_DIR, "assets")
LOCAL = os.path.join(HERE, "..", "branding-local")
BUILTIN_SPLASH = {
    "racetiming": {"label": "RaceTiming – trail og løber", "file": os.path.join(HERE, "static", "splash", "racetiming.webp")},
    "plain": {"label": "Ensfarvet med klubnavn", "file": None},
}
DEFAULT = {"name": "RaceTimer", "logo": None, "splash": "builtin:racetiming", "splash_text": "", "scan_banner": True, "v": 0}
SPLASH_TEXT_MAX = 160
IMAGE_TYPES = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}
MAX_BYTES = 8 * 1024 * 1024


def safe_asset(name):
    """Kun filer, vi selv har gemt (fx 'splash.webp') – aldrig stier ud af assets-mappen."""
    ok = name and os.path.basename(name) == name and os.path.splitext(name)[1].lower() in IMAGE_TYPES
    p = ok and os.path.join(ASSETS, name)
    return p if p and os.path.isfile(p) else None


def get():
    b = dict(DEFAULT)
    b.update(db.setting("branding") or {})
    return b


def save(**changes):
    b = get()
    b.update(changes, v=int(time.time()))  # v bruges til at bryde browserens cache
    db.set_setting("branding", b)
    return b


def public():
    """Til resultatskærm, admin og hjemmeside."""
    b = get()
    kind, _, ref = b["splash"].partition(":")
    plain = kind == "builtin" and ref == "plain"
    return {"name": b["name"], "logo": f"/branding/logo?v={b['v']}" if b["logo"] else None,
            "splash": None if plain else f"/branding/splash?v={b['v']}", "splash_choice": b["splash"],
            "splash_text": b.get("splash_text") or "", "scan_banner": b.get("scan_banner", True), "v": b["v"]}


WEB_IMAGE_MAX = 4 * 1024 * 1024  # større billeder sendes ikke til hjemmesiden (mange webhoteller har små POST-grænser)


def web_export(with_images=False):
    """Udseende til hjemmeside/spejlserver. Billeder (base64) kun når de er ændret siden sidst."""
    import base64
    b = get()
    kind, _, ref = b["splash"].partition(":")
    out = {"name": b["name"], "splash_text": b.get("splash_text") or "", "v": b["v"],
           "splash": "plain" if (kind == "builtin" and ref == "plain") else "image",
           "splash_choice": b["splash"] if kind == "builtin" else "upload", "logo": bool(b["logo"]), "images": {}}
    if with_images:
        for name, path in (("logo", logo_path()), ("splash", None if out["splash"] == "plain" else splash_path())):
            if path and os.path.getsize(path) <= WEB_IMAGE_MAX:
                with open(path, "rb") as f:
                    out["images"][name] = {"ext": os.path.splitext(path)[1].lower(), "data": base64.b64encode(f.read()).decode()}
    return out


def apply_export(e):
    """Spejlserver: brug samme udseende som Pi'en."""
    import base64
    changes = {"name": (e.get("name") or "RaceTimer")[:60], "splash_text": (e.get("splash_text") or "")[:SPLASH_TEXT_MAX]}
    imgs = e.get("images") or {}
    if "logo" in imgs:
        changes["logo"] = store_upload("logo", "logo" + imgs["logo"]["ext"], base64.b64decode(imgs["logo"]["data"]))
    elif e.get("logo") is False:
        changes["logo"] = None
    choice = e.get("splash_choice") or ""
    if choice.startswith("builtin:") and choice.partition(":")[2] in BUILTIN_SPLASH:
        changes["splash"] = choice
    elif "splash" in imgs:
        changes["splash"] = "upload:" + store_upload("splash", "splash" + imgs["splash"]["ext"], base64.b64decode(imgs["splash"]["data"]))
    save(**changes)


def logo_path():
    return safe_asset(get()["logo"])


def splash_path():
    kind, _, ref = get()["splash"].partition(":")
    if kind == "upload" and safe_asset(ref):
        return safe_asset(ref)
    f = BUILTIN_SPLASH.get(ref, {}).get("file") if kind == "builtin" else None
    return f or BUILTIN_SPLASH["racetiming"]["file"]


def store_upload(kind, filename, data):
    """Gem et uploadet logo/splash-billede i datamappen og returnér filnavnet."""
    ext = os.path.splitext(filename or "")[1].lower()
    if ext not in IMAGE_TYPES:
        raise ValueError("Billedet skal være PNG, JPG eller WebP")
    if len(data) > MAX_BYTES:
        raise ValueError("Billedet er for stort (højst 8 MB)")
    os.makedirs(ASSETS, exist_ok=True)
    for old in os.listdir(ASSETS):  # kun ét af hver slags
        if old.startswith(kind + "."):
            os.remove(os.path.join(ASSETS, old))
    name = kind + ext
    with open(os.path.join(ASSETS, name), "wb") as f:
        f.write(data)
    os.chmod(os.path.join(ASSETS, name), 0o644)
    return name


def import_local_once():
    """Første start: hent privat branding fra branding-local/ (fx en klubs egen Pi), ellers standard."""
    if db.setting("branding") is not None:
        return
    changes = {}
    cfg = os.path.join(LOCAL, "branding.json")
    if os.path.exists(cfg):
        with open(cfg) as f:
            changes.update({k: v for k, v in json.load(f).items() if k == "name"})
        os.makedirs(ASSETS, exist_ok=True)
        for kind in ("logo", "splash"):
            for ext in IMAGE_TYPES:
                src = os.path.join(LOCAL, kind + ext)
                if os.path.exists(src):
                    shutil.copyfile(src, os.path.join(ASSETS, kind + ext))
                    os.chmod(os.path.join(ASSETS, kind + ext), 0o644)
                    changes["logo" if kind == "logo" else "splash"] = kind + ext if kind == "logo" else "upload:" + kind + ext
                    break
    save(**changes)
