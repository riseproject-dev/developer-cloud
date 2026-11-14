"""Labgrid TFTP boot strategy for Zhihe A210."""

import enum
import subprocess
import threading
import time
import attr
from labgrid.driver import Driver, ShellDriver, UBootDriver
from labgrid.factory import target_factory
from labgrid.protocol import ConsoleProtocol
from labgrid.strategy import Strategy, StrategyError

import helpers


class TftpStatus(enum.Enum):
    unknown = 0
    uboot = 1
    tftp = 2
    emmc = 3


@target_factory.reg_driver
@attr.s(eq=False)
class ZhiheA210TftpBootStrategy(Strategy):
    """Volatile RAM TFTP boot strategy for Zhihe A210 with persistent eMMC restore."""

    bindings = {
        "console": ConsoleProtocol,
        "uboot": UBootDriver,
        "shell": ShellDriver,
    }

    status = attr.ib(default=TftpStatus.unknown)
    target_ip = attr.ib(default="", validator=attr.validators.instance_of(str))
    server_ip = attr.ib(default="", validator=attr.validators.instance_of(str))
    tftp_dir = attr.ib(default="", validator=attr.validators.instance_of(str))
    bootargs = attr.ib(
        default=helpers.default_bootargs, validator=attr.validators.instance_of(str)
    )

    def _trigger_soft_reboot(self) -> None:
        try:
            self.console.sendline("sync; reboot -f")
        except Exception:
            pass

        def _reboot() -> None:
            time.sleep(0.5)
            if self.target_ip:
                subprocess.run(
                    [
                        "ssh",
                        "-o",
                        "StrictHostKeyChecking=no",
                        "-o",
                        "UserKnownHostsFile=/dev/null",
                        "-o",
                        "ConnectTimeout=5",
                        f"root@{self.target_ip}",
                        "sync; reboot",
                    ],
                    timeout=12,
                    capture_output=True,
                    check=False,
                )

        threading.Thread(target=_reboot, daemon=True).start()

    def _tftp_stage_files(self) -> None:
        helpers.uboot_set_server_ip(self, self.server_ip)
        helpers.uboot_set_bootargs(self, self.bootargs)
        helpers.uboot_tftpboot_file(self, "0x84000000", self.tftp_dir, "Image", timeout=60)
        helpers.uboot_tftpboot_file(
            self, "0x8c000000", self.tftp_dir, "a210-dev.dtb", timeout=30
        )
        # Staged last so U-Boot's ${filesize} reflects the initramfs size for booti.
        helpers.uboot_tftpboot_file(
            self, "0x8d000000", self.tftp_dir, "rootfs.cpio.gz", timeout=60
        )

    @Driver.check_bound
    def transition(self, status) -> None:
        if not isinstance(status, TftpStatus):
            status = TftpStatus[status]
        if status == TftpStatus.unknown:
            raise StrategyError(f"cannot transition to {status}")
        if status == self.status:
            return

        if status == TftpStatus.uboot:
            self.target.deactivate(self.shell)
            self.target.deactivate(self.uboot)
            self.target.activate(self.console)
            self._trigger_soft_reboot()
            self.target.activate(self.uboot)
        elif status == TftpStatus.tftp:
            self.transition(TftpStatus.uboot)
            self._tftp_stage_files()
            self.uboot.boot("tftp")
            self.uboot.await_boot()
            self.target.deactivate(self.uboot)
            self.target.activate(self.shell)
        elif status == TftpStatus.emmc:
            self.target.deactivate(self.shell)
            self.target.deactivate(self.uboot)
            self.target.activate(self.console)
            self.console.sendline("sync; reboot -f")
            time.sleep(0.2)
            self.console.sendline("reset")
            self.console.expect(r"a210-[^\r\n]*login:", timeout=90)
        else:
            raise StrategyError(f"no transition found from {self.status} to {status}")

        self.status = status
