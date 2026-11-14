"""pytest fixtures and Labgrid setup for Zhihe A210 TFTP boot tests."""

import json
import os
from pathlib import Path
import re
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
        default="a210-yocto",
        help="Labgrid pool tag to dynamically reserve an available board from (default: a210-yocto)",
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
        "--serial-log",
        action="store",
        default="yocto_serial_boot.log",
        help="Path to write the full captured UART boot and teardown transcript",
    )
    parser.addoption(
        "--expected-kernel-prefix",
        action="store",
        default="",
        help="Optional expected kernel release prefix (e.g. '7.2.12')",
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


@pytest.fixture(scope="module")
def tftp(request):
    pool_name = request.config.getoption("--pool")
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
        target = env.get_target("main")
        if place_name:
            target.resources[0].name = place_name

        console = target.get_driver("SerialDriver", activate=False)
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
