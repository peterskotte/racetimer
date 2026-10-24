"""Løbsmotor: rene funktioner der beregner stilling ud fra løb, deltagere og læsninger.

Intet tilstand gemmes her – alt genberegnes ved hvert kald. Det gør systemet
robust: genstartes Pi'en midt i et løb, er stillingen præcis den samme bagefter.
"""

BACKYARD_KM = 6.7056  # 4 miles + 880 fod → 24 omgange = 100 miles

RACE_TYPES = {
    "backyard": {
        "label": "Backyard Ultra (officiel)",
        "locked": True,
        "config": {"checkin_min": 30, "loop_km": BACKYARD_KM, "interval_min": 60, "warnings_min": [3, 2, 1],
                   "start_window_min": 3, "goal_window_min": 25},
    },
    "backyard_custom": {
        "label": "Backyard Ultra (custom)",
        "config": {"checkin_min": 30, "loop_km": BACKYARD_KM, "interval_min": 60, "warnings_min": [3, 2, 1],
                   "start_window_min": 3, "goal_window_min": 25, "min_lap_min": 10,
                   "end_mode": "last_man", "max_yards": 5, "total_h": 3},
    },
    "p2p": {
        "label": "Alm. tidtagning (A til B)",
        "config": {"checkin_min": 30, "distance_km": 10.0, "min_time_min": 5, "canicross": False},
    },
    "record": {
        "label": "Rekordløb (Årets rekord)",
        "config": {"checkin_min": 30, "loop_km": 1.0, "min_lap_min": 2, "record_km": 0, "record_label": "Årets rekord", "canicross": False},
    },
    "timed": {
        "label": "Tidsbaseret (6/12/24/48 t)",
        "config": {"checkin_min": 30, "duration_h": 24, "loop_km": 1.0, "min_lap_min": 2, "canicross": False},
    },
    "timetrial": {
        "label": "Intervalstart / enkeltstart",
        "config": {"checkin_min": 30, "distance_km": 10.0, "start_mode": "interval", "interval_sec": 30, "min_time_min": 5, "canicross": False,
                   "waves": [{"name": "Bølge 1", "from_bib": 1, "to_bib": 20, "offset_sec": 0},
                             {"name": "Bølge 2", "from_bib": 21, "to_bib": 40, "offset_sec": 120}]},
    },
}

STATUS_LABELS = {
    "waiting": "Venter", "active": "Aktiv", "resting": "I mål", "finished": "Færdig",
    "winner": "Vinder", "dnf": "DNF", "rtc": "RTC", "dsq": "DSQ", "dns": "DNS",
    "checkedin": "Tjekket ind", "nocheckin": "Ikke tjekket ind",
}


def merged_config(race_type, cfg):
    base = dict(RACE_TYPES[race_type]["config"])
    if not RACE_TYPES[race_type].get("locked"):
        base.update(cfg or {})
    return base


TEST_SPEEDS = (1, 10, 60, 120)
_SCALE_MIN = ("checkin_min", "interval_min", "start_window_min", "goal_window_min", "min_lap_min", "min_time_min")


def test_config(cfg, opts):
    """Testløb: kør hurtigere end virkeligheden og/eller slå begrænsninger fra.

    speed 60 → alle tider ÷ 60 (en backyard-time varer 1 minut). Distancer er uændrede.
    """
    cfg = dict(cfg)
    speed = opts.get("speed") if opts.get("speed") in TEST_SPEEDS else 1
    if speed != 1:
        for k in _SCALE_MIN:
            if cfg.get(k):
                cfg[k] = cfg[k] / speed
        for k in ("total_h", "duration_h", "interval_sec"):
            if cfg.get(k):
                cfg[k] = cfg[k] / speed
        if cfg.get("warnings_min"):
            cfg["_warn_labels"] = list(cfg["warnings_min"])  # skærmen viser stadig "3-2-1"
            cfg["warnings_min"] = [m / speed for m in cfg["warnings_min"]]
        if cfg.get("waves"):
            cfg["waves"] = [{**w, "offset_sec": w.get("offset_sec", 0) / speed} for w in cfg["waves"]]
    if opts.get("no_minimum"):
        cfg.update(min_lap_min=0, min_time_min=0)
        if "goal_window_min" in cfg:  # backyard: ingen flagzone – første læsning i runden tæller
            cfg.update(goal_window_min=0, start_window_min=0)
    if opts.get("no_checkin"):
        cfg["checkin_min"] = 0
    return cfg


def effective_config(race):
    """Den konfiguration, motoren regner med (inkl. testløbets indstillinger)."""
    cfg = merged_config(race["type"], race["config"])
    return test_config(cfg, race["test"]) if race.get("test") else cfg


def _manual(p):
    """Manuel status sat af admin (RTC/DSQ/DNS) → lille bogstav-nøgle, ellers None."""
    return (p.get("status") or "").lower() or None


def _out_before(p, ts):
    return _manual(p) in ("rtc", "dsq") and (p.get("status_at") or 0) <= ts


def dog_names(p):
    """Canicross: hundenavne som liste (tom hvis ingen hunde er registreret)."""
    n = p.get("dogs") or 0
    return [d for d in (p.get("dog1"), p.get("dog2"))[:n] if d]


def _row(p, **kw):
    row = {"id": p["id"], "bib": p.get("bib"), "name": p["name"], "sex": p.get("sex") or "", "club": p.get("club") or "",
           "dogs": dog_names(p),
           "laps": 0, "distance_km": 0.0, "total_time": None, "last_lap": None, "best_lap": None, "status": "waiting"}
    row.update(kw)
    row["status_label"] = STATUS_LABELS.get(row["status"], row["status"])
    return row


def _reads_by_pid(reads):
    by = {}
    for r in sorted(reads, key=lambda r: r["ts"]):
        if r.get("participant_id"):
            by.setdefault(r["participant_id"], []).append(r["ts"])
    return by


def _place(rows, key):
    rows.sort(key=key)
    for i, r in enumerate(rows, 1):
        r["place"] = i
    return rows


# ---------------------------------------------------------------- backyard

def compute_backyard_open(race, cfg, parts, reads, now):
    """Custom backyard uden fælles starter: omgange løbes i træk fra start.

    end_mode "duration": flest omgange inden for total_h timer (ved lige mange: først til sidste omgang)
    end_mode "yards":    cutoff – først færdig med max_yards omgange (hurtigste samlede tid)
    """
    mode = cfg["end_mode"]
    start = race.get("started_at")
    loop = cfg["loop_km"]
    max_yards = max(1, int(cfg.get("max_yards") or 1)) if mode == "yards" else None
    total = float(cfg.get("total_h") or 0) * 3600 if mode == "duration" else None
    info = {"loop_km": loop, "continuous": True, "end_mode": mode, "max_yards": max_yards,
            "duration_sec": total}
    if not start:
        info.update(phase="before", next_start=race.get("scheduled_start"))
        return [_row(p, status="dns" if _manual(p) == "dns" else "waiting") for p in parts], info

    end = start + total if total else None
    stop = race.get("finished_at")
    limit = min(x for x in (end, stop) if x) if (end or stop) else None
    time_up = bool(stop) or bool(end and now >= end)
    by, ok = _reads_by_pid(reads), _approved_by_pid(reads)
    rows = []
    for p in parts:
        laps = _count_laps(by.get(p["id"], []), start, limit, cfg.get("min_lap_min", 0) * 60, ok.get(p["id"], ()))
        if max_yards:
            laps = laps[:max_yards]  # læsninger efter sidste omgang tæller ikke
        splits = [b - a for a, b in zip([start] + laps, laps)]
        m = _manual(p)
        if m:
            st = m
        elif max_yards and len(laps) >= max_yards:
            st = "finished"
        elif time_up:
            st = "finished" if mode == "duration" else "dnf"
        else:
            st = "active"
        rows.append(_row(p, status=st, laps=len(laps), distance_km=round(len(laps) * loop, 3),
                         total_time=(laps[-1] - start) if laps else None, last_lap=splits[-1] if splits else None,
                         best_lap=min(splits) if splits else None, last_ts=laps[-1] if laps else None))
    _place(rows, lambda r: (r["status"] in ("dsq", "dns"), -r["laps"], r["last_ts"] or 9e18))

    still_running = any(r["status"] == "active" for r in rows)
    ended = time_up or (max_yards is not None and rows and not still_running)
    leader = rows[0] if rows and rows[0]["laps"] else None
    info.update(
        phase="ended" if ended else "running",
        end_at=end, remaining=max(0, end - now) if end else None,
        resolved_at=(end if end and now >= end else now) if ended and not stop else None,
        finishers=sum(1 for r in rows if r["status"] == "finished"),
        on_course=sum(1 for r in rows if r["status"] == "active"),
        total_km=round(sum(r["distance_km"] for r in rows), 2),
        leader=leader["name"] if leader else None, leader_laps=leader["laps"] if leader else 0,
        leader_time=leader["total_time"] if leader else None,
        completed_yards=leader["laps"] if leader else 0,
    )
    return rows, info


def compute_backyard(race, cfg, parts, reads, now):
    if cfg.get("end_mode", "last_man") != "last_man":
        return compute_backyard_open(race, cfg, parts, reads, now)
    start = race.get("started_at")
    I = cfg["interval_min"] * 60
    loop = cfg["loop_km"]
    info = {"interval_sec": I, "warnings_min": cfg.get("warnings_min", [3, 2, 1]), "loop_km": loop,
            "warnings_labels": cfg.get("_warn_labels") or cfg.get("warnings_min", [3, 2, 1])}
    if not start:
        info.update(phase="before", next_start=race.get("scheduled_start"))
        return [_row(p, status="dns" if _manual(p) == "dns" else "waiting") for p in parts], info

    # Tidsvinduer i hver runde (officielt: 0–3 min afgang, 3–25 min flagzone, 25–60 min målvindue)
    goal = cfg.get("goal_window_min", cfg.get("min_lap_min", 0)) * 60
    startw = min(cfg.get("start_window_min", 0) * 60, goal)
    laps = {}     # pid -> {blok: ts for første læsning i målvinduet}
    started = {}  # pid -> blokke med læsning i afgangsvinduet (bekræfter start)
    flags = []    # læsninger i flagzonen, som en official skal vurdere
    for r in sorted(reads, key=lambda r: r["ts"]):
        pid, ts = r.get("participant_id"), r["ts"]
        b = int((ts - start) // I)
        if not pid or b < 0:
            continue
        off = ts - (start + b * I)
        if off >= goal or r.get("approved"):
            laps.setdefault(pid, {}).setdefault(b, ts)
        elif off < startw:
            started.setdefault(pid, set()).add(b)
        else:
            flags.append({"read_id": r.get("id"), "participant_id": pid, "ts": ts, "yard": b + 1, "minute": off / 60})

    end_ts = race.get("finished_at") or now
    cur = max(0, int((end_ts - start) // I))
    alive = [p for p in parts if _manual(p) != "dns"]
    out = {}  # pid -> (status, laps)
    winner = None
    ended_at = resolved_at = None
    current = {}  # pid -> lap ts i igangværende blok

    for k in range(cur + 1):
        bs = start + k * I
        still = []
        for p in alive:
            if _out_before(p, bs):
                out[p["id"]] = (_manual(p), k)
            else:
                still.append(p)
        alive = still

        def finished(p):
            ts = laps.get(p["id"], {}).get(k)
            return ts if ts is not None and not _out_before(p, ts) else None

        fin = [p for p in alive if finished(p)]
        pending = [p for p in alive if not finished(p) and not _out_before(p, end_ts)]
        block_over = bs + I <= end_ts
        if block_over or not pending:
            # blokken er afgjort: enten er tiden gået, eller ingen er længere på ruten
            for p in alive:
                if p not in fin:
                    m = _manual(p)
                    out[p["id"]] = (m if m in ("rtc", "dsq") else "dnf", k)
            alive = fin
            if len(fin) <= 1:
                resolved_at = bs + I if block_over else end_ts
                if len(fin) == 1:
                    winner = fin[0]
                    winner_laps = k + 1
                    ended_at = laps[winner["id"]][k]
                else:
                    ended_at = resolved_at
                break
        if k == cur:
            current = {p["id"]: finished(p) for p in alive}

    rows = []
    for p in parts:
        pid = p["id"]
        pl = laps.get(pid, {})
        if winner is not None and pid == winner["id"]:
            n, st = winner_laps, "winner"
        elif pid in out:
            st, n = out[pid]
        elif pid in current:
            n = cur + (1 if current[pid] else 0)
            st = "resting" if current[pid] else "active"
            if _out_before(p, end_ts):  # meldt fra i denne runde/hvilepausen → vis det med det samme
                st = _manual(p)
        else:
            st, n = (_manual(p) or "dnf"), 0
        times = [pl[b] - (start + b * I) for b in range(n) if b in pl]
        rows.append(_row(p, status=st, laps=n, distance_km=round(n * loop, 3),
                         total_time=sum(times) if times else None,
                         last_lap=times[-1] if times else None, best_lap=min(times) if times else None,
                         current_lap_done=current.get(pid), started_current=cur in started.get(pid, ()),
                         flags=sum(1 for f in flags if f["participant_id"] == pid)))

    group = {"winner": 0, "resting": 1, "active": 1}
    _place(rows, lambda r: (group.get(r["status"], 2), -r["laps"], r["total_time"] or 9e18))
    info.update(
        phase="ended" if ended_at else "running",
        yard=cur + 1, block_start=start + cur * I, next_start=start + (cur + 1) * I,
        runners_left=sum(1 for r in rows if r["status"] in ("active", "resting", "winner")),
        on_course=sum(1 for r in rows if r["status"] == "active"),
        winner=winner["name"] if winner else None, ended_at=ended_at, resolved_at=resolved_at,
        completed_yards=max((r["laps"] for r in rows), default=0),
        no_winner=bool(ended_at and not winner),
        flags=flags, goal_window_min=goal / 60, start_window_min=startw / 60,
    )
    # Én løber tilbage med lige så mange runder som de andre → skal løbe én runde alene for at vinde
    left = [r for r in rows if r["status"] in ("active", "resting")]
    if not ended_at and len(left) == 1:
        others = max((r["laps"] for r in rows if r is not left[0]), default=0)
        if left[0]["laps"] <= others or left[0]["status"] == "active":
            info["solo"] = {"name": left[0]["name"], "state": left[0]["status"] == "active" and "running" or "next"}
    return rows, info


# ---------------------------------------------------------------- omgangsløb

def _approved_by_pid(reads):
    """Tidspunkter for manuelle/godkendte læsninger – officialens afgørelse, så minimumstiden gælder ikke."""
    by = {}
    for r in reads:
        if r.get("approved") and r.get("participant_id"):
            by.setdefault(r["participant_id"], set()).add(r["ts"])
    return by


def _count_laps(tss, start, end, minlap, approved=()):
    laps, last = [], start
    for ts in tss:
        if ts < start or (end and ts > end):
            continue
        if ts - last >= minlap or (ts in approved and ts > last):
            laps.append(ts)
            last = ts
    return laps


def _lap_rows(parts, reads, start, end, minlap, loop, done):
    by, ok = _reads_by_pid(reads), _approved_by_pid(reads)
    rows = []
    for p in parts:
        laps = _count_laps(by.get(p["id"], []), start, end, minlap, ok.get(p["id"], ()))
        splits = [b - a for a, b in zip([start] + laps, laps)]
        m = _manual(p)
        st = m if m else ("finished" if done else "active")
        rows.append(_row(p, status=st, laps=len(laps), distance_km=round(len(laps) * loop, 3),
                         total_time=(laps[-1] - start) if laps else None, last_lap=splits[-1] if splits else None,
                         best_lap=min(splits) if splits else None, last_ts=laps[-1] if laps else None))
    bad = ("dsq", "dns")
    return _place(rows, lambda r: (r["status"] in bad, -r["laps"], r["last_ts"] or 9e18))


def compute_timed(race, cfg, parts, reads, now):
    start = race.get("started_at")
    dur = cfg["duration_h"] * 3600
    info = {"duration_sec": dur, "loop_km": cfg["loop_km"]}
    if not start:
        info.update(phase="before", next_start=race.get("scheduled_start"))
        return [_row(p) for p in parts], info
    end = start + dur
    done = now >= end or bool(race.get("finished_at"))
    rows = _lap_rows(parts, reads, start, end, cfg.get("min_lap_min", 0) * 60, cfg["loop_km"], done)
    info.update(phase="ended" if done else "running", end_at=end, remaining=max(0, end - now),
                total_km=round(sum(r["distance_km"] for r in rows), 2))
    return rows, info


def compute_record(race, cfg, parts, reads, now):
    start = race.get("started_at")
    info = {"loop_km": cfg["loop_km"], "record_km": cfg.get("record_km") or 0,
            "record_label": cfg.get("record_label") or "Årets rekord"}
    if not start:
        info.update(phase="before", next_start=race.get("scheduled_start"), total_km=0)
        return [_row(p) for p in parts], info
    done = bool(race.get("finished_at"))
    rows = _lap_rows(parts, reads, start, race.get("finished_at"), cfg.get("min_lap_min", 0) * 60, cfg["loop_km"], done)
    total = round(sum(r["distance_km"] for r in rows), 2)
    info.update(phase="ended" if done else "running", total_km=total,
                total_laps=sum(r["laps"] for r in rows), new_record=bool(info["record_km"]) and total > info["record_km"])
    return rows, info


# ---------------------------------------------------------------- A→B og tidskørsel

def _finish_rows(parts, reads, starts, minimum, now):
    by, ok = _reads_by_pid(reads), _approved_by_pid(reads)
    rows = []
    for p in parts:
        ps = starts.get(p["id"])
        m = _manual(p)
        fin = None
        if ps is not None:
            mine = ok.get(p["id"], ())
            fin = next((ts for ts in by.get(p["id"], []) if ts >= ps + minimum or (ts in mine and ts > ps)), None)
        if m in ("rtc",):
            st = "dnf"
        elif m:
            st = m
        elif fin:
            st = "finished"
        elif ps is None or now < ps:
            st = "waiting"
        else:
            st = "active"
        rows.append(_row(p, status=st, start_ts=ps, finish_ts=fin, total_time=(fin - ps) if fin else None,
                         elapsed=(now - ps) if (ps and not fin and now >= ps) else None, laps=1 if fin else 0))
    order = {"finished": 0, "active": 1, "waiting": 2}
    return _place(rows, lambda r: (order.get(r["status"], 3), r["total_time"] or 9e18, r["start_ts"] or 9e18, r["bib"] or 0))


def compute_p2p(race, cfg, parts, reads, now):
    start = race.get("started_at")
    info = {"distance_km": cfg["distance_km"]}
    if not start:
        info.update(phase="before", next_start=race.get("scheduled_start"))
        return [_row(p) for p in parts], info
    rows = _finish_rows(parts, reads, {p["id"]: start for p in parts}, cfg.get("min_time_min", 0) * 60, now)
    info.update(phase="ended" if race.get("finished_at") else "running", elapsed=now - start,
                finished=sum(1 for r in rows if r["status"] == "finished"))
    return rows, info


def timetrial_starts(race, cfg, parts, reads):
    """Beregn hver løbers starttid (epoch). Manuel start_offset vinder altid."""
    start = race.get("started_at")
    if not start:
        return {}
    mode = cfg.get("start_mode", "interval")
    starts = {}
    if mode == "chip":
        by = _reads_by_pid(reads)
        for p in parts:
            first = next((ts for ts in by.get(p["id"], []) if ts >= start), None)
            if first is not None:
                starts[p["id"]] = first
    elif mode == "waves":
        for p in parts:
            for w in cfg.get("waves", []):
                if p.get("bib") is not None and w["from_bib"] <= p["bib"] <= w["to_bib"]:
                    starts[p["id"]] = start + w["offset_sec"]
                    break
    else:
        ordered = sorted(parts, key=lambda p: (p.get("bib") is None, p.get("bib") or 0, p["id"]))
        for i, p in enumerate(ordered):
            starts[p["id"]] = start + i * cfg.get("interval_sec", 30)
    for p in parts:
        if p.get("start_offset") is not None:
            starts[p["id"]] = start + p["start_offset"]
    return starts


def compute_timetrial(race, cfg, parts, reads, now):
    start = race.get("started_at")
    info = {"distance_km": cfg["distance_km"], "start_mode": cfg.get("start_mode", "interval")}
    if not start:
        info.update(phase="before", next_start=race.get("scheduled_start"))
        return [_row(p) for p in parts], info
    starts = timetrial_starts(race, cfg, parts, reads)
    minimum = cfg.get("min_time_min", 0) * 60
    if info["start_mode"] == "chip":
        # første læsning er start – mållæsning skal derfor ligge efter minimumstiden
        reads = [r for r in reads if r["ts"] != starts.get(r.get("participant_id"))]
    rows = _finish_rows(parts, reads, starts, minimum, now)
    upcoming = sorted((r for r in rows if r["status"] == "waiting" and r["start_ts"]), key=lambda r: r["start_ts"])
    info.update(phase="ended" if race.get("finished_at") else "running", elapsed=now - start,
                next_starters=[{"bib": r["bib"], "name": r["name"], "start_ts": r["start_ts"]} for r in upcoming[:5]],
                finished=sum(1 for r in rows if r["status"] == "finished"))
    return rows, info


COMPUTE = {
    "backyard": compute_backyard, "backyard_custom": compute_backyard, "timed": compute_timed,
    "record": compute_record, "p2p": compute_p2p, "timetrial": compute_timetrial,
}


def checkin_window(race, cfg):
    """Indtjekning: sek. før start, hvor løberen skal scanne chippen (0 = slået fra).
    Ved chipstart er startscanningen selve starten, så der er ingen særskilt indtjekning."""
    if race["type"] == "timetrial" and cfg.get("start_mode") == "chip":
        return 0
    return float(cfg.get("checkin_min") or 0) * 60


def checked_in(race, cfg, reads, now):
    """Deltagere med en læsning i indtjekningsvinduet før start (manuel indtjekning er også en læsning)."""
    w = checkin_window(race, cfg)
    ref = race.get("started_at") or now
    end = ref + (0 if race.get("started_at") else 1)
    # chip-scanning inden for vinduet – eller manuel indtjekning fra en official (udløber ikke)
    return {r["participant_id"] for r in reads
            if r.get("participant_id") and r["ts"] < end and (r["ts"] >= ref - w or r.get("approved"))}


def compute(race, parts, reads, now):
    cfg = effective_config(race)
    w = checkin_window(race, cfg)
    ok = checked_in(race, cfg, reads, now) if w else set()
    started = bool(race.get("started_at"))
    hold = set()
    if w and started:
        # ikke tjekket ind → intet tæller (og de er ikke med i fx backyards "sidste mand"-regel)
        hold = {p["id"] for p in parts if p["id"] not in ok and _manual(p) != "dns"}
        reads = [r for r in reads if r.get("participant_id") not in hold]
    keep_all = race["type"] == "timetrial"  # intervalstart: startrækkefølgen må ikke rykke sig
    cparts = parts if keep_all else [p for p in parts if p["id"] not in hold]
    rows, info = COMPUTE[race["type"]](race, cfg, cparts, reads, now)
    if hold:
        held = [r for r in rows if r["id"] in hold] + [_row(p) for p in parts if p["id"] in hold and not keep_all]
        for r in held:
            r.update(status="nocheckin", status_label=STATUS_LABELS["nocheckin"], laps=0, distance_km=0.0,
                     total_time=None, last_lap=None, best_lap=None, elapsed=None, finish_ts=None)
        rows = [r for r in rows if r["id"] not in hold]
        for i, r in enumerate(rows, 1):
            r["place"] = i
        for r in held:
            r["place"] = None
        rows += sorted(held, key=lambda r: (r["bib"] is None, r["bib"] or 0, r["name"]))
    if w:
        info["checkin"] = {"min": w / 60, "count": len(ok & {p["id"] for p in parts}), "total": len(parts)}
    if info.get("phase") == "before":
        for r in rows:
            if r["id"] in ok and r["status"] == "waiting":
                r.update(status="checkedin", status_label=STATUS_LABELS["checkedin"])
        # ingen placeringer før start – vis startlisten i startnummer-orden
        rows.sort(key=lambda r: (r["bib"] is None, r["bib"] or 0, r["name"]))
        for r in rows:
            r["place"] = None
    if race.get("test"):
        info["test"] = race["test"]
    info["type"] = race["type"]
    info["type_label"] = RACE_TYPES[race["type"]]["label"]
    return rows, info
