"""Helper functions for the Zhihe A210 Labgrid test suite and boot strategy."""

import re

default_bootargs = (
    "console=ttyS4,115200 earlycon rdinit=/sbin/init "
    "root=/dev/ram0 rw clk_ignore_unused panic=30"
)


def kernel_version_in(version: str | None, uname: str) -> bool:
    """True if the kernel recipe's version (as CI takes it from the deployed
    kernel's file name, e.g. "7.4-rc1") is the one ``uname`` reports. The
    kernel always has a sublevel, so an rc reports "7.4.0-rc1"."""
    if not version:
        return True
    return version in uname or re.sub(r"^(\d+\.\d+)(?=-|$)", r"\1.0", version) in uname


def uboot_set_server_ip(strategy, serverip: str, dhcp_timeout: int = 40) -> None:
    strategy.uboot.run_check("setenv autoload no")
    strategy.uboot.run_check("dhcp", timeout=dhcp_timeout)
    strategy.uboot.run_check(f"setenv serverip {serverip}")


def uboot_set_bootargs(strategy, bootargs: str = default_bootargs) -> None:
    strategy.uboot.run_check(f"setenv bootargs '{bootargs}'")


def uboot_tftpboot_file(
    strategy, loadaddr: str, tftp_dir: str, file_name: str, timeout: int = 60
) -> None:
    strategy.uboot.run_check(f"tftpboot {loadaddr} {tftp_dir}/{file_name}", timeout=timeout)
