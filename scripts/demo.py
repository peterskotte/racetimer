"""Opret et demo-backyardløb midt i yard 41 (til test af skærmen uden hardware).

Kør:  python scripts/demo.py
"""
import json
import os
import random
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from racetimer import db, engine  # noqa: E402

H = 3600
now = time.time()
start = now - 40 * H - 52 * 60  # 52 min inde i yard 41 → advarsler kommer om lidt
runners = [  # navn, køn, antal gennemførte yards, manuel status
    ("Kenneth Risom", "Mand", 41, None), ("Morten Klingenberg", "Mand", 41, None),
    ("Nikolaj Olsen", "Mand", 40, None), ("Mads Hansen", "Mand", 41, None),
    ("Jens Christian Mortensen", "Mand", 40, None), ("David Stoltenborg", "Mand", 40, None),
    ("Rasmus Kristensen", "Mand", 37, None), ("Martin Bremholm", "Mand", 35, "RTC"),
    ("Christian Balthazar Møller", "Mand", 31, None), ("Mette Sørensen", "Kvinde", 28, None),
]

db.conn()
cfg = engine.merged_config("backyard", {})
rid = db.ex("INSERT INTO races(name, type, config, status, started_at, created_at) VALUES (?,?,?,?,?,?)",
            ("Demo Backyard Ultra", "backyard", json.dumps(cfg), "running", start, now))
db.ex("UPDATE races SET is_active=(id=?)", (rid,))
random.seed(1)
for bib, (name, sex, yards, status) in enumerate(runners, 1):
    chip = f"DEMO{bib:04d}"
    pid = db.ex("INSERT INTO participants(race_id, bib, name, sex, chip, status, status_at) VALUES (?,?,?,?,?,?,?)",
                (rid, bib, name, sex, chip, status, start + yards * H + 60 if status else None))
    for y in range(yards):
        ts = start + y * H + random.randint(44 * 60, 57 * 60)
        if ts < now:
            db.ex("INSERT INTO reads(race_id, chip, reader, ts, participant_id) VALUES (?,?,?,?,?)",
                  (rid, chip, random.choice(["primary", "backup"]), ts, pid))
print(f"Demo-løb oprettet (id {rid}) og sat som aktivt.")
