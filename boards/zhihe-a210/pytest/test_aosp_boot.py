"""Hardware-in-the-loop AOSP boot and smoke tests for Zhihe A210."""

import os
import time
import helpers


def test_boot_completed(aosp):
    deadline = time.monotonic() + 150.0
    last_val = ""
    while time.monotonic() < deadline:
        out = aosp.run_check("getprop sys.boot_completed", timeout=15.0)
        last_val = out[0].strip() if out else ""
        if last_val == "1":
            break
        time.sleep(3.0)
    assert last_val == "1", f"Android sys.boot_completed did not reach 1 (last='{last_val}')"


def test_android_release_and_device(aosp):
    rel = aosp.run_check("getprop ro.build.version.release", timeout=15.0)[0].strip()
    device = aosp.run_check("getprop ro.product.device", timeout=15.0)[0].strip()
    fingerprint = aosp.run_check("getprop ro.build.fingerprint", timeout=15.0)[0].strip()
    display_id = aosp.run_check("getprop ro.build.display.id", timeout=15.0)[0].strip()
    print(f"Android {rel} | device={device} | display={display_id} | fingerprint={fingerprint}")
    assert rel == "17", f"Expected Android release 17, got '{rel}'"
    assert "a210" in device.lower() or "a210" in fingerprint.lower(), (
        f"Unexpected device='{device}' fingerprint='{fingerprint}'"
    )


def test_kernel_and_smp_cores(aosp):
    version = os.environ.get("VERSION")
    uname = aosp.run_check("uname -a", timeout=15.0)[0].strip()
    cores = aosp.run_check("nproc", timeout=15.0)[0].strip()
    assert helpers.kernel_version_in(version, uname), uname
    assert cores == "8", f"Expected 8 active RISC-V harts, got '{cores}'"


def test_userdata_and_metadata_mounted(aosp):
    mounts = aosp.run_check("grep -E ' /(data|metadata) ' /proc/mounts", timeout=15.0)
    joined = "\n".join(mounts)
    assert " /data " in joined and " /metadata " in joined, joined
