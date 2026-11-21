"""Demoløb (demo.py): deltagere, plan og simulator for alle løbstyper. Kør: python tests/test_demo.py

Hvert demoløb "løbes" færdigt på et simuleret ur: simulatoren afspiller planen gennem handle_read,
og motoren skal give et fornuftigt resultat (vinder, mål, omgange) – uden dubletter eller fejl.
"""
import json
import os
import sys
import tempfile
import time

os.environ["RACETIMER_DATA"] = tempfile.mkdtemp()
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from racetimer import app, db, demo, engine  # noqa: E402

T0 = 1_800_000_000.0


def run(race_type, n=None, canicross=False, minutes=60, **cfg):
    db.ex("UPDATE races SET is_active=0")
    rid = demo.create(race_type, n, canicross=canicross, seed=4)
    if cfg:
        race = db.race(rid)
        db.ex("UPDATE races SET config=? WHERE id=?", (json.dumps({**race["config"], **cfg}), rid))
    db.ex("UPDATE races SET is_active=1, status='running', started_at=? WHERE id=?", (T0, rid))
    sim = demo.Simulator(app.handle_read)
    sent = 0
    for s in range(0, minutes * 60, 5):  # 5 sek. ad gangen på det simulerede ur
        sent += sim.step(T0 + s)
    race = db.race(rid)
    parts = db.q("SELECT * FROM participants WHERE race_id=?", (rid,))
    reads = db.q("SELECT * FROM reads WHERE race_id=? AND deleted=0 AND duplicate=0", (rid,))
    rows, info = engine.compute(race, parts, reads, T0 + minutes * 60)
    assert sent == len(reads), (race_type, sent, len(reads))
    assert all(r["participant_id"] for r in reads), "alle simulerede chips hører til en deltager"
    return race, parts, rows, info, sim


def test_people():
    import random
    ps = demo.make_people(150, random.Random(1), [{"id": "d1"}, {"id": "d2"}], canicross=True)
    assert len({p["name"] for p in ps}) == 150
    assert {p["distance"] for p in ps} == {"d1", "d2"}
    assert all(p["dogs"] in (1, 2) and p["dog1"] and (p["dog2"] is None) == (p["dogs"] == 1) for p in ps)
    assert all(16 <= time.localtime().tm_year - p["birth_year"] <= 68 for p in ps)


def test_all_presets_create():
    for p in demo.presets():
        rid = demo.create(p["type"])
        race = db.race(rid)
        assert race["test"]["demo"] and race["test"]["sim"] and race["test"]["no_dedup"]
        assert db.q1("SELECT COUNT(*) AS n FROM participants WHERE race_id=?", (rid,))["n"] == p["n"]
        assert race["type"] == p["type"]
    try:
        demo.create("nope")
        raise AssertionError("ukendt type skulle afvises")
    except ValueError:
        pass


def test_backyard_has_one_winner():
    race, parts, rows, info, _ = run("backyard", minutes=40)
    assert info["phase"] == "ended" and info["winner"], info
    assert sum(1 for r in rows if r["status"] == "winner") == 1
    assert not info["flags"], "simulatoren læser aldrig i flagzonen"
    w = next(r for r in rows if r["status"] == "winner")
    assert w["laps"] == max(r["laps"] for r in rows if r["status"] != "winner") + 1


def test_backyard_custom_duration():
    race, parts, rows, info, _ = run("backyard_custom", minutes=8)
    assert info["phase"] == "ended" and info["leader_laps"] >= 3, info


def test_p2p_distances():
    race, parts, rows, info, _ = run("p2p", minutes=20)
    fin = [r for r in rows if r["status"] == "finished"]
    assert len(fin) >= len(parts) * 0.8, len(fin)
    by = {}
    for r in fin:
        by.setdefault(r["distance_name"], []).append(r["total_time"])
    assert set(by) == {"5 km", "10 km", "15 km"}
    # tiderne er i "rigtig" tid ÷ 10: 5 km på 18–47 min → 1,8–4,7 min på uret
    assert all(100 < t < 300 for t in by["5 km"]), by["5 km"]
    assert sum(by["15 km"]) / len(by["15 km"]) > sum(by["5 km"]) / len(by["5 km"]) * 2.5


def test_p2p_chipstart_and_callout():
    for extra in ({"chip_start": True}, {"callout": True, "callout_sec": 15}):
        race, parts, rows, info, _ = run("p2p", minutes=20, **extra)
        fin = [r for r in rows if r["status"] == "finished"]
        assert len(fin) >= len(parts) * 0.8, (extra, len(fin))
        starts = {r["start_ts"] for r in fin}
        assert len(starts) > 5, "hver løber har sin egen start"


def test_timed_and_record():
    race, parts, rows, info, _ = run("timed", minutes=8)
    assert info["phase"] == "ended"
    three = [r["laps"] for r in rows if r["distance_name"] == "3 timer" and r["laps"]]
    six = [r["laps"] for r in rows if r["distance_name"] == "6 timer" and r["laps"]]
    assert max(six) > max(three) > 20, (three, six)
    race, parts, rows, info, _ = run("record", canicross=True, minutes=20)
    assert info["total_km"] > 100 and all(p["dog1"] for p in parts), info


def test_timetrial():
    race, parts, rows, info, _ = run("timetrial", minutes=10)
    fin = [r for r in rows if r["status"] == "finished"]
    assert len(fin) >= len(parts) * 0.8
    assert len({r["start_ts"] for r in fin}) == len(fin), "intervalstart: alle starter hver for sig"


def test_restart_does_not_double_count():
    """Ny simulator midt i løbet (genstart af Pi'en) sender kun det, der mangler."""
    db.ex("UPDATE races SET is_active=0")
    rid = demo.create("timed", 10, seed=2)
    db.ex("UPDATE races SET is_active=1, status='running', started_at=? WHERE id=?", (T0, rid))
    a = demo.Simulator(app.handle_read)
    for s in range(0, 120, 5):
        a.step(T0 + s)
    b = demo.Simulator(app.handle_read)
    for s in range(120, 480, 5):
        b.step(T0 + s)
    full = demo.plan(db.race(rid), db.q("SELECT * FROM participants WHERE race_id=?", (rid,)), seed=rid)
    n = db.q1("SELECT COUNT(*) AS n FROM reads WHERE race_id=?", (rid,))["n"]
    assert n == sum(1 for ts, _ in full if ts <= T0 + 475), (n, len(full))
    # RTC midt i løbet: løberen får ikke flere omgange
    pid = db.q1("SELECT id FROM participants WHERE race_id=? AND bib=1", (rid,))["id"]
    before = db.q1("SELECT COUNT(*) AS n FROM reads WHERE participant_id=?", (pid,))["n"]
    db.ex("UPDATE participants SET status='RTC', status_at=? WHERE id=?", (T0 + 480, pid))
    for s in range(480, 600, 5):
        b.step(T0 + s)
    assert db.q1("SELECT COUNT(*) AS n FROM reads WHERE participant_id=?", (pid,))["n"] == before


def test_not_running_or_not_demo_does_nothing():
    db.ex("UPDATE races SET is_active=0")
    rid = demo.create("p2p", 5)
    db.ex("UPDATE races SET is_active=1 WHERE id=?", (rid,))
    sim = demo.Simulator(app.handle_read)
    assert sim.step(T0 + 10_000) == 0  # ikke startet
    db.ex("UPDATE races SET status='running', started_at=?, test=? WHERE id=?",
          (T0, json.dumps({**db.race(rid)["test"], "sim": False}), rid))
    assert sim.step(T0 + 10_000) == 0  # simulatoren slået fra


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
