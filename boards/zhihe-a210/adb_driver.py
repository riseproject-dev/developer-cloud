"""Labgrid USB-C ADB driver for Zhihe A210 AOSP boards."""

from pathlib import Path
import shutil
import subprocess
import attr
from labgrid.driver import Driver, ExecutionError
from labgrid.factory import target_factory
from labgrid.resource.remote import RemoteAndroidUSBFastboot
from labgrid.step import step


DEFAULT_RELEASE_ADB = Path("/var/lib/tftpboot/releases/rise-android-17-v1.0-a210-evb/adb")


@target_factory.reg_driver
@attr.s(eq=False)
class ZhiheADBDriver(Driver):
    """Executes bounded ADB commands against an exported USB-C Android device.

    Connects to the persistent host `adb-server.service` on 127.0.0.1:5037 and
    never invokes `adb kill-server` so concurrent USB ports on the exporter are
    not disrupted.
    """

    bindings = {
        "usb": {RemoteAndroidUSBFastboot, None},
    }

    tool = attr.ib(default="", validator=attr.validators.instance_of(str))
    serial = attr.ib(default="", validator=attr.validators.instance_of(str))
    wait_timeout = attr.ib(default=40.0, validator=attr.validators.instance_of(float))

    def __attrs_post_init__(self):
        super().__attrs_post_init__()
        if not self.tool:
            found = shutil.which("adb")
            if found:
                self.tool = found
            elif DEFAULT_RELEASE_ADB.is_file():
                self.tool = str(DEFAULT_RELEASE_ADB)
            else:
                self.tool = "adb"

    @property
    def usb_available(self) -> bool:
        return bool(self.usb is not None and self.usb.avail)

    def _selector_args(self) -> list[str]:
        if self.serial:
            return ["-s", self.serial]
        if self.usb is not None and getattr(self.usb, "path", None):
            return ["-s", f"usb:{self.usb.path}"]
        return []

    def _run_adb(self, args: list[str], timeout: float = 30.0, check: bool = True) -> subprocess.CompletedProcess[str]:
        cmd = [self.tool, *self._selector_args(), *args]
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise ExecutionError(f"ADB command timed out after {timeout}s: {' '.join(cmd)}") from exc

        if check and proc.returncode != 0:
            detail = (proc.stderr or proc.stdout).strip()
            raise ExecutionError(
                f"ADB command failed (rc={proc.returncode}): {' '.join(cmd)}: {detail}"
            )
        return proc

    def on_activate(self):
        self.wait_for_device(timeout=self.wait_timeout)

    @Driver.check_active
    @step(args=["timeout"])
    def get_state(self, timeout: float = 15.0) -> str:
        return self._run_adb(["get-state"], timeout=timeout).stdout.strip()

    @step(args=["timeout"])
    def wait_for_device(self, timeout: float = 40.0) -> None:
        self._run_adb(["wait-for-device"], timeout=timeout)

    @Driver.check_active
    @step(args=["cmd", "timeout"])
    def run_check(self, cmd: str, timeout: float = 30.0) -> list[str]:
        proc = self._run_adb(["shell", cmd], timeout=timeout)
        return [line.rstrip("\r") for line in proc.stdout.splitlines()]

    @Driver.check_active
    @step(args=["local_path", "remote_path", "timeout"])
    def push(self, local_path: str, remote_path: str, timeout: float = 60.0) -> str:
        return self._run_adb(["push", local_path, remote_path], timeout=timeout).stdout.strip()

    @Driver.check_active
    @step(args=["remote_path", "local_path", "timeout"])
    def pull(self, remote_path: str, local_path: str, timeout: float = 60.0) -> str:
        return self._run_adb(["pull", remote_path, local_path], timeout=timeout).stdout.strip()
