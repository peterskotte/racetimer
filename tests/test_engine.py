"""Kør: python -m pytest tests/   (eller: python tests/test_engine.py)"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from racetimer import engine  # noqa: E402


def compute(race, parts, reads, now, checkin=True):
    """Som engine.compute, men alle deltagere er tjekket ind 5 min før start (medmindre checkin=False)."""
    if checkin and race.get("started_at"):
        reads = list(reads) + [{"participant_id": p["id"], "ts": race["started_at"] - 300} for p in parts]
    return engine.compute(race, parts, reads, now)

H = 3600
S = 1_000_000.0  # starttid


def P(i, name=None, **kw):
    return {"id": i, "bib": i, "name": name or f"L{i}", "sex": "Mand", **kw}


def by(rows):
    return {r["name"]: r for r in rows}


def backyard(reads, now, parts, **race):
    r = {"type": "backyard", "config": {}, "started_at": S, **race}
    return compute(r, parts, [{"participant_id": p, "ts": S + t} for p, t in reads], S + now)


def test_backyard_running_and_resting():
    rows, info = backyard([(1, 40 * 60)], 45 * 60, [P(1), P(2)])
    b = by(rows)
    assert b["L1"]["status"] == "resting" and b["L1"]["laps"] == 1
    assert b["L2"]["status"] == "active" and b["L2"]["laps"] == 0
    assert info["yard"] == 1 and info["phase"] == "running"


def test_backyard_missed_cutoff_is_dnf_and_last_runner_wins():
    # yard 1: begge i mål. yard 2: kun L1 i mål → L1 har én omgang mere end alle → vinder
    reads = [(1, 50 * 60), (2, 55 * 60), (1, H + 50 * 60)]
    rows, info = backyard(reads, 2 * H + 60, [P(1), P(2)])
    b = by(rows)
    assert b["L1"]["status"] == "winner" and b["L1"]["laps"] == 2
    assert b["L2"]["status"] == "dnf" and b["L2"]["laps"] == 1
    assert info["winner"] == "L1" and info["phase"] == "ended"
    assert rows[0]["name"] == "L1"


def test_backyard_nobody_finishes_no_winner():
    reads = [(1, 50 * 60), (2, 50 * 60)]
    rows, info = backyard(reads, 2 * H + 60, [P(1), P(2)])
    assert info["no_winner"] and not info["winner"]
    assert all(r["status"] == "dnf" and r["laps"] == 1 for r in rows)


def test_backyard_read_too_early_ignored():
    # læsning 2 min. efter start (fx i startboksen) tæller ikke
    rows, _ = backyard([(1, 120)], 30 * 60, [P(1), P(2)])
    assert by(rows)["L1"]["status"] == "active"


def test_backyard_rtc_then_solo_winner_immediately():
    # L2 trækker sig (RTC) i yard 2; L1 kommer i mål → afgjort med det samme
    parts = [P(1), P(2, status="RTC", status_at=S + H + 5 * 60)]
    reads = [(1, 50 * 60), (2, 50 * 60), (1, H + 45 * 60)]
    rows, info = backyard(reads, H + 46 * 60, parts)
    b = by(rows)
    assert b["L1"]["status"] == "winner" and b["L2"]["status"] == "rtc"
    assert b["L2"]["laps"] == 1


def test_backyard_stable_after_finished_at_persisted():
    reads = [(1, 50 * 60), (2, 55 * 60), (1, H + 50 * 60)]
    _, info = backyard(reads, 2 * H + 60, [P(1), P(2)])
    rows, info2 = backyard(reads, 9 * H, [P(1), P(2)], finished_at=info["resolved_at"])
    assert info2["winner"] == "L1" and by(rows)["L1"]["laps"] == 2


def test_backyard_time_windows_start_flag_goal():
    # 0–3 min: afgang (bekræfter start) · 3–25 min: flagzone · 25–60 min: målvindue
    reads = [{"id": 1, "participant_id": 1, "ts": S + 60},           # afgang
             {"id": 2, "participant_id": 1, "ts": S + 12 * 60},      # flagzone → ikke runde
             {"id": 3, "participant_id": 2, "ts": S + 26 * 60}]      # målvindue → runde
    rows, info = compute({"type": "backyard", "config": {}, "started_at": S}, [P(1), P(2)], reads, S + 30 * 60)
    b = by(rows)
    assert b["L1"]["status"] == "active" and b["L1"]["laps"] == 0 and b["L1"]["started_current"] and b["L1"]["flags"] == 1
    assert b["L2"]["status"] == "resting" and b["L2"]["laps"] == 1
    assert [f["read_id"] for f in info["flags"]] == [2] and info["goal_window_min"] == 25
    reads[1]["approved"] = 1  # official godkender
    rows, info = compute({"type": "backyard", "config": {}, "started_at": S}, [P(1), P(2)], reads, S + 30 * 60)
    assert by(rows)["L1"]["laps"] == 1 and not info["flags"]


def test_backyard_withdraw_in_rest_shows_rtc_and_solo_next():
    # begge gennemfører runde 1; B melder fra i hvilepausen → RTC med det samme, A skal løbe solo
    parts = [P(1), P(2, status="RTC", status_at=S + 55 * 60)]
    rows, info = backyard([(1, 50 * 60), (2, 52 * 60)], 56 * 60, parts)
    assert by(rows)["L2"]["status"] == "rtc" and by(rows)["L1"]["status"] == "resting"
    assert info["runners_left"] == 1 and info["solo"] == {"name": "L1", "state": "next"}
    rows, info = backyard([(1, 50 * 60), (2, 52 * 60)], H + 5 * 60, parts)
    assert info["solo"]["state"] == "running" and info["phase"] == "running"
    rows, info = backyard([(1, 50 * 60), (2, 52 * 60), (1, H + 50 * 60)], H + 51 * 60, parts)
    assert info["winner"] == "L1" and "solo" not in info


def test_backyard_several_drop_same_round_survivor_wins_immediately():
    reads = [(1, 50 * 60), (2, 51 * 60), (3, 52 * 60), (1, H + 45 * 60)]
    rows, info = backyard(reads, 2 * H + 30, [P(1), P(2), P(3)])
    assert info["winner"] == "L1" and by(rows)["L1"]["laps"] == 2 and "solo" not in info


def custom(reads, now, parts, **cfg):
    r = {"type": "backyard_custom", "config": cfg, "started_at": S}
    return compute(r, parts, [{"participant_id": p, "ts": S + t} for p, t in reads if t <= now], S + now)


def test_custom_total_time_counts_continuous_laps():
    # 3 timer, omgange i træk (min. omgangstid 10 min). Ingen fælles starter.
    reads = [(1, 30 * 60), (1, 62 * 60), (1, 95 * 60), (2, 40 * 60), (2, 81 * 60), (3, 35 * 60),
             (1, 3 * H + 60)]  # sidste læsning er efter tiden – tæller ikke
    rows, info = custom(reads, 2 * H, [P(1), P(2), P(3)], end_mode="duration", total_h=3)
    assert info["phase"] == "running" and info["continuous"] and abs(info["remaining"] - H) < 1
    assert [r["name"] for r in rows] == ["L1", "L2", "L3"] and rows[0]["laps"] == 3
    assert "next_start" not in info and "warnings_min" not in info
    rows, info = custom(reads, 3 * H + 120, [P(1), P(2), P(3)], end_mode="duration", total_h=3)
    assert info["phase"] == "ended" and info["leader"] == "L1" and info["leader_laps"] == 3
    assert all(r["status"] == "finished" for r in rows) and info["resolved_at"] == S + 3 * H


def test_custom_total_time_tie_broken_by_first_to_last_lap():
    reads = [(1, 30 * 60), (1, 70 * 60), (2, 31 * 60), (2, 65 * 60)]
    rows, _ = custom(reads, 4 * H, [P(1), P(2)], end_mode="duration", total_h=3)
    assert [r["name"] for r in rows] == ["L2", "L1"]


def test_custom_cutoff_fixed_laps_fastest_total_time():
    # cutoff 3 omgange i træk: L2 er hurtigst færdig, L1 bagefter, L3 mangler stadig
    reads = [(1, 20 * 60), (1, 41 * 60), (1, 63 * 60), (1, 80 * 60),   # 4. omgang ignoreres
             (2, 19 * 60), (2, 38 * 60), (2, 58 * 60), (3, 25 * 60)]
    rows, info = custom(reads, 85 * 60, [P(1), P(2), P(3)], end_mode="yards", max_yards=3)
    b = by(rows)
    assert info["phase"] == "running" and info["finishers"] == 2 and info["on_course"] == 1
    assert [r["name"] for r in rows] == ["L2", "L1", "L3"]
    assert b["L1"]["laps"] == 3 and b["L1"]["total_time"] == 63 * 60 and b["L2"]["status"] == "finished"
    # L3 udgår (RTC) → alle er færdige eller ude → løbet er slut
    parts = [P(1), P(2), P(3, status="RTC", status_at=S + 90 * 60)]
    rows, info = custom(reads, 91 * 60, parts, end_mode="yards", max_yards=3)
    assert info["phase"] == "ended" and info["leader"] == "L2"


def test_custom_cutoff_admin_finish_marks_unfinished_dnf():
    reads = [(1, 20 * 60), (1, 41 * 60), (1, 63 * 60), (2, 19 * 60)]
    r = {"type": "backyard_custom", "config": {"end_mode": "yards", "max_yards": 3}, "started_at": S,
         "finished_at": S + 70 * 60}
    rows, info = compute(r, [P(1), P(2)], [{"participant_id": p, "ts": S + t} for p, t in reads], S + 2 * H)
    assert info["phase"] == "ended" and by(rows)["L2"]["status"] == "dnf" and by(rows)["L1"]["status"] == "finished"


def test_custom_default_is_last_man():
    reads = [(1, 50 * 60), (2, 55 * 60), (1, H + 50 * 60)]
    rows, info = custom(reads, 2 * H + 60, [P(1), P(2)])
    assert info["winner"] == "L1" and not info.get("continuous")


def test_before_start_every_type_has_place_key_and_bib_order():
    RACE_TYPES = engine.RACE_TYPES
    parts = [P(3, "C"), P(1, "A"), {"id": 9, "bib": None, "name": "Uden nr"}]
    for typ in RACE_TYPES:
        rows, info = compute({"type": typ, "config": {}, "started_at": None}, parts, [], S)
        assert info["phase"] == "before", typ
        assert all("place" in r and r["place"] is None for r in rows), typ
        assert [r["name"] for r in rows] == ["A", "C", "Uden nr"], typ


def test_timed_ranking_laps_then_time():
    race = {"type": "timed", "config": {"duration_h": 6, "loop_km": 1.0, "min_lap_min": 2}, "started_at": S}
    reads = [(1, 300), (1, 600), (2, 290), (2, 590), (3, 400), (1, 610), (2, 7 * H)]  # 610 = dublet, 7h efter slut
    rows, info = compute(race, [P(1), P(2), P(3)], [{"participant_id": p, "ts": S + t} for p, t in reads], S + 1000)
    assert [r["name"] for r in rows] == ["L2", "L1", "L3"]
    assert by(rows)["L1"]["laps"] == 2 and info["total_km"] == 5.0


def test_record_total():
    race = {"type": "record", "config": {"loop_km": 2.5, "record_km": 10}, "started_at": S}
    reads = [(1, 300), (1, 900), (2, 400), (2, 1000), (2, 1600)]
    rows, info = compute(race, [P(1), P(2)], [{"participant_id": p, "ts": S + t} for p, t in reads], S + 2000)
    assert info["total_km"] == 12.5 and info["new_record"]


def test_manual_laps_bypass_min_lap_time():
    # rekordløb med 2 min minimumsomgangstid: chip-læsning efter 1 min ignoreres, manuel tæller
    race = {"type": "record", "config": {"loop_km": 1, "min_lap_min": 2}, "started_at": S}
    reads = [{"participant_id": 1, "ts": S + 60}, {"participant_id": 2, "ts": S + 60, "approved": 1},
             {"participant_id": 2, "ts": S + 90, "approved": 1}]
    rows, _ = compute(race, [P(1), P(2)], reads, S + 120)
    assert by(rows)["L1"]["laps"] == 0 and by(rows)["L2"]["laps"] == 2


def test_checkin_required_within_30_min_before_start():
    race = {"type": "p2p", "config": {"distance_km": 5, "min_time_min": 5}, "started_at": S}
    reads = [{"participant_id": 1, "ts": S - 10 * 60},   # tjekket ind 10 min før
             {"participant_id": 2, "ts": S - 40 * 60},   # for tidligt (40 min før)
             {"participant_id": 1, "ts": S + 1500}, {"participant_id": 2, "ts": S + 1400}, {"participant_id": 3, "ts": S + 1300}]
    rows, info = compute(race, [P(1), P(2), P(3)], reads, S + 2000, checkin=False)
    b = by(rows)
    assert b["L1"]["status"] == "finished" and b["L1"]["total_time"] == 1500 and b["L1"]["place"] == 1
    for n in ("L2", "L3"):
        assert b[n]["status"] == "nocheckin" and b[n]["total_time"] is None and b[n]["place"] is None
    assert info["checkin"] == {"min": 30, "count": 1, "total": 3}


def test_checkin_backyard_not_checked_in_does_not_count_as_competitor():
    # L3 er ikke tjekket ind → tæller ikke med i "sidste mand"; L1 vinder, da L2 ikke når runde 1
    race = {"type": "backyard", "config": {}, "started_at": S}
    reads = [{"participant_id": 1, "ts": S - 60}, {"participant_id": 2, "ts": S - 60},
             {"participant_id": 1, "ts": S + 50 * 60}, {"participant_id": 3, "ts": S + 50 * 60}]
    rows, info = compute(race, [P(1), P(2), P(3)], reads, S + H + 60, checkin=False)
    assert info["winner"] == "L1" and by(rows)["L3"]["status"] == "nocheckin" and by(rows)["L3"]["laps"] == 0


def test_checkin_shown_before_start_and_timetrial_keeps_start_order():
    race = {"type": "p2p", "config": {}, "started_at": None}
    rows, info = compute(race, [P(1), P(2)], [{"participant_id": 2, "ts": S - 120}], S, checkin=False)
    assert by(rows)["L2"]["status"] == "checkedin" and by(rows)["L1"]["status"] == "waiting" and info["checkin"]["count"] == 1
    tt = {"type": "timetrial", "config": {"start_mode": "interval", "interval_sec": 30, "min_time_min": 1}, "started_at": S}
    reads = [{"participant_id": 1, "ts": S - 60}, {"participant_id": 3, "ts": S - 60}, {"participant_id": 3, "ts": S + 60 + 600}]
    rows, _ = compute(tt, [P(1), P(2), P(3)], reads, S + 900, checkin=False)
    b = by(rows)
    assert b["L3"]["start_ts"] == S + 60 and b["L3"]["total_time"] == 600 and b["L2"]["status"] == "nocheckin"


def test_p2p():
    race = {"type": "p2p", "config": {"distance_km": 10, "min_time_min": 5}, "started_at": S}
    reads = [(1, 10), (1, 2400), (2, 2300)]
    rows, _ = compute(race, [P(1), P(2), P(3)], [{"participant_id": p, "ts": S + t} for p, t in reads], S + 3000)
    assert [r["name"] for r in rows] == ["L2", "L1", "L3"]
    assert by(rows)["L1"]["total_time"] == 2400 and by(rows)["L3"]["status"] == "active"


def test_timetrial_interval_and_waves():
    parts = [P(1), P(2), P(3)]
    race = {"type": "timetrial", "config": {"distance_km": 5, "start_mode": "interval", "interval_sec": 30, "min_time_min": 5},
            "started_at": S}
    rows, _ = compute(race, parts, [{"participant_id": 3, "ts": S + 60 + 1200}], S + 1300)
    assert by(rows)["L3"]["total_time"] == 1200 and by(rows)["L3"]["place"] == 1
    race["config"].update(start_mode="waves", waves=[{"name": "A", "from_bib": 1, "to_bib": 2, "offset_sec": 0},
                                                     {"name": "B", "from_bib": 3, "to_bib": 9, "offset_sec": 120}])
    rows, _ = compute(race, parts, [], S + 60)
    assert by(rows)["L3"]["status"] == "waiting" and by(rows)["L3"]["start_ts"] == S + 120


def test_timetrial_chip_start():
    race = {"type": "timetrial", "config": {"distance_km": 5, "start_mode": "chip", "min_time_min": 5}, "started_at": S}
    reads = [(1, 100), (1, 103), (1, 1300)]
    rows, _ = compute(race, [P(1)], [{"participant_id": p, "ts": S + t} for p, t in reads], S + 1400)
    assert rows[0]["total_time"] == 1200


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
