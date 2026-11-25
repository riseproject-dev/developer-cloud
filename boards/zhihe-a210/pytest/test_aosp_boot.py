"""Hardware-in-the-loop AOSP boot and smoke tests for Zhihe A210."""

import os
import time
import helpers


def test_boot_completed(aosp):
    deadline = time.monotonic() + 180.0
    last_val = ""
    while time.monotonic() < deadline:
        try:
            out = aosp.run_check("getprop sys.boot_completed", timeout=20.0)
            last_val = out[0].strip() if out else ""
            if last_val == "1":
                break
        except Exception as exc:
            print(f"[poll retry] getprop sys.boot_completed transient UART error: {exc}")
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


def test_aon_pmic_watchdog_loaded(aosp):
    mods = aosp.run_check("grep -E '^zhihe_wdt ' /proc/modules || true", timeout=15.0)
    identities = aosp.run_check(
        "su 0 sh -c 'cat /sys/class/watchdog/watchdog*/identity 2>/dev/null' || true",
        timeout=15.0,
    )
    assert any("zhihe_wdt" in line for line in mods), f"zhihe_wdt module not loaded: {mods}"
    assert any("zhihe Watchdog" in line for line in identities), (
        f"zhihe Watchdog not registered in /sys/class/watchdog: {identities}"
    )


def test_usb_adb_connectivity(aosp_adb, tmp_path):
    assert aosp_adb.get_state() == "device"
    boot_prop = aosp_adb.run_check("getprop sys.boot_completed", timeout=15.0)[0].strip()
    arch = aosp_adb.run_check("uname -m", timeout=15.0)[0].strip()
    assert boot_prop == "1", f"Expected sys.boot_completed=1 over ADB, got '{boot_prop}'"
    assert arch == "riscv64", f"Expected riscv64 over ADB, got '{arch}'"

    payload = f"labgrid-adb-ok-{int(time.time())}\n"
    src = tmp_path / "adb_probe_in.txt"
    dst = tmp_path / "adb_probe_out.txt"
    remote = "/data/local/tmp/labgrid_adb_probe.txt"
    src.write_text(payload, encoding="utf-8")
    aosp_adb.push(str(src), remote)
    aosp_adb.pull(remote, str(dst))
    aosp_adb.run_check(f"rm -f {remote}", timeout=15.0)
    assert dst.read_text(encoding="utf-8") == payload
