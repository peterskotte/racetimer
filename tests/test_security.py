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

if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
