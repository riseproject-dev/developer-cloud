"""Hardware-in-the-loop Yocto volatile RAM netboot smoke tests for Zhihe A210."""

import os
from labgrid.driver import ExecutionError
import helpers


def test_uname_a(tftp):
    version = os.environ.get("VERSION")
    try:
        state = tftp.run_check("/bin/uname -a", timeout=60.0)
        assert helpers.kernel_version_in(version, state[0]), state[0]
    except ExecutionError:
        tftp.run("ls /bin/uname")
        raise


def test_smp_cores(tftp):
    state = tftp.run_check("/usr/bin/nproc", timeout=30.0)
    assert state[0].strip() == "8", state


def test_opensbi_reserved_memory(tftp):
    state = tftp.run_check(
        "dmesg | grep 'nomap non-reusable opensbi@80000000'",
        timeout=30.0,
    )
    assert any("opensbi@80000000" in line for line in state), state
