"""Tilmelding på hjemmesiden og aldersklasser.

Pi'en sender en offentlig beskrivelse af de løb, man kan tilmelde sig (navn, dato, frist, distancer –
ingen persondata), med til hjemmesiden. tilmeld.php viser formularen og gemmer tilmeldingerne på
webhotellet, hvor de ikke kan hentes udefra. Pi'en henter nye tilmeldinger med nøglen og opretter
dem som deltagere. Hjemmesiden sletter tilmeldingerne selv, når fristen for sletning er nået.
"""
import json
import re
import time

from . import db, engine

DEFAULTS = {"open": False, "deadline": None, "birth_year": "required", "public_list": True, "auto_bib": True,
            "bib_from": 1, "delete_days": 30, "note": "", "age_step": 0, "age_from": 35,
            "confirm_email": True, "reply_to": ""}
FETCH_EVERY = 60  # sek. mellem hentninger, mens der er tilmeldinger på hjemmesiden


def settings(race):
    s = json.loads(race["signup"]) if race.get("signup") else {}
    return {**DEFAULTS, **s}


def clean(b, old):
    """Indstillinger fra admin → gemt form. Hentestatus (fetched, count …) bevares."""
    out = dict(old)
    for k in ("open", "public_list", "auto_bib", "confirm_email"):
        if k in b:
            out[k] = bool(b[k])
    if "birth_year" in b:
        out["birth_year"] = b["birth_year"] if b["birth_year"] in ("required", "optional", "off") else "required"
    if "deadline" in b:
        out["deadline"] = float(b["deadline"]) if b["deadline"] else None
    for k, lo, hi in (("bib_from", 1, 99999), ("delete_days", 1, 365), ("age_from", 20, 90)):
        if k in b:
            try:
                out[k] = max(lo, min(hi, int(b[k])))
            except (TypeError, ValueError):
                pass
    if "age_step" in b:
        out["age_step"] = int(b["age_step"]) if str(b["age_step"]) in ("0", "5", "10") else 0
    if "reply_to" in b:  # klubbens adresse – svar på bekræftelsen går hertil
        r = str(b["reply_to"] or "").strip()[:200]
        out["reply_to"] = r if re.fullmatch(r"[^@\s<>,;]+@[^@\s<>,;]+\.[a-zA-Z]{2,}", r) else ""
    if "note" in b:
        out["note"] = str(b["note"] or "").strip()[:500]
    return out


def save(rid, s):
    db.ex("UPDATE races SET signup=? WHERE id=?", (json.dumps(s), rid))


def race_date(race):
    return race.get("started_at") or race.get("scheduled_start") or time.time()


def purge_at(race, s):
    """Hvornår hjemmesiden skal slette tilmeldingerne (None = løbet er ikke afsluttet endnu)."""
    return race["finished_at"] + s["delete_days"] * 86400 if race.get("finished_at") else None


def is_open(race, s, now=None):
    now = now or time.time()
    return bool(s["open"]) and race["status"] != "finished" and not (s.get("deadline") and now > s["deadline"])


def _signup_races():
    rows = db.q("SELECT * FROM races WHERE signup IS NOT NULL AND test IS NULL")
    for r in rows:
        r["config"] = json.loads(r["config"])
    return rows


def public_list(now=None):
    """Løb med tilmelding, som hjemmesiden skal kende. Et løb, der ikke står her, slettes på hjemmesiden."""
    now = now or time.time()
    out = []
    for r in _signup_races():
        s = settings(r)
        pa = purge_at(r, s)
        if not (s["open"] or s.get("fetched")) or (pa and now > pa):
            continue
        ds = engine.distances(r["type"], engine.merged_config(r["type"], r["config"]))
        # startnumre tildeles på hjemmesiden ved tilmeldingen – den skal kende de numre, Pi'en allerede har brugt
        taken = [x["bib"] for x in db.q("SELECT bib FROM participants WHERE race_id=? AND bib IS NOT NULL ORDER BY bib",
                                         (r["id"],))]
        out.append({"id": r["id"], "name": r["name"], "date": race_date(r), "open": is_open(r, s, now),
                    "deadline": s["deadline"], "distances": [{"id": d["id"], "name": d["name"]} for d in ds],
                    "birth_year": s["birth_year"], "public_list": s["public_list"], "note": s["note"],
                    "delete_days": s["delete_days"], "purge_at": pa,
                    "auto_bib": s["auto_bib"], "bib_from": s["bib_from"], "taken_bibs": taken,
                    "confirm_email": s["confirm_email"], "reply_to": s["reply_to"]})
    return out


def _wanted(now=None):
    """Løb, hvor der kan ligge nye tilmeldinger på hjemmesiden → {race_id: sidste hentede id}."""
    now = now or time.time()
    out = {}
    for r in _signup_races():
        s = settings(r)
        if s["open"] or (s.get("deadline") and now < s["deadline"] + 86400):
            out[str(r["id"])] = s.get("fetched", 0)
    return out


def fetch(dest, post, now=None):
    """Hent nye tilmeldinger fra én hjemmeside og opret dem som deltagere. Returnerer antal nye."""
    now = now or time.time()
    want = _wanted(now)
    if not want:
        return 0
    resp = post(dest["url"], {"event": "hent_tilmeldinger", "loeb": want, "sent_at": now}, dest.get("key"), gz=False)
    added = 0
    for rid, entries in (resp.get("tilmeldinger") or {}).items():
        race = db.race(int(rid))
        if not race or not isinstance(entries, list):
            continue
        added += import_entries(race, entries, now)
    return added


def import_entries(race, entries, now=None):
    """Tilmeldinger fra hjemmesiden → deltagere (dubletter springes over via tilmeldingens id)."""
    from .app import norm_sex
    s = settings(race)
    ds = {d["id"] for d in engine.distances(race["type"], engine.merged_config(race["type"], race["config"]))}
    added, last = 0, s.get("fetched", 0)
    for e in sorted(entries, key=lambda e: int(e.get("id") or 0)):
        eid = int(e.get("id") or 0)
        last = max(last, eid)
        name = str(e.get("name") or "").strip()[:100]
        if not name or db.q1("SELECT 1 FROM participants WHERE race_id=? AND signup_id=?", (race["id"], eid)):
            continue
        # startnummeret fra hjemmesiden er det, løberen har fået at vide – det bevares, hvis det er ledigt
        bib = int(e["bib"]) if str(e.get("bib") or "").isdigit() else None
        if bib is not None and db.q1("SELECT 1 FROM participants WHERE race_id=? AND bib=?", (race["id"], bib)):
            top = db.q1("SELECT MAX(bib) m FROM participants WHERE race_id=?", (race["id"],))["m"]
            new = max(s["bib_from"], (top or 0) + 1)
            s.setdefault("bib_conflicts", []).append(f"{name}: nr. {bib} var optaget og blev ændret til {new}")
            bib = new
        elif bib is None and s["auto_bib"]:  # ældre tilmelding uden nummer
            top = db.q1("SELECT MAX(bib) m FROM participants WHERE race_id=?", (race["id"],))["m"]
            bib = max(s["bib_from"], (top or 0) + 1)
        by = e.get("birth_year")
        db.ex("INSERT INTO participants(race_id, bib, name, sex, club, birth_year, email, distance, signup_id) "
              "VALUES (?,?,?,?,?,?,?,?,?)",
              (race["id"], bib, name, norm_sex(e.get("sex")), str(e.get("club") or "").strip()[:100],
               int(by) if str(by or "").isdigit() else None, str(e.get("email") or "").strip()[:200] or None,
               e.get("distance") if e.get("distance") in ds else None, eid))
        added += 1
    s.update(fetched=last, fetched_at=now or time.time(), error=None)
    save(race["id"], s)
    return added


def age_class(p, race, s):
    """Aldersklasse ud fra køn og fødselsår på løbsdagen, fx "M40", "K Senior", "M Junior" (None = ingen)."""
    step, by = s.get("age_step") or 0, p.get("birth_year")
    if not step or not by:
        return None
    sex = {"Mand": "M", "Kvinde": "K"}.get(p.get("sex") or "", "")
    age = time.localtime(race_date(race)).tm_year - int(by)
    if age < 18:
        grp = "Junior"
    elif age < s["age_from"]:
        grp = "Senior"
    else:
        grp = str(s["age_from"] + (age - s["age_from"]) // step * step)
    return f"{sex}{' ' if not grp.isdigit() and sex else ''}{grp}"
