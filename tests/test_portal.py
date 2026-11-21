"""Løbsportal (portal.py): parring, kobling, tilmeldinger og hvad portalen får. Kør: python tests/test_portal.py

Portalen er en falsk server i testen (sync._post erstattes), så der bruges ikke net.
"""
import asyncio
import json
import os
import sys
import tempfile
from types import SimpleNamespace as N

os.environ["RACETIMER_DATA"] = tempfile.mkdtemp()
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from fastapi import HTTPException  # noqa: E402

from racetimer import app, db, engine, portal, signup, sync  # noqa: E402

SENT = []  # (url, payload, key)
CREATED = []
TEMPLATES = []
SIGNUPS = [{"id": 1, "name": "Mette Kjærsgaard", "sex": "Kvinde", "club": "Skørping IF", "birth_year": 1984,
            "email": "mette@example.test", "distance": "d1"},
           {"id": 2, "name": "Line Mortensen", "sex": "Kvinde", "club": "", "birth_year": 1995, "email": "line@example.test",
            "distance": None}]


def fake_post(url, payload, key=None, gz=True):
    SENT.append((url, payload, key))
    if "/wp-json/" in url and url.endswith("/pair"):
        raise RuntimeError("HTTP 404: rest_no_route")  # pæne adresser slået fra – Pi'en skal prøve ?rest_route=
    if url.endswith("rest_route=/racetimer/v1/pair"):
        if payload["code"] != "K7QM4TXD":
            raise RuntimeError("HTTP 403: Koden er forkert eller udløbet.")
        return {"ok": True, "token": "tok-123456789012345678901234", "organizer": "Skørping IF", "portal": "Rebild Trail",
                "sync_url": "https://rebildtrail.example/?rest_route=/racetimer/v1/sync", "events_url": "https://rebildtrail.example/loeb/"}
    assert key == "tok-123456789012345678901234" or "modtag.php" in url
    ev = payload["event"]
    if ev == "portal_events":
        return {"ok": True, "organizer": "Skørping IF", "events": [{"id": 5, "title": "Nisseløbet", "distances": [{"id": 50, "name": "5 km"}]}]}
    if ev == "portal_link":
        return {"ok": True, "event": {"id": payload["event_id"], "title": "Nisseløbet", "url": "https://rebildtrail.example/loeb/nisse/"}}
    if ev == "portal_create":
        CREATED.append(payload)
        return {"ok": True, "besked": "Oprettet", "event": {"id": 9, "title": payload["race_name"], "url": "https://rebildtrail.example/loeb/x/"},
                "distances": {d["id"]: 90 + i for i, d in enumerate(payload["distances"]) if d["id"]}}
    if ev == "portal_templates":
        TEMPLATES.append(payload["templates"])
        return {"ok": True, "count": len(payload["templates"]), "url": "https://rebildtrail.example/arrangoer/nyt/"}
    if ev == "hent_tilmeldinger":
        if "modtag.php" in url:
            return {"tilmeldinger": {}}
        return {"tilmeldinger": {rid: [e for e in SIGNUPS if e["id"] > since] for rid, since in payload["loeb"].items()}}
    return {"ok": True}


def req(body):
    async def j():
        return body
    return N(json=j)


def test_pair_link_fetch_and_results():
    sync._post = fake_post
    # forkert kode: fejlen fra portalen vises, og der oprettes ingen forbindelse
    try:
        asyncio.run(app.portal_pair(req({"url": "rebildtrail.example", "code": "AAAA-BBBB"}), u={}))
        raise AssertionError("forkert kode skulle afvises")
    except HTTPException as e:
        assert e.status_code == 502 and "Koden" in e.detail
    assert not portal.portals()
    d = asyncio.run(app.portal_pair(req({"url": "rebildtrail.example/", "code": "k7qm-4txd"}), u={}))
    assert d["organizer"] == "Skørping IF" and d["base"] == "https://rebildtrail.example"
    dest = portal.portals()[0]
    assert dest["url"].endswith("rest_route=/racetimer/v1/sync") and dest["type"] == "webhook" and dest["key"]

    # en almindelig hjemmeside ved siden af portalen
    sync.save_destinations(sync.destinations() + [{"id": "web1", "name": "Klubben", "type": "webhook", "url": "https://klub.example/racetimer/modtag.php",
                                                   "key": "hemmelig-noegle-12", "interval_sec": 60, "on_finish": True, "enabled": True}])
    # portalen får aldrig mailopsætningen (SMTP-adgangskoden) – kun egne hjemmesider
    assert [x["id"] for x in app._signup_dests()] == ["web1"]
    assert {x["id"] for x in app._signup_dests(portals=True)} == {"web1", dest["id"]}

    cfg = engine.merged_config("p2p", {"distances": [{"id": "d1", "name": "5 km", "km": 5}, {"id": "d2", "name": "10 km", "km": 10}]})
    db.ex("UPDATE races SET is_active=0")  # demoløbet er aktivt i en ny database
    rid = db.ex("INSERT INTO races(name, type, config, status, is_active, created_at) VALUES (?,?,?,?,1,0)",
                ("Nisseløbet 2026", "p2p", json.dumps(cfg), "planned"))
    db.ex("INSERT INTO participants(race_id, bib, name, signup_id) VALUES (?,?,?,?)", (rid, 1, "Fra hjemmesiden", 1))
    r = asyncio.run(app.link_portal(rid, req({"dest": dest["id"], "event_id": 5, "distances": {"d1": 50, "zz": 51}}), u={}))
    assert r["added"] == 2, r
    s = signup.settings(db.race(rid))
    assert s["mode"] == "portal" and s["portal"]["distances"] == {"d1": 50} and s["portal_fetched"] == 2
    link = next(p for u, p, k in SENT if p.get("event") == "portal_link")
    assert link["race_id"] == rid and link["distances"] == {"d1": 50}
    # portalens tilmelding nr. 1 blandes ikke med hjemmesidens nr. 1 – og får startnummer på Pi'en
    ps = db.q("SELECT bib, name, distance, signup_id FROM participants WHERE race_id=? ORDER BY bib", (rid,))
    assert [(p["name"], p["signup_id"]) for p in ps] == [("Fra hjemmesiden", 1), ("Mette Kjærsgaard", -1), ("Line Mortensen", -2)]
    assert ps[1]["distance"] == "d1" and ps[1]["bib"] == 2 and ps[2]["bib"] == 3
    # hjemmesiden får ikke løbet som tilmeldingsløb, og den spørges ikke efter portalens tilmeldte
    assert all(x["id"] != rid for x in signup.public_list())
    assert str(rid) not in signup._wanted(dest=next(x for x in sync.destinations() if x["id"] == "web1"))
    assert signup._wanted(dest=dest) == {str(rid): 2}
    # hentes igen: ingen dubletter
    SENT.clear()
    assert sync.SyncManager(app.standings).fetch_signups(dest, force=True) == 0
    assert SENT[0][1]["loeb"] == {str(rid): 2}

    # resultaterne til portalen: portalens løbere kan genkendes, billeder sendes ikke
    db.ex("UPDATE races SET status='running', started_at=? WHERE id=?", (1_000, rid))
    SENT.clear()
    mgr = sync.SyncManager(app.standings)
    assert mgr.send(dest)
    payload = SENT[-1][1]
    rows = {x["name"]: x for x in payload.get("results") or []}
    assert rows["Mette Kjærsgaard"]["portal_signup"] == 1 and "portal_signup" not in rows["Fra hjemmesiden"]
    assert not payload["branding"].get("images")
    assert "chip" not in json.dumps(payload["results"])

    # skift væk fra portalen: koblingen fjernes på portalen
    SENT.clear()
    asyncio.run(app.put_signup(rid, req({"mode": "none"}), u={}))
    assert any(p.get("event") == "portal_link" and p["event_id"] == 0 for u, p, k in SENT)
    assert "portal" not in signup.settings(db.race(rid))
    # testløb kan ikke kobles
    tid = db.ex("INSERT INTO races(name, type, config, status, created_at, test) VALUES (?,?,?,?,0,?)", ("Test", "p2p", json.dumps(cfg), "planned", '{"speed": 1}'))
    try:
        asyncio.run(app.link_portal(tid, req({"dest": dest["id"], "event_id": 5}), u={}))
        raise AssertionError("testløb skulle afvises")
    except HTTPException as e:
        assert e.status_code == 400

    # afbryd: destinationen forsvinder, også uden svar fra portalen
    asyncio.run(app.link_portal(rid, req({"dest": dest["id"], "event_id": 5}), u={}))
    r = asyncio.run(app.portal_unpair(dest["id"], u={}))
    assert not portal.portals() and signup.settings(db.race(rid))["mode"] == "none"


def test_transfer_races():
    sync._post = fake_post
    if not portal.portals():
        asyncio.run(app.portal_pair(req({"url": "rebildtrail.example", "code": "K7QM4TXD"}), u={}))
    dest = portal.portals()[0]
    cfg = engine.merged_config("p2p", {"routes": [{"id": "r1", "name": "Rute", "km": 5, "min_min": 10}],
                                       "distances": [{"id": "d1", "name": "10 km", "routes": ["r1", "r1"]}]})
    db.ex("UPDATE races SET is_active=0")
    coming = db.ex("INSERT INTO races(name, type, config, status, scheduled_start, created_at) VALUES (?,?,?,?,?,0)",
                   ("Forårsløbet", "p2p", json.dumps(cfg), "planned", 2_000_000_000))
    done = db.ex("INSERT INTO races(name, type, config, status, started_at, finished_at, created_at) VALUES (?,?,?,?,?,?,0)",
                 ("6 timer", "timed", json.dumps(engine.merged_config("timed", {"duration_h": 6})), "finished", 1_000, 22_600))
    db.ex("INSERT INTO participants(race_id, bib, name) VALUES (?,?,?)", (done, 1, "Anna"))
    listed = {r["id"]: r for r in app.portal_transferable(dest["id"], u={})["races"]}
    assert coming in listed and done in listed and not listed[coming]["portal"]
    CREATED.clear(); SENT.clear()
    res = asyncio.run(app.portal_transfer(dest["id"], req({"race_ids": [coming, done]}), u={}))["results"]
    assert all(x["ok"] for x in res), res
    c = next(x for x in CREATED if x["race_id"] == coming)
    assert c["distances"] == [{"id": "d1", "name": "10 km", "km": 10, "start_min": 0}] and c["starts_at"] == 2_000_000_000 and not c["finished"]
    t = next(x for x in CREATED if x["race_id"] == done)
    assert t["finished"] and t["distances"][0]["name"] == "6 timer"
    # kommende løb: koblet som tilmeldingsløb; afholdt løb: de endelige resultater er sendt
    s = signup.settings(db.race(coming))
    assert s["mode"] == "portal" and s["portal"]["distances"] == {"d1": 90}
    final = [p for u, p, k in SENT if p.get("event") == "final"]
    assert final and final[0]["race"]["id"] == done and final[0]["results"][0]["name"] == "Anna"
    assert signup.settings(db.race(done))["portal_results"]["event_id"] == 9
    assert app.portal_transferable(dest["id"], u={})["races"][0]["portal"]



def test_templates_to_portal():
    sync._post = fake_post
    if not portal.portals():
        asyncio.run(app.portal_pair(req({"url": "rebildtrail.example", "code": "K7QM4TXD"}), u={}))
    dest = portal.portals()[0]
    TEMPLATES.clear()
    cfg = {"routes": [{"id": "r1", "name": "A", "km": 8, "min_min": 20}, {"id": "r2", "name": "B", "km": 13, "min_min": 30}],
           "distances": [{"id": "d1", "name": "21 km", "routes": ["r1", "r2"]}, {"id": "d2", "name": "8 km", "start_min": 30, "routes": ["r1"]}]}
    db.set_setting("templates", [])
    app._push_templates_bg = lambda: None  # baggrundsafsendelsen testes ikke her
    asyncio.run(app.save_template(req({"name": "Rebild Trail", "description": "Tre ruter", "type": "p2p", "config": cfg})))
    r = asyncio.run(app.portal_templates(dest["id"], u={}))
    sent = TEMPLATES[-1]
    assert r["count"] == len(sent) == 1 + len(engine.EXAMPLE_TEMPLATES)
    own = sent[0]
    assert own["name"] == "Rebild Trail" and not own["example"] and set(own) == {"id", "name", "description", "type", "example", "distances"}
    assert own["distances"] == [{"id": "d1", "name": "21 km", "km": 21, "start_min": 0}, {"id": "d2", "name": "8 km", "km": 8, "start_min": 30}]
    assert all(t["example"] for t in sent[1:])
    assert next(t for t in sent if t["id"] == "ex-traening")["distances"][0]["name"] == "1 time"



def test_callout_names_never_leave_the_pi():
    info = {"callout_sec": 15, "callouts": [{"name": "Anna", "start_ts": 1}], "distances": [{"id": "d1", "callouts": [{"name": "Anna"}]}]}
    out = sync._public_info(info)
    assert "callouts" not in out and "callouts" not in out["distances"][0] and out["callout_sec"] == 15
    assert info["callouts"]  # admin beholder listen



def test_lap_times_are_sent():
    db.ex("UPDATE races SET is_active=0")
    rid = db.ex("INSERT INTO races(name, type, config, status, started_at, created_at, is_active) VALUES (?,?,?,?,?,0,1)",
                ("Omgange", "timed", json.dumps(engine.merged_config("timed", {"checkin_min": 0, "min_lap_min": 1, "duration_h": 1})),
                 "running", 1000.0))
    pid = db.ex("INSERT INTO participants(race_id, bib, name) VALUES (?,?,?)", (rid, 1, "Bo"))
    for ts in (1300.04, 1610.0, 1880.26):
        db.ex("INSERT INTO reads(race_id, chip, reader, ts, participant_id) VALUES (?,?,?,?,?)", (rid, "X", "primary", ts, pid))
    row = app.sync_mgr._results_payload(db.race(rid), False)["results"][0]
    assert row["splits"] == [300.0, 310.0, 270.3] and row["best_lap"] == 270.26 and row["laps"] == 3



def test_import_race_from_portal():
    import time as _t
    start = _t.mktime((2026, 12, 31, 10, 0, 0, 0, 0, -1))
    ev = {"id": 77, "title": "Nytårsløbet", "starts_at": start, "kind": "trail", "racetimer": True,
          "distances": [{"id": 701, "name": "15 km", "km": 15, "start_time": None},
                        {"id": 702, "name": "5 km", "km": 5, "start_time": "10:30", "start_ts": start + 1800}]}
    typ, name, st, cfg, link = portal.race_from_event(ev)
    assert typ == "p2p" and name == "Nytårsløbet" and st == start and link == {"d1": 701, "d2": 702}
    assert [(d["name"], d["start_min"], d["routes"]) for d in cfg["distances"]] == [("15 km", 0, ["r1"]), ("5 km", 30, ["r2"])]
    assert [r["km"] for r in cfg["routes"]] == [15, 5]
    typ, _, _, cfg, link = portal.race_from_event({"title": "6/12", "starts_at": start, "kind": "timeloeb",
        "distances": [{"id": 1, "name": "6 timer", "km": None}, {"id": 2, "name": "12 timer", "km": None}]})
    assert typ == "timed" and cfg["duration_h"] == 12 and [d["duration_h"] for d in cfg["distances"]] == [6, 12] and link == {"d1": 1, "d2": 2}
    assert portal.race_from_event({"title": "By", "starts_at": start, "kind": "backyard", "distances": []})[0] == "backyard"
    # ældre portal uden start_ts: klokkeslæt i Pi'ens tidszone
    old = portal.race_from_event({**ev, "distances": [{"id": 1, "name": "A", "km": 5}, {"id": 2, "name": "B", "km": 5, "start_time": "10:45"}]})
    assert [d["start_min"] for d in old[3]["distances"]] == [0, 45]
    assert portal.race_from_event({"title": "5 km", "starts_at": start, "kind": "vej", "distances": [{"id": 9, "name": "5 km", "km": 5}]})[3]["distance_km"] == 5

    # hent løbet: kun med flueben, og det kobles og henter tilmeldte
    sync._post = fake_post
    if not portal.portals():
        asyncio.run(app.portal_pair(req({"url": "rebildtrail.example", "code": "K7QM4TXD"}), u={}))
    dest = portal.portals()[0]
    no_flag = {**ev, "id": 78, "racetimer": False}
    orig = portal.events
    portal.events = lambda d: {"events": [ev, no_flag], "links": {}}
    try:
        lst = asyncio.run(app.portal_importable(dest["id"], u={}))
        assert [e["id"] for e in lst["events"]] == [77] and lst["without_flag"] == 1
        try:
            asyncio.run(app.portal_import(dest["id"], req({"event_id": 78}), u={}))
            raise AssertionError("løb uden flueben skulle afvises")
        except HTTPException as e:
            assert e.status_code == 400
        out = asyncio.run(app.portal_import(dest["id"], req({"event_id": 77}), u={}))
        assert out["ok"], out
        race = db.race(out["id"])
        s = signup.settings(race)
        assert race["name"] == "Nytårsløbet" and race["type"] == "p2p" and race["scheduled_start"] == start
        assert s["mode"] == "portal" and s["portal"]["event_id"] and s["portal"]["distances"] == {"d1": 701, "d2": 702}
        linked = [p for u, p, k in SENT if p.get("event") == "portal_link"][-1]
        assert linked["event_id"] == 77 and linked["distances"] == {"d1": 701, "d2": 702}

        # hent igen = overfør ændringerne: nyt navn, ny distance, starttid før start
        ev2 = {**ev, "title": "Nytårsløbet 2027", "starts_at": start + 3600,
               "distances": ev["distances"] + [{"id": 703, "name": "Børneløb", "km": 1, "start_time": "11:00", "start_ts": start + 3600}]}
        portal.events = lambda d: {"events": [ev2], "links": {str(out["id"]): {"event_id": 77}}}
        lst = asyncio.run(app.portal_importable(dest["id"], u={}))
        assert lst["events"][0]["race_id"] == out["id"]
        up = asyncio.run(app.portal_import(dest["id"], req({"event_id": 77}), u={}))
        assert up["updated"] and up["id"] == out["id"], up
        race = db.race(out["id"])
        ds = {d["name"]: d for d in race["config"]["distances"]}
        assert race["name"] == "Nytårsløbet 2027" and race["scheduled_start"] == start + 3600 and set(ds) == {"15 km", "5 km", "Børneløb"}
        assert ds["Børneløb"]["start_min"] == 0 and signup.settings(race)["portal"]["distances"][ds["Børneløb"]["id"]] == 703
        assert db.q1("SELECT COUNT(*) n FROM races")["n"] == db.q1("SELECT MAX(id) m FROM races")["m"]  # intet nyt løb
    finally:
        portal.events = orig


def test_portal_signup_changes_v2():
    """Løbsportalen (v2) sender også rettede og afmeldte tilmeldinger."""
    db.ex("UPDATE races SET is_active=0")
    rid = db.ex("INSERT INTO races(name, type, config, status, created_at, is_active) VALUES (?,?,?,?,0,1)",
                ("Ændringer", "p2p", json.dumps(engine.merged_config("p2p", {})), "planned"))
    race = db.race(rid)
    signup.save(rid, {**signup.settings(race), "mode": "portal"})
    n = signup.import_entries(db.race(rid), [{"id": 11, "seq": 11, "name": "Anne Berg", "sex": "Kvinde", "club": "A"},
                                             {"id": 12, "seq": 12, "name": "Bo Lund", "sex": "Mand"},
                                             {"id": 13, "seq": 13, "name": "Carl Holm"}], portal=True)
    assert n == 3
    pid13 = db.q1("SELECT id FROM participants WHERE race_id=? AND signup_id=-13", (rid,))["id"]
    db.ex("INSERT INTO reads(race_id, chip, reader, ts, participant_id) VALUES (?,?,?,?,?)", (rid, "X", "primary", 1.0, pid13))
    bib = db.q1("SELECT bib FROM participants WHERE signup_id=-11 AND race_id=?", (rid,))["bib"]
    signup.import_entries(db.race(rid), [{"id": 11, "seq": 20, "name": "Anne Berg-Holm", "sex": "Kvinde", "club": "B"},
                                         {"id": 12, "seq": 21, "cancelled": True}, {"id": 13, "seq": 22, "cancelled": True}], portal=True)
    a = db.q1("SELECT * FROM participants WHERE race_id=? AND signup_id=-11", (rid,))
    assert a["name"] == "Anne Berg-Holm" and a["club"] == "B" and a["bib"] == bib  # rettet – startnummer bevaret
    assert not db.q1("SELECT 1 FROM participants WHERE race_id=? AND signup_id=-12", (rid,))  # afmeldt → fjernet
    assert db.q1("SELECT 1 FROM participants WHERE race_id=? AND signup_id=-13", (rid,))  # har tider → bliver
    assert signup.settings(db.race(rid))["portal_fetched"] == 22


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
