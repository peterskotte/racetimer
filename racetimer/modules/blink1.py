"""blink(1) mk3: lille USB-lampe, der sidder ved RFID-læseren, så løberen kan se, om scanningen talte.

Lampen blinker grønt (talt), gult (læst, men tæller ikke), rødt (ukendt armbånd) og blåt (callout, chip tildelt).
Mellem scanningerne lyser den grønt, når Pi'en er klar (som forsiden på Luxafor-lampen), eller er slukket.
Hver lampe vælger sin læser, så to lamper ved to læsere kun blinker ved deres egen læser.

blink(1) styres med HID feature reports (ikke almindelige skrivninger som Luxafor): rapport 1, kommandoen 'c'
(fade til farve) med fade-tid 0 og LED 0 = begge lysdioder. Det sendes med ioctl HIDIOCSFEATURE direkte til
/dev/hidrawN – ingen ekstra pakker. udev-reglen 60-racetimer-luxafor.rules giver også adgang til blink(1).
"""
import fcntl
import os
import time

from .. import health
from .base import READER_CHOICES
from .luxafor import FRONT, OFF, STATUS_LOOK, Luxafor, _devices, describe, frame

VID, PID = "000027B8", "000001ED"
IDLE = [("status", "Grøn, når Pi'en er klar (rød ved fejl)"), ("off", "Slukket – lyser kun ved scanninger")]


def _hidiocsfeature(size):
    return (3 << 30) | (size << 16) | (ord("H") << 8) | 0x06  # _IOC(_IOC_WRITE|_IOC_READ, 'H', 0x06, size)


class Blink1(Luxafor):
    kind = "blink1"
    label = "Lampe ved læseren (blink(1))"
    icon = "💡"
    auto_add = True  # sættes i ved læseren og skal virke med det samme
    fields = [
        {"key": "reader", "label": "Sidder ved læser", "type": "select", "options": READER_CHOICES, "default": "all"},
        {"key": "brightness", "label": "Lysstyrke", "type": "range", "min": 10, "max": 100, "default": 100},
        {"key": "idle", "label": "Mellem scanninger", "type": "select", "options": IDLE, "default": "status"},
    ]

    @classmethod
    def detect(cls):
        return _devices(VID, PID, "blink1", "blink(1)")

    def _render(self):
        found_at, st, st_at = 0, None, 0
        while not self._stop.is_set():
            now = time.time()
            if now - found_at > 3:
                found_at = now
                self._path = next((d["path"] for d in self.detect() if d["device"] == self.cfg["device"]), None)
            if now - st_at > 1:
                st, st_at = health.current(), now
            if not self._path:
                self._close()
            elif not self.cfg.get("enabled"):
                self._write_side(FRONT, OFF)
            else:
                k, c, p = STATUS_LOOK.get(st["state"], STATUS_LOOK["error"])[0]  # forsidens udseende: det løberne skal se
                look = (k, c, st["code"]) if k == "code" else (k, c, p)
                if self.cfg.get("idle") == "off" and st["state"] not in ("error",):
                    look = ("solid", OFF, 0)
                self._look = (look, look)
                color = frame(look, now)
                fl = self._flash
                if fl and now < fl[2]:
                    color = frame(fl[0], now - fl[1])
                b = int(self.cfg.get("brightness") or 100) / 100
                self._write_side(FRONT, tuple(int(v * b) for v in color))
            self._stop.wait(0.05)

    def status(self):
        st = super(Luxafor, self).status()
        if st["state"] == "ok" and self._look:
            st["text"] = f"Viser: {describe(self._look[0])}"
        return st

    def _write_side(self, led, rgb, force=False):
        """Begge lysdioder får samme farve. Send kun ændringer – men gentag hvert 5. sekund (lampen kan være sat i igen)."""
        now = time.time()
        if not force and self._sent.get(FRONT, (None, 0))[0] == rgb and now - self._sent[FRONT][1] < 5:
            return
        log = os.environ.get("RACETIMER_LUXAFOR_LOG")  # test uden lampe: skriv i stedet for at sende
        try:
            if log:
                with open(log, "a") as f:
                    f.write(f"{self.cfg['device']}\tblink1\t{rgb[0]},{rgb[1]},{rgb[2]}\n")
            else:
                if not self._path:
                    return
                if self._fd is None:
                    self._fd = os.open(self._path, os.O_RDWR)
                buf = bytes([0x01, ord("c"), *rgb, 0, 0, 0, 0])  # rapport 1: fade til farve på 0 ms, begge lysdioder
                fcntl.ioctl(self._fd, _hidiocsfeature(len(buf)), buf)
            self._sent[FRONT] = (rgb, now)
            self.error = None
        except PermissionError:
            self.error = "Ingen adgang til lampen – kør opdateringen af Pi'en (installerer adgangsreglen) og sæt lampen i igen"
            self._close()
        except OSError as e:
            self.error = f"Kunne ikke styre lampen ({e.strerror or e})"
            self._close()

    def stop(self):
        super(Luxafor, self).stop()
        self._write_side(FRONT, OFF, force=True)
        self._close()
