"""Pi'ens skærm slukker efter et stykke tid uden aktivitet (screen.py). Kør: python tests/test_screen.py"""
import asyncio
import json
import os
import sys
import tempfile
import time
from types import SimpleNamespace as N

os.environ["RACETIMER_DATA"] = tempfile.mkdtemp()
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from fastapi import HTTPException  # noqa: E402

from racetimer import app, db, screen  # noqa: E402

CALLS = []
screen.power_cmd = lambda on: (["true"], dict(os.environ), "test") if CALLS.append(on) is None else None


def req(ip, body=None, host="localhost:8000"):
    async def j():
        return body or {}
    return N(client=N(host=ip), headers={"host": host}, cookies={}, json=j)


def test_sleeps_after_idle_and_wakes():
    sp = app.screen_power
    assert screen.settings() == {"minutes": 5, "during_race": False}
    sp.last = time.time()
    sp.check(time.time() + 4 * 60)
    assert not sp.asleep and not CALLS
    sp.check(time.time() + 5 * 60 + 1)
    assert sp.asleep and CALLS == [False]  # skærmen er slukket
    assert app.screen_state(req("127.0.0.1")) == {"asleep": True}
    assert app.screen_activity(req("127.0.0.1")) == {"woke": True} and CALLS == [False, True]
    assert app.screen_activity(req("127.0.0.1")) == {"woke": False}  # vågen: bare aktivitet
    for bad in (req("192.168.1.20"), req("127.0.0.1", host="racetimer.example")):  # kun Pi'ens egen skærm
        try:
            app.screen_state(bad)
            raise AssertionError("skulle afvises")
        except HTTPException as e:
            assert e.status_code == 403


def test_never_during_race_unless_chosen():
    sp = app.screen_power
    CALLS.clear()
    db.ex("UPDATE races SET is_active=0")  # demo-løbet
    rid = db.ex("INSERT INTO races(name, type, config, status, started_at, created_at, is_active) VALUES (?,?,?,?,?,0,1)",
                ("Løb", "p2p", json.dumps({}), "running", time.time()))
    sp.last = 0
    sp.check()
    assert not sp.asleep and time.time() - sp.last < 5  # tæller fra løbet er slut
    asyncio.run(app.screen_settings_put(req("127.0.0.1", {"during_race": True}), u={}))
    sp.last = 0
    sp.check()
    assert sp.asleep
    sp.activity()
    db.ex("UPDATE races SET status='finished', is_active=0 WHERE id=?", (rid,))
    asyncio.run(app.screen_settings_put(req("127.0.0.1", {"minutes": 0}), u={}))
    sp.last = 0
    sp.check()
    assert not sp.asleep  # 0 = aldrig
    try:
        asyncio.run(app.screen_settings_put(req("127.0.0.1", {"minutes": 7}), u={}))
        raise AssertionError("7 er ikke et valg")
    except HTTPException as e:
        assert e.status_code == 400
    asyncio.run(app.screen_settings_put(req("127.0.0.1", {"minutes": 5, "during_race": False}), u={}))


def test_admin_chip_and_reads_wake_without_switching_page():
    sp = app.screen_power
    asyncio.run(app.admin_chips_add(req("127.0.0.1", {"chip": "AB12CD"}), u={}))
    t = 1_900_000_000
    app.handle_read("AB12CD", "primary", t)
    assert app._admin_scan["at"] == t
    sp.sleep_now()
    app.handle_read("AB12CD", "primary", t + 10)  # skærmen sov: vækkes, men skifter ikke til klar-tjekket
    assert not sp.asleep and app._admin_scan["at"] == t
    app.handle_read("AB12CD", "primary", t + 20)  # vågen: skifter som før
    assert app._admin_scan["at"] == t + 20
    sp.sleep_now()
    app.handle_read("FFEE01", "primary", t + 30)  # en løber scanner (fx indtjekning)
    assert not sp.asleep


if __name__ == "__main__":
    db.conn()
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
