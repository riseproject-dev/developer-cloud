# Alibaba Zhihe A210 Compliance Checklist

This checklist tracks compliance of the Alibaba Zhihe A210 against the [RISC-V Developer Cloud Target Hardware Onboarding & Upstreaming Policy](../compliance-requirements.md).

* **Hardware Onboarding Track:** **Embedded / SBC Track (Labgrid)** *(Server Track OpenBMC/Redfish/OpenStack Ironic items are marked N/A below.)*
* **Current Active Stage:** **Stage 1: Isolated Bring-up Bench** (progressing toward Stage 2 Pilot Pool)

---

## Stage 1: Isolated Bring-up Bench (Current Active Stage)

### Hardware & Physical Checklist
* [x] **Physical Hardware & Intake Clearance:** Supply 1-2 working prototype or engineering sample units to a RISC-V Developer Cloud hosting site, with contribution terms and hosting-site safety, electrical, and chassis certifications confirmed prior to shipment.
  * *100 units donated by Alibaba to OSU-OSL (20 early manual-power pilot units plus 80 factory-modified units with auto-power-on strap); site intake completed.*
* [x] **Hardware Documentation & Specs:** Provide board schematics (or equivalent documentation), SoC memory maps, strap configurations, and component datasheets.
  * *Docs and specs shared with the Developer Tooling WG. Official datasheet: [https://developer.zhcomputing.com/en/docs/A210/A210_Datasheet/](https://developer.zhcomputing.com/en/docs/A210/A210_Datasheet/).*
* [x] **Mechanical, Mounting & Thermal Specs:** Document mechanical clearance, dimensional constraints, and thermal/airflow expectations for racked continuous operation; supply 3D CAD models and cooling kits for custom shelves.
  * *Dimensions, airflow specs, and 3D CAD models incorporated into OSU-OSL's custom 10-board 3D-printed shelves; heatsinks prepped with thermal paste.*
* [x] **Power Envelope & Electrical Input:** Document peak and instantaneous power consumption under stress, along with AC/DC input voltage and connector specifications.
  * *Power envelope and 12V DC input specs shared with maintainers and validated for OSU-OSL shelf PSU and per-board fused relay sizing.*
* [x] **Physical Modifications (if any):** Document any mandatory physical pad soldering, resistor straps, or board modifications needed for remote power/reset circuits or I/O access.
  * *80 production units include the factory `R1113` auto-power-on resistor strap (no post-delivery board surgery required). The 20 early pilot units omit `R1113` and require manual or external relay power actuation.*
* [x] **Network & Console Interfaces:** Dedicated Gigabit Ethernet interface supporting DHCP and network boot, plus out-of-band 3-pin UART with documented pinout, voltage level, baud rate, and parity.
  * *Onboard Gigabit Ethernet (DHCP, U-Boot TFTP netboot, and `fastboot udp`) and UART header J4 (`/dev/ttyS4`, `115200 8N1`) confirmed.*
* [x] **Out-of-Band Power & Management:**
  * *Embedded / SBC Track:* *80 factory-modified units auto-power-on on 12V restoration (Shelf 1 uses Devantech `ETH008-B` Ethernet relays under Labgrid). Clean cold software reboot implemented via the `zhihe_wdt` AON PMIC watchdog driver.*
  * *Server Track (BMC/Redfish): N/A (Embedded / SBC Track).*
* *Memory & Storage Sizing Guidance (Recommended, non-gating):*
  * *Deployed OSU-OSL units carry 8 GB LPDDR4X and 64 GB eMMC (sufficient for Yocto/Android netboot and flash CI; M.2 B-Key SATA `2242` or USB storage expansion is used on nodes hosting persistent container CI runners).*

### Firmware & Bootloader Checklist
* [x] **Firmware & Bootloader Source:** Provide functional binaries, reproducible build instructions, and source repositories for GPL components (U-Boot, Linux kernel) and OpenSBI where available.
  * *OpenSBI and U-Boot source repositories are mirrored in both `riseproject-dev` ([`opensbi`](https://github.com/riseproject-dev/opensbi/tree/v1.5-a210), [`u-boot`](https://github.com/riseproject-dev/u-boot/tree/v2024.10-a210)) and OSU-OSL GitLab ([`zhihe-a210-opensbi`](https://git.osuosl.org/osuosl/zhihe-a210-opensbi), [`zhihe-a210-u-boot`](https://git.osuosl.org/osuosl/zhihe-a210-u-boot)).*
* [ ] **Remote Flashing & Recovery:**
  * *Embedded / SBC Track:* *U-Boot `fastboot udp` flashing and TFTP netboot are verified in automated CI. Zero-touch hardware MaskROM DFU (`Flash` + `Reset` actuation via BayLibre Copilot + Triple Relays Hat over USB-A, plus USB-C ADB) is planned for Shelf 2; sample hardware kit is on site and bench validation is pending Shelf 1 completion.*
  * *Server Track (BMC firmware update/recovery): N/A (Embedded / SBC Track).*
* [x] **MAC Address Persistence:** Document non-volatile storage mechanisms for preserving deterministic, unique MAC addresses across reflashes and cold power cycles.
  * *Vendor confirmed no factory-burned MAC and documented U-Boot `fnv save ethaddr eth1addr` targeting the dedicated `factory` non-volatile partition (`mmcblk0p1`, separate from `uboot_env`, preserved at `512KiB` in both OSU-OSL Debian and Android 64 GB GPT layouts). OSU-OSL documented and bench-confirmed the deterministic `48:da:00:00:BB:0P` scheme in [`osuosl/a210-linux/docs/MAC_SCHEME.md`](https://git.osuosl.org/osuosl/a210-linux/-/blob/main/docs/MAC_SCHEME.md); fleet-wide `fnv` verification across CI and racked shelves is tracked under Stage 2.*
* [x] **Early Boot Firmware Blobs:** Temporary prebuilt non-GPL early boot firmware blobs and proprietary hardware/co-processor firmware are permitted during Stage 1; GPL components always include source.
  * *`a210-aon.bin` (SHA256: `d24a9a6c8aab1f3d3049211b6509a503172c381778dcf1c9f23291e5082e999c`) is required for Always-On (AON) low-power processor initialization, and prebuilt vendor `bootzero2.bin` (SHA256: `fa640d8e5cbd69fbc1b5d3a2b5e78e5b4aa2cc158e83bd28d443cdddd6023f63`, packaged in [`riseproject-dev/android_bootloader_build`](https://github.com/riseproject-dev/android_bootloader_build/tree/alibaba-android-17)) runs ahead of U-Boot SPL. OpenSBI, U-Boot, and Linux kernel sources are publicly available.*

### Linux Kernel Checklist
* [x] **Kernel Enablement:** Out-of-tree vendor kernel forks permitted for early bring-up with repository access or patches plus upstream base provided to maintainers.
  * *Mainline-rebased kernel actively maintained at [`riseproject-dev/linux`](https://github.com/riseproject-dev/linux/tree/alibaba-a210) (tag `v7.2.12-a210`, synced with [`osuosl/a210-linux`](https://git.osuosl.org/osuosl/a210-linux)) and Android kernel at [`riseproject-dev/android_kernel_common`](https://github.com/riseproject-dev/android_kernel_common/tree/android-mainline-alibaba).*

### RISC-V Architecture Checklist
* [x] **ISA & Extensions:** Define and document supported RISC-V profile, ISA string, platform extensions, and known silicon errata requiring firmware or kernel workarounds.
  * *Datasheet confirms `RV64GCV` (`IMAFDC` + ratified `RVV 1.0`, non-RVA23). Documented bring-up errata and workarounds: (1) OpenSBI 2 MB `/reserved-memory` (`no-map` at `0x80000000`) is required in the DTB to avoid PMP store access faults; (2) warm SoC reset without AON PMIC cold-reset (`zhihe_wdt`) leaves eMMC rails live and causes U-Boot SPL `-110` timeout until a 12V cold power cycle; (3) `CONFIG_XUANTIE_SSTC` and `CONFIG_RISCV_SLOW_VECTOR_UNALIGNED_ACCESS` workarounds are documented for Android GKI; (4) factory March 2026 OpenSBI does not enable `Zicbom`/`Zicboz` unless updated from `riseproject-dev/opensbi`.*

---

## Stage 2: Pilot Pool (Target Phase)

### Hardware & Physical Checklist
* [ ] **Verification Compliance:** Pass all Stage 1 verification checks (automated power cycling, remote flashing/recovery, MAC persistence, and network boot).
  * *Yocto TFTP netboot nightly CI (`riscv/meta-riscv`) and Android 17 `fastboot udp` nightly CI are operational on bench nodes. Pending Shelf 1 automated `ETH008-B` relay power-cycling, fleet `fnv` MAC persistence verification, and Shelf 2 hardware DFU recovery verification.*
* [ ] **Form Factor & Fleet Allocation:**
  * *Embedded / SBC Track:* *100 units are available at OSU-OSL (exceeding the 10+ unit plus 10-15% spare replacement pool requirement). Shelf 1 (10 boards) assembly and 208V thermal soak are in progress.*
  * *Server Track Exception: N/A (Embedded / SBC Track).*

### Firmware & Bootloader Checklist
* [x] **Mandatory RISE Source Mirroring:** Open-source firmware, bootloader, and kernel sources publicly accessible under OSI-approved licenses and mirrored into `riseproject-dev`.
  * *Mirrored in [`riseproject-dev/linux`](https://github.com/riseproject-dev/linux/tree/alibaba-a210), [`riseproject-dev/u-boot`](https://github.com/riseproject-dev/u-boot/tree/v2024.10-a210), [`riseproject-dev/opensbi`](https://github.com/riseproject-dev/opensbi/tree/v1.5-a210), and [`riseproject-dev/android_manifest`](https://github.com/riseproject-dev/android_manifest/tree/android-17); Yocto BSP merged upstream in [`riscv/meta-riscv`](https://github.com/riscv/meta-riscv/blob/master/docs/zhihe-a210.md).*
* [ ] **Firmware Upstreaming Plan:** Documented upstreaming plan outlining timelines and mailing list or PR series for OpenSBI and U-Boot.
  * *Pending documented upstreaming roadmap and patch timelines for OpenSBI and U-Boot from the vendor.*
* [ ] **Boot Standards:**
  * *Embedded / SBC Track:* *Native UEFI (`CONFIG_EFI_LOADER=y` / EBBR) is currently unsupported by the vendor's U-Boot fork. Requires an explicit **Developer Tooling WG waiver** to enter Stage 2 under Labgrid (using U-Boot TFTP/HTTP netboot, Yocto, and Android workflows).*
  * *Server Track (RISC-V BRS-I): N/A (Embedded / SBC Track).*
* [ ] **Binary Blob Governance & Redistribution Rights:** SHA256 manifests, reserved memory maps, written legal redistribution licenses, and Binary Sunset Plan for any remaining non-GPL early boot blobs.
  * *OpenSBI and U-Boot are built from source, and `a210-aon.bin` (SHA256 `d24a9a6c8aab1f3d3049211b6509a503172c381778dcf1c9f23291e5082e999c`) is an exempt Always-On (AON) co-processor binary (no sunset plan required). Prebuilt `bootzero2.bin` (SHA256 `fa640d8e5cbd69fbc1b5d3a2b5e78e5b4aa2cc158e83bd28d443cdddd6023f63`, used by [`riseproject-dev/android_bootloader_build`](https://github.com/riseproject-dev/android_bootloader_build/tree/alibaba-android-17)) also remains a vendor binary. **Pending:** written legal redistribution license confirmation (without click-through EULAs/NDAs, confirming third-party IP sublicensing rights) for `a210-aon.bin`, `bootzero2.bin`, and any DDR/GPU firmware blobs, plus a Binary Sunset Plan (or written hardware-init exemption rationale) for `bootzero2.bin`.*

### Linux Kernel Checklist
* [ ] **Linux Upstreaming Plan:** Documented Linux Upstreaming Plan outlining active, in-progress, and planned `lore.kernel.org` patch series.
  * *RVCK `6.6` upstreaming is complete, and initial mainline LKML patch series were posted in Nov 2026 ([A210 SCMI v3](https://patch.msgid.link/20261103-a210-scmi-v3-0-ee6b31580808@iscas.ac.cn) and split A210 pinctrl series under review). Pending a complete documented upstreaming timeline for remaining SoC drivers and board Device Trees.*

### RISC-V Architecture Checklist
* [ ] **ISA Extension Validation:** Accurate Device Tree (`riscv,isa-extensions`) advertisement without false-positive `SIGILL` faults, verified via `riscv_hwprobe` and `/proc/cpuinfo`.
  * *Basic `RV64GCV` boot verified on Stage 2 Yocto (`v7.2.12-a210`) and Android kernels; formal `riscv_hwprobe` and Device Tree false-positive audit plus mainline `kselftest` validation pending.*

---

## Stage 3: Production Pool

### Platform & Control-Plane Readiness (Verified Jointly with Developer Cloud Maintainers)
* [ ] **Stage 2 Continuity & Stability Soak:** Maintains all Stage 2 gates (mirrors, fleet/spares, verified blob redistribution licenses, and confirmed WG UEFI waiver for Labgrid-managed Embedded pools) and passes sustained production thermal and load soak testing.
  * *Pending Stage 2 completion, formal WG UEFI waiver confirmation, and Shelf 1 208V sustained thermal and load soak testing.*
* [ ] **Embedded / SBC Track:** Automated power cycling, serial console, netboot/flashing, and remote DFU recovery (for flash-mutating workloads) pass reliability verification for production Labgrid multi-pool scheduling and telemetry.
  * *Bench Labgrid CI (`pool=a210-yocto`, `pool=a210-aosp`) and public telemetry dashboard are live; pending Shelf 1 relay power cutover, Shelf 2 Copilot DFU validation, and multi-shelf scaling.*
* **Server Track (OpenBMC/Redfish/OpenStack Ironic):** *N/A (Embedded / SBC Track).*

### Firmware & Bootloader Checklist
* [ ] **Upstream Submission Progress:** Upstream PRs or patch series merged, queued in maintainer `-next` branches, or actively advancing through review for OpenSBI and U-Boot.
  * *Pending upstream OpenSBI (`riscv-software-src/opensbi`) and U-Boot (`u-boot/u-boot`) submissions.*
* [ ] **Binary Sunset Plan Completion:** Prebuilt non-GPL early boot blobs replaced by source-built open-source firmware; exempt hardware subsystem blobs retain documented SHA256 manifests and legal redistribution clearance.
  * *OpenSBI and U-Boot are already built from source and `a210-aon.bin` is exempt from sunsetting; pending Stage 2 Binary Sunset Plan (or documented exemption) for `bootzero2.bin` and written legal redistribution clearance for all remaining binary blobs.*

### Linux Kernel Checklist
* [ ] **Linux Upstreaming Plan Completion:** Core SoC drivers and board Device Trees plus DT bindings merged, queued in `linux-next`, or actively advancing through review targeting `linux-riscv` and `torvalds/linux`.
  * *Early SCMI v3 and pinctrl series are under review on LKML; remaining SoC drivers, clock/reset controllers, and board Device Tree + DT bindings have not yet landed in `linux-riscv` / `torvalds/linux`.*

### RISC-V Architecture Checklist
* [ ] **Declared Architecture Compliance:** Full hardware compatibility with declared profile (`RV64GCV` / `RVV 1.0`) under production workloads, with known silicon errata and required firmware/kernel workarounds documented.
  * *Pending full `RV64GCV` (`RVV 1.0`) production workload validation on mainline kernel.*
