"""Løbsportal: forbind RaceTimer til en WordPress-portal med pluginet RaceTimer Portal (fx rebildtrail.dk).

Portalen er en tilføjelse, ikke en del af RaceTimer. Forbindelsen er en almindelig destination af typen
"webhook" med ekstra oplysninger under "portal". Derfor sender Pi'en resultater til portalen præcis som til
modtag.php på en hjemmeside. Det nye er kun:

* parring: arrangøren laver en kode på portalen, Pi'en sender den og får sin egen nøgle
* kobling: et løb på Pi'en kobles til et godkendt løb på portalen (og distancerne til portalens distancer)
* tilmeldinger: løb med tilmeldingsformen "portal" henter de tilmeldte fra portalen (se signup.py)
* skabeloner: Pi'ens skabeloner sendes til portalen, så arrangøren kan oprette løb ud fra dem dér

Portalen får aldrig Pi'ens mailopsætning, og chip-ID'er sendes ikke.
"""
import re
import secrets
import socket
import urllib.parse

from . import sync

DEFAULT_URL = "https://rebildtrail.dk"


def normalize_base(url):
    url = (url or "").strip().rstrip("/")
    if not url:
        raise ValueError("Skriv portalens adresse, fx rebildtrail.dk")
    if not re.match(r"^https?://", url):
        url = "https://" + url
    p = urllib.parse.urlparse(url)
    if not p.netloc or " " in url:
        raise ValueError("Adressen ser forkert ud – skriv fx rebildtrail.dk")
    return f"{p.scheme}://{p.netloc}{p.path.rstrip('/')}"


def _api_urls(base, route):
    # pæne adresser (/wp-json/…) virker ikke på alle WordPress-installationer – ?rest_route= gør altid
    return [f"{base}/wp-json/racetimer/v1/{route}", f"{base}/?rest_route=/racetimer/v1/{route}"]


def is_portal(d):
    return bool(d.get("portal")) and d.get("type") == "webhook"


def portals():
    return [d for d in sync.destinations() if is_portal(d)]


def find(did):
    return next((d for d in portals() if d["id"] == did), None)


def pair(url, code, version=""):
    """Brug en forbindelseskode fra portalen. Opretter destinationen og returnerer den."""
    base = normalize_base(url)
    code = re.sub(r"[^A-Za-z0-9]", "", code or "").upper()
    if len(code) != 8:
        raise ValueError("Koden har 8 tegn, fx K7QM-4TXD. Du får den på portalen under “Mine RaceTimere”.")
    body = {"code": code, "name": socket.gethostname() or "RaceTimer", "version": version}
    last = None
    resp = None
    for u in _api_urls(base, "pair"):
        try:
            resp = sync._post(u, body, gz=False)
            break
        except RuntimeError as e:
            last = e
            if "HTTP 403" in str(e) or "HTTP 429" in str(e):  # portalen svarede – koden er forkert, ikke adressen
                raise
    if resp is None:
        raise RuntimeError(f"Fandt ingen løbsportal på {base} ({last}). Er pluginet RaceTimer Portal aktivt på siden?")
    if not resp.get("token") or not resp.get("sync_url"):
        raise RuntimeError(resp.get("besked") or "Portalen svarede uden nøgle")
    host = urllib.parse.urlparse(base).netloc
    d = {"id": secrets.token_hex(4), "name": resp.get("portal") or host, "type": "webhook", "url": resp["sync_url"],
         "key": resp["token"], "interval_sec": 15, "on_finish": True, "enabled": True, "announce_admin": False,
         "portal": {"base": base, "host": host, "organizer": resp.get("organizer") or "", "events_url": resp.get("events_url") or base}}
    dests = [x for x in sync.destinations() if not (is_portal(x) and x["portal"].get("base") == base)]  # forbind igen = erstat
    sync.save_destinations(dests + [d])
    return d


def call(d, payload):
    return sync._post(d["url"], payload, d.get("key"), gz=False)


def events(d):
    r = call(d, {"event": "portal_events"})
    if r.get("organizer") and r["organizer"] != d["portal"].get("organizer"):  # arrangøren har skiftet navn på portalen
        dests = sync.destinations()
        for x in dests:
            if x["id"] == d["id"]:
                x["portal"]["organizer"] = r["organizer"]
        sync.save_destinations(dests)
    return r


def link(d, race, event_id, distances):
    return call(d, {"event": "portal_link", "race_id": race["id"], "race_name": race["name"],
                    "event_id": int(event_id or 0), "distances": distances or {}})


def race_distances(race):
    """Løbets distancer, som portalen skal have dem: [{"id", "name", "km"}]. Uden distancer: én med løbets længde."""
    from . import engine
    cfg = engine.merged_config(race["type"], race["config"])
    routes = {r["id"]: r for r in cfg.get("routes") or []}
    out = []
    for d in engine.distances(race["type"], cfg):
        km = d.get("km")
        if km is None and d.get("routes"):
            km = round(sum(routes[x]["km"] for x in d["routes"] if x in routes), 2) or None
        out.append({"id": d["id"], "name": d["name"], "km": km, "start_min": float(d.get("start_min") or 0)})
    if not out:
        if race["type"] == "timed":
            h = float(cfg.get("duration_h") or 0)
            name = ("1 time" if h == 1 else f"{int(h)} timer") if h == int(h) else f"{round(h * 60)} min"
        elif cfg.get("distance_km"):
            name = f"{cfg['distance_km']:g} km".replace(".", ",")
        else:
            name = race["name"]
        out.append({"id": "", "name": name, "km": cfg.get("distance_km"), "start_min": 0})
    return out


def template_payload(templates):
    """Skabelonerne, som portalen skal have dem: navn, beskrivelse, løbstype og distancer – ingen indstillinger i øvrigt."""
    out = []
    for t in templates:
        try:
            dists = race_distances({"type": t["type"], "config": t.get("config") or {}, "name": t["name"]})
        except (KeyError, TypeError, ValueError):
            continue
        out.append({"id": t["id"], "name": t["name"], "description": t.get("description") or "", "type": t["type"],
                    "example": bool(t.get("example")), "distances": dists})
    return out


def push_templates(d, templates):
    """Send alle skabeloner til portalen. Portalen erstatter dem, den har fra denne Pi."""
    return call(d, {"event": "portal_templates", "templates": template_payload(templates)})


def create(d, race):
    """Opret løbet på portalen (eller find det, hvis det allerede er overført)."""
    return call(d, {"event": "portal_create", "race_id": race["id"], "race_name": race["name"], "race_type": race["type"],
                    "starts_at": race.get("scheduled_start") or race.get("started_at") or race.get("created_at"),
                    "finished": race["status"] == "finished", "distances": race_distances(race)})


def unpair(d):
    """Afbryd forbindelsen. Portalen sletter nøglen; lykkes det ikke (fx uden net), fjernes den alligevel her."""
    err = None
    try:
        call(d, {"event": "portal_unpair"})
    except RuntimeError as e:
        err = str(e)
    sync.save_destinations([x for x in sync.destinations() if x["id"] != d["id"]])
    return err
