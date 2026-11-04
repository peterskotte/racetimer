"""RFID-læsere: én primær og én backup.

Understøtter to slags "dumme" læsere, som er de mest udbredte og driftssikre:

* USB HID / "keyboard wedge" (fx 13,56 MHz MIFARE/NTAG eller 125 kHz EM4100):
  læseren "skriver" chip-ID'et + Enter som et tastatur. Vi læser via evdev og
  *grabber* enheden, så tallene ikke ender i kiosk-browseren.
* Seriel (USB-TTL, fx UHF-moduler i "ASCII output"-tilstand): én linje pr. chip.

Hver læser kører i sin egen tråd og genforbinder automatisk hvis kablet
rives ud. Begge læsere sender til samme callback – dubletter (samme chip set
af begge læsere) frasorteres i app.handle_read.
"""
import collections
import glob
import os
import re
import threading
import time

try:
    import evdev
    from evdev import ecodes
except ImportError:  # fx under udvikling på Mac
    evdev = None

try:
    import serial
except ImportError:
    serial = None

ROLES = ("primary", "backup")
ROOT = os.environ.get("RACETIMER_DEV_ROOT", "")  # kun til test: falsk /dev og /sys

_KEYS = {}
if evdev:
    for ch in "0123456789":
        _KEYS[getattr(ecodes, f"KEY_{ch}")] = ch
    for ch in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
        _KEYS[getattr(ecodes, f"KEY_{ch}")] = ch
    for i in range(10):
        _KEYS[getattr(ecodes, f"KEY_KP{i}")] = str(i)


def normalize(uid):
    if uid is None:  # "ingen chip" må aldrig blive til teksten "NONE"
        return ""
    return "".join(c for c in str(uid).strip().upper() if c.isalnum())


def _name(path):
    """Enhedens navn fra kernen, fx "Sycreader RFID Technology USB Reader"."""
    ev = os.path.basename(os.path.realpath(path))
    try:
        with open(f"{ROOT}/sys/class/input/{ev}/device/name") as f:
            return f.read().strip()
    except OSError:
        return None


def _port(path):
    """USB-porten i en by-path-sti, fx '...-usb-0:1.3:1.0-event-kbd' → '1.3'."""
    m = re.search(r"-usb(?:v\d+)?-\d+:([\d.]+):", os.path.basename(path))
    return m.group(1) if m else None


def _keyboards():
    """(by-id-stier, by-path-stier, navn pr. fysisk enhed) for tastatur-læsere."""
    byid = {os.path.realpath(p): p for p in sorted(glob.glob(f"{ROOT}/dev/input/by-id/*-event-kbd"))}
    bypath = sorted(glob.glob(f"{ROOT}/dev/input/by-path/*-event-kbd"))
    names = {os.path.realpath(p): _name(p) or os.path.basename(p) for p in bypath}
    for real, p in byid.items():
        names.setdefault(real, _name(p) or os.path.basename(p))
    return byid, bypath, names


def ambiguous_paths():
    """by-id-stier, der deles af flere ens læsere (samme model uden serienummer) – peger på en tilfældig af dem."""
    byid, _, names = _keyboards()
    count = collections.Counter(names.values())
    return [p for real, p in byid.items() if count[names[real]] > 1]


def list_devices():
    """Mulige læsere til admin-dropdown.

    En læser vises med sin by-id-sti (følger læseren, uanset USB-port). Har man to ens læsere,
    får de samme by-id-navn, og Linux laver kun ét link – så ens læsere vises i stedet med
    deres USB-port (by-path), og de skal blive siddende i samme port.
    """
    out = []
    byid, bypath, names = _keyboards()
    count = collections.Counter(names.values())
    seen = set()
    for p in bypath:
        real = os.path.realpath(p)
        if real in seen:  # samme port har flere navne (fx "usb-0:2.2" og "usbv2-0:2.2") – vis den kun én gang
            continue
        seen.add(real)
        if count[names[real]] == 1 and real in byid:
            out.append({"path": byid[real], "label": os.path.basename(byid[real])})
        else:
            out.append({"path": p, "label": f"{names[real]} · USB-port {_port(p) or os.path.basename(p)}"})
    for real, p in byid.items():  # by-id uden by-path (sjældent)
        if real not in seen:
            out.append({"path": p, "label": os.path.basename(p)})
    for path in sorted(glob.glob(f"{ROOT}/dev/serial/by-id/*")):
        out.append({"path": "serial:" + path, "label": "Seriel: " + os.path.basename(path)})
    if evdev and not out:
        for path in evdev.list_devices():
            try:
                out.append({"path": path, "label": evdev.InputDevice(path).name})
            except OSError:
                pass
    return out


def device_name(path):
    """Læserens modelnavn (gemmes sammen med valget, så en ens læser kan genkendes i en anden port)."""
    if not path or path.startswith("serial:"):
        return None
    return _name(path) if os.path.exists(path) else None


def resolve(paths, names=None):
    """De stier, læserne faktisk skal bruge. En læser valgt på USB-port (ens læsere) kan være flyttet til en
    anden port, fx når de sættes i en hub. Mangler den gemte port, bruges en ledig, tilsluttet læser af samme
    model i stedet – i portrækkefølge, så læser 1 får den første. Den gemte port bruges igen, når den kommer tilbage."""
    names = names or {}
    eff = {r: (paths or {}).get(r) for r in ROLES}
    _, bypath, devnames = _keyboards()
    count = collections.Counter(devnames.values())
    free = {}  # fysisk enhed → by-path, sorteret efter port
    for p in sorted(bypath, key=lambda p: [int(x) for x in (_port(p) or "0").split(".")]):
        free.setdefault(os.path.realpath(p), p)
    used = {os.path.realpath(p) for p in eff.values() if p and not p.startswith("serial:") and os.path.exists(p)}
    for role in ROLES:
        p = eff[role]
        if not p or p.startswith("serial:") or os.path.exists(p) or "/by-path/" not in p:
            continue
        want = names.get(role)
        for real, cand in free.items():
            # samme model som gemt – eller (ældre valg uden navn) en af flere ens læsere
            if real not in used and (devnames.get(real) == want if want else count[devnames.get(real)] > 1):
                eff[role] = cand
                used.add(real)
                break
    return eff


class Reader(threading.Thread):
    def __init__(self, role, path, on_read):
        super().__init__(daemon=True, name=f"reader-{role}")
        self.role, self.path, self.on_read = role, path, on_read
        self.connected = False
        self.last_read = None
        self.error = None
        self.reads = 0
        self._stop = threading.Event()
        self._dev = None

    def stop(self):
        self._stop.set()
        if self._dev:  # afbryder blokerende read_loop og frigiver grab
            try:
                self._dev.close()
            except OSError:
                pass

    def status(self):
        return {"role": self.role, "path": self.path, "connected": self.connected,
                "last_read": self.last_read, "error": self.error, "reads": self.reads}

    def _emit(self, uid, ts):
        uid = normalize(uid)
        if len(uid) >= 4:
            self.last_read = ts
            self.reads += 1
            self.on_read(uid, self.role, ts)

    def run(self):
        while not self._stop.is_set():
            try:
                if self.path.startswith("serial:"):
                    self._run_serial(self.path[7:])
                else:
                    self._run_evdev(self.path)
            except Exception as e:  # noqa: BLE001 – læseren må aldrig dø
                self.error = str(e)
            self.connected = False
            self._stop.wait(2)

    def _run_evdev(self, path):
        if not evdev:
            raise RuntimeError("python-evdev er ikke installeret")
        dev = self._dev = evdev.InputDevice(path)
        dev.grab()
        self.connected, self.error = True, None
        buf, first_ts = "", None
        try:
            for ev in dev.read_loop():
                if self._stop.is_set():
                    return
                if ev.type != ecodes.EV_KEY or ev.value != 1:  # kun key-down
                    continue
                if ev.code in (ecodes.KEY_ENTER, ecodes.KEY_KPENTER):
                    if buf:
                        self._emit(buf, first_ts)
                    buf, first_ts = "", None
                elif ev.code in _KEYS:
                    if not buf:
                        first_ts = time.time()  # tidsstempel = første tegn, ikke Enter
                    buf += _KEYS[ev.code]
        finally:
            try:
                dev.ungrab()
            except OSError:
                pass

    def _run_serial(self, port):
        if not serial:
            raise RuntimeError("pyserial er ikke installeret")
        with serial.Serial(port, 9600, timeout=1) as s:
            self.connected, self.error = True, None
            while not self._stop.is_set():
                line = s.readline()
                if line:
                    # mange læsere sender STX/ETX-rammer – normalize() fjerner dem
                    self._emit(line.decode("ascii", "ignore"), time.time())


class ReaderManager:
    WATCH_SEC = 3  # hvor ofte der tjekkes, om en ens læser er flyttet til en anden USB-port

    def __init__(self, on_read):
        self.on_read = on_read
        self.readers = {}
        self.wanted, self.names = {}, {}
        self._lock = threading.Lock()
        self._watch = None

    def configure(self, paths, names=None):
        """paths: {"primary": "/dev/input/by-id/...", "backup": "..."}; names: modelnavn pr. rolle (valgfrit)."""
        with self._lock:
            self.wanted = {r: (paths or {}).get(r) for r in ROLES}
            self.names = dict(names or {})
            self._apply()
        if not self._watch:
            self._watch = threading.Thread(target=self._watch_loop, daemon=True, name="reader-watch")
            self._watch.start()

    def _apply(self):
        eff = resolve(self.wanted, self.names)
        for role in ROLES:
            path = eff.get(role)
            old = self.readers.get(role)
            if old and old.path == path:
                continue
            if old:
                old.stop()
                self.readers.pop(role)
            if path:
                r = Reader(role, path, self.on_read)
                self.readers[role] = r
                r.start()

    def _watch_loop(self):
        while True:
            time.sleep(self.WATCH_SEC)
            try:
                with self._lock:
                    eff = resolve(self.wanted, self.names)
                    if any((self.readers.get(r).path if r in self.readers else None) != eff.get(r) for r in ROLES):
                        self._apply()
            except Exception:  # noqa: BLE001 – overvågningen må aldrig stoppe læserne
                pass

    def status(self):
        out = []
        for role in ROLES:
            st = self.readers[role].status() if role in self.readers else {"role": role, "path": None, "connected": False}
            want = self.wanted.get(role)
            if st.get("path") and want and st["path"] != want:  # fulgt med til en anden USB-port
                st["moved_from"], st["port"] = _port(want), _port(st["path"])
            out.append(st)
        return out
