"""Løbsmotoren findes to steder: racetimer/engine.py (Pi'en) og web/engine.js (browser-udgaven).
Denne test laver mange tilfældige løb, regner dem i Python og tjekker, at JavaScript giver præcis det samme.

Kør: python tests/engine_parity.py   (kræver Node.js)
"""
import json
import os
import random
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from racetimer import engine  # noqa: E402

S = 1_800_000_000.0
N = int(os.environ.get("PARITY_CASES", 600))


def scenario(rnd):
    typ = rnd.choice(list(engine.RACE_TYPES))
    cfg = {"checkin_min": rnd.choice([0, 0, 30]), "min_lap_min": rnd.choice([0, 1, 2, 10]), "loop_km": rnd.choice([1.0, 2.5, 6.7056])}
    span = 3 * 3600
    if typ == "backyard_custom":
        cfg.update(end_mode=rnd.choice(["last_man", "duration", "yards"]), max_yards=rnd.randint(1, 4),
                   total_h=rnd.choice([0.5, 1, 2]), interval_min=rnd.choice([20, 60]), goal_window_min=rnd.choice([5, 10]),
                   start_window_min=rnd.choice([0, 2]))
    if typ == "timed":
        cfg.update(duration_h=rnd.choice([0.5, 1, 2]))
    if typ == "record":
        cfg.update(record_km=rnd.choice([0, 10, 50]))
    if typ in ("p2p", "timetrial"):
        cfg.update(min_time_min=rnd.choice([0, 5, 20]), distance_km=5.0)
    if typ == "timetrial":
        cfg.update(start_mode=rnd.choice(["interval", "waves", "chip"]), interval_sec=rnd.choice([15, 30, 60]),
                   waves=[{"name": "A", "from_bib": 1, "to_bib": 3, "offset_sec": 0},
                          {"name": "B", "from_bib": 4, "to_bib": 9, "offset_sec": rnd.choice([60, 300])}])
    race = {"id": 1, "type": typ, "config": cfg, "scheduled_start": S + rnd.choice([-60, 600, 90000]),
            "started_at": None if rnd.random() < 0.12 else S, "finished_at": None,
            "test": None}
    if race["started_at"] and rnd.random() < 0.25:
        race["finished_at"] = S + rnd.uniform(600, span)
    if rnd.random() < 0.25:
        race["test"] = {"speed": rnd.choice([1, 10, 60]), "no_minimum": rnd.random() < 0.5,
                        "no_checkin": rnd.random() < 0.5, "no_dedup": False}
    parts = []
    for i in range(1, rnd.randint(1, 8) + 1):
        p = {"id": i, "bib": None if rnd.random() < 0.1 else rnd.choice(range(1, 10)), "name": f"Løber {rnd.randint(1, 99)}",
             "sex": rnd.choice(["Mand", "Kvinde", ""]), "club": rnd.choice(["", "RTT"]), "status": None, "status_at": None,
             "dogs": rnd.choice([None, 1, 2]), "dog1": "Fido", "dog2": rnd.choice([None, "Bella"]), "start_offset": None}
        if rnd.random() < 0.15:
            p["status"] = rnd.choice(["RTC", "DSQ", "DNS"])
            p["status_at"] = S + rnd.uniform(-100, span)
        if typ == "timetrial" and rnd.random() < 0.15:
            p["start_offset"] = rnd.choice([0, 45, 120])
        parts.append(p)
    reads, rid = [], 1
    for p in parts:
        if rnd.random() < 0.7:  # indtjekning før start
            reads.append({"id": rid, "participant_id": p["id"], "ts": S - rnd.uniform(1, 2400), "approved": int(rnd.random() < 0.1)})
            rid += 1
        t = S
        for _ in range(rnd.randint(0, 12)):
            t += rnd.choice([rnd.uniform(5, 200), rnd.uniform(300, 1800), rnd.uniform(1500, 3700)])
            if t > S + span:
                break
            reads.append({"id": rid, "participant_id": p["id"], "ts": round(t, 3), "approved": int(rnd.random() < 0.08)})
            rid += 1
    rnd.shuffle(reads)
    now = S + rnd.choice([-300, rnd.uniform(0, span), span + 3600])
    return {"race": race, "parts": parts, "reads": reads, "now": now}


def main():
    rnd = random.Random(int(os.environ.get("PARITY_SEED", 20261025)))
    cases = []
    for _ in range(N):
        sc = scenario(rnd)
        rows, info = engine.compute(sc["race"], sc["parts"], sc["reads"], sc["now"])
        cases.append({**sc, "expected": {"rows": rows, "info": info}})
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(cases, f, ensure_ascii=False)
    js = os.path.join(os.path.dirname(__file__), "engine_parity.mjs")
    r = subprocess.run(["node", js, f.name])
    os.unlink(f.name)
    sys.exit(r.returncode)


if __name__ == "__main__":
    main()
