"""Hændelser og moduler. Kør: python tests/test_events.py  (bruger en midlertidig datamappe)"""
import json
import os
import sys
import tempfile

TMP = tempfile.mkdtemp()
os.environ["RACETIMER_DATA"] = TMP
os.environ["RACETIMER_AUDIO_LOG"] = os.path.join(TMP, "lyd.log")
os.environ["RACETIMER_FAKE_ASOUND"] = os.path.join(TMP, "cards")
with open(os.environ["RACETIMER_FAKE_ASOUND"], "w") as f:
    f.write(" 0 [vc4hdmi0       ]: vc4-hdmi - vc4-hdmi-0\n"
            "                      vc4-hdmi-0\n"
            " 2 [Speak410       ]: USB-Audio - Jabra SPEAK 410 USB\n"
            "                      Jabra SPEAK 410 USB at usb-xhci-hcd.1-1, full speed\n")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from racetimer import app, db, engine, modules, outcome  # noqa: E402
from racetimer.modules import speaker  # noqa: E402

S = 2_000_000_000.0


def race(type_, cfg=None, started=None):
    db.ex("UPDATE races SET is_active=0")
    rid = db.ex("INSERT INTO races(name, type, config, status, started_at, is_active, created_at) VALUES (?,?,?,?,?,1,?)",
                ("Test", type_, json.dumps(engine.merged_config(type_, cfg or {})), "running" if started else "planned",
                 started, S))
    for bib in (1, 2):
        db.ex("INSERT INTO participants(race_id, bib, name, chip) VALUES (?,?,?,?)", (rid, bib, f"Løber {bib}", f"CHIP{bib}"))
    return rid


def scan(chip, t, reader="primary"):
    return outcome.evaluate(app.handle_read(chip, reader, S + t)["id"])


def kind(ev):
    return ev["type"] if ev["type"] != "read.ignored" else "ignored:" + ev["reason"]


def test_checkin_and_laps():
    rid = race("timed", {"duration_h": 1, "loop_km": 1, "min_lap_min": 1})
    assert kind(scan("CHIP1", -600)) == "read.checkin"
    assert kind(scan("CHIP1", -500)) == "ignored:already_checked_in"
    assert kind(scan("UKENDT", -400)) == "read.unknown"
    db.ex("UPDATE races SET status='running', started_at=? WHERE id=?", (S, rid))
    assert kind(scan("CHIP2", 100)) == "ignored:not_checked_in"
    ev = scan("CHIP1", 90)
    assert kind(ev) == "read.counted" and ev["lap"] == 1 and round(ev["time"]) == 90 and ev["name"] == "Løber 1"
    assert kind(scan("CHIP1", 100)) == "ignored:duplicate"
    assert kind(scan("CHIP1", 140)) == "ignored:too_early"
    assert scan("CHIP1", 200)["lap"] == 2
    db.ex("UPDATE participants SET status='RTC' WHERE race_id=? AND bib=1", (rid,))
    assert kind(scan("CHIP1", 400)) == "ignored:out"


def test_backyard_windows():
    rid = race("backyard")
    scan("CHIP1", -300)
    scan("CHIP2", -300)  # to løbere – ellers er den ene vinder med det samme
    db.ex("UPDATE races SET status='running', started_at=? WHERE id=?", (S, rid))
    assert kind(scan("CHIP1", 60)) == "read.departure"
    assert kind(scan("CHIP1", 600)) == "ignored:flag_zone"
    ev = scan("CHIP1", 1600)
    assert kind(ev) == "read.counted" and ev["lap"] == 1
    scan("CHIP2", 1650)
    assert kind(scan("CHIP1", 1700)) == "ignored:already_lap"


def test_p2p_finish():
    rid = race("p2p", {"min_time_min": 1})
    scan("CHIP1", -60)
    db.ex("UPDATE races SET status='running', started_at=? WHERE id=?", (S, rid))
    ev = scan("CHIP1", 1234)
    assert kind(ev) == "read.counted" and ev["finish"] and round(ev["time"]) == 1234
    assert kind(scan("CHIP1", 1300)) == "ignored:already_finished"


def test_speaker_module():
    found = speaker.Speaker.detect()
    assert found[0]["device"] == "Speak410" and found[0]["usb"] and found[-1]["device"] == "default"
    wav = speaker.tones_to_wav(speaker.SOUNDS["ok2"][1], 70)
    assert wav[:4] == b"RIFF" and len(wav) > 5000
    mgr = modules.ModuleManager()
    cfg = mgr.add("speaker", "Speak410", "Jabra")
    assert cfg["sounds"]["counted"] == "ok2" and cfg["reader"] == "all"
    cfg = mgr.update(cfg["id"], {"volume": 500, "reader": "backup", "sounds": {"counted": "chime", "ignored": "bogus"}})
    assert cfg["volume"] == 100 and cfg["reader"] == "backup"
    assert cfg["sounds"]["counted"] == "chime" and cfg["sounds"]["ignored"] == "low"  # ugyldig lyd → standard
    m = mgr.running[cfg["id"]]
    assert m.present
    assert not m.wants({"type": "read.counted", "reader": "primary"})
    assert m.wants({"type": "read.counted", "reader": "backup"}) and m.wants({"type": "race.countdown"})
    assert m.handle({"type": "read.counted", "reader": "backup"})
    assert m.handle({"type": "race.countdown", "min": 0}) and not m.handle({"type": "race.started"})  # ingen dobbelt startlyd
    log = open(os.environ["RACETIMER_AUDIO_LOG"]).read().split("\n")
    assert log[0].startswith("Speak410\tchime") and log[1].startswith("Speak410\tlong")
    try:
        mgr.add("laser", "x")
        raise AssertionError("ukendt modultype skulle afvises")
    except modules.ModuleError:
        pass


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
