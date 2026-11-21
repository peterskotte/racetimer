"""Pi'ens samlede tilstand til statuslampen: klar, starter, søger net, advarsel eller fejl.

Koderne er de samme som lampens blinkkoder (N blink + pause), så de kan slås op i vejledningen:
  1 rød  – en valgt RFID-læser er ikke tilsluttet
  2 gul  – intet netværk (tidtagningen virker, men intet net)
  3 gul  – uret er ikke stillet via internettet
  4 rød  – databasen kan ikke læses
  5 rød  – RaceTimer kunne ikke starte (vises af racetimer-led, ikke herfra)

Offline-tilstand (valgt i klar-tjekket): Pi'en kører bevidst uden net. Er læsere, database og ur
i orden, er tilstanden "offline" (lampen lyser orange) i stedet for advarslen om intet netværk.
"""
import time

from . import db

STARTED = time.time()
STARTUP_SEC = 10        # vis "starter" de første sekunder, mens læsere forbindes
SEARCH_SEC = 120        # efter opstart af Pi'en: "søger netværk" i stedet for advarsel

CODES = {
    1: ("error", "RFID-læser ikke tilsluttet"),
    2: ("warn", "Intet netværk"),
    3: ("warn", "Uret er ikke stillet"),
    4: ("error", "Databasen kan ikke læses"),
    5: ("error", "RaceTimer kunne ikke starte"),
}

_src = {}


def configure(readers, host, clock, offline=None):
    """readers() → [{"path", "connected"}], host() → {"ip"}, clock() → {"synced", "manual"}, offline() → bool."""
    _src.update(readers=readers, host=host, clock=clock, offline=offline or (lambda: False))


def _uptime():
    try:
        with open("/proc/uptime") as f:
            return float(f.read().split()[0])
    except (OSError, ValueError, IndexError):
        return time.time() - STARTED


def _code(n):
    state, text = CODES[n]
    return {"state": state, "code": n, "text": text}


def current():
    """{"state": starting|searching|ready|warn|error, "code": n|None, "text": "..."}"""
    if not _src or time.time() - STARTED < STARTUP_SEC:
        return {"state": "starting", "code": None, "text": "RaceTimer starter"}
    try:
        db.q1("SELECT 1")
    except Exception:  # noqa: BLE001
        return _code(4)
    try:
        if any(r.get("path") and not r.get("connected") for r in _src["readers"]()):
            return _code(1)
    except Exception:  # noqa: BLE001
        pass
    clock = _src["clock"]() or {}
    clock_bad = clock.get("synced") is False and not clock.get("manual")
    if _src["offline"]():
        return _code(3) if clock_bad else {"state": "offline", "code": None, "text": "Offline-tilstand – klar uden netværk"}
    if not (_src["host"]() or {}).get("ip"):
        if _uptime() < SEARCH_SEC:
            return {"state": "searching", "code": None, "text": "Søger netværk"}
        return _code(2)
    if clock_bad:
        return _code(3)
    return {"state": "ready", "code": None, "text": "Klar"}
