"""Førstegangskode, stærke koder og system-hjælperen. Kør: python tests/test_security.py"""
import asyncio
import json
import os
import stat
import subprocess
import sys
import tempfile
from types import SimpleNamespace as N

TMP = tempfile.mkdtemp()
os.environ["RACETIMER_DATA"] = TMP
ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, ROOT)
from fastapi import HTTPException  # noqa: E402
from racetimer import app, db  # noqa: E402

HELPER = os.path.join(ROOT, "deploy", "racetimer-system")


def test_first_code_on_new_install():
    db.conn()
    code = db.first_code()
    assert code and len(code) == 14 and code.count("-") == 2
    assert db.login("admin", "admin") is None and db.login("admin", code)  # ikke længere admin/admin
    assert db.default_password_in_use()
    assert stat.S_IMODE(os.stat(db.FIRST_CODE_FILE).st_mode) == 0o600
    uid = db.q1("SELECT id FROM users WHERE username='admin'")["id"]
    db.set_password(uid, "en-lang-ny-kode")
    assert db.first_code() is None and not os.path.exists(db.FIRST_CODE_FILE) and not db.default_password_in_use()
    assert db.q1("SELECT strong FROM users WHERE id=?", (uid,))["strong"] == 1


def _req(ip, body, headers=None):
    async def j():
        return body
    return N(client=N(host=ip), headers=headers or {}, json=j, url=N(scheme="http"))


def _login(ip, user, pw, headers=None):
    resp = N(set_cookie=lambda *a, **k: None)
    return asyncio.run(app.login(_req(ip, {"username": user, "password": pw}, headers), resp))


def test_remote_login_needs_long_password():
    db.create_user("kort", "kort-kode")  # 9 tegn
    assert _login("192.168.1.9", "kort", "kort-kode")["ok"]  # lokalt: ok
    try:
        _login("127.0.0.1", "kort", "kort-kode", {"cf-ray": "x", "cf-connecting-ip": "8.8.8.8"})
        raise AssertionError("kort kode skulle afvises via det offentlige link")
    except HTTPException as e:
        assert e.status_code == 403 and "for kort" in e.detail


def test_public_link_requires_strong_passwords_for_all():
    try:
        asyncio.run(app.remote_toggle(_req("192.168.1.9", {"on": True}), u={"id": 1}))
        raise AssertionError("skulle afvises, fordi brugeren 'kort' har en kort kode")
    except HTTPException as e:
        assert e.status_code == 400 and "kort" in e.detail
    try:
        asyncio.run(app.add_user(_req("192.168.1.9", {"username": "x", "password": "123456789"}), u={"id": 1}))
        raise AssertionError("9 tegn skulle afvises")
    except HTTPException as e:
        assert "10" in e.detail


def _helper(args, stdin="", **env):
    e = dict(os.environ, **{k: str(v) for k, v in env.items()})
    r = subprocess.run([sys.executable, "-I", HELPER, *args], input=stdin, capture_output=True, text=True, env=e)
    return json.loads(r.stdout)


def test_system_helper():
    d = tempfile.mkdtemp()
    mark, boot, sud, code = (os.path.join(d, x) for x in ("mark", "boot", "sudoers.d", "code"))
    os.makedirs(boot), os.makedirs(sud)
    fake_chpasswd = os.path.join(d, "chpasswd")
    with open(fake_chpasswd, "w") as f:
        f.write(f"#!/bin/sh\ncat > {d}/chpasswd.in\n")
    os.chmod(fake_chpasswd, 0o755)
    with open(os.path.join(sud, "010_pi-nopasswd"), "w") as f:
        f.write("racetimer ALL=(ALL) NOPASSWD: ALL\n")
    env = dict(RACETIMER_SYS_MARK=mark, RACETIMER_SYS_BOOT=boot, RACETIMER_SYS_SUDOERS=sud, RACETIMER_SYS_CODE=code,
               RACETIMER_SYS_USER="racetimer", RACETIMER_SYS_CHPASSWD=fake_chpasswd)
    # uden markør (koden er ikke standard): passwd afvises – appen kan ikke overtage Pi-brugeren
    r = _helper(["passwd"], json.dumps({"password": "en-lang-ny-kode"}), **env)
    assert not r["ok"] and "allerede skiftet" in r["error"]
    open(mark, "w").close()
    assert _helper(["status"], **env) == {"ok": True, "user": "racetimer", "default": True}
    assert not _helper(["passwd"], json.dumps({"password": "kort"}), **env)["ok"]
    assert _helper(["passwd"], json.dumps({"password": "en-lang-ny-kode"}), **env)["ok"]
    assert open(f"{d}/chpasswd.in").read() == "racetimer:en-lang-ny-kode\n"
    assert not os.path.exists(mark) and "NOPASSWD" not in open(os.path.join(sud, "010_pi-nopasswd")).read()
    assert not _helper(["passwd"], json.dumps({"password": "endnu-en-ny-kode"}), **env)["ok"]  # kun én gang
    # førstegangskoden på SD-kortet – og væk igen, når koden er skiftet
    with open(code, "w") as f:
        f.write("ABCD-EF23-GH45\n")
    assert _helper(["bootcode"], **env)["written"] and "ABCD-EF23-GH45" in open(os.path.join(boot, "racetimer-kode.txt")).read()
    os.remove(code)
    assert not _helper(["bootcode"], **env)["written"] and not os.path.exists(os.path.join(boot, "racetimer-kode.txt"))
    with open(code, "w") as f:
        f.write("ikke en kode; rm -rf /\n")  # kun koder i det rigtige format skrives
    assert not _helper(["bootcode"], **env)["written"]
    assert not _helper(["noget-andet"], **env)["ok"]
    # manuelt ur: kun et rimeligt tidspunkt, og kun som tal (ingen tekst til date-kommandoen)
    fake_date = os.path.join(d, "date")
    with open(fake_date, "w") as f:
        f.write(f"#!/bin/sh\necho \"$@\" > {d}/date.in\n")
    os.chmod(fake_date, 0o755)
    env["RACETIMER_SYS_DATE"] = fake_date
    assert _helper(["settime"], json.dumps({"epoch": 1793800000.7}), **env) == {"ok": True, "epoch": 1793800000}
    assert open(f"{d}/date.in").read().strip() == "-s @1793800000"
    for bad in (0, 4102444800, "1793800000; rm -rf /", True, None):
        assert not _helper(["settime"], json.dumps({"epoch": bad}), **env)["ok"]


def test_manual_clock_and_offline_mode():
    def req(body):
        async def j():
            return body
        return N(client=N(host="127.0.0.1"), headers={"host": "localhost:8000"}, cookies={}, json=j)
    calls = []
    real_sys, real_clock, real_host = app._system, app.clock_info, app.host_info
    app._system = lambda *a, stdin=None: calls.append((a, stdin)) or {"ok": True}
    net = {"ip": "192.168.1.5"}
    app.host_info = lambda: dict(net)
    app._clock_cache["t"] = 0
    os.environ["RACETIMER_CLOCK_SYNCED"] = "0"

    def refused(word):
        try:
            asyncio.run(app.ready_set_clock(req({"epoch": 1793800000}), u={}))
            raise AssertionError("skulle afvises")
        except HTTPException as e:
            assert word in e.detail, e.detail
    try:
        refused("offline-tilstand")  # kun i offline-tilstand
        asyncio.run(app.ready_offline(req({"on": True}), u={}))
        refused("netværk")  # med net stilles uret automatisk
        net["ip"] = None
        assert asyncio.run(app.ready_set_clock(req({"epoch": 1793800000}), u={}))["manual"]
        assert calls == [(("settime",), json.dumps({"epoch": 1793800000}))]
        r = app.ready_status(req({}), u={})
        clock = next(c for c in r["checks"] if c["id"] == "clock")
        assert clock["state"] == "ok" and "manuelt" in clock["text"]
        # ikke mens et løb kører – så ville tiderne springe
        db.ex("UPDATE races SET is_active=0")
        rid = db.ex("INSERT INTO races(name, type, config, status, is_active, created_at) VALUES ('Kører', 'timed', '{}', 'running', 1, 0)")
        refused("kører")
        db.ex("UPDATE races SET status='finished', is_active=0 WHERE id=?", (rid,))
        r = app.ready_status(req({}), u={})
        assert r["offline"] and next(c for c in r["checks"] if c["id"] == "offline")["state"] == "ok"
        # offline-tilstand fra → det manuelle ur gælder ikke længere
        assert asyncio.run(app.ready_offline(req({"on": False}), u={})) == {"offline": False}
        assert not app.clock_info()["manual"]
    finally:
        app._system, app.clock_info, app.host_info = real_sys, real_clock, real_host
        os.environ.pop("RACETIMER_CLOCK_SYNCED")
        app._clock_cache["t"] = 0



def test_kiosk_screen_only_from_pi_itself():
    def req(ip, headers=None, host="localhost:8000"):
        return N(client=N(host=ip), headers={"host": host, **(headers or {})}, cookies={})
    assert app.kiosk_screen(req("127.0.0.1"))
    assert app.kiosk_screen(req("::1", host="[::1]:8000"))
    assert not app.kiosk_screen(req("192.168.1.20"))  # en anden på netværket
    assert not app.kiosk_screen(req("127.0.0.1", {"cf-connecting-ip": "1.2.3.4"}))  # via Cloudflare-tunnelen
    assert not app.kiosk_screen(req("127.0.0.1", {"x-forwarded-for": "1.2.3.4"}))  # via en proxy
    assert not app.kiosk_screen(req("127.0.0.1", host="abc.trycloudflare.com"))
    # uden for Pi'ens skærm kræver klar-tjekket login
    try:
        app.admin_or_screen(req("192.168.1.20"))
        raise AssertionError("skulle kræve login")
    except HTTPException as e:
        assert e.status_code == 401
    assert app.admin_or_screen(req("127.0.0.1"))["id"] is None
    assert app.ready_page(req("192.168.1.20")).status_code == 307  # /klar viderestiller til /admin
    r = app.ready_status(req("127.0.0.1"), u={})
    assert r["overall"] in ("ok", "warn", "error") and {c["id"] for c in r["checks"]} >= {"net", "clock", "readers", "race"}


def test_admin_chip_switches_pi_screen_and_never_counts():
    def req(ip, host="localhost:8000"):
        return N(client=N(host=ip), headers={"host": host}, cookies={})
    chips = asyncio.run(app.admin_chips_add(_req("127.0.0.1", {"chip": "ab 12 cd", "label": "Peters"}), u={}))
    assert chips[0]["chip"] == "AB12CD" and chips[0]["label"] == "Peters"
    before = db.q1("SELECT COUNT(*) n FROM reads")["n"]
    t = 1_900_000_000
    assert app.handle_read("AB12CD", "primary", t) == {"admin": True}
    assert db.q1("SELECT COUNT(*) n FROM reads")["n"] == before  # gemmes ikke som læsning
    assert app.live(req("127.0.0.1"))["admin_scan"] == t
    assert "admin_scan" not in app.live(req("192.168.1.20"))  # kun Pi'ens egen skærm
    assert app.ready_status(req("192.168.1.20"), u={})["admin_scan"] is None
    app.handle_read("AB12CD", "primary", t + 1)  # læseren gentager, mens armbåndet holdes der
    assert app._admin_scan["at"] == t
    app.handle_read("AB12CD", "primary", t + 6)  # ny scanning
    assert app._admin_scan["at"] == t + 6
    assert app.admin_chips_delete("AB12CD", u={}) == []
    assert "admin" not in app.handle_read("AB12CD", "primary", t + 20)

def test_results_csv_neutralises_formulas():
    db.ex("UPDATE races SET is_active=0")
    rid = db.ex("INSERT INTO races(name, type, config, created_at) VALUES ('CSV', 'p2p', '{}', 0)")
    db.ex("INSERT INTO participants(race_id, bib, name, club) VALUES (?, 1, '=HYPERLINK(\"http://x\")', '+45 klub')", (rid,))
    out = app.results_csv(rid, u={}).body.decode()
    assert "'=HYPERLINK" in out and "'+45 klub" in out and "\n=" not in out.replace("\r", "")


def test_password_change_logs_out_other_sessions():
    uid = db.create_user("sess", "en-lang-kode-1")
    other = db.login("sess", "en-lang-kode-1")
    mine = db.login("sess", "en-lang-kode-1")

    async def j():
        return {"password": "en-ny-lang-kode-2"}
    asyncio.run(app.change_pw(uid, N(json=j, cookies={"rt_session": mine}), u={"id": uid}))
    assert db.session_user(mine) and not db.session_user(other)


def test_no_plain_http_or_ftp_over_internet():
    from racetimer import ftpupload, sync
    for h in ("localhost", "racetimer.local", "192.168.1.20", "10.0.0.5", "100.101.1.2", "mirror", "::1"):
        assert ftpupload.local_host(h), h
    for h in ("example.dk", "8.8.8.8", "resultater.rebildtrail.dk", ""):
        assert not ftpupload.local_host(h), h
    for url in ("http://example.dk/modtag.php", "ftp://ftp.example.dk/r"):
        try:
            app._dest_fields({"type": "ftp" if url.startswith("ftp") else "webhook", "url": url})
            raise AssertionError(url)
        except HTTPException as e:
            assert e.status_code == 400
    assert app._dest_fields({"type": "webhook", "url": "http://192.168.1.5/modtag.php"})["url"]
    try:
        sync._post("http://example.dk/modtag.php", {"event": "x"}, "nøgle-1234567890")
        raise AssertionError("http til internettet skulle afvises")
    except RuntimeError as e:
        assert "https://" in str(e)
    try:
        ftpupload.upload({"url": "ftp://ftp.example.dk/r", "username": "u", "key": "k"}, {})
        raise AssertionError("ftp til internettet skulle afvises")
    except RuntimeError as e:
        assert "ftps://" in str(e)


def test_private_data_purged_after_deadline():
    from racetimer import signup
    import time as _t
    now = _t.time()
    old = db.ex("INSERT INTO races(name, type, config, created_at, finished_at, signup) VALUES ('Gl', 'p2p', '{}', 0, ?, ?)",
                (now - 40 * 86400, json.dumps({"delete_days": 30})))
    ages = db.ex("INSERT INTO races(name, type, config, created_at, finished_at, signup) VALUES ('Alder', 'p2p', '{}', 0, ?, ?)",
                 (now - 40 * 86400, json.dumps({"delete_days": 30, "age_step": 5})))
    new = db.ex("INSERT INTO races(name, type, config, created_at, finished_at) VALUES ('Ny', 'p2p', '{}', 0, ?)", (now - 86400,))
    for r in (old, ages, new):
        db.ex("INSERT INTO participants(race_id, name, email, birth_year) VALUES (?, 'A', 'a@example.test', 1980)", (r,))
    signup.purge_private(now)
    get = lambda r: db.q1("SELECT name, email, birth_year FROM participants WHERE race_id=?", (r,))  # noqa: E731
    assert get(old) == {"name": "A", "email": None, "birth_year": None}
    assert get(ages) == {"name": "A", "email": None, "birth_year": 1980}  # aldersklasser bruger fødselsåret
    assert get(new) == {"name": "A", "email": "a@example.test", "birth_year": 1980}


def test_update_helper_never_follows_symlinks():
    import importlib.machinery
    import importlib.util
    d = tempfile.mkdtemp()
    victim = os.path.join(d, "victim")
    with open(victim, "w") as f:
        f.write("hemmelig")
    os.chmod(victim, 0o600)
    status = os.path.join(d, "update-status.json")
    os.symlink(victim, status)
    os.environ["RACETIMER_UPDATE_STATUS"] = status
    loader = importlib.machinery.SourceFileLoader("rt_update", os.path.join(ROOT, "deploy", "racetimer-update"))
    spec = importlib.util.spec_from_loader("rt_update", loader)
    m = importlib.util.module_from_spec(spec)
    loader.exec_module(m)
    os.symlink(victim, f"{status}.{os.getpid()}.tmp")
    m.log("test", state="running")
    del os.environ["RACETIMER_UPDATE_STATUS"]
    assert open(victim).read() == "hemmelig" and stat.S_IMODE(os.stat(victim).st_mode) == 0o600
    assert not os.path.islink(status) and m.read_status()["state"] == "running"


def test_wifi_enterprise_needs_certificate_domain():
    import importlib.machinery
    import importlib.util
    loader = importlib.machinery.SourceFileLoader("rt_wifi", os.path.join(ROOT, "deploy", "racetimer-wifi"))
    spec = importlib.util.spec_from_loader("rt_wifi", loader)
    m = importlib.util.module_from_spec(spec)
    loader.exec_module(m)
    assert m.eap_domain("", "navn@aau.dk") == "aau.dk"
    assert m.eap_domain("*.AAU.dk.", "") == "aau.dk"
    assert m.eap_domain("", "navn") is None and m.eap_domain("x;rm -rf", "a@b") is None
    # nmcli får certifikat og domæne med, når et eduroam-netværk gemmes
    log = os.path.join(tempfile.mkdtemp(), "nmcli.log")
    fake = log + ".sh"
    with open(fake, "w") as f:
        f.write(f'#!/bin/sh\necho "$@" >> {log}\n')
    os.chmod(fake, 0o755)
    m.NMCLI = fake
    m.apply({"networks": [{"ssid": "eduroam", "security": "eap", "identity": "navn@aau.dk", "password": "hemmelig-kode"}]})
    calls = open(log).read()
    assert "802-1x.ca-cert " + m.CA_BUNDLE in calls and "802-1x.domain-suffix-match aau.dk" in calls, calls
    try:
        m.apply({"networks": [{"ssid": "eduroam", "security": "eap", "identity": "navn", "password": "hemmelig-kode"}]})
        raise AssertionError("uden domæne skulle afvises")
    except ValueError as e:
        assert "domænet" in str(e)


def test_security_headers_and_open_wifi_warning():
    from fastapi import Response

    def get(path):
        async def call_next(_):
            return Response("x")
        return asyncio.run(app._no_stale_pages(N(url=N(path=path)), call_next))
    r = get("/admin")
    assert r.headers["x-content-type-options"] == "nosniff" and r.headers["x-frame-options"] == "DENY"
    assert "frame-ancestors 'none'" in r.headers["content-security-policy"]
    r = get("/")
    assert r.headers["x-content-type-options"] == "nosniff" and "x-frame-options" not in r.headers  # skærmen må indlejres
    fake = os.path.join(TMP, "nmcli-open")
    for sec, expect in (("", True), ("WPA2", False)):
        with open(fake, "w") as f:
            f.write(f'#!/bin/sh\necho "no:WPA2"\necho "yes:{sec}"\n')
        os.chmod(fake, 0o755)
        os.environ["RACETIMER_NMCLI"] = fake
        try:
            assert app.wifi_open() is expect, sec
        finally:
            del os.environ["RACETIMER_NMCLI"]


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
