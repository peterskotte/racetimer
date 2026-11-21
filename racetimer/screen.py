"""Pi'ens egen skærm slukker efter et stykke tid uden aktivitet og vækkes af et tryk, en scanning eller admin-armbåndet.

Skærmen slukkes rigtigt (strøm/baggrundslys) med wlopm på Wayland (Raspberry Pi OS med labwc) eller xset på X11.
Kiosk-siden viser samtidig en sort flade. Den fanger det første tryk, så et tryk for at vække aldrig også trykker på
en knap. Findes ingen af værktøjerne, er den sorte flade det eneste, der sker.

Mens et løb kører, slukker skærmen ikke (medmindre det er slået til), og de 5 minutter tælles fra løbet er slut.
"""
import glob
import os
import shutil
import subprocess
import threading
import time

from . import db

DEFAULTS = {"minutes": 5, "during_race": False}
CHOICES = (0, 1, 2, 5, 10, 15, 30, 60)  # 0 = aldrig


def settings():
    s = db.setting("screen_sleep") or {}
    return {**DEFAULTS, **{k: s[k] for k in DEFAULTS if k in s}}


def save_settings(b):
    s = settings()
    if "minutes" in b:
        m = int(b["minutes"]) if str(b["minutes"]).isdigit() else -1
        if m not in CHOICES:
            raise ValueError("Vælg et af tallene på listen")
        s["minutes"] = m
    if "during_race" in b:
        s["during_race"] = bool(b["during_race"])
    db.set_setting("screen_sleep", s)
    return s


def power_cmd(on):
    """Kommandoen, der tænder/slukker skærmen: (cmd, env, metode) – eller None, hvis Pi'en ikke kan."""
    rt = os.environ.get("XDG_RUNTIME_DIR") or f"/run/user/{os.getuid()}"
    sockets = sorted(glob.glob(os.path.join(rt, "wayland-[0-9]")))
    if sockets and shutil.which("wlopm"):
        env = {**os.environ, "XDG_RUNTIME_DIR": rt, "WAYLAND_DISPLAY": os.path.basename(sockets[0])}
        return ["wlopm", "--on" if on else "--off", "*"], env, "wlopm"
    if os.path.exists("/tmp/.X11-unix/X0") and shutil.which("xset"):
        return ["xset", "-display", ":0", "dpms", "force", "on" if on else "off"], dict(os.environ), "xset"
    return None


class ScreenPower(threading.Thread):
    def __init__(self, race_running):
        super().__init__(daemon=True, name="screen")
        self.race_running = race_running  # funktion: kører der et løb lige nu?
        self.last = time.time()
        self.asleep = False
        self.method = None
        self.error = None
        self._lock = threading.Lock()

    def run(self):
        while True:
            time.sleep(5)
            try:
                self.check()
            except Exception as e:  # noqa: BLE001 – skærmen må aldrig vælte tidtagningen
                self.error = str(e)

    def check(self, now=None):
        now = now or time.time()
        s = settings()
        with self._lock:
            if self.asleep or not s["minutes"]:
                return
            if not s["during_race"] and self.race_running():
                self.last = now  # tæl fra løbet er slut
                return
            if now - self.last < s["minutes"] * 60:
                return
            self.asleep = True
        self._power(False)

    def activity(self):
        """Nogen bruger skærmen (tryk, scanning). Returnerer True, hvis skærmen sov og nu er vækket."""
        with self._lock:
            self.last = time.time()
            if not self.asleep:
                return False
            self.asleep = False
        self._power(True)
        return True

    def sleep_now(self):
        with self._lock:
            self.asleep = True
        self._power(False)

    def _power(self, on):
        c = power_cmd(on)
        if not c:
            self.method = None
            return
        cmd, env, self.method = c
        try:
            r = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=5)
            self.error = None if r.returncode == 0 else (r.stderr or r.stdout or f"{cmd[0]} fejlede").strip()[:200]
        except (OSError, subprocess.SubprocessError) as e:
            self.error = str(e)

    def status(self):
        if self.method is None and power_cmd(True):
            self.method = power_cmd(True)[2]
        return {**settings(), "choices": list(CHOICES), "asleep": self.asleep, "method": self.method, "error": self.error,
                "idle_sec": round(time.time() - self.last)}
