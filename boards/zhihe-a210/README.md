# Alibaba Zhihe A210 Board Specification & Bring-Up Notes

*Note: For the official onboarding state covering hardware intake, firmware mirrors, binary blob governance, and kernel upstreaming against the [Target Hardware Onboarding & Upstreaming Policy](../compliance-requirements.md), see the [Zhihe A210 Compliance Checklist](compliance-checklist.md).*

## 1. Hardware Overview

* **Processor Architecture:** [Octa-core RISC-V 64GCV (4xC920 @ 1.9GHz + 4xC908 @ 1.9GHz)](https://developer.zhcomputing.com/en/docs/A210/A210_Datasheet/) with ratified RISC-V Vector 1.0 (`RVV 1.0`). *(Does not meet the full RVA23 profile.)*
* **Memory & Storage:** Datasheet supports up to 16 GB LPDDR4/LPDDR4X. Deployed OSU-OSL units are provisioned with **8 GB LPDDR4X** and **64 GB eMMC** (plus an M.2 B-Key SATA `2242` slot for local storage expansion on container-runner nodes).
* **Onboarding Track:** **Embedded / SBC Track (Labgrid)**.
* **Current Stage:** **Stage 1 (Isolated Bring-up Bench)**, progressing toward Stage 2 Pilot Pool (with automated Yocto and Android 17 nightly hardware CI already running on bench units).

---

## 2. Public Source Code Mirrors & Ecosystem Repositories

For the Alibaba Zhihe A210, low-level firmware, bootloader, Linux kernel, and OS BSP sources are open-sourced and mirrored in RISE-owned and OSU-OSL repositories, but have yet to be upstreamed to their respective mainline repositories (early Linux kernel SCMI and pinctrl series are under review on `lore.kernel.org`):

### RISE Project GitHub Mirrors (`riseproject-dev`)
* **Linux Kernel (mainline rebase):** [https://github.com/riseproject-dev/linux/tree/alibaba-a210](https://github.com/riseproject-dev/linux/tree/alibaba-a210) (tag `v7.2.12-a210`)
* **U-Boot:** [https://github.com/riseproject-dev/u-boot/tree/v2024.10-a210](https://github.com/riseproject-dev/u-boot/tree/v2024.10-a210)
* **OpenSBI:** [https://github.com/riseproject-dev/opensbi/tree/v1.5-a210](https://github.com/riseproject-dev/opensbi/tree/v1.5-a210)
* **Android 17 BSP & Kernel Manifest:** [https://github.com/riseproject-dev/android_manifest/tree/android-17](https://github.com/riseproject-dev/android_manifest/tree/android-17)

### Upstream Yocto BSP
* **Yocto `meta-riscv` Machine Support:** [https://github.com/riscv/meta-riscv/blob/master/docs/zhihe-a210.md](https://github.com/riscv/meta-riscv/blob/master/docs/zhihe-a210.md) (`MACHINE = "zhihe-a210"`)

### OSU-OSL Mirrors & Shelf Bring-Up Docs
* **OpenSBI:** [https://git.osuosl.org/osuosl/zhihe-a210-opensbi](https://git.osuosl.org/osuosl/zhihe-a210-opensbi)
* **U-Boot:** [https://git.osuosl.org/osuosl/zhihe-a210-u-boot](https://git.osuosl.org/osuosl/zhihe-a210-u-boot)
* **Buildroot:** [https://git.osuosl.org/osuosl/zhihe-a210-buildroot](https://git.osuosl.org/osuosl/zhihe-a210-buildroot)
* **Linux Kernel & Onboarding Docs:** [https://git.osuosl.org/osuosl/a210-linux](https://git.osuosl.org/osuosl/a210-linux) ([`docs/`](https://git.osuosl.org/osuosl/a210-linux/-/tree/main/docs?ref_type=heads))

---

## 3. Labgrid & Hardware CI Assets (`boards/zhihe-a210/`)

This directory also houses the live Labgrid definitions and pytest suites backing automated Yocto and Android 17 hardware CI:
* `exporter.yaml`, `client.yaml`, `client-aosp.yaml`: Reference Labgrid exporter and client environment configs for `pool=a210-yocto` and `pool=a210-aosp`.
* `strategy.py`, `aosp_strategy.py`, `adb_driver.py`, `helpers.py`: Labgrid TFTP netboot and `fastboot udp` flashing strategies plus ADB/serial helpers.
* `pytest/`: Automated boot and connectivity verification tests (`test_yocto_netboot.py`, `test_aosp_boot.py`).
