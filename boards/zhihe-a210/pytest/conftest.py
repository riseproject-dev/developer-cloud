"""pytest fixtures and Labgrid setup for Zhihe A210 Yocto TFTP and AOSP fastboot tests."""

import json
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import sys
import pytest
from labgrid import Environment

BOARD_DIR = Path(__file__).resolve().parent.parent
if str(BOARD_DIR) not in sys.path:
    sys.path.insert(0, str(BOARD_DIR))

COORDINATOR_ADDR = os.environ.get("LG_COORDINATOR", "127.0.0.1:20408")


def pytest_addoption(parser):
    parser.addoption(
        "--pool",
        action="store",
        default="",
        help="Labgrid pool tag to dynamically reserve an available board from",
    )
    parser.addoption(
        "--place",
        action="store",
        default="",
        help="Optional explicit Labgrid place override (if empty, dynamically reserves from --pool)",
    )
    parser.addoption(
        "--tftp-dir",
        action="store",
        default=os.environ.get("TFTP_DIR", ""),
        help="Relative directory under /var/lib/tftpboot containing Image, a210-dev.dtb, and rootfs.cpio.gz",
    )
    parser.addoption(
        "--release-dir",
        action="store",
        default=os.environ.get("AOSP_RELEASE_DIR", ""),
        help="Directory containing unpacked AOSP release images and fastboot binary",
    )
    parser.addoption(
        "--skip-flash",
        action="store_true",
        default=False,
        help="Skip U-Boot fastboot flashing and run smoke tests against the currently booted Android system",
    )
    parser.addoption(
        "--no-wipe",
        action="store_true",
        default=False,
        help="Do not erase userdata during fastboot flashing",
    )
    parser.addoption(
        "--serial-log",
        action="store",
        default="yocto_serial_boot.log",
        help="Path to write the full captured UART boot and teardown transcript",
    )
    parser.addoption(
        "--expected-kernel-prefix",
        action="store",
        default="",
        help="Optional expected kernel release prefix (e.g. '7.2.12' or '6.12')",
    )
    parser.addoption(
        "--require-adb",
        action="store_true",
        default=False,
        help="Fail instead of skipping USB-C ADB tests when the exporter USB resource is detached",
    )


def _run_lg(
    args: list[str],
    token: str | None = None,
    timeout: int = 30,
    check: bool = True,
) -> str:
    env = os.environ.copy()
    env["LG_COORDINATOR"] = COORDINATOR_ADDR
    if token:
        env["LG_TOKEN"] = token
    res = subprocess.run(
        ["labgrid-client", "-x", COORDINATOR_ADDR, *args],
        env=env,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=check,
    )
    return res.stdout


def _reserve_from_pool(pool: str, timeout: int = 900) -> str:
    out = _run_lg(
        ["reserve", "--wait", "--shell", f"pool={pool}"],
        timeout=timeout,
    )
    match = re.search(r"LG_TOKEN=([A-Za-z0-9]+)", out)
    if not match:
        raise RuntimeError(f"Failed to parse LG_TOKEN from labgrid reservation output:\n{out}")
    return match.group(1)


def _resolve_place_endpoints(
    place_selector: str, token: str | None = None
) -> tuple[str, str, str]:
    info = _run_lg(["-p", place_selector, "show"], token=token)

    place_match = re.search(r"Place\s+'([^']+)':", info)
    allocated_place = place_match.group(1) if place_match else place_selector

    addr_match = re.search(r"'address':\s*'([^']+)'", info)
    if not addr_match:
        raise RuntimeError(
            f"Could not resolve NetworkService address from Labgrid place '{allocated_place}':\n{info}"
        )
    target_ip = addr_match.group(1)

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.connect((target_ip, 69))
        server_ip = sock.getsockname()[0]

    return allocated_place, target_ip, server_ip


def _attach_console_logger(console, log_fp):
    orig_read = console._read

    def _logged_read(*args, **kwargs):
        data = orig_read(*args, **kwargs)
        if data:
            text = data.decode("latin1", errors="replace")
            sys.stdout.write(text)
            sys.stdout.flush()
            log_fp.write(text)
            log_fp.flush()
        return data

    console._read = _logged_read


@pytest.fixture(scope="module")
def tftp(request):
    pool_name = request.config.getoption("--pool") or "a210-yocto"
    place_name = request.config.getoption("--place")
    tftp_dir = request.config.getoption("--tftp-dir").strip("/")
    serial_log_path = request.config.getoption("--serial-log")
    expected_kernel_prefix = request.config.getoption("--expected-kernel-prefix")

    assert tftp_dir, "Must specify --tftp-dir or TFTP_DIR"
    for artifact in ("Image", "a210-dev.dtb", "rootfs.cpio.gz"):
        full_path = Path("/var/lib/tftpboot") / tftp_dir / artifact
        assert full_path.is_file(), f"Missing staged TFTP artifact: {full_path}"

    if not expected_kernel_prefix:
        build_info_path = Path("/var/lib/tftpboot") / tftp_dir / "build-info.json"
        if build_info_path.is_file():
            try:
                build_info = json.loads(build_info_path.read_text(encoding="utf-8"))
                expected_kernel_prefix = build_info.get("kernel_version", "")
            except Exception:
                pass
    if expected_kernel_prefix and not os.environ.get("VERSION"):
        os.environ["VERSION"] = expected_kernel_prefix

    token = os.environ.get("LG_TOKEN")
    owned_reservation = False
    place_selector = place_name or "+"
    acquired = False
    strategy = None
    log_fp = None

    try:
        if not place_name and not token:
            print(f"Waiting for available board in Labgrid pool 'pool={pool_name}'...")
            token = _reserve_from_pool(pool_name)
            os.environ["LG_TOKEN"] = token
            owned_reservation = True
            place_selector = "+"

        allocated_place, target_ip, server_ip = _resolve_place_endpoints(
            place_selector, token=token
        )
        print(f"Allocated Labgrid place '{allocated_place}' (pool={pool_name})")
        Path("yocto_allocated_place.txt").write_text(allocated_place + "\n", encoding="utf-8")

        _run_lg(["-p", place_selector, "acquire"], token=token)
        acquired = True

        log_fp = open(serial_log_path, "w", encoding="utf-8", errors="replace")
        log_fp.write(f"# Allocated Labgrid Place: {allocated_place} (pool={pool_name})\n")
        log_fp.flush()

        env = Environment(str(BOARD_DIR / "client.yaml"))
        if place_name:
            env.config.data["targets"]["main"]["resources"]["RemotePlace"]["name"] = place_name
        target = env.get_target("main")

        console = target.get_driver("SerialDriver", activate=False)
        _attach_console_logger(console, log_fp)

        strategy = target.get_driver("ZhiheA210TftpBootStrategy", activate=False)
        strategy.target_ip = target_ip
        strategy.server_ip = server_ip
        strategy.tftp_dir = tftp_dir

        strategy.transition("tftp")
        yield target.get_driver("ShellDriver")
    finally:
        if strategy is not None:
            try:
                strategy.transition("emmc")
            except Exception as exc:
                print(f"\n[Warning] eMMC restore transition raised: {exc}")
            try:
                strategy.target.deactivate(strategy.console)
            except Exception:
                pass
        if log_fp is not None:
            log_fp.close()
        if acquired:
            _run_lg(["-p", place_selector, "release"], token=token, check=False)
        if owned_reservation and token:
            _run_lg(["cancel-reservation", token], token=token, check=False)


def _resolve_place_adb_serial(place_selector: str, token: str | None = None) -> str:
    info = _run_lg(["-p", place_selector, "show"], token=token, check=False)
    tag_match = re.search(r"adb_serial=([A-Za-z0-9._-]+)", info)
    return tag_match.group(1) if tag_match else ""


def _ensure_adb_authorized(shell_driver, force: bool = False) -> None:
    if not force:
        existing = shell_driver.run_check(
            "su 0 sh -c 'test -s /data/misc/adb/adb_keys && echo PRESENT || echo MISSING'",
            timeout=10.0,
        )
        if existing and existing[0].strip() == "PRESENT":
            return

    candidates = [
        Path(os.environ.get("ADB_PUBKEY_PATH", "")) if os.environ.get("ADB_PUBKEY_PATH") else None,
        Path("/var/lib/tftpboot/releases/adbkey.pub"),
        Path.home() / ".android" / "adbkey.pub",
    ]
    pubkey = ""
    for candidate in candidates:
        if candidate and candidate.is_file():
            pubkey = candidate.read_text(encoding="utf-8").strip()
            if pubkey:
                break
    if not pubkey:
        return

    shell_driver.run_check(
        f'su 0 sh -c \'pub="{pubkey}"; '
        "mkdir -p /data/misc/adb && "
        '(grep -qxF "$pub" /data/misc/adb/adb_keys 2>/dev/null || echo "$pub" >> /data/misc/adb/adb_keys) && '
        "chown system:shell /data/misc/adb/adb_keys && "
        "chmod 0640 /data/misc/adb/adb_keys && "
        "restorecon /data/misc/adb/adb_keys 2>/dev/null || true'",
        timeout=25.0,
    )


@pytest.fixture(scope="module")
def aosp(request):
    pool_name = request.config.getoption("--pool") or "a210-aosp"
    place_name = request.config.getoption("--place")
    release_dir = request.config.getoption("--release-dir")
    skip_flash = request.config.getoption("--skip-flash")
    no_wipe = request.config.getoption("--no-wipe")
    serial_log_path = request.config.getoption("--serial-log")
    expected_kernel_prefix = request.config.getoption("--expected-kernel-prefix")

    if not skip_flash:
        assert release_dir, "Must specify --release-dir or AOSP_RELEASE_DIR unless --skip-flash is set"
        rel_path = Path(release_dir)
        assert rel_path.is_dir(), f"Release directory does not exist: {rel_path}"

    if expected_kernel_prefix and not os.environ.get("VERSION"):
        os.environ["VERSION"] = expected_kernel_prefix

    token = os.environ.get("LG_TOKEN")
    owned_reservation = False
    place_selector = place_name or "+"
    acquired = False
    strategy = None
    log_fp = None

    try:
        if not place_name and not token:
            print(f"Waiting for available board in Labgrid pool 'pool={pool_name}'...")
            token = _reserve_from_pool(pool_name)
            os.environ["LG_TOKEN"] = token
            owned_reservation = True
            place_selector = "+"

        allocated_place, target_ip, _ = _resolve_place_endpoints(
            place_selector, token=token
        )
        adb_serial = _resolve_place_adb_serial(place_selector, token=token)
        print(f"Allocated Labgrid place '{allocated_place}' (pool={pool_name})")
        Path("aosp_allocated_place.txt").write_text(allocated_place + "\n", encoding="utf-8")

        _run_lg(["-p", place_selector, "acquire"], token=token)
        acquired = True

        log_fp = open(serial_log_path, "w", encoding="utf-8", errors="replace")
        log_fp.write(f"# Allocated Labgrid Place: {allocated_place} (pool={pool_name})\n")
        log_fp.flush()

        env = Environment(str(BOARD_DIR / "client-aosp.yaml"))
        if place_name:
            env.config.data["targets"]["main"]["resources"][0]["RemotePlace"]["name"] = place_name
        target = env.get_target("main")

        console = target.get_driver("SerialDriver", activate=False)
        _attach_console_logger(console, log_fp)

        fb_driver = target.get_driver("AndroidFastbootDriver", activate=False)
        fb_driver.fastboot.address = target_ip
        if release_dir:
            rel_bin_dir = str(Path(release_dir).resolve())
            cur_path = os.environ.get("PATH", "")
            if rel_bin_dir not in cur_path.split(os.pathsep):
                os.environ["PATH"] = f"{rel_bin_dir}{os.pathsep}{cur_path}"
            for helper_bin in ("fastboot", "adb", "mke2fs"):
                helper_path = Path(release_dir) / helper_bin
                if helper_path.is_file():
                    helper_path.chmod(helper_path.stat().st_mode | 0o111)
            bundled_fb = Path(release_dir) / "fastboot"
            if bundled_fb.is_file():
                fb_driver.tool = str(bundled_fb)
            else:
                fb_driver.tool = shutil.which("fastboot") or "fastboot"

        adb_driver = target.get_driver("ZhiheADBDriver", activate=False)
        if adb_serial:
            adb_driver.serial = adb_serial
        if release_dir:
            bundled_adb = Path(release_dir) / "adb"
            if bundled_adb.is_file():
                bundled_adb.chmod(bundled_adb.stat().st_mode | 0o111)
                adb_driver.tool = str(bundled_adb)

        strategy = target.get_driver("ZhiheA210AospFastbootStrategy", activate=False)
        strategy.target_ip = target_ip
        strategy.release_dir = release_dir
        strategy.wipe = not no_wipe
        strategy.skip_flash = skip_flash

        strategy.transition("shell")
        shell_driver = target.get_driver("ShellDriver")
        _ensure_adb_authorized(shell_driver, force=not skip_flash)
        yield shell_driver
    finally:
        if strategy is not None:
            try:
                strategy.target.deactivate(strategy.shell)
            except Exception:
                pass
            try:
                strategy.target.deactivate(strategy.console)
            except Exception:
                pass
        if log_fp is not None:
            log_fp.close()
        if acquired:
            _run_lg(["-p", place_selector, "release"], token=token, check=False)
        if owned_reservation and token:
            _run_lg(["cancel-reservation", token], token=token, check=False)


@pytest.fixture(scope="module")
def aosp_adb(aosp, request):
    require_adb = request.config.getoption("--require-adb")
    target = aosp.target
    adb_driver = target.get_driver("ZhiheADBDriver", activate=False)
    if not adb_driver.usb_available:
        msg = (
            "USB-C ADB resource 'RemoteAndroidUSBFastboot' is not enumerated on the "
            "Labgrid exporter (avail=False); verify the physical USB-C cable seating."
        )
        if require_adb:
            pytest.fail(msg)
        pytest.skip(msg)

    target.activate(adb_driver)
    try:
        yield adb_driver
    finally:
        try:
            target.deactivate(adb_driver)
        except Exception:
            pass
