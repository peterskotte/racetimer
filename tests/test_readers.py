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


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
