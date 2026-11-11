import asyncio
import fcntl
import logging
import os
import select
import shutil
import stat
import subprocess
import termios
import time
from typing import Any, Dict, List, Optional, Tuple

from app.config import ADB_BIN, BOARD_DEFINITIONS, SERIAL_BAUD, SSH_KEY_PATH
from app.db import get_place_and_online_state, upsert_telemetry

logger = logging.getLogger("hub.telemetry")

_SERIAL_LOCKS: Dict[str, asyncio.Lock] = {}


def _get_serial_lock(serial_port: str) -> asyncio.Lock:
    lock = _SERIAL_LOCKS.get(serial_port)
    if lock is None:
        lock = asyncio.Lock()
        _SERIAL_LOCKS[serial_port] = lock
    return lock


def _resolve_adb_bin() -> Optional[str]:
    if ADB_BIN and os.path.isfile(ADB_BIN) and os.access(ADB_BIN, os.X_OK):
        return ADB_BIN
    return shutil.which("adb")


async def check_port_open(ip: str, port: int = 22, timeout: float = 1.5) -> bool:
    try:
        _, writer = await asyncio.wait_for(asyncio.open_connection(ip, port), timeout=timeout)
        writer.close()
        await writer.wait_closed()
        return True
    except Exception:
        return False


def _parse_gb(s: str) -> float:
    s = s.upper()
    if "G" in s:
        return float(s.replace("G", ""))
    if "M" in s:
        return float(s.replace("M", "")) / 1024.0
    return 0.0


def _parse_marked_probe_output(raw_text: str, probe_method: str) -> Optional[Dict[str, Any]]:
    """
    Parses output produced between `__HBS__` and `__HBE__` markers from either
    an ADB shell or a serial console shell (Android toybox/mksh or Linux sh).
    """
    start_idx = -1
    for marker in ("\n__HBS__\r\n", "\n__HBS__\n", "\r__HBS__\r\n", "__HBS__\r\n", "__HBS__\n"):
        pos = raw_text.rfind(marker)
        if pos != -1:
            start_idx = pos + len(marker)
            break
    if start_idx == -1:
        return None

    end_idx = raw_text.find("__HBE__", start_idx)
    if end_idx == -1:
        return None

    body = raw_text[start_idx:end_idx]
    parts = body.split("__OS__")
    sys_lines = [ln.strip() for ln in parts[0].splitlines() if ln.strip()]
    os_lines = [ln.strip() for ln in parts[1].splitlines()] if len(parts) > 1 else []

    uptime_seconds = 0
    load_avg = [0.0, 0.0, 0.0]
    raw_kernel = ""
    mem_total_kb = 0
    mem_avail_kb = 0
    disk_total_gb = 0.0
    disk_used_gb = 0.0

    # Expected sys_lines order:
    # 0: /proc/uptime  ("<up> <idle>")
    # 1: /proc/loadavg ("<1m> <5m> <15m> ...")
    # 2: uname -r
    # 3+: MemTotal / MemAvailable + statfs "<bsize> <blocks> <bavail>"
    if len(sys_lines) >= 1:
        try:
            uptime_seconds = int(float(sys_lines[0].split()[0]))
        except Exception:
            pass
    if len(sys_lines) >= 2:
        try:
            lp = sys_lines[1].split()
            load_avg = [float(lp[0]), float(lp[1]), float(lp[2])]
        except Exception:
            pass
    if len(sys_lines) >= 3:
        raw_kernel = sys_lines[2]

    for ln in sys_lines[3:]:
        if ln.startswith("MemTotal:"):
            try:
                mem_total_kb = int(ln.split()[1])
            except Exception:
                pass
        elif ln.startswith("MemAvailable:"):
            try:
                mem_avail_kb = int(ln.split()[1])
            except Exception:
                pass
        else:
            toks = ln.split()
            if len(toks) == 3 and all(t.isdigit() for t in toks):
                bsize, blocks, bavail = int(toks[0]), int(toks[1]), int(toks[2])
                if bsize > 0 and blocks > 0:
                    disk_total_gb = round((bsize * blocks) / (1024.0 ** 3), 1)
                    disk_used_gb = round((bsize * max(blocks - bavail, 0)) / (1024.0 ** 3), 1)

    ram_total_mb = mem_total_kb // 1024 if mem_total_kb > 0 else 0
    ram_used_mb = max(mem_total_kb - mem_avail_kb, 0) // 1024 if mem_total_kb > 0 else 0

    # Clean trailing/leading empty lines in os_lines while preserving positional fields
    while os_lines and os_lines[0] == "":
        os_lines.pop(0)

    android_version = os_lines[0] if len(os_lines) > 0 else ""
    build_display = os_lines[1] if len(os_lines) > 1 else ""
    product_model = os_lines[2] if len(os_lines) > 2 else ""
    boot_completed = os_lines[3] if len(os_lines) > 3 else ""
    adbd_status = os_lines[4] if len(os_lines) > 4 else ""

    if android_version:
        os_info: Dict[str, Any] = {
            "os_type": "android",
            "android_version": android_version,
            "build_display": build_display,
            "model": product_model,
            "boot_completed": boot_completed == "1",
            "adbd_status": adbd_status or "unknown",
            "probe_method": probe_method,
        }
        kernel_label = f"Android {android_version} ({raw_kernel})" if raw_kernel else f"Android {android_version}"
    else:
        os_info = {
            "os_type": "linux",
            "probe_method": probe_method,
        }
        kernel_label = raw_kernel

    return {
        "is_online": True,
        "uptime_seconds": uptime_seconds,
        "load_avg": load_avg,
        "ram_used_mb": ram_used_mb,
        "ram_total_mb": ram_total_mb,
        "disk_used_gb": disk_used_gb,
        "disk_total_gb": disk_total_gb,
        "kernel": kernel_label,
        "os_info": os_info,
    }


_PROBE_SHELL_SNIPPET = (
    "echo __HBS__;"
    "cat /proc/uptime /proc/loadavg;"
    "uname -r;"
    "grep -E \"^Mem(Total|Available):\" /proc/meminfo;"
    "stat -f -c \"%S %b %a\" /storage/emulated/0 2>/dev/null||stat -f -c \"%S %b %a\" /;"
    "echo __OS__;"
    "getprop ro.build.version.release 2>/dev/null;"
    "getprop ro.build.display.id 2>/dev/null;"
    "getprop ro.product.model 2>/dev/null;"
    "getprop sys.boot_completed 2>/dev/null;"
    "getprop init.svc.adbd 2>/dev/null;"
    "echo __HBE__"
)


async def _poll_via_ssh(board_name: str, ip: str, is_k8s_worker: bool) -> Optional[Dict[str, Any]]:
    if not await check_port_open(ip, 22, timeout=1.5):
        return None

    remote_cmd = (
        "cat /proc/uptime; echo '---'; "
        "cat /proc/loadavg; echo '---'; "
        "uname -r; echo '---'; "
        "free -m; echo '---'; "
        "df -h /; echo '---'; "
    )
    if is_k8s_worker:
        remote_cmd += (
            f"kubectl --kubeconfig /etc/kubernetes/kubelet.conf get node {board_name} "
            "-o jsonpath='Ready:{.status.conditions[?(@.type==\"Ready\")].status}' 2>/dev/null || echo 'Unknown'; echo '---'; "
            "ip -brief addr show dev flannel.1 2>/dev/null || echo 'None'; echo '---'"
        )

    ssh_args = [
        "ssh", "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=3",
        "-o", "UserKnownHostsFile=/dev/null", "-o", "LogLevel=ERROR",
    ]
    if SSH_KEY_PATH and os.path.exists(SSH_KEY_PATH):
        ssh_args.extend(["-i", SSH_KEY_PATH])
    ssh_args.extend([f"root@{ip}", remote_cmd])

    proc = await asyncio.create_subprocess_exec(
        *ssh_args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=4.0)
    if proc.returncode != 0 and not stdout:
        return None

    output = stdout.decode("utf-8", errors="replace")
    sections = output.split("---")

    uptime_seconds = 0
    if len(sections) > 0 and sections[0].strip():
        try:
            uptime_seconds = int(float(sections[0].strip().split()[0]))
        except Exception:
            pass

    load_avg = [0.0, 0.0, 0.0]
    if len(sections) > 1 and sections[1].strip():
        try:
            parts = sections[1].strip().split()
            load_avg = [float(parts[0]), float(parts[1]), float(parts[2])]
        except Exception:
            pass

    kernel = sections[2].strip() if len(sections) > 2 else ""

    ram_total = 0
    ram_used = 0
    if len(sections) > 3 and sections[3].strip():
        for line in sections[3].splitlines():
            if line.startswith("Mem:"):
                vals = line.split()
                if len(vals) >= 3:
                    ram_total = int(vals[1])
                    ram_used = int(vals[2])

    disk_total = 0.0
    disk_used = 0.0
    if len(sections) > 4 and sections[4].strip():
        lines = [ln for ln in sections[4].splitlines() if ln.strip()]
        if len(lines) >= 2:
            parts = lines[1].split()
            if len(parts) >= 3:
                disk_total = _parse_gb(parts[1])
                disk_used = _parse_gb(parts[2])

    k8s_status: Dict[str, Any] = {"worker": is_k8s_worker}
    if is_k8s_worker:
        k8s_node_cond = sections[5].strip() if len(sections) > 5 else "Unknown"
        flannel_info = sections[6].strip() if len(sections) > 6 else ""
        k8s_ready = "Ready:True" in k8s_node_cond
        overlay_up = "flannel.1" in flannel_info
        k8s_status.update({
            "ready": k8s_ready,
            "node_condition": k8s_node_cond,
            "overlay_active": overlay_up,
            "overlay_dev": "flannel.1",
            "flannel_ip": flannel_info.split()[2] if len(flannel_info.split()) >= 3 else "",
        })

    return {
        "is_online": True,
        "uptime_seconds": uptime_seconds,
        "load_avg": load_avg,
        "ram_used_mb": ram_used,
        "ram_total_mb": ram_total,
        "disk_used_gb": disk_used,
        "disk_total_gb": disk_total,
        "kernel": kernel,
        "k8s_status": k8s_status,
        "os_info": {"os_type": "linux", "probe_method": "ssh"},
    }


async def _poll_via_adb(ip: str, adb_serial: Optional[str]) -> Optional[Dict[str, Any]]:
    adb_bin = _resolve_adb_bin()
    if not adb_bin:
        return None

    target: Optional[str] = None
    probe_method = "adb"

    if adb_serial:
        proc = await asyncio.create_subprocess_exec(
            adb_bin, "devices",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=3.0)
        for ln in stdout.decode("utf-8", errors="replace").splitlines():
            toks = ln.split()
            if len(toks) >= 2 and toks[0] == adb_serial and toks[1] == "device":
                target = adb_serial
                probe_method = "adb-usb"
                break

    if not target and ip and await check_port_open(ip, 5555, timeout=1.0):
        target = f"{ip}:5555"
        probe_method = "adb-tcp"
        conn_proc = await asyncio.create_subprocess_exec(
            adb_bin, "connect", target,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await asyncio.wait_for(conn_proc.communicate(), timeout=3.0)

    if not target:
        return None

    proc = await asyncio.create_subprocess_exec(
        adb_bin, "-s", target, "shell", _PROBE_SHELL_SNIPPET,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=4.0)
    if proc.returncode != 0:
        return None

    return _parse_marked_probe_output(
        "\n" + stdout.decode("utf-8", errors="replace"),
        probe_method=probe_method,
    )


def _is_serial_port_in_use(serial_port: str) -> bool:
    """
    Returns True if any process currently holds `serial_port` open so Hub
    never interferes with active `tio`, `labgrid`, or CI console sessions.
    """
    fuser_bin = "/sbin/fuser" if os.path.exists("/sbin/fuser") else shutil.which("fuser")
    if not fuser_bin:
        return False

    # Try passwordless sudo fuser first to detect processes owned by any user
    # (e.g., labgrid, root, or another engineer), falling back to non-sudo fuser.
    for cmd in (["sudo", "-n", fuser_bin, serial_port], [fuser_bin, serial_port]):
        try:
            res = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=1.5,
                check=False,
            )
            if cmd[0] == "sudo" and res.returncode != 0 and b"sudo:" in res.stderr:
                continue
            # fuser exits 0 and prints PIDs when at least one process has the file open
            if res.returncode == 0 or res.stdout.strip():
                return True
            return False
        except Exception:
            continue
    return False


def _probe_serial_console_sync(serial_port: str) -> Tuple[str, Optional[Dict[str, Any]]]:
    """
    Non-intrusive two-stage serial console probe (runs inside asyncio.to_thread).
    Returns:
      - ("busy", None)    if another process holds the port open
      - ("offline", None) if the console does not respond or sits in U-Boot
      - ("online", dict)  if an Android or Linux shell/login prompt responds
    """
    try:
        st = os.stat(serial_port)
        if not stat.S_ISCHR(st.st_mode):
            return ("offline", None)
    except OSError:
        return ("offline", None)

    if _is_serial_port_in_use(serial_port):
        return ("busy", None)

    baud_const = getattr(termios, f"B{SERIAL_BAUD}", termios.B115200)
    fd = -1
    try:
        fd = os.open(serial_port, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return ("busy", None)

        # Configure raw 8N1 without HUPCL so closing fd never pulses DTR/reset lines
        attrs = termios.tcgetattr(fd)
        attrs[0] = 0
        attrs[1] = 0
        attrs[2] = termios.CS8 | termios.CREAD | termios.CLOCAL | baud_const
        attrs[3] = 0
        attrs[4] = baud_const
        attrs[5] = baud_const
        termios.tcsetattr(fd, termios.TCSANOW, attrs)
        termios.tcflush(fd, termios.TCIOFLUSH)

        # Stage 1: Send a single CR to sniff the active prompt without typing into U-Boot/login
        os.write(fd, b"\r")
        prompt_buf = b""
        t_prompt = time.monotonic() + 0.35
        while time.monotonic() < t_prompt:
            r, _, _ = select.select([fd], [], [], 0.05)
            if r:
                chunk = os.read(fd, 4096)
                if chunk:
                    prompt_buf += chunk

        if not prompt_buf:
            return ("offline", None)

        prompt_txt = prompt_buf.decode("utf-8", errors="replace")
        stripped = prompt_txt.strip()

        # Do not inject shell commands into U-Boot or SPL error prompts
        if stripped.endswith("=>") or "### ERROR ###" in prompt_txt:
            return ("offline", None)

        # Linux console waiting at `login:` without an active shell
        if "login:" in prompt_txt.lower() and ("$" not in stripped and "#" not in stripped):
            return (
                "online",
                {
                    "is_online": True,
                    "uptime_seconds": 0,
                    "load_avg": [0.0, 0.0, 0.0],
                    "ram_used_mb": 0,
                    "ram_total_mb": 0,
                    "disk_used_gb": 0.0,
                    "disk_total_gb": 0.0,
                    "kernel": "Linux (serial login)",
                    "os_info": {"os_type": "linux", "probe_method": "serial-login"},
                },
            )

        if "$" not in prompt_txt and "#" not in prompt_txt:
            return ("offline", None)

        # Stage 2: Active shell detected (e.g. Android `console:/ $` or Linux `#`).
        # Pace TX in 8-byte chunks (12ms) to prevent 16-byte 8250_dw UART RX FIFO overrun.
        cmd_bytes = ("\r" + _PROBE_SHELL_SNIPPET + "\r").encode("ascii")
        for i in range(0, len(cmd_bytes), 8):
            os.write(fd, cmd_bytes[i : i + 8])
            time.sleep(0.012)

        out_buf = b""
        deadline = time.monotonic() + 2.5
        while time.monotonic() < deadline:
            r, _, _ = select.select([fd], [], [], 0.05)
            if r:
                chunk = os.read(fd, 4096)
                if chunk:
                    out_buf += chunk
                    if b"\n__HBE__" in out_buf or b"\r__HBE__" in out_buf:
                        break

        parsed = _parse_marked_probe_output(
            out_buf.decode("utf-8", errors="replace"),
            probe_method="serial",
        )
        if parsed:
            return ("online", parsed)
        return ("offline", None)

    except Exception as e:
        logger.debug(f"Serial probe failed on {serial_port}: {e}")
        return ("offline", None)
    finally:
        if fd >= 0:
            try:
                fcntl.flock(fd, fcntl.LOCK_UN)
            except Exception:
                pass
            try:
                os.close(fd)
            except Exception:
                pass


async def poll_board_telemetry(board_name: str, defn: Dict[str, Any]):
    ip = defn["ip"]
    serial_port = defn.get("serial_port", "")
    adb_serial = defn.get("adb_serial")
    is_k8s_worker = defn.get("k8s_worker", False)

    try:
        # 1. Primary path: SSH over Ethernet (standard Debian / Yocto boards)
        ssh_res = await _poll_via_ssh(board_name, ip, is_k8s_worker)
        if ssh_res:
            upsert_telemetry(board_id=board_name, **ssh_res)
            return

        # 2. Secondary path: ADB over USB or TCP :5555 (Android boards with ADB transport)
        adb_res = await _poll_via_adb(ip, adb_serial)
        if adb_res:
            adb_res["k8s_status"] = {"worker": is_k8s_worker}
            upsert_telemetry(board_id=board_name, **adb_res)
            return

        # 3. Fallback path: Non-intrusive UART probe (Android / Linux boards without Ethernet SSH)
        if serial_port:
            place_status, prev_online = get_place_and_online_state(board_name)
            if place_status == "acquired":
                # Never touch the UART while a user or CI job holds the Labgrid place
                if prev_online:
                    logger.debug(f"Skipping serial probe for acquired board {board_name}; keeping cached online state.")
                    return

            async with _get_serial_lock(serial_port):
                state, serial_res = await asyncio.to_thread(_probe_serial_console_sync, serial_port)
                if state == "busy":
                    # Interactive user (e.g. `tio`) holds the console open; preserve prior online state
                    if prev_online:
                        logger.debug(f"Serial port {serial_port} is busy; keeping cached online state for {board_name}.")
                        return
                elif state == "online" and serial_res:
                    serial_res["k8s_status"] = {"worker": is_k8s_worker}
                    upsert_telemetry(board_id=board_name, **serial_res)
                    return

        # All paths unreachable -> mark offline
        upsert_telemetry(
            board_id=board_name,
            is_online=False,
            uptime_seconds=0,
            load_avg=[0.0, 0.0, 0.0],
            ram_used_mb=0,
            ram_total_mb=0,
            disk_used_gb=0.0,
            disk_total_gb=0.0,
            kernel="",
            k8s_status={"worker": is_k8s_worker, "status": "offline"},
            os_info={},
        )

    except Exception as e:
        logger.debug(f"Error collecting telemetry for {board_name} ({ip}): {e}")


async def run_telemetry_loop():
    """Polls all cluster boards concurrently."""
    tasks = []
    for name, defn in BOARD_DEFINITIONS.items():
        tasks.append(poll_board_telemetry(name, defn))
    await asyncio.gather(*tasks, return_exceptions=True)
