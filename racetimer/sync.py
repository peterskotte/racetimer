"""Synkronisering: Pi'en sender resultater til en eller flere webservere.

Pi'en er hele systemet og tager altid tiden lokalt. Hver destination har sin
egen plan:

* interval_sec > 0  → send automatisk med faste mellemrum (0 = kun manuelt)
* on_finish         → send de endelige resultater, når løbet afsluttes
* "Send nu"-knap    → manuel afsendelse fra admin

Tre typer destinationer:

* "mirror":  en anden RaceTimer i spejl-tilstand (RACETIMER_MODE=mirror), som
             viser den samme resultatskærm offentligt. Kun nye/ændrede
             læsninger sendes, så det er billigt selv over mobilnet.
* "webhook": din egen hjemmeside. Modtager hele stillingen som JSON (POST),
             fx til et PHP-script, der gemmer den eller viser den.
* "ftp":     upload en færdig resultatside (index.html) + resultater.json til et
             webhotel via FTP eller FTPS (se ftpupload.py).

Chip-ID'er sendes aldrig.
"""
import gzip
import json
import re
import secrets
import threading
import time
import urllib.error
import urllib.request

from . import db, ftpupload

BATCH = 5000
TYPES = ("mirror", "webhook", "ftp")


def destinations():
    dests = db.setting("destinations")
    if dests is None:
        dests = []
        old = db.setting("mirror") or {}  # tidligere enkelt-spejling → første destination
        if old.get("url"):
            dests.append({"id": secrets.token_hex(4), "name": "Webserver", "type": "mirror", "url": old["url"],
                          "key": old.get("key", ""), "interval_sec": 10, "on_finish": True,
                          "enabled": bool(old.get("enabled"))})
        db.set_setting("destinations", dests)
    return dests


def save_destinations(dests):
    db.set_setting("destinations", dests)


def public_race():
    """Det aktive løb, som det må vises på hjemmesiden – testløb sendes aldrig ud."""
    race = db.active_race()
    return None if race and race.get("test") else race


class SyncManager(threading.Thread):
    def __init__(self, standings):
        super().__init__(daemon=True, name="sync")
        self.standings = standings  # app.standings – beregner rows/info for et løb
        self.status = {}            # dest_id -> {"last_ok", "last_error", "last_event", "next_due"}
        self.tunnel_url = lambda: None  # sættes af app.py – aktuel fjernadgangs-adresse
        self._announced = {}        # dest_id -> (adresse, tidspunkt) for sidst meldte admin-adresse
        self._locks = {}
        self._wake = threading.Event()

    # ------------------------------------------------------------ planlægning

    def run(self):
        while True:
            for d in destinations():
                if d.get("enabled") and d.get("url"):
                    try:
                        self._tick(d)
                        if d["type"] == "webhook" and d.get("announce_admin"):
                            self._announce(d)
                    except Exception as e:  # noqa: BLE001 – tråden må aldrig dø
                        self._st(d)["last_error"] = str(e)
            self._wake.wait(1)
            self._wake.clear()

    def poke_state(self):
        """Løb vist/skjult/arkiveret eller udseende ændret → send til alle destinationer med det samme."""
        for d in destinations():
            self._st(d)["force"] = True
        self._wake.set()

    def poke_tunnel(self):
        """Fjernadgang slået til/fra → meld den nye admin-adresse med det samme."""
        self._announced.clear()
        self._wake.set()

    def _announce(self, d):
        """Meld Pi'ens aktuelle admin-adresse til hjemmesiden (…/racetimer/admin viderestiller)."""
        url, now = self.tunnel_url(), time.time()
        last = self._announced.get(d["id"])
        if last and last[0] == url and now - last[1] < (300 if url else 3600):
            return
        if last and last[0] == "fejl" and now - last[1] < 60:
            return
        try:
            _post(d["url"], {"event": "tunnel", "url": url, "sent_at": now}, d.get("key"), gz=False)
            self._announced[d["id"]] = (url, now)
            self._st(d).update(admin_announced=now, admin_error=None)
        except RuntimeError as e:
            self._announced[d["id"]] = ("fejl", now)
            self._st(d)["admin_error"] = str(e)

    def _st(self, d):
        return self.status.setdefault(d["id"], {"last_ok": None, "last_error": None, "last_event": None,
                                                "next_due": 0})

    def _final_key(self, race):
        if race and race["status"] == "finished" and race.get("finished_at"):
            return f"{race['id']}:{race['finished_at']:.0f}"
        return None

    def _tick(self, d):
        st = self._st(d)
        now = time.time()
        race = public_race()
        fk = self._final_key(race)
        final_due = bool(d.get("on_finish") and fk and fk not in (db.setting("final_sent", {}) or {}).get(d["id"], []))
        interval = float(d.get("interval_sec") or 0)
        interval_due = interval > 0 and now >= st["next_due"]
        if not (final_due or interval_due or st.get("force")) or now < st.get("retry_at", 0):
            return
        force, st["force"] = st.get("force"), False
        ok = self.send(d, final=final_due)  # send() kan selv bede om en ny afsendelse (manglende billeder)
        if not ok and force:
            st["force"] = True
        if interval:
            st["next_due"] = now + interval
        st["retry_at"] = 0 if ok else now + 30  # ingen forbindelse → prøv igen om 30 sek.

    # ------------------------------------------------------------ afsendelse

    def send(self, d, final=False, manual=False):
        """Send til én destination nu. Returnerer True ved succes."""
        lock = self._locks.setdefault(d["id"], threading.Lock())
        st = self._st(d)
        with lock:
            race = public_race()
            fk = self._final_key(race)
            from . import branding
            brand_v = branding.get()["v"]
            new_brand = st.get("brand_v") != brand_v  # billeder sendes kun, når udseendet er ændret
            brand_ok = True
            try:
                if d["type"] == "webhook":
                    resp = _post(d["url"], self._results_payload(race, final, images=new_brand), d.get("key"), gz=False)
                    if isinstance(resp, dict) and "brand_v" in resp and resp["brand_v"] != brand_v:
                        brand_ok = False  # hjemmesiden mangler billederne – send dem igen
                        if not new_brand:
                            st["force"] = True  # med det samme (én gang – næste afsendelse har billederne med)
                elif d["type"] == "ftp":
                    ftpupload.upload(d, self._results_payload(race, final), splash_file=new_brand)
                else:
                    self._send_mirror(d, race, images=new_brand)
            except Exception as e:  # noqa: BLE001
                st["last_error"] = str(e)
                return False
            st["brand_v"] = brand_v if brand_ok else None
            st.update(last_ok=time.time(), last_error=None,
                      last_event="Endelige resultater" if final else ("Manuel" if manual else "Interval"))
            if final and fk:
                sent = db.setting("final_sent", {}) or {}
                sent.setdefault(d["id"], []).append(fk)
                db.set_setting("final_sent", sent)
            return True

    def _results_payload(self, race, final, images=False):
        """race=None betyder intet aktivt løb → hjemmesiden viser splash med den valgte tekst."""
        from . import branding
        payload = {"event": "final" if final else "update", "sent_at": time.time(), "race": None,
                   "brand": branding.get()["name"], "branding": branding.web_export(images),
                   "archived": [r["id"] for r in db.q("SELECT id FROM races WHERE archived_at IS NOT NULL")]}
        if race:
            rows, info = self.standings(race)
            payload.update(
                race={k: race[k] for k in ("id", "name", "type", "status", "scheduled_start", "started_at",
                                           "finished_at")},
                info=info,
                results=[{k: r.get(k) for k in ("place", "bib", "name", "sex", "club", "status", "status_label",
                                                 "laps", "distance_km", "total_time", "last_lap", "best_lap", "dogs",
                                                 "distance", "distance_name")}
                         for r in rows])
        return payload

    def _send_mirror(self, d, race, images=False):
        from . import branding
        url = d["url"].rstrip("/") + "/api/mirror/push"
        brand = branding.web_export(images)
        if not race:
            _post(url, {"pi_now": time.time(), "race": None, "branding": brand}, d.get("key"))
            return
        rid = race["id"]
        allstate = db.setting("mirror_state", {}) or {}
        state = allstate.setdefault(d["id"], {})
        for _ in range(100):  # flere portioner, hvis der er meget at indhente
            since = state.get(str(rid), 0)
            parts = db.q("SELECT id, bib, name, sex, club, status, status_at, start_offset, dogs, dog1, dog2, distance "
                         "FROM participants "
                         "WHERE race_id=?", (rid,))
            reads = db.q("SELECT id, participant_id, ts, reader, duplicate, deleted, approved, rev FROM reads "
                         "WHERE race_id=? AND rev>? ORDER BY rev LIMIT ?", (rid, since, BATCH))
            payload = {
                "pi_now": time.time(),
                "branding": brand,
                "race": {k: race[k] for k in ("id", "name", "type", "config", "status", "scheduled_start",
                                              "started_at", "finished_at")},
                "participants": parts,  # lille liste – sendes altid, så rettelser altid kommer med
                "reads": [[r["id"], r["participant_id"], r["ts"], r["reader"], r["duplicate"], r["deleted"],
                           r["approved"]] for r in reads],
                "since": since,
                "rev": reads[-1]["rev"] if reads else since,
            }
            resp = _post(url, payload, d.get("key"))
            brand = {**brand, "images": {}}  # billeder kun med i første portion
            state[str(rid)] = 0 if resp.get("need_full") else payload["rev"]
            db.set_setting("mirror_state", allstate)
            if not resp.get("need_full") and len(reads) < BATCH:
                return

    def pending(self, d):
        """Læsninger i det aktive løb, som en spejl-destination endnu ikke har fået."""
        race = public_race()
        if not race or d["type"] != "mirror":
            return 0
        since = ((db.setting("mirror_state", {}) or {}).get(d["id"], {})).get(str(race["id"]), 0)
        return db.q1("SELECT COUNT(*) n FROM reads WHERE race_id=? AND rev>?", (race["id"], since))["n"]

    def reset(self, dest_id):
        """Glem hvad destinationen har fået (fx ny adresse) → alt sendes forfra."""
        allstate = db.setting("mirror_state", {}) or {}
        allstate.pop(dest_id, None)
        db.set_setting("mirror_state", allstate)
        self.status.pop(dest_id, None)
        self._wake.set()


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Følg aldrig omdirigeringer: en POST bliver ellers til en GET, data forsvinder – og det ligner succes."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


_opener = urllib.request.build_opener(_NoRedirect)


def _post(url, payload, key=None, gz=True):
    body = json.dumps(payload).encode()
    headers = {"Content-Type": "application/json", "User-Agent": "RaceTimer"}
    if gz:
        body = gzip.compress(body)
        headers["Content-Encoding"] = "gzip"
    if key:
        headers["Authorization"] = "Bearer " + key
        headers["X-RaceTimer-Key"] = key  # mange PHP-webhoteller fjerner Authorization-headeren
    req = urllib.request.Request(url, data=body, method="POST", headers=headers)
    try:
        with _opener.open(req, timeout=20) as r:
            raw = r.read()
            if "text/html" in (r.headers.get("Content-Type") or ""):
                # en almindelig hjemmeside svarede – data er ikke modtaget af et script
                raise RuntimeError("Adressen svarede med en hjemmeside i stedet for at modtage data – "
                                   "peg på selve scriptet, fx https://ditdomæne.dk/racetimer/modtag.php")
    except urllib.error.HTTPError as e:
        body = e.read()[:300].decode("utf-8", "ignore")
        try:  # modtag.php svarer med {"besked": "..."} – vis den i stedet for rå HTML
            body = json.loads(body).get("besked") or body
        except ValueError:
            if "<html" in body.lower():
                body = re.sub(r"<[^>]+>", " ", body)
                body = " ".join(body.split())[:120]
        hint = ""
        if e.code in (301, 302, 307, 308):
            body = f"serveren omdirigerer til {e.headers.get('Location')}"
        if e.code in (301, 302, 307, 308, 403, 404, 405) and not url.split("?")[0].endswith(".php") and "/api/" not in url:
            hint = " – peger adressen på selve scriptet? Fx https://ditdomæne.dk/racetimer/modtag.php"
        raise RuntimeError(f"HTTP {e.code}: {body}{hint}") from None
    except urllib.error.URLError as e:
        raise RuntimeError(f"Ingen forbindelse: {e.reason} – er Pi'en på internettet? (se fanen WiFi)") from None
    try:
        return json.loads(raw or b"{}")
    except ValueError:
        return {}

