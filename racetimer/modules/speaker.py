"""USB-højttaler: Pi'en spiller korte lyde ved scanning og nedtælling.

Lydene laves her i programmet (ingen lydfiler) og afspilles med aplay direkte på den valgte
lydenhed via ALSA. Virker ens på Pi 3, 4 og 5 og kræver ingen browser.
"""
import io
import math
import os
import re
import shutil
import struct
import subprocess
import time
import wave

from .base import READER_CHOICES, Module

RATE = 22050
# navn → (etiket, toner) – en tone er (frekvens Hz, sekunder); frekvens 0 = pause
SOUNDS = {
    "ok2": ("Lyst dobbelt-bip", [(1320, .09), (0, .05), (1760, .14)]),
    "ok": ("Lyst bip", [(1320, .16)]),
    "chime": ("Klokkespil", [(988, .11), (1319, .11), (1568, .22)]),
    "beep": ("Kort bip", [(880, .12)]),
    "long": ("Lang høj tone", [(1200, .9)]),
    "low": ("Dyb tone", [(330, .4)]),
    "low2": ("Dyb tone ×2", [(330, .22), (0, .08), (330, .22)]),
    "none": ("Ingen lyd", []),
}
# hvilke hændelser der spiller hvilken "plads", og standardlyden for hver
SLOTS = [
    ("counted", "Omgang / mål talt", "ok2"),
    ("checkin", "Tjekket ind / afgang / start", "ok"),
    ("ignored", "Læst, men tæller ikke", "low"),
    ("unknown", "Ukendt armbånd", "low2"),
    ("registered", "Chip tildelt (Deltagere → Scan)", "beep"),
    ("countdown", "Nedtælling 3-2-1 min", "beep"),
    ("go", "Start", "long"),
    ("reader_lost", "Læser mistet", "low2"),
]
EVENT_SLOT = {"read.counted": "counted", "read.checkin": "checkin", "read.departure": "checkin", "read.started": "checkin",
              "read.ignored": "ignored", "read.unknown": "unknown", "chip.registered": "registered",
              "race.started": "go", "reader.lost": "reader_lost"}


def tones_to_wav(tones, volume):
    """Lav en lille WAV i hukommelsen. Bløde kanter, så der ikke klikker."""
    amp = 32767 * max(0, min(100, volume)) / 100 * 0.9
    frames = bytearray()
    for freq, dur in tones:
        n = int(RATE * dur)
        fade = min(int(RATE * 0.008), n // 2)
        for i in range(n):
            env = min(1.0, i / fade, (n - 1 - i) / fade) if fade else 1.0
            v = amp * env * math.sin(2 * math.pi * freq * i / RATE) if freq else 0
            frames += struct.pack("<h", int(v))
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(bytes(frames))
    return buf.getvalue()


def _cards():
    """ALSA-lydkort fra /proc/asound/cards (RACETIMER_FAKE_ASOUND kan pege på en testfil)."""
    path = os.environ.get("RACETIMER_FAKE_ASOUND", "/proc/asound/cards")
    try:
        with open(path) as f:
            text = f.read()
    except OSError:
        return []
    out = []
    for m in re.finditer(r"^\s*(\d+)\s+\[(\S+)\s*\]:\s*(\S+)\s+-\s+(.+)$", text, re.M):
        idx, cid, driver, name = m.groups()
        out.append({"device": cid, "name": name.strip(), "usb": driver == "USB-Audio"})
    return out


class Speaker(Module):
    kind = "speaker"
    label = "Højttaler"
    icon = "🔊"
    fields = [
        {"key": "reader", "label": "Læser", "type": "select", "options": READER_CHOICES, "default": "all"},
        {"key": "volume", "label": "Lydstyrke", "type": "range", "min": 5, "max": 100, "default": 70},
        {"key": "sounds", "label": "Lyde", "type": "slots", "slots": [(k, lbl) for k, lbl, _ in SLOTS],
         "options": [(k, v[0]) for k, v in SOUNDS.items()], "default": {k: d for k, _, d in SLOTS}},
    ]

    def __init__(self, cfg):
        super().__init__(cfg)
        self._last = {}  # slot → tidspunkt (samme startlyd må ikke spille to gange lige efter hinanden)

    @classmethod
    def detect(cls):
        # USB-højttalere først; Pi'ens egne udgange (HDMI, minijack) kan også vælges
        return sorted(_cards(), key=lambda c: not c["usb"]) + [
            {"device": "default", "name": "Pi'ens standard-lydudgang", "usb": False}]

    def slot_for(self, ev):
        if ev["type"] == "race.countdown":
            return "go" if ev.get("min") == 0 else "countdown"
        return EVENT_SLOT.get(ev["type"])

    def handle(self, ev):
        slot = self.slot_for(ev)
        if not slot:
            return None
        if slot == "go" and time.time() - self._last.get("go", 0) < 5:
            return None  # nedtællingens "start" og selve starten falder sammen
        self._last[slot] = time.time()
        sound = (self.cfg.get("sounds") or {}).get(slot) or dict((k, d) for k, _, d in SLOTS)[slot]
        if sound == "none":
            return None
        self.play(sound)
        return f"{SOUNDS[sound][0]} ({dict((k, lbl) for k, lbl, _ in SLOTS)[slot].lower()})"

    def test(self):
        self.play("chime")
        return "Klokkespil afspillet"

    def play(self, sound):
        data = tones_to_wav(SOUNDS[sound][1], int(self.cfg.get("volume") or 70))
        log = os.environ.get("RACETIMER_AUDIO_LOG")  # test uden højttaler: skriv i stedet for at spille
        if log:
            with open(log, "a") as f:
                f.write(f"{self.cfg['device']}\t{sound}\t{len(data)}\n")
            return
        aplay = shutil.which("aplay")
        if not aplay:
            raise RuntimeError("aplay mangler – installér pakken alsa-utils")
        dev = "default" if self.cfg["device"] == "default" else f"plughw:CARD={self.cfg['device']}"
        r = subprocess.run([aplay, "-q", "-D", dev, "-"], input=data, capture_output=True, timeout=10)
        if r.returncode:
            err = r.stderr.decode("utf-8", "ignore").strip()
            if "busy" in err.lower():
                err = "Højttaleren er optaget af et andet program – prøv at sætte den i en anden USB-port eller genstart Pi'en"
            elif "permission" in err.lower():
                err = "Ingen adgang til lyd – kør opdateringen af Pi'en (giver RaceTimer adgang til lydenheder)"
            raise RuntimeError(err[:200] or "Afspilning fejlede")
