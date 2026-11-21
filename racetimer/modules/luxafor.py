"""Luxafor Flag: USB-statuslampe med 3 LED'er på forsiden og 3 på bagsiden.

Bagsiden viser Pi'ens tilstand (se health.py) – grøn = klar, gul/rød blinkkode = advarsel/fejl.
Forsiden viser det samme, men blinker kort ved scanninger, så løberen kan se, om læsningen talte.

Lampen er en USB HID-enhed (04D8:F372). Vi skriver rapporter direkte til /dev/hidrawN – ingen
ekstra pakker. udev-reglen 60-racetimer-luxafor.rules giver gruppen input adgang. Selve blinkene
styres herfra (20 gange i sekundet), så mønstrene er ens på alle lamper.
"""
import colorsys
import math
import os
import threading
import time

from .. import health
from .base import READER_CHOICES, Module

VID, PID = "000004D8", "0000F372"
FRONT, BACK, ALL = 0x41, 0x42, 0xFF

GREEN, YELLOW, RED = (0, 255, 0), (255, 150, 0), (255, 0, 0)
BLUE, WHITE, OFF = (0, 70, 255), (255, 255, 255), (0, 0, 0)
ORANGE = (255, 45, 0)  # offline-tilstand: fast lys (gul bruges kun som blinkkode)

# Pi'ens tilstand → (forside, bagside). Et mønster er (art, farve, parameter).
STATUS_LOOK = {
    "starting": (("pulse", BLUE, 2.5), ("pulse", BLUE, 2.5)),
    "searching": (("blink", BLUE, 1), ("blink", BLUE, 1)),
    "ready": (("solid", GREEN, 0), ("solid", GREEN, 0)),
    "offline": (("solid", ORANGE, 0), ("solid", ORANGE, 0)),  # bevidst uden net – alt andet virker
    "warn": (("solid", GREEN, 0), ("code", YELLOW, None)),   # tidtagningen virker – kun bagsiden advarer
    "error": (("code", RED, None), ("code", RED, None)),
}
LOOK_TEXT = {"solid": "", "pulse": " pulserende", "blink": " blink", "code": " ×{n}"}
COLOR_NAME = {GREEN: "grøn", YELLOW: "gul", RED: "rød", BLUE: "blå", WHITE: "hvid", ORANGE: "orange", OFF: "slukket"}

# hændelse → (mønster, sekunder, tekst)
FLASH = {
    "read.counted": (("blink", GREEN, 5), 1.2, "Grønt blink (talt)"),
    "read.checkin": (("blink", GREEN, 5), 1.2, "Grønt blink (tjekket ind)"),
    "read.departure": (("blink", GREEN, 5), 1.2, "Grønt blink (afgang)"),
    "read.started": (("blink", GREEN, 5), 1.2, "Grønt blink (startet)"),
    "read.ignored": (("blink", YELLOW, 5), 1.6, "Gult blink (tæller ikke)"),
    "read.unknown": (("blink", RED, 5), 2.0, "Rødt blink (ukendt armbånd)"),
    "chip.registered": (("blink", BLUE, 5), 1.2, "Blåt blink (chip tildelt)"),
    "admin.chip": (("blink", BLUE, 5), 1.2, "Blåt blink (admin-armbånd)"),
    "read.callout": (("blink", BLUE, 5), 1.2, "Blåt blink (callout)"),
    "race.started": (("solid", GREEN, 0), 3.0, "Grønt lys (start)"),
}
SCAN_SIDES = [("front", "Forsiden"), ("both", "Begge sider"), ("off", "Ingen (kun status)")]


def frame(look, t):
    """Farven for et mønster til tiden t (sekunder)."""
    kind, color, p = look
    if kind == "solid":
        return color
    if kind == "pulse":
        level = 0.12 + 0.88 * (0.5 - 0.5 * math.cos(2 * math.pi * t / p))
        return tuple(int(c * level) for c in color)
    if kind == "blink":
        return color if (t * p) % 1 < 0.5 else OFF
    if kind == "code":  # p blink à 0,3 s med 0,3 s mellemrum, derefter 1,5 s pause
        pos = t % (p * 0.6 + 1.2)
        return color if pos < p * 0.6 and pos % 0.6 < 0.3 else OFF
    if kind == "rainbow":
        r, g, b = colorsys.hsv_to_rgb((t / 1.5) % 1, 1, 1)
        return int(r * 255), int(g * 255), int(b * 255)
    return OFF


def describe(look):
    kind, color, p = look
    return COLOR_NAME.get(color, "farve") + LOOK_TEXT.get(kind, "").format(n=p)


def _devices(vid=VID, pid=PID, prefix="luxafor", label="Luxafor Flag"):
    """Lamper af én type (USB VID/PID) fundet i sysfs: [{"device", "name", "path", "usb"}]. Bruges også af blink1.py."""
    root = os.environ.get("RACETIMER_FAKE_HIDRAW", "/sys/class/hidraw")
    try:
        names = sorted(os.listdir(root))
    except OSError:
        return []
    out = []
    for n in names:
        try:
            with open(os.path.join(root, n, "device", "uevent")) as f:
                ue = dict(line.strip().split("=", 1) for line in f if "=" in line)
        except OSError:
            continue
        if ue.get("HID_ID", "").upper().split(":")[1:] != [vid, pid]:
            continue
        # serienummeret følger lampen på tværs af USB-porte; uden serienummer bruges USB-stien
        dev = ue.get("HID_UNIQ") or prefix
        if any(d["device"] == dev for d in out):
            dev = f"{prefix}@{ue.get('HID_PHYS', n).split('/')[0]}"
        out.append({"device": dev, "name": ue.get("HID_NAME") or label, "path": f"/dev/{n}", "usb": True})
    return out


class Luxafor(Module):
    kind = "luxafor"
    label = "Statuslampe (Luxafor)"
    icon = "🚦"
    auto_add = True  # lampen skal vise opstart og fejl, også før nogen har været i admin
    fields = [
        {"key": "reader", "label": "Læser", "type": "select", "options": READER_CHOICES, "default": "all"},
        {"key": "brightness", "label": "Lysstyrke", "type": "range", "min": 10, "max": 100, "default": 70},
        {"key": "scans", "label": "Scanninger vises på", "type": "select", "options": SCAN_SIDES, "default": "front"},
    ]

    def __init__(self, cfg):
        self._flash = None   # (mønster, start, slut, sider)
        self._fd = None
        self._path = None
        self._sent = {}      # led → (farve, tidspunkt)
        self._look = None
        super().__init__(cfg)
        threading.Thread(target=self._render, daemon=True, name=f"luxafor-{cfg['id']}").start()

    @classmethod
    def detect(cls):
        return _devices()

    def handle(self, ev):
        look, secs, text = None, 0, None
        if ev["type"] == "race.countdown":
            n = ev.get("min") or 0
            look, secs, text = (("solid", GREEN, 0), 3.0, "Grønt lys (start)") if n == 0 else \
                (("code", WHITE, n), n * 0.6, f"Hvide blink ×{n} (nedtælling)")
        elif ev["type"] == "callout.tick":  # callout: hvidt blink pr. sekund-mærke, grønt ved løberens start
            n = ev.get("sec") or 0
            look, secs, text = (("solid", GREEN, 0), 2.0, "Grønt lys (callout-start)") if n == 0 else \
                (("solid", WHITE, 0), 0.25, f"Hvidt blink (callout {n} sek.)")
        elif ev["type"] in FLASH:
            look, secs, text = FLASH[ev["type"]]
        if not look or self.cfg.get("scans") == "off":
            return None
        if ev["type"] == "race.started" and self._flash and self._flash[0][1] == GREEN and time.time() < self._flash[2]:
            return None  # nedtællingens start og selve starten falder sammen
        sides = (FRONT, BACK) if self.cfg.get("scans") == "both" else (FRONT,)
        now = time.time()
        self._flash = (look, now, now + secs, sides)
        return text

    def test(self):
        now = time.time()
        self._flash = (("rainbow", WHITE, 0), now, now + 3, (FRONT, BACK))
        return "Lampen skifter mellem alle farver i 3 sekunder"

    def status(self):
        st = super().status()
        if st["state"] == "ok" and self._look:
            st["text"] = f"Forside: {describe(self._look[0])} · bagside: {describe(self._look[1])}"
        return st

    def stop(self):
        super().stop()
        self._write_side(ALL, OFF, force=True)
        self._close()

    # ------------------------------------------------------------ tegning

    def _render(self):
        found_at, st, st_at = 0, None, 0
        while not self._stop.is_set():
            now = time.time()
            if now - found_at > 3:
                found_at = now
                self._path = next((d["path"] for d in _devices() if d["device"] == self.cfg["device"]), None)
            if now - st_at > 1:  # tilstanden ændrer sig sjældent – blinkene tegnes stadig 20 gange i sekundet
                st, st_at = health.current(), now
            if not self._path:
                self._close()
            elif not self.cfg.get("enabled"):
                self._write_side(ALL, OFF)
            else:
                front, back = STATUS_LOOK.get(st["state"], STATUS_LOOK["error"])
                front, back = [(k, c, st["code"]) if k == "code" else (k, c, p) for k, c, p in (front, back)]
                self._look = (front, back)
                colors = {FRONT: frame(front, now), BACK: frame(back, now)}
                fl = self._flash
                if fl and now < fl[2]:
                    for side in fl[3]:
                        colors[side] = frame(fl[0], now - fl[1])
                b = int(self.cfg.get("brightness") or 70) / 100
                colors = {s: tuple(int(v * b) for v in c) for s, c in colors.items()}
                if colors[FRONT] == colors[BACK]:
                    self._write_side(ALL, colors[FRONT])
                else:
                    self._write_side(FRONT, colors[FRONT])
                    self._write_side(BACK, colors[BACK])
            self._stop.wait(0.05)

    def _write_side(self, led, rgb, force=False):
        """Send kun ændringer – men gentag hvert 5. sekund, hvis lampen er sat i igen eller noget andet har skrevet til den."""
        now = time.time()
        sides = (FRONT, BACK) if led == ALL else (led,)
        if not force and all(self._sent.get(s, (None, 0))[0] == rgb and now - self._sent[s][1] < 5 for s in sides):
            return
        data = bytes([0x00, 0x01, led, *rgb, 0, 0, 0])
        log = os.environ.get("RACETIMER_LUXAFOR_LOG")  # test uden lampe: skriv i stedet for at sende
        try:
            if log:
                with open(log, "a") as f:
                    f.write(f"{self.cfg['device']}\t{led:02x}\t{rgb[0]},{rgb[1]},{rgb[2]}\n")
            else:
                if not self._path:
                    return
                if self._fd is None:
                    self._fd = os.open(self._path, os.O_WRONLY)
                os.write(self._fd, data)
            for s in sides:
                self._sent[s] = (rgb, now)
            self.error = None
        except PermissionError:
            self.error = "Ingen adgang til lampen – kør opdateringen af Pi'en (installerer adgangsreglen) og sæt lampen i igen"
            self._close()
        except OSError as e:
            self.error = f"Kunne ikke styre lampen ({e.strerror or e})"
            self._close()

    def _close(self):
        if self._fd is not None:
            try:
                os.close(self._fd)
            except OSError:
                pass
            self._fd = None
            self._sent = {}
