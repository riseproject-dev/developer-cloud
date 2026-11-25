"""Labgrid AOSP UDP fastboot flashing and boot strategy for Zhihe A210."""

import enum
from pathlib import Path
import time
import attr
from labgrid.driver import AndroidFastbootDriver, Driver, ShellDriver, UBootDriver
from labgrid.factory import target_factory
from labgrid.protocol import ConsoleProtocol
from labgrid.strategy import Strategy, StrategyError


class AospStatus(enum.Enum):
    unknown = 0
    uboot = 1
    fastboot = 2
    flashed = 3
    shell = 4


@target_factory.reg_driver
@attr.s(eq=False)
class ZhiheA210AospFastbootStrategy(Strategy):
    """Flashes AOSP eMMC partitions via U-Boot UDP fastboot and boots to Android shell."""

    bindings = {
        "console": ConsoleProtocol,
        "uboot": UBootDriver,
        "fastboot": AndroidFastbootDriver,
        "shell": ShellDriver,
    }

    status = attr.ib(default=AospStatus.unknown)
    target_ip = attr.ib(default="", validator=attr.validators.instance_of(str))
    release_dir = attr.ib(default="", validator=attr.validators.instance_of(str))
    wipe = attr.ib(default=True, validator=attr.validators.instance_of(bool))
    skip_flash = attr.ib(default=False, validator=attr.validators.instance_of(bool))

    def _trigger_reboot_to_uboot(self) -> None:
        self.console.sendline("")
        time.sleep(0.2)
        self.console.sendline("su 0 sh -c 'sync; reboot'")
        time.sleep(2.5)

    def _flash_release_images(self) -> None:
        if not self.release_dir:
            raise StrategyError("release_dir must be set before flashing AOSP images")
        rel_path = Path(self.release_dir)

        product = self.fastboot.getvar("product").strip()
        if not product.startswith("a2"):
            raise StrategyError(
                f"Expected U-Boot fastboot product starting with 'a2', got '{product}'"
            )

        for partition, image_name in self.fastboot.flash_images.items():
            img_file = rel_path / image_name
            if not img_file.is_file() or img_file.stat().st_size == 0:
                raise StrategyError(f"Missing or empty image for {partition}: {img_file}")
            self.fastboot.flash(partition, str(img_file))

        if self.wipe:
            self.fastboot.erase("userdata")
        self.fastboot.erase("misc")

    @Driver.check_bound
    def transition(self, status) -> None:
        if not isinstance(status, AospStatus):
            status = AospStatus[status]
        if status == AospStatus.unknown:
            raise StrategyError(f"cannot transition to {status}")
        if status == self.status:
            return

        if status == AospStatus.uboot:
            self.target.deactivate(self.shell)
            self.target.deactivate(self.fastboot)
            self.target.deactivate(self.uboot)
            self.target.activate(self.console)
            self._trigger_reboot_to_uboot()
            # UBootDriver catches autoboot and runs init_commands (`setenv autoload no`, `dhcp`).
            self.target.activate(self.uboot)

        elif status == AospStatus.fastboot:
            self.transition(AospStatus.uboot)
            self.uboot.boot("fastboot_udp")
            _, _, match, _ = self.console.expect(
                r"Listening for fastboot command on (\d+\.\d+\.\d+\.\d+)",
                timeout=20,
            )
            bound_ip = match.group(1).decode("ascii")
            self.fastboot.fastboot.address = bound_ip or self.target_ip
            self.target.deactivate(self.uboot)
            self.target.activate(self.fastboot)

        elif status == AospStatus.flashed:
            self.transition(AospStatus.fastboot)
            self._flash_release_images()
            self.fastboot.continue_boot()
            self.target.deactivate(self.fastboot)
            try:
                self.console.expect(r"u-boot#", timeout=10)
            except Exception:
                self.console.sendline("")
                self.console.expect(r"u-boot#", timeout=10)
            self.console.sendline("run bootcmd")
            self.console.expect(r"Linux version \d", timeout=90)

        elif status == AospStatus.shell:
            if self.skip_flash:
                self.target.deactivate(self.fastboot)
                self.target.deactivate(self.uboot)
                self.target.activate(self.console)
                self.target.activate(self.shell)
            else:
                self.transition(AospStatus.flashed)
                self.target.activate(self.shell)

        else:
            raise StrategyError(f"no transition found from {self.status} to {status}")

        self.status = status
