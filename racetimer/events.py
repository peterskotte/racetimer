"""Hændelser: hvad der sker ved læserne og i løbet – til moduler og skærmens scan-besked.

Tidtagningen påvirkes aldrig: læsningen er gemt, før den lægges i køen her, og vurderingen
(outcome.py) sker i en tråd for sig. Abonnenter (moduler) får hændelserne i deres egen kø.
"""
import collections
import queue
import threading
import time

from . import db, outcome


class EventBus:
    def __init__(self):
        self._lock = threading.Lock()
        self._seq = 0
        self._recent = collections.deque(maxlen=60)
        self._subs = []
        self._reads = queue.Queue(maxsize=1000)
        threading.Thread(target=self._read_worker, daemon=True, name="events-reads").start()

    # ------------------------------------------------------------ udgiv / abonnér

    def subscribe(self, fn):
        """fn(event) kaldes for hver hændelse. Må ikke blokere (læg i egen kø)."""
        self._subs.append(fn)

    def publish(self, event):
        with self._lock:
            self._seq += 1
            ev = {"seq": self._seq, "ts": time.time(), **event}
            self._recent.append(ev)
        for fn in list(self._subs):
            try:
                fn(ev)
            except Exception:  # noqa: BLE001 – et modul må aldrig stoppe hændelserne
                pass
        return ev

    def recent(self, seconds=12):
        """Seneste hændelser – resultatskærmen henter dem med hvert svar og viser nye som scan-besked."""
        cut = time.time() - seconds
        with self._lock:
            return [e for e in self._recent if e["ts"] >= cut]

    # ------------------------------------------------------------ læsninger

    def read_stored(self, read_id):
        """Kaldes efter en læsning er gemt. Vurderes i baggrunden."""
        try:
            self._reads.put_nowait(read_id)
        except queue.Full:
            pass

    def _read_worker(self):
        while True:
            rid = self._reads.get()
            try:
                ev = outcome.evaluate(rid)
            except Exception:  # noqa: BLE001
                ev = None
            if ev:
                self.publish(ev)


class Ticker(threading.Thread):
    """Hændelser, der kommer af tiden: nedtælling til start og læsere, der mistes/kommer igen."""

    def __init__(self, bus, standings, reader_status):
        super().__init__(daemon=True, name="events-ticker")
        self.bus, self.standings, self.reader_status = bus, standings, reader_status
        self._fired = set()
        self._readers = None

    def run(self):
        while True:
            try:
                self._countdown()
                self._readers_changed()
            except Exception:  # noqa: BLE001
                pass
            time.sleep(1)

    def _countdown(self):
        race = db.active_race()
        if not race:
            return
        target = None
        if not race.get("started_at") and race.get("scheduled_start"):
            target = race["scheduled_start"]
        elif race["status"] == "running" and race["type"].startswith("backyard"):
            _, info = self.standings(race)
            if info.get("phase") == "running" and not info.get("continuous"):
                target = info.get("next_start")
        if not target:
            return
        rem = target - time.time()
        for m in (3, 2, 1, 0):
            key = (race["id"], round(target), m)
            if key not in self._fired and m * 60 - 5 < rem <= m * 60:
                self._fired.add(key)
                self.bus.publish({"type": "race.countdown", "min": m, "race": race["name"]})

    def _readers_changed(self):
        now = {r["role"]: r["connected"] for r in self.reader_status() if r.get("path")}
        if self._readers is not None:
            for role, ok in now.items():
                if self._readers.get(role) is not None and self._readers[role] != ok:
                    self.bus.publish({"type": "reader.connected" if ok else "reader.lost", "reader": role})
        self._readers = now
