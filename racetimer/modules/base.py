"""Fælles grundlag for moduler (eksterne enheder, typisk på USB)."""
import queue
import threading
import time

READER_CHOICES = [("all", "Begge læsere"), ("primary", "Læser 1 (primær)"), ("backup", "Læser 2 (backup)")]


class Module:
    """Én tilsluttet enhed. Underklasser sætter kind/label/fields og implementerer handle() og test().

    cfg er modulets gemte indstillinger (dict). handle() kører i modulets egen tråd, så en enhed,
    der hænger, aldrig forsinker andre moduler eller tidtagningen.
    """
    kind = ""
    label = ""
    icon = "🔌"
    fields = []

    def __init__(self, cfg):
        self.cfg = cfg
        self.present = False      # er enheden tilsluttet lige nu?
        self.error = None
        self.last_action = None   # (tidspunkt, tekst) – vises i admin
        self._q = queue.Queue(maxsize=50)
        self._stop = threading.Event()
        self._t = threading.Thread(target=self._run, daemon=True, name=f"module-{cfg['id']}")
        self._t.start()

    @classmethod
    def detect(cls):
        """Liste over tilsluttede enheder af denne type: [{"device": id, "name": tekst, "usb": bool}]."""
        return []

    def wants(self, ev):
        """Skal modulet reagere på hændelsen? Læser-filter: hændelser uden læser gælder alle."""
        reader = self.cfg.get("reader") or "all"
        return reader == "all" or ev.get("reader") in (None, reader) or ev.get("reader") not in ("primary", "backup")

    def offer(self, ev):
        if not self.cfg.get("enabled") or not self.wants(ev):
            return
        try:
            self._q.put_nowait(ev)
        except queue.Full:  # enheden hænger – smid den ældste hændelse væk
            try:
                self._q.get_nowait()
                self._q.put_nowait(ev)
            except (queue.Empty, queue.Full):
                pass

    def _run(self):
        while not self._stop.is_set():
            try:
                ev = self._q.get(timeout=1)
            except queue.Empty:
                continue
            if ev is None:
                break
            try:
                done = self.handle(ev)
                if done:
                    self.last_action = (time.time(), done)
                self.error = None
            except Exception as e:  # noqa: BLE001 – vises i admin, modulet kører videre
                self.error = str(e)

    def stop(self):
        self._stop.set()
        self._q.put(None)

    def handle(self, ev):
        """Reagér på en hændelse. Returnér en kort tekst om, hvad der skete (eller None)."""
        raise NotImplementedError

    def test(self):
        raise NotImplementedError

    def status(self):
        if not self.cfg.get("enabled"):
            return {"state": "off", "text": "Slået fra"}
        if not self.present:
            return {"state": "missing", "text": "Ikke tilsluttet"}
        if self.error:
            return {"state": "error", "text": self.error}
        return {"state": "ok", "text": "Klar"}
