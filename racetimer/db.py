"""SQLite-lag. Rå chip-læsninger er "sandheden" – alle resultater beregnes ud fra dem.

WAL-mode + synchronous=FULL betyder at en læsning er skrevet til disk før vi
svarer, så strømsvigt på Pi'en ikke koster registreringer.
"""
import hashlib
import json
import os
import secrets
import sqlite3
import threading
import time

# Data (database, læselog, uploadede logoer/splash) ligger ADSKILT fra programmet, så en opdatering
# aldrig kan røre klubbens løb og indstillinger. På Pi'en: /var/lib/racetimer. Under udvikling: ./data
DATA_DIR = os.path.abspath(os.environ.get("RACETIMER_DATA") or os.path.join(os.path.dirname(__file__), "..", "data"))
DB_PATH = os.environ.get("RACETIMER_DB", os.path.join(DATA_DIR, "racetimer.db"))

_lock = threading.RLock()
_conn = None

SCHEMA = """
CREATE TABLE IF NOT EXISTS races (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    type TEXT NOT NULL,              -- backyard | timed | record | p2p | timetrial
    config TEXT NOT NULL,            -- JSON med løbstype-parametre
    status TEXT NOT NULL DEFAULT 'planned',  -- planned | running | finished
    scheduled_start REAL,
    started_at REAL,
    finished_at REAL,
    is_active INTEGER NOT NULL DEFAULT 0,
    created_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS participants (
    id INTEGER PRIMARY KEY,
    race_id INTEGER NOT NULL REFERENCES races(id) ON DELETE CASCADE,
    bib INTEGER,
    name TEXT NOT NULL,
    sex TEXT,
    club TEXT,
    chip TEXT,
    status TEXT,          -- NULL (automatisk) | RTC | DSQ | DNS
    status_at REAL,
    start_offset REAL,    -- tidskørsel: manuel startforskydning i sekunder
    UNIQUE(race_id, chip)
);
CREATE TABLE IF NOT EXISTS reads (
    id INTEGER PRIMARY KEY,
    race_id INTEGER,
    chip TEXT NOT NULL,
    reader TEXT NOT NULL,  -- primary | backup | manual | sim
    ts REAL NOT NULL,
    participant_id INTEGER,
    duplicate INTEGER NOT NULL DEFAULT 0,
    deleted INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS reads_race ON reads(race_id, ts);
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    pw_hash TEXT NOT NULL,
    created_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS sessions (
    token TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    expires REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


def conn():
    global _conn
    if _conn is None:
        os.makedirs(os.path.dirname(os.path.abspath(DB_PATH)), exist_ok=True)
        _conn = sqlite3.connect(DB_PATH, check_same_thread=False, isolation_level=None)
        _conn.row_factory = sqlite3.Row
        _conn.execute("PRAGMA journal_mode=WAL")
        _conn.execute("PRAGMA synchronous=FULL")
        _conn.execute("PRAGMA foreign_keys=ON")
        _conn.executescript(SCHEMA)
        _migrate(_conn)
        if not q("SELECT 1 FROM users LIMIT 1"):
            # helt ny installation: tilfældig førstegangskode (vises kun på Pi'ens egen skærm og på
            # SD-kortet), ét demoløb og opsætningsguiden ved første login
            code = new_first_code()
            create_user("admin", code)
            set_setting("first_code", code)
            _write_first_code(code)
            _create_demo()
            set_setting("setup_done", False)
    return _conn


def _migrate(c):
    # rev: stigende ændringsnummer pr. læsning, så spejlingen kun sender det nye
    cols = [r[1] for r in c.execute("PRAGMA table_info(reads)")]
    if "rev" not in cols:
        c.execute("ALTER TABLE reads ADD COLUMN rev INTEGER")
        c.execute("UPDATE reads SET rev=id")
    if "approved" not in cols:
        # official har godkendt en læsning fra flagzonen (backyard 3–25 min) som gennemført runde
        c.execute("ALTER TABLE reads ADD COLUMN approved INTEGER NOT NULL DEFAULT 0")
        c.execute("DROP TRIGGER IF EXISTS reads_rev_upd")
    # oprydning: tidligere fejl gemte "ingen chip" som teksten NONE ved redigering
    c.execute("UPDATE participants SET chip=NULL WHERE chip='NONE'")
    pcols = [r[1] for r in c.execute("PRAGMA table_info(participants)")]
    if "dogs" not in pcols:  # canicross: antal hunde (1/2) og deres navne
        c.execute("ALTER TABLE participants ADD COLUMN dogs INTEGER")
        c.execute("ALTER TABLE participants ADD COLUMN dog1 TEXT")
        c.execute("ALTER TABLE participants ADD COLUMN dog2 TEXT")
    ucols = [r[1] for r in c.execute("PRAGMA table_info(users)")]
    if "strong" not in ucols:  # koden er mindst MIN_PW tegn (kræves for login via det offentlige link)
        c.execute("ALTER TABLE users ADD COLUMN strong INTEGER NOT NULL DEFAULT 0")
    rcols = [r[1] for r in c.execute("PRAGMA table_info(races)")]
    if "archived_at" not in rcols:  # arkiverede løb skjules i løbslisten, men kan gendannes
        c.execute("ALTER TABLE races ADD COLUMN archived_at REAL")
    if "test" not in rcols:  # testløb: JSON med {speed, no_minimum, no_checkin, no_dedup}, NULL = rigtigt løb
        c.execute("ALTER TABLE races ADD COLUMN test TEXT")
    c.executescript("""
        CREATE INDEX IF NOT EXISTS reads_rev ON reads(race_id, rev);
        CREATE TRIGGER IF NOT EXISTS reads_rev_ins AFTER INSERT ON reads BEGIN
            UPDATE reads SET rev=(SELECT COALESCE(MAX(rev), 0) + 1 FROM reads) WHERE id=NEW.id;
        END;
        CREATE TRIGGER IF NOT EXISTS reads_rev_upd AFTER UPDATE OF participant_id, duplicate, deleted, approved ON reads BEGIN
            UPDATE reads SET rev=(SELECT COALESCE(MAX(rev), 0) + 1 FROM reads) WHERE id=NEW.id;
        END;
    """)


def _create_demo():
    """Et lille demoløb (ikke startet) med 3 testløbere – kan prøves med 'Test uden hardware' og slettes bagefter."""
    from . import engine
    cfg = engine.merged_config("timed", {"duration_h": 1, "loop_km": 1.0, "min_lap_min": 1})
    rid = ex("INSERT INTO races(name, type, config, is_active, created_at) VALUES (?,?,?,1,?)",
             ("Demoløb (kan slettes)", "timed", json.dumps(cfg), time.time()))
    for bib, name, sex in ((1, "Anna Demo", "Kvinde"), (2, "Bo Demo", "Mand"), (3, "Carla Demo", "Kvinde")):
        ex("INSERT INTO participants(race_id, bib, name, sex, chip) VALUES (?,?,?,?,?)", (rid, bib, name, sex, f"DEMO{bib:02d}"))


def q(sql, args=()):
    with _lock:
        return [dict(r) for r in conn().execute(sql, args).fetchall()]


def q1(sql, args=()):
    rows = q(sql, args)
    return rows[0] if rows else None


def ex(sql, args=()):
    with _lock:
        return conn().execute(sql, args).lastrowid


# ---------- brugere ----------

def hash_pw(pw, salt=None):
    salt = salt or secrets.token_hex(16)
    h = hashlib.pbkdf2_hmac("sha256", pw.encode(), salt.encode(), 200_000).hex()
    return f"{salt}${h}"


def check_pw(pw, stored):
    salt, _ = stored.split("$", 1)
    return secrets.compare_digest(hash_pw(pw, salt), stored)


MIN_PW = 10
FIRST_CODE_FILE = os.path.join(DATA_DIR, "forste-kode.txt")


def new_first_code():
    """Fx 'K7PQ-M2XD-9HTA' – uden tegn der let forveksles (0/O, 1/I/L)."""
    alphabet = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
    return "-".join("".join(secrets.choice(alphabet) for _ in range(4)) for _ in range(3))


def _write_first_code(code):
    """Til hjælperen, der lægger koden på SD-kortet (til dem uden skærm). Kun læsbar for RaceTimer."""
    try:
        fd = os.open(FIRST_CODE_FILE, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w") as f:
            f.write(code + "\n")
    except OSError:
        pass


def first_code():
    """Førstegangskoden, så længe den ikke er skiftet."""
    return setting("first_code")


def create_user(username, pw):
    return ex("INSERT INTO users(username, pw_hash, created_at, strong) VALUES (?,?,?,?)",
              (username, hash_pw(pw), time.time(), int(len(pw) >= MIN_PW)))


def set_password(uid, pw):
    ex("UPDATE users SET pw_hash=?, strong=? WHERE id=?", (hash_pw(pw), int(len(pw) >= MIN_PW), uid))
    u = q1("SELECT username FROM users WHERE id=?", (uid,))
    if u and u["username"] == "admin" and first_code():
        ex("DELETE FROM settings WHERE key='first_code'")
        try:
            os.remove(FIRST_CODE_FILE)
        except OSError:
            pass


def login(username, pw):
    u = q1("SELECT * FROM users WHERE username=?", (username,))
    if not u or not check_pw(pw, u["pw_hash"]):
        return None
    if bool(u.get("strong")) != (len(pw) >= MIN_PW):  # hold "stærk kode" opdateret for ældre brugere
        ex("UPDATE users SET strong=? WHERE id=?", (int(len(pw) >= MIN_PW), u["id"]))
    token = secrets.token_urlsafe(32)
    ex("INSERT INTO sessions VALUES (?,?,?)", (token, u["id"], time.time() + 12 * 3600))
    return token


def session_user(token):
    if not token:
        return None
    return q1("SELECT u.id, u.username FROM sessions s JOIN users u ON u.id=s.user_id WHERE s.token=? AND s.expires>?",
              (token, time.time()))


def default_password_in_use():
    """Bruges admin stadig med admin/admin (ældre installationer) eller med førstegangskoden?"""
    u = q1("SELECT pw_hash FROM users WHERE username='admin'")
    if not u:
        return False
    code = first_code()
    return check_pw("admin", u["pw_hash"]) or bool(code and check_pw(code, u["pw_hash"]))


# ---------- løb ----------

def race(race_id):
    r = q1("SELECT * FROM races WHERE id=?", (race_id,))
    if r:
        r["config"] = json.loads(r["config"])
        r["test"] = json.loads(r["test"]) if r.get("test") else None
    return r


def active_race():
    r = q1("SELECT id FROM races WHERE is_active=1")
    return race(r["id"]) if r else None


def setting(key, default=None):
    r = q1("SELECT value FROM settings WHERE key=?", (key,))
    return json.loads(r["value"]) if r else default


def set_setting(key, value):
    ex("INSERT INTO settings(key, value) VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
       (key, json.dumps(value)))
