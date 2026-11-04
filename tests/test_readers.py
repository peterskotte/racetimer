"""Læserlisten med to ens læsere. Kør: python tests/test_readers.py  (bygger et falsk /dev og /sys)"""
import os
import sys
import tempfile

ROOT = tempfile.mkdtemp()
os.environ["RACETIMER_DEV_ROOT"] = ROOT
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from racetimer import readers  # noqa: E402


def dev(event, name, by_path=None, by_id=None):
    os.makedirs(f"{ROOT}/dev/input/by-path", exist_ok=True)
    os.makedirs(f"{ROOT}/dev/input/by-id", exist_ok=True)
    os.makedirs(f"{ROOT}/sys/class/input/{event}/device", exist_ok=True)
    open(f"{ROOT}/dev/input/{event}", "w").close()
    with open(f"{ROOT}/sys/class/input/{event}/device/name", "w") as f:
        f.write(name + "\n")
    if by_path:
        os.symlink(f"../{event}", f"{ROOT}/dev/input/by-path/{by_path}")
    if by_id:
        os.symlink(f"../{event}", f"{ROOT}/dev/input/by-id/{by_id}")


def test_two_identical_readers():
    # to ens læsere: Linux laver kun ét by-id-link (til den sidst tilsluttede)
    dev("event3", "Sycreader USB Reader", "platform-xhci-hcd.0-usb-0:1:1.0-event-kbd")
    dev("event4", "Sycreader USB Reader", "platform-xhci-hcd.1-usb-0:2:1.0-event-kbd", "usb-Sycreader_USB_Reader-event-kbd")
    # en anden model ved siden af beholder sin by-id-sti
    dev("event5", "Other Reader", "platform-xhci-hcd.0-usb-0:1.3:1.0-event-kbd", "usb-Other_Reader-event-kbd")
    devs = readers.list_devices()
    labels = [d["label"] for d in devs]
    assert labels.count("Sycreader USB Reader · USB-port 1") == 1 and labels.count("Sycreader USB Reader · USB-port 2") == 1, labels
    assert all("by-path" in d["path"] for d in devs if "Sycreader" in d["label"])
    assert any(d["path"].endswith("by-id/usb-Other_Reader-event-kbd") for d in devs)
    assert readers.ambiguous_paths() == [f"{ROOT}/dev/input/by-id/usb-Sycreader_USB_Reader-event-kbd"]



def test_same_port_listed_once_and_moved_readers_followed():
    import shutil
    shutil.rmtree(f"{ROOT}/dev", ignore_errors=True)
    shutil.rmtree(f"{ROOT}/sys", ignore_errors=True)
    # Pi 5: samme port har to navne (usb-0:2.2 og usbv2-0:2.2) – to ens læsere i en hub på port 2
    dev("event6", "IC Reader IC Reader", "platform-xhci-hcd.0-usb-0:2.2:1.0-event-kbd")
    os.symlink("../event6", f"{ROOT}/dev/input/by-path/platform-xhci-hcd.0-usbv2-0:2.2:1.0-event-kbd")
    dev("event7", "IC Reader IC Reader", "platform-xhci-hcd.0-usb-0:2.3:1.0-event-kbd", "usb-IC_Reader_IC_Reader_08FF-event-kbd")
    os.symlink("../event7", f"{ROOT}/dev/input/by-path/platform-xhci-hcd.0-usbv2-0:2.3:1.0-event-kbd")
    labels = [d["label"] for d in readers.list_devices()]
    assert labels == ["IC Reader IC Reader · USB-port 2.2", "IC Reader IC Reader · USB-port 2.3"], labels
    # gemt i port 1 og 2 (direkte i Pi'en) – nu flyttet til hubben: læser 1 → 2.2, læser 2 → 2.3
    saved = {"primary": f"{ROOT}/dev/input/by-path/platform-xhci-hcd.0-usbv2-0:1:1.0-event-kbd",
             "backup": f"{ROOT}/dev/input/by-path/platform-xhci-hcd.0-usbv2-0:2:1.0-event-kbd"}
    eff = readers.resolve(saved)  # ældre valg uden modelnavn: ens læsere bruges
    assert eff["primary"].endswith("usb-0:2.2:1.0-event-kbd") and eff["backup"].endswith("usb-0:2.3:1.0-event-kbd"), eff
    # med modelnavn: kun samme model – en anden læser overtager ikke pladsen
    assert readers.resolve(saved, {"primary": "Andet Mærke", "backup": "Andet Mærke"}) == saved
    # én læser sidder stadig i sin gemte port – den anden flyttes ikke ind i den
    keep = {"primary": f"{ROOT}/dev/input/by-path/platform-xhci-hcd.0-usb-0:2.3:1.0-event-kbd", "backup": saved["backup"]}
    eff = readers.resolve(keep, {"primary": "IC Reader IC Reader", "backup": "IC Reader IC Reader"})
    assert eff["primary"] == keep["primary"] and eff["backup"].endswith("usb-0:2.2:1.0-event-kbd"), eff
    assert readers._port(saved["primary"]) == "1" and readers._port(eff["backup"]) == "2.2"

if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
