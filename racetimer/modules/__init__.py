"""Moduler: eksterne enheder (helst på USB), der reagerer på hændelser – fx en højttaler ved læseren.

Opsætningen gemmes i databasen (setting "modules") som en liste:
    {"id", "kind", "device", "name", "enabled", "reader", ...modulets egne felter}
Enheder findes automatisk; et modul, hvis enhed ikke er sat i, venter bare (status "Ikke tilsluttet").
"""
import secrets
import threading
import time

from .. import db
from .speaker import Speaker

KINDS = {k.kind: k for k in (Speaker,)}


class ModuleManager(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True, name="modules")
        self.running = {}   # id → Module
        self.detected = {}  # kind → [enheder]
        self._lock = threading.Lock()

    # ------------------------------------------------------------ opsætning

    def configs(self):
        return db.setting("modules", []) or []

    def _save(self, cfgs):
        db.set_setting("modules", cfgs)
        self.sync()

    def add(self, kind, device, name=None):
        cls = KINDS.get(kind) or _bad("Ukendt modultype")
        cfg = {"id": secrets.token_hex(4), "kind": kind, "device": device, "name": name or cls.label, "enabled": True}
        for f in cls.fields:
            cfg[f["key"]] = f.get("default")
        self._save(self.configs() + [cfg])
        return cfg

    def update(self, mid, changes):
        cfgs = self.configs()
        cfg = next((c for c in cfgs if c["id"] == mid), None) or _bad("Modulet findes ikke")
        cls = KINDS[cfg["kind"]]
        allowed = {"enabled", "name"} | {f["key"] for f in cls.fields}
        for k, v in changes.items():
            if k in allowed:
                cfg[k] = _clean(next((f for f in cls.fields if f["key"] == k), None), v)
        self._save(cfgs)
        return cfg

    def remove(self, mid):
        self._save([c for c in self.configs() if c["id"] != mid])

    def test(self, mid):
        m = self.running.get(mid) or _bad("Modulet findes ikke")
        if not m.present:
            _bad("Enheden er ikke tilsluttet")
        try:
            out = m.test()
            m.error = None
            return out
        except RuntimeError as e:
            m.error = str(e)
            raise

    # ------------------------------------------------------------ kørsel

    def on_event(self, ev):
        for m in list(self.running.values()):
            m.offer(ev)

    def sync(self):
        """Start/stop moduler efter opsætningen, og opdatér hvilke enheder der er sat i."""
        with self._lock:
            cfgs = {c["id"]: c for c in self.configs()}
            for mid in list(self.running):
                if mid not in cfgs:
                    self.running.pop(mid).stop()
            for mid, cfg in cfgs.items():
                if cfg["kind"] not in KINDS:
                    continue
                if mid in self.running:
                    self.running[mid].cfg = cfg
                else:
                    self.running[mid] = KINDS[cfg["kind"]](cfg)
            self.detected = {k: cls.detect() for k, cls in KINDS.items()}
            for m in self.running.values():
                devs = {d["device"] for d in self.detected.get(m.kind, [])}
                m.present = m.cfg["device"] == "default" or m.cfg["device"] in devs

    def run(self):
        while True:
            try:
                self.sync()
            except Exception:  # noqa: BLE001
                pass
            time.sleep(3)

    def overview(self):
        """Til admin: moduler med status, fundne enheder og modultyper med deres felter."""
        self.sync()
        used = {(c["kind"], c["device"]) for c in self.configs()}
        mods = []
        for c in self.configs():
            m = self.running.get(c["id"])
            st = m.status() if m else {"state": "error", "text": "Ukendt modultype"}
            last = m.last_action if m else None
            mods.append({**c, "status": st, "last": {"ts": last[0], "text": last[1]} if last else None})
        found = [{**d, "kind": k, "label": KINDS[k].label, "icon": KINDS[k].icon, "added": (k, d["device"]) in used}
                 for k, devs in self.detected.items() for d in devs]
        kinds = {k: {"label": c.label, "icon": c.icon, "fields": c.fields} for k, c in KINDS.items()}
        return {"modules": mods, "detected": found, "kinds": kinds}


class ModuleError(ValueError):
    pass


def _bad(msg):
    raise ModuleError(msg)


def _clean(field, v):
    """Tjek en værdi mod feltets type, så admin ikke kan gemme noget, modulet ikke forstår."""
    if field is None:
        return bool(v) if isinstance(v, bool) else str(v or "")[:60]
    t = field["type"]
    if t == "range":
        try:
            return max(field["min"], min(field["max"], int(v)))
        except (TypeError, ValueError):
            return field["default"]
    if t == "select":
        return v if v in {o[0] for o in field["options"]} else field["default"]
    if t == "slots":
        ok = {o[0] for o in field["options"]}
        return {k: (v or {}).get(k) if (v or {}).get(k) in ok else field["default"][k] for k, _ in field["slots"]}
    return v
