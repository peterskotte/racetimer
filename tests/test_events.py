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



def test_devtest_reads_do_not_count():
    import time
    race("timed")
    before = db.q1("SELECT COUNT(*) n FROM reads")["n"]
    app._devtest.update(until=time.time() + 60, reads=[])
    try:
        assert app.handle_read("CHIP1", "backup") == {"test": True}
        assert app._devtest["reads"][0]["reader"] == "backup" and app._devtest["reads"][0]["chip"] == "CHIP1"
        assert db.q1("SELECT COUNT(*) n FROM reads")["n"] == before  # intet gemt som læsning
    finally:
        app._devtest.update(until=0)
    assert "id" in app.handle_read("CHIP1", "backup")  # efter testen tæller læsninger igen


def test_wifi_name_on_danish_pi():
    fake = os.path.join(TMP, "nmcli")
    with open(fake, "w") as f:  # som nmcli: oversætter yes/no, medmindre LC_ALL=C
        f.write('#!/bin/sh\n[ "$LC_ALL" = C ] && A=yes || A=ja\necho "no:Naboen"\necho "$A:Klubhus\\\\:5G"\n')
    os.chmod(fake, 0o755)
    os.environ["RACETIMER_NMCLI"] = fake
    try:
        assert app.wifi_ssid() == "Klubhus:5G"
    finally:
        del os.environ["RACETIMER_NMCLI"]


def test_testrace_dedup_and_not_published():
    from racetimer import sync
    rid = race("timed", {"min_lap_min": 0})
    db.ex("UPDATE races SET test=? WHERE id=?", (json.dumps({"speed": 1, "no_dedup": True, "no_checkin": True}), rid))
    assert not app.handle_read("CHIP1", "primary", S + 1)["duplicate"]
    assert not app.handle_read("CHIP1", "primary", S + 2)["duplicate"]  # intet dublet-filter i testløbet
    assert sync.public_race() is None  # testløb sendes aldrig til hjemmesiden
    db.ex("UPDATE races SET test=NULL WHERE id=?", (rid,))
    assert sync.public_race()["id"] == rid



def test_countdown_and_start_signal_each_yard():
    from racetimer import events
    rid = race("backyard", started=S)
    clock = {"t": S + 60 - 3}  # 3 sek. før næste start (60× testløb: 3-2-1 min = 3-2-1 sek.)
    info = {"phase": "running", "warnings_min": [3 / 60, 2 / 60, 1 / 60], "warnings_labels": [3, 2, 1]}
    got = []
    bus = type("B", (), {"publish": lambda self, ev: got.append(ev.get("min"))})()
    t = events.Ticker(bus, lambda r: ([], {**info, "next_start": S + 60 if clock["t"] < S + 60 else S + 120}), lambda: [])
    real = events.time.time
    events.time.time = lambda: clock["t"]
    try:
        for dt in (0, 1, 2, 3.2, 4):
            clock["t"] = S + 57 + dt
            t._countdown()
    finally:
        events.time.time = real
    assert got == [3, 2, 1, 0], got  # startsignalet kommer, selv om "næste start" er rykket til timen efter
    db.ex("DELETE FROM races WHERE id=?", (rid,))


def test_address_only_on_pi_screen():
    from types import SimpleNamespace as N
    req = lambda ip, h=None: N(client=N(host=ip), headers=h or {})
    assert "host" in app.live(req("127.0.0.1"))                      # Pi'ens egen kiosk-skærm
    assert "host" not in app.live(req("192.168.1.50"))               # publikum på netværket
    assert "host" not in app.live(req("100.84.51.64"))               # Tailscale
    assert "host" not in app.live(req("127.0.0.1", {"cf-ray": "x"}))  # Cloudflare-tunnel


def test_login_lockout_cannot_be_bypassed_with_fake_header():
    from types import SimpleNamespace as N
    req = lambda ip, h=None: N(client=N(host=ip), headers=h or {})
    assert app.client_ip(req("192.168.1.50", {"cf-connecting-ip": "1.2.3.4"})) == "192.168.1.50"  # forfalsket på LAN
    assert app.client_ip(req("127.0.0.1", {"cf-connecting-ip": "1.2.3.4"})) == "1.2.3.4"          # via cloudflared
    assert app.client_ip(req("192.168.1.50")) == "192.168.1.50"


def test_manual_taps():
    import asyncio
    from types import SimpleNamespace as N
    from fastapi import HTTPException

    def req(body):
        async def j():
            return body
        return N(json=j)
    rid = race("timed", {"min_lap_min": 0, "checkin_min": 0}, started=S)
    pid = db.q1("SELECT id FROM participants WHERE race_id=? AND bib=1", (rid,))["id"]
    db.ex("UPDATE races SET started_at=? WHERE id=?", (__import__("time").time() - 600, rid))
    assert asyncio.run(app.set_timing(rid, req({"timing": "manual"}), u={}))["timing"] == "manual"
    assert db.race(rid)["timing"] == "manual"
    r1 = asyncio.run(app.tap(rid, req({"participant_id": pid}), u={}))
    assert r1["event"]["type"] == "read.counted" and r1["event"]["lap"] == 1 and r1["event"]["name"] == "Løber 1"
    r2 = asyncio.run(app.tap(rid, req({"participant_id": pid}), u={}))  # dobbelttryk
    assert r2["event"]["type"] == "read.ignored" and r2["event"]["reason"] == "duplicate"
    u = app.tap_undo(rid, u={})
    assert u["name"] == "Løber 1" and db.q1("SELECT deleted FROM reads WHERE id=?", (r1["id"],))["deleted"] == 1
    try:
        app.tap_undo(rid, u={})
        raise AssertionError("intet at fortryde")
    except HTTPException as e:
        assert e.status_code == 404
    try:
        asyncio.run(app.set_timing(rid, req({"timing": "rfid"}), u={}))
        raise AssertionError("ukendt tæller skulle afvises")
    except HTTPException as e:
        assert e.status_code == 400


def test_distances_participants_and_events():
    import asyncio
    from types import SimpleNamespace as N
    from fastapi import HTTPException

    def req(body):
        async def j():
            return body
        return N(json=j)
    cfg = {"checkin_min": 0, "routes": [{"name": "Kort", "km": 5, "min_min": 1}, {"name": "Lang", "km": 10, "min_min": 2}],
           "distances": [{"name": "5 km", "routes": ["r1"]}, {"name": "15 km", "routes": ["r1", "r2"], "start_min": 0}]}
    rid = asyncio.run(app.create_race(req({"name": "Nytår", "type": "p2p", "config": cfg}), u={}))["id"]
    ds = db.race(rid)["config"]["distances"]
    assert [d["id"] for d in ds] == ["d1", "d2"] and ds[1]["routes"] == ["r1", "r2"]
    pid = asyncio.run(app.add_participant(rid, req({"name": "Ulla", "bib": 9, "chip": "U9", "distance": "15 KM"}), u={}))["id"]
    assert db.q1("SELECT distance FROM participants WHERE id=?", (pid,))["distance"] == "d2"
    try:
        asyncio.run(app.add_participant(rid, req({"name": "X", "distance": "42 km"}), u={}))
        raise AssertionError("ukendt distance skulle afvises")
    except HTTPException as e:
        assert e.status_code == 400
    app._activate(rid)
    db.ex("UPDATE races SET status='running', started_at=? WHERE id=?", (S, rid))
    ev = scan("U9", 90)  # 1. rute (kort) – ikke i mål endnu
    assert kind(ev) == "read.counted" and ev["lap"] == 1 and not ev["finish"]
    ev = scan("U9", 150)  # under lang rutes minimum (2 min)
    assert kind(ev) == "ignored:too_early"
    ev = scan("U9", 240)
    assert kind(ev) == "read.counted" and ev["finish"] and round(ev["time"]) == 240
    csv = app.results_csv(rid, u={}).body.decode()
    assert csv.splitlines()[0].lstrip("\ufeff").startswith("Distance;Placering") and "\n15 km;" in csv


def test_templates():
    import asyncio
    from types import SimpleNamespace as N
    from fastapi import HTTPException

    def req(body):
        async def j():
            return body
        return N(json=j)
    assert len(app.templates(u={})["examples"]) >= 3
    rid = race("p2p", {"cutoff_min": 90, "routes": [{"id": "r1", "name": "A", "km": 5, "min_min": 10}],
                       "distances": [{"id": "d1", "name": "5 km", "routes": ["r1"]}]})
    t = asyncio.run(app.save_template(req({"race_id": rid, "name": "Sommerløb"}), u={}))
    assert t["type"] == "p2p" and t["config"]["cutoff_min"] == 90 and t["config"]["distances"][0]["name"] == "5 km"
    t2 = asyncio.run(app.save_template(req({"name": "sommerløb", "type": "timed", "config": {"duration_h": 6}}), u={}))
    assert t2["id"] == t["id"] and len(app.templates(u={})["own"]) == 1  # samme navn → opdateret
    exp = json.loads(app.export_template(t["id"], u={}).body)
    assert exp["racetimer_template"] == 1 and exp["config"]["duration_h"] == 6
    for bad in ({"name": "X", "type": "golf"}, {"name": "", "type": "p2p"}):
        try:
            asyncio.run(app.save_template(req(bad), u={}))
            raise AssertionError("ugyldig skabelon skulle afvises")
        except HTTPException as e:
            assert e.status_code == 400
    app.delete_template(t["id"], u={})
    assert app.templates(u={})["own"] == []


def test_signup_import_and_age_classes():
    import asyncio
    from types import SimpleNamespace as N
    from racetimer import signup

    def req(body):
        async def j():
            return body
        return N(json=j)
    rid = race("p2p", {"routes": [{"id": "r1", "name": "A", "km": 5, "min_min": 1}],
                       "distances": [{"id": "d1", "name": "5 km", "routes": ["r1"]}, {"id": "d2", "name": "10 km", "routes": ["r1"]}]})
    db.ex("UPDATE races SET scheduled_start=? WHERE id=?", (__import__("time").mktime((2026, 12, 31, 12, 0, 0, 0, 0, -1)), rid))
    st = asyncio.run(app.put_signup(rid, req({"open": True, "age_step": 5, "age_from": 35, "bib_from": 100, "delete_days": 7}), u={}))
    assert st["open"] and st["age_step"] == 5 and st["confirm_email"]
    assert signup.clean({"reply_to": "loeb@klubben.dk"}, {})["reply_to"] == "loeb@klubben.dk"
    assert signup.clean({"reply_to": "x@y.dk\r\nBcc: a@b.dk"}, {})["reply_to"] == ""  # ingen header-injektion
    pub = signup.public_list()
    one = next(x for x in pub if x["id"] == rid)
    assert one["open"] and [d["name"] for d in one["distances"]] == ["5 km", "10 km"] and not any(k == "email" for x in pub for k in x)
    race_ = db.race(rid)
    entries = [{"id": 1, "name": "Ida Holm", "sex": "Kvinde", "birth_year": 1984, "club": "RTT", "email": "ida@example.dk", "distance": "d2"},
               {"id": 2, "name": "Ole Bo", "sex": "Mand", "birth_year": 2010, "email": "o@example.dk", "distance": "x"}]
    assert signup.import_entries(race_, entries) == 2
    assert signup.import_entries(db.race(rid), entries) == 0  # allerede hentet
    ida = db.q1("SELECT * FROM participants WHERE race_id=? AND name='Ida Holm'", (rid,))
    ole = db.q1("SELECT * FROM participants WHERE race_id=? AND name='Ole Bo'", (rid,))
    assert ida["bib"] == 100 and ida["distance"] == "d2" and ida["email"] == "ida@example.dk" and ole["bib"] == 101
    assert ole["distance"] is None and signup.settings(db.race(rid))["fetched"] == 2
    # nummeret fra hjemmesiden bevares; er det optaget på Pi'en, gives et nyt, og admin får besked
    one = next(x for x in signup.public_list() if x["id"] == rid)
    assert one["auto_bib"] and {1, 2, 100, 101} <= set(one["taken_bibs"])
    assert signup.import_entries(db.race(rid), [{"id": 3, "name": "Web Nr", "sex": "Mand", "bib": 150},
                                                {"id": 4, "name": "Dublet", "sex": "Mand", "bib": 1}]) == 2
    assert db.q1("SELECT bib FROM participants WHERE race_id=? AND name='Web Nr'", (rid,))["bib"] == 150
    assert db.q1("SELECT bib FROM participants WHERE race_id=? AND name='Dublet'", (rid,))["bib"] == 151
    assert "Dublet: nr. 1 var optaget" in signup.settings(db.race(rid))["bib_conflicts"][0]
    assert "ida@example.dk" not in json.dumps(signup.public_list())  # deltagernes e-mail sendes aldrig ud
    s = signup.settings(db.race(rid))
    assert signup.age_class(ida, db.race(rid), s) == "K40"  # 42 år på løbsdagen → 40-44
    assert signup.age_class(ole, db.race(rid), s) == "M Junior"
    assert signup.age_class({"sex": "Mand", "birth_year": 1996}, db.race(rid), s) == "M Senior"
    rows, _ = app.standings(db.race(rid))
    assert next(r for r in rows if r["name"] == "Ida Holm")["class"] == "K40"
    # afsluttet løb: hjemmesiden skal slette tilmeldingerne efter 7 dage
    db.ex("UPDATE races SET status='finished', finished_at=? WHERE id=?", (__import__("time").time() - 8 * 86400, rid))
    assert not any(x["id"] == rid for x in signup.public_list())


def test_mail_settings():
    import asyncio
    from types import SimpleNamespace as N
    from fastapi import HTTPException
    from racetimer import sync

    def req(body):
        async def j():
            return body
        return N(json=j)
    base = {"host": "smtp.klubben.dk", "security": "starttls", "user": "t@klubben.dk", "from_email": "t@klubben.dk"}
    r = asyncio.run(app.put_mail(req({**base, "password": "hemmelig"}), u={}))
    assert r["password_set"] and "password" not in r and r["port"] == 587 and sync.mail_config()["v"] == 1
    asyncio.run(app.put_mail(req({**base, "password": ""}), u={}))  # tom = behold
    assert sync.mail_config()["password"] == "hemmelig" and sync.mail_config()["v"] == 2
    for bad in ({**base, "host": "smtp.x.dk\r\nRCPT"}, {**base, "from_email": "ikke-en-mail"}):
        try:
            asyncio.run(app.put_mail(req(bad), u={}))
            raise AssertionError("ugyldig mailopsætning skulle afvises")
        except HTTPException as e:
            assert e.status_code == 400
    asyncio.run(app.put_mail(req({"clear": True}), u={}))
    assert not sync.mail_config().get("host") and not app.get_mail(u={})["password_set"]


def test_teaser_before_checkin():
    import time as _t
    rid = race("p2p", {"checkin_min": 30})
    now = _t.time()
    db.ex("UPDATE races SET scheduled_start=?, started_at=NULL, status='planned' WHERE id=?", (now + 2 * 3600, rid))
    rows, info = app.standings(db.race(rid), now)
    t = info["teaser"]
    assert t["count"] == 2 and t["list_at"] == now + 2 * 3600 - 1800 and t["name"] == "Test"
    payload = app.sync_mgr._results_payload(db.race(rid), False)
    assert payload["results"] == [] and payload["info"]["teaser"]  # ingen deltagerliste til hjemmesiden
    rows, info = app.standings(db.race(rid), now + 2 * 3600 - 1700)  # indtjekningen er åben
    assert "teaser" not in info and len(rows) == 2
    db.ex("UPDATE races SET scheduled_start=NULL WHERE id=?", (rid,))  # intet planlagt starttidspunkt
    assert "teaser" not in app.standings(db.race(rid), now)[1]
    db.ex("UPDATE races SET scheduled_start=?, config=? WHERE id=?",
          (now + 2 * 3600, json.dumps(engine.merged_config("p2p", {"checkin_min": 0})), rid))
    assert app.standings(db.race(rid), now)[1]["teaser"]["list_at"] == now + 2 * 3600 - 1800  # uden indtjekning: 30 min


def test_timed_label_shows_duration():
    rid = race("timed", {"duration_h": 6})
    assert app.standings(db.race(rid))[1]["type_label"] == "Tidsbaseret · 6 timer"
    assert app.hours_label(1) == "1 time" and app.hours_label(1.5) == "90 min"

if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
