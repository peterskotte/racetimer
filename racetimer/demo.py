"""Demoløb: et færdigt testløb af en hvilken som helst løbstype med tilfældige deltagere – og en simulator,
der "løber" for dem, så man kan se tidtagning, stilling og skærm uden læsere, armbånd eller tilmelding.

Simulatoren regner med motorens egne regler (engine.effective_config): starttider, distancer, omgange,
backyard-timer og callout. Læsningerne går ind ad samme vej som rigtige scanninger (handle_read) med
læseren "sim", så alt efter den – stilling, skærm, moduler, log – opfører sig som til et rigtigt løb.
"""
import json
import random
import threading
import time

from . import db, engine

FIRST_F = ["Anna", "Mette", "Louise", "Camilla", "Sofie", "Ida", "Maria", "Line", "Julie", "Emma", "Karen", "Signe",
           "Laura", "Freja", "Rikke", "Helle", "Pernille", "Trine", "Marie", "Cecilie", "Nanna", "Astrid", "Maja",
           "Birgitte", "Lene", "Hanne", "Josefine", "Clara", "Sara", "Tina"]
FIRST_M = ["Peter", "Jens", "Lars", "Michael", "Søren", "Thomas", "Rasmus", "Mads", "Anders", "Morten", "Jesper",
           "Kasper", "Martin", "Niels", "Christian", "Henrik", "Frederik", "Mikkel", "Jonas", "Emil", "Ole", "Bo",
           "Kristian", "Torben", "Jakob", "Simon", "Oliver", "Magnus", "Esben", "Troels"]
LAST = ["Jensen", "Nielsen", "Hansen", "Pedersen", "Andersen", "Christensen", "Larsen", "Sørensen", "Rasmussen",
        "Jørgensen", "Petersen", "Madsen", "Kristensen", "Olsen", "Thomsen", "Poulsen", "Johansen", "Møller",
        "Mortensen", "Knudsen", "Lund", "Holm", "Bach", "Skov", "Dahl", "Bjerre", "Vestergaard", "Kjær",
        "Lauridsen", "Frost", "Krogh", "Østergaard", "Bisgaard", "Fogh", "Riis"]
CLUBS = ["Rebild Trail", "Aalborg Triathlon", "Skørping IF", "Støvring Løbeklub", "Hobro IK", "Rold Skov Runners",
         "Nørresundby Motion", "Arden Løbeklub", "Hadsund Trail", "Team Himmerland"]
DOGS = ["Bella", "Luna", "Max", "Molly", "Charlie", "Bailey", "Rocky", "Freja", "Balder", "Loke", "Sif", "Kaj",
        "Tyson", "Nala", "Odin", "Zita", "Fido", "Mille", "Basse", "Kira"]

# Demoopsætninger pr. løbstype: lille nok til at løbe på få minutter (testløbets hurtige tid), men med
# typens særkender – distancer, ruter i træk, bølger, omgange, backyard-timer.
PRESETS = {
    "backyard": {
        "name": "Backyard Ultra", "speed": 60, "n": 16,
        "about": "Ny runde hver time (her hvert minut). Løberne falder fra én for én, til der er én vinder.",
        "config": {},
    },
    "backyard_custom": {
        "name": "Backyard custom · 6 timer", "speed": 60, "n": 20,
        "about": "Omgange i træk fra start. Flest omgange på 6 timer vinder (her 6 minutter).",
        "config": {"end_mode": "duration", "total_h": 6, "min_lap_min": 10},
    },
    "p2p": {
        "name": "A til B · 5, 10 og 15 km", "speed": 10, "n": 40,
        "about": "Tre distancer. 15 km er kort + lang rute i træk og starter 30 min før de andre (her 3 min).",
        "config": {"checkin_min": 0, "cutoff_min": 0,
                   "routes": [{"id": "r1", "name": "Kort rute", "km": 5, "min_min": 15},
                              {"id": "r2", "name": "Lang rute", "km": 10, "min_min": 30}],
                   "distances": [{"id": "d1", "name": "15 km", "start_min": 0, "routes": ["r1", "r2"]},
                                 {"id": "d2", "name": "5 km", "start_min": 30, "routes": ["r1"]},
                                 {"id": "d3", "name": "10 km", "start_min": 30, "routes": ["r2"]}]},
    },
    "record": {
        "name": "Rekordløb", "speed": 10, "n": 25,
        "about": "Alle løber 1 km-omgange, så længe de vil. Fælles kilometer mod årets rekord. Afslut løbet selv.",
        "config": {"loop_km": 1.0, "min_lap_min": 2, "record_km": 400},
    },
    "timed": {
        "name": "3- og 6-timersløb", "speed": 60, "n": 30,
        "about": "Fælles start på en 1 km-omgang. 3-timersløberne stopper efter 3 timer, de andre efter 6 (her minutter).",
        "config": {"loop_km": 1.0, "min_lap_min": 2,
                   "distances": [{"id": "d1", "name": "3 timer", "start_min": 0, "duration_h": 3},
                                 {"id": "d2", "name": "6 timer", "start_min": 0, "duration_h": 6}]},
    },
    "timetrial": {
        "name": "Enkeltstart · 5 km", "speed": 10, "n": 30,
        "about": "En løber hvert 30. sek. (her hvert 3. sek.). Tiden måles fra hver løbers egen start.",
        "config": {"distance_km": 5.0, "start_mode": "interval", "interval_sec": 30, "min_time_min": 10},
    },
}
CANICROSS_TYPES = ("p2p", "record", "timed", "timetrial")
MAX_N = 200


def presets():
    return [{"type": t, "label": engine.RACE_TYPES[t]["label"], **{k: p[k] for k in ("name", "speed", "n", "about")},
             "canicross": t in CANICROSS_TYPES} for t, p in PRESETS.items()]


def make_people(n, rng, distances=(), canicross=False, birth_now=None):
    """n tilfældige deltagere – unikke navne, køn, årgang, klub (ikke alle) og evt. distance og hunde."""
    year = birth_now or time.localtime().tm_year
    used, out = set(), []
    dist_ids = [d["id"] for d in distances]
    for i in range(n):
        for _ in range(50):
            sex = rng.choice(("Kvinde", "Mand"))
            name = f"{rng.choice(FIRST_F if sex == 'Kvinde' else FIRST_M)} {rng.choice(LAST)}"
            if name not in used:
                break
        else:
            name = f"{name} {i + 1}"
        used.add(name)
        p = {"bib": i + 1, "name": name, "sex": sex, "birth_year": year - rng.randint(16, 68),
             "club": rng.choice(CLUBS) if rng.random() < 0.7 else None,
             "distance": dist_ids[i % len(dist_ids)] if dist_ids else None}
        if canicross:
            p["dogs"] = 2 if rng.random() < 0.15 else 1
            dogs = rng.sample(DOGS, p["dogs"])
            p["dog1"], p["dog2"] = dogs[0], (dogs[1] if p["dogs"] == 2 else None)
        out.append(p)
    return out


def create(race_type, n=None, sim=True, canicross=False, seed=None):
    """Opret demoløbet med deltagere og chips. Returnerer race_id (løbet er ikke startet)."""
    if race_type not in PRESETS:
        raise ValueError("Ukendt løbstype")
    pre = PRESETS[race_type]
    n = max(1, min(MAX_N, int(n or pre["n"])))
    cfg = dict(pre["config"])
    if canicross and race_type in CANICROSS_TYPES:
        cfg["canicross"] = True
    cfg = engine.clean_distances(race_type, engine.merged_config(race_type, cfg))
    test = {"speed": pre["speed"], "no_minimum": False, "no_checkin": True, "no_dedup": True, "demo": True, "sim": bool(sim)}
    name = f"🎲 Demo: {pre['name']}{' · canicross' if cfg.get('canicross') else ''}"
    rid = db.ex("INSERT INTO races(name, type, config, created_at, test, timing) VALUES (?,?,?,?,?,?)",
                (name, race_type, json.dumps(cfg), time.time(), json.dumps(test), "armband"))
    rng = random.Random(seed if seed is not None else rid * 7919 + int(time.time()))
    for p in make_people(n, rng, engine.distances(race_type, cfg), bool(cfg.get("canicross"))):
        db.ex("INSERT INTO participants(race_id, bib, name, sex, club, chip, dogs, dog1, dog2, distance, birth_year) "
              "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
              (rid, p["bib"], p["name"], p["sex"], p["club"], f"DEMO{rid}X{p['bib']:03d}", p.get("dogs"), p.get("dog1"),
               p.get("dog2"), p["distance"], p["birth_year"]))
    return rid


def is_demo(race):
    return bool((race or {}).get("test") and race["test"].get("demo"))


# ------------------------------------------------------------------ simulator

def _runner(rng):
    """En løbers niveau: fart (sek/km i virkeligheden), hvor jævnt hun løber, og om hun dukker op."""
    pace = min(560.0, max(220.0, rng.gauss(345, 55)))
    return {"pace": pace, "jitter": rng.uniform(0.02, 0.07), "dns": rng.random() < 0.03, "dnf": rng.random() < 0.05,
            "stamina": rng.uniform(0.35, 1.0)}


def _lap(r, km, rng, fatigue=1.0):
    return km * r["pace"] * fatigue * (1 + rng.gauss(0, r["jitter"]))


def _own_start(race, cfg, r, base, rng, scan_needed):
    """(scanning ved start eller None, løberens egen starttid). Callout/chipstart: løberen scanner lidt efter start."""
    if not scan_needed:
        return None, base
    scan = base + rng.uniform(3, 150) / max(1, (race.get("test") or {}).get("speed") or 1)
    return scan, scan + engine.callout_sec(race["type"], cfg)


def plan(race, parts, seed=0):
    """Alle simulerede læsninger for løbet: [(ts, chip)], sorteret. Ren funktion af løb, deltagere og frø."""
    start = race.get("started_at")
    if not start:
        return []
    cfg = engine.effective_config(race)
    speed = max(1, (race.get("test") or {}).get("speed") or 1)
    typ = race["type"]
    out = []
    dists = {d["id"]: d for d in engine.distances(typ, cfg)}
    first = next(iter(dists), None)
    scan_needed = bool(engine.callout_sec(typ, cfg) or engine.chip_start(typ, cfg)
                       or (typ == "timetrial" and cfg.get("start_mode") == "chip"))
    tt_starts = engine.timetrial_starts(race, cfg, parts, []) if typ == "timetrial" and not scan_needed else {}
    racers = [p for p in parts if p.get("chip") and not p.get("status")]

    if typ in ("backyard", "backyard_custom") and cfg.get("end_mode", "last_man") == "last_man":
        return _plan_backyard(race, cfg, racers, seed)

    for p in sorted(racers, key=lambda p: p["id"]):
        rng = random.Random(seed * 1000003 + p["id"])
        r = _runner(rng)
        if r["dns"]:
            continue
        chip = p["chip"]
        d = dists.get(p.get("distance")) or dists.get(first) if dists else None
        sub = cfg
        base = start
        if d is not None:
            srace, sub, base = engine._distance_setup({**race, "started_at": start}, cfg, d, start)
        if typ == "timetrial" and not scan_needed:
            base = tt_starts.get(p["id"], start)
        if p.get("start_offset") is not None:
            base = start + p["start_offset"]
        scan, own = _own_start(race, sub, r, base, rng, scan_needed)
        if scan is not None:
            out.append((scan, chip))
        t = own
        if typ in ("p2p", "timetrial"):
            legs = sub.get("legs") or [{"km": sub["distance_km"]}]
            for i, lg in enumerate(legs):
                if r["dnf"] and i == len(legs) - 1:
                    break
                t += _lap(r, lg["km"], rng, 1 + 0.04 * i) / speed
                out.append((t, chip))
        else:  # omgange: timed, record og backyard custom uden fælles starter
            loop = sub["loop_km"]
            minlap = (sub.get("min_lap_min") or 0) * 60
            if typ == "timed":
                end = own + sub["duration_h"] * 3600
                if r["dnf"]:
                    end = own + (end - own) * r["stamina"]
                maxlaps = 10 ** 6
            elif typ == "record":
                end = own + rng.uniform(25, 150) * 60 / speed
                maxlaps = 10 ** 6
            else:
                total = float(sub.get("total_h") or 0) * 3600
                end = own + total if total else own + 48 * 3600 / speed
                maxlaps = int(sub.get("max_yards") or 1) if sub.get("end_mode") == "yards" else 10 ** 6
                if r["dnf"]:
                    end = own + (end - own) * r["stamina"]
            n = 0
            while n < maxlaps and n < 5000:
                fatigue = 1 + 0.25 * n * loop / 50  # lidt langsommere for hver 50 km
                dt = max(minlap + 1 / speed, _lap(r, loop, rng, fatigue) / speed)
                if t + dt > end:
                    break
                t += dt
                n += 1
                out.append((t, chip))
    out.sort()
    return out


def _plan_backyard(race, cfg, racers, seed):
    """Backyard: ny runde hver interval. Hver løber holder et tilfældigt antal runder; den bedste én runde mere
    end nummer to (solo-runden), så der altid er én vinder."""
    start = race["started_at"]
    speed = max(1, (race.get("test") or {}).get("speed") or 1)
    I = cfg["interval_min"] * 60
    goal = cfg.get("goal_window_min", cfg.get("min_lap_min", 0)) * 60
    startw = min(cfg.get("start_window_min", 0) * 60, goal)
    real_i = I * speed
    rng0 = random.Random(seed * 7 + 1)
    order = sorted(racers, key=lambda p: p["id"])
    yards = {p["id"]: min(13, int(rng0.expovariate(1 / 4)) + 1) for p in order}  # demoen slutter efter højst 14 runder
    if order:
        ranked = sorted(order, key=lambda p: -yards[p["id"]])
        second = yards[ranked[1]["id"]] if len(ranked) > 1 else 0
        yards[ranked[0]["id"]] = second + 1
        for p in ranked[1:]:
            yards[p["id"]] = min(yards[p["id"]], second)
    out = []
    for p in order:
        rng = random.Random(seed * 1000003 + p["id"])
        r = _runner(rng)
        for k in range(yards[p["id"]]):
            bs = start + k * I
            if startw:
                out.append((bs + rng.uniform(0.05, 0.9) * startw, p["chip"]))  # over startlinjen i afgangsvinduet
            lo, hi = goal / I * real_i + 60, real_i - 90  # i målvinduet – aldrig i flagzonen, altid før næste start
            lap = min(hi, max(lo, _lap(r, cfg["loop_km"], rng, 1 + 0.02 * k)))
            out.append((bs + lap / speed, p["chip"]))
    out.sort()
    return out


class Simulator:
    """Tråd, der afspiller planen for det aktive demoløb i takt med uret. Genstartes Pi'en (eller ændres
    deltagerne, starten eller indstillingerne), lægges planen om, og kun læsninger efter de allerede
    afspillede sendes – så intet tælles to gange."""

    TICK = 0.5

    def __init__(self, on_read):
        self.on_read = on_read
        self.key = None
        self.queue = []
        self.pos = 0
        self._stop = threading.Event()

    def start(self):
        threading.Thread(target=self._loop, daemon=True, name="demo-sim").start()

    def stop(self):
        self._stop.set()

    def _loop(self):
        while not self._stop.wait(self.TICK):
            try:
                self.step(time.time())
            except Exception:  # noqa: BLE001 – simulatoren må aldrig vælte serveren
                pass

    def status(self, race):
        if not is_demo(race) or not race["test"].get("sim"):
            return None
        left = len(self.queue) - self.pos if self.key and self.key[0] == race["id"] else None
        return {"left": left}

    def step(self, now):
        race = db.active_race()
        if not race or not is_demo(race) or not race["test"].get("sim") or race.get("status") != "running" \
                or not race.get("started_at") or race.get("finished_at"):
            self.key = None
            return 0
        parts = db.q("SELECT id, chip, distance, start_offset, status FROM participants WHERE race_id=?", (race["id"],))
        key = (race["id"], race["started_at"], json.dumps(race["config"], sort_keys=True), json.dumps(race["test"], sort_keys=True),
               tuple((p["id"], p["chip"], p["distance"], p["start_offset"], p["status"]) for p in parts))
        if key != self.key:
            self.key = key
            self.queue = plan(race, parts, seed=race["id"])
            done = db.q1("SELECT MAX(ts) AS m FROM reads WHERE race_id=? AND reader='sim'", (race["id"],))["m"]
            floor = max(done or 0, race["started_at"] - 1) if done else race["started_at"] - 1
            self.pos = next((i for i, (ts, _) in enumerate(self.queue) if ts > floor), len(self.queue))
        sent = 0
        while self.pos < len(self.queue) and self.queue[self.pos][0] <= now:
            ts, chip = self.queue[self.pos]
            self.pos += 1
            self.on_read(chip, "sim", ts)
            sent += 1
        return sent

