"""Vurdering af én læsning: talte den – og hvis ikke, hvorfor?

Løbsmotoren gemmer ingen tilstand, så vurderingen beregner løberens række to gange med
samme tidspunkt: uden og med læsningen. Forskellen fortæller, hvad læsningen gjorde.
Bruges af hændelserne (moduler og skærmens scan-besked) – aldrig til selve resultaterne.
"""
from . import db, engine

REASONS = {
    "duplicate": "Allerede registreret",
    "too_early": "For tidligt – tæller ikke",
    "not_checked_in": "Ikke tjekket ind – kontakt en official",
    "flag_zone": "Uden for målvinduet – en official vurderer",
    "after_finish": "Løbet er slut",
    "already_finished": "Allerede i mål",
    "already_checked_in": "Allerede tjekket ind",
    "already_lap": "Runden er allerede registreret",
    "not_started": "Løbet er ikke startet",
    "out": "Udgået",
}


def _row(rows, pid):
    return next((r for r in rows if r["id"] == pid), None)


def _ignored(reason, **kw):
    return {"type": "read.ignored", "reason": reason, "reason_label": REASONS[reason], **kw}


def evaluate(read_id):
    """Returnér en hændelse (dict) for læsningen, eller None hvis der ikke er et aktivt løb."""
    rd = db.q1("SELECT id, race_id, chip, reader, ts, participant_id, duplicate FROM reads WHERE id=?", (read_id,))
    if not rd or not rd["race_id"]:
        return None
    race = db.race(rd["race_id"])
    base = {"reader": rd["reader"], "ts": rd["ts"]}
    if not rd["participant_id"]:
        return {"type": "read.unknown", **base}
    p = db.q1("SELECT id, bib, name, status FROM participants WHERE id=?", (rd["participant_id"],))
    who = {"bib": p["bib"], "name": p["name"], **base}
    if rd["duplicate"]:
        return _ignored("duplicate", **who)
    if (p["status"] or "").lower() in ("rtc", "dsq", "dns"):
        return _ignored("out", **who)

    parts = db.q("SELECT * FROM participants WHERE race_id=?", (race["id"],))
    reads = db.q("SELECT id, participant_id, ts, approved FROM reads WHERE race_id=? AND duplicate=0 AND deleted=0 "
                 "AND participant_id IS NOT NULL", (race["id"],))
    now = rd["ts"] + 0.001
    before = _row(engine.compute(race, parts, [r for r in reads if r["id"] != read_id], now)[0], p["id"]) or {}
    after_rows, info = engine.compute(race, parts, reads, now)
    after = _row(after_rows, p["id"]) or {}

    # flere distancer: hver distance har sin egen start
    start = after["dist_start"] if "dist_start" in after else race.get("started_at")
    if not start or rd["ts"] < start:
        if after.get("status") == "checkedin" and before.get("status") != "checkedin":
            return {"type": "read.checkin", **who}
        if after.get("status") == "checkedin":
            return _ignored("already_checked_in", **who)
        return _ignored("not_started", **who)
    if race.get("finished_at") and rd["ts"] > race["finished_at"]:
        return _ignored("after_finish", **who)
    if after.get("start_ts") and not before.get("start_ts") and race["type"] == "timetrial":
        return {"type": "read.started", **who}
    if (after.get("laps") or 0) > (before.get("laps") or 0) or (after.get("finish_ts") and not before.get("finish_ts")):
        finish = (race["type"] in ("p2p", "timetrial") and bool(after.get("finish_ts"))) or \
            bool(info.get("continuous") and after.get("status") == "finished")
        return {"type": "read.counted", "lap": after.get("laps"), "finish": finish,
                "time": after.get("total_time") if finish or info.get("continuous") else after.get("last_lap"), **who}
    if after.get("started_current") and not before.get("started_current"):
        return {"type": "read.departure", **who}  # backyard: scanning i afgangsvinduet
    if after.get("status") == "nocheckin":
        return _ignored("not_checked_in", **who)
    if (after.get("flags") or 0) > (before.get("flags") or 0):
        return _ignored("flag_zone", **who)
    if before.get("current_lap_done"):
        return _ignored("already_lap", **who)  # backyard: ekstra passage i samme runde
    if before.get("status") in ("finished", "winner") or before.get("finish_ts"):
        return _ignored("already_finished", **who)
    return _ignored("too_early", **who)
