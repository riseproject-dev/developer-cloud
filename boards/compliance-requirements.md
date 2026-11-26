# RISC-V Developer Cloud: Target Hardware Onboarding & Upstreaming Policy

## 1. Overview

The RISE Project adheres to a collaborative, upstream-first open-source philosophy. Physical hardware integrated into the **RISC-V Developer Cloud** moves through a progressive, phased compliance framework anchored around **Lab Integration & Access Stages**.

This policy enables early access to engineering samples while establishing clear operational, legal, and upstreaming gates for hardware to progress into shared CI pools and production bare-metal pools. Compliance with these gates and binary blob sunset clauses is enforced by the **RISE Developer Tooling WG** and the **Developer Cloud Maintainers**, who independently evaluate and approve stage progression and track-specific waivers. Platforms that miss agreed sunset or upstreaming milestones without an approved WG extension remain at their current stage and may be paused or removed from shared CI pools.

*(Note: Physical facility, colocation, and operational custody boundaries between RISE and hosting partners are governed separately by the RISC-V Developer Cloud Hosting Provider Requirements. RISE retains exclusive operational control of firmware, operating systems, credentials, provisioning, and workloads across hosted systems.)*

---

## 2. Hardware Onboarding Tracks

Because RISC-V systems span both single-board computers and rackable servers, hardware onboarded to the RISC-V Developer Cloud follows one of two long-term control-plane tracks:

* **Embedded / SBC Track:** Development boards and single-board computers without an on-board BMC (e.g., U-Boot-based boards targeting Yocto, Android/AOSP, Linux kernel, and userspace CI). These systems use the external power, reset, and serial-console bridge exception from the Hosting Provider Requirements, are hosted at sites equipped for shelf/Labgrid deployments, and remain managed by **Labgrid** long-term (networked serial console, switched power relays, TFTP/PXE/HTTP netboot, and remote DFU recovery harnesses for flash-mutating workloads).
* **Server Track:** Rackable server-class systems equipped with an on-board BMC (preferably OpenBMC with Redfish) and UEFI firmware. These systems integrate with **OpenStack Nova / Ironic** (or equivalent bare-metal and VM cloud provisioning) rather than Labgrid once entering shared pools (following Stage 1 isolated BMC bring-up).

---

## 3. Phased Onboarding Framework (Lab Integration Stages)

Target platforms progress through three Lab Integration Stages. For each stage, this policy defines the onboarding readiness checklist and the corresponding RISC-V Developer Cloud services provided.

---

### Stage 1: Isolated Bring-up Bench

* **Target Scope:** Initial lab bring-up, prototype staging, and early hardware enablement.
* **Vendor Requirements Checklist:**
  * **Hardware & Physical Checklist:**
    * [ ] **Physical Hardware & Intake Clearance:** Supply 1-2 working prototype or engineering sample units to a RISC-V Developer Cloud hosting site, with contribution terms (donation vs. loan, spares/RMA, return/EOL) and hosting-site safety, electrical, and chassis certifications confirmed prior to shipment.
    * [ ] **Hardware Documentation & Specs:** Provide board schematics (or equivalent block diagrams and header/jumper/pinout documentation for rackable Server Track systems, under NDA if required), SoC memory maps, strap configurations, and component datasheets.
    * [ ] **Mechanical, Mounting & Thermal Specs:** Document mechanical clearance, dimensional constraints, and thermal/airflow expectations for racked continuous operation. Supply rack rails (Server Track) or 3D CAD models (`STEP`/`DXF`) and required heatsink/cooling kits (Embedded / SBC Track custom shelves).
    * [ ] **Power Envelope & Electrical Input:** Document peak and instantaneous power consumption under simultaneous all-cores plus NPU/GPU stress, along with AC/DC input voltage, connector polarity/specs, and included power cords or adapters for safe PSU/PDU sizing.
    * [ ] **Physical Modifications (if any):** Document any mandatory physical pad soldering, resistor straps, or board modifications needed to access remote power/reset circuits or specific I/O connectors.
    * [ ] **Network & Console Interfaces:** Dedicated Gigabit Ethernet (or faster) host interface supporting standard DHCP and network boot (TFTP, PXE/iPXE, or HTTP Boot); Server Track systems must additionally provide a dedicated BMC management Ethernet port for isolated out-of-band networking. Out-of-band serial console: BMC serial console / SOL (Server Track), or standard 3-pin TX/RX/GND UART with documented pinout, logic voltage level (e.g., 1.8V vs. 3.3V TTL), baud rate, and parity settings (Embedded / SBC Track).
    * [ ] **Out-of-Band Power & Management:**
      * *Server Track:* On-board BMC (preferably OpenBMC) exposing Redfish (or a documented equivalent API) with remote power control, serial-over-LAN (SOL), and one-time boot-device override (`BootSourceOverrideTarget` for PXE/HTTP/disk). Vendors must supply BMC credential reset/rotation procedures so RISE holds exclusive administrative ownership (no undocumented vendor accounts or mandatory phone-home agents).
      * *Embedded / SBC Track:* Boards must automatically power on and boot upon AC/DC power restoration, or expose accessible header pins/jumpers for simple external relay control without requiring complex board surgery, with clean cold power-cycle behavior (no USB/UART back-powering preventing reset) and working software reboot (`SBI SRST` / UEFI `ResetSystem`).
    * *Memory & Storage Sizing Guidance (Recommended, non-gating):* For CI-targeted Embedded / SBC platforms, **16 GB RAM minimum (32 GB preferred)** is strongly recommended to compile modern C++ workloads without excessive swap wear (8 GB boards are discouraged for shared build pools); **64 GB+ internal eMMC/flash** suffices for netboot and image-test CI boards, while **128 GB+ kernel-supported local storage** (e.g., M.2 SATA/NVMe SSD) is recommended for nodes hosting persistent Kubernetes or GitHub Actions runner containers. Server Track systems should be sized for multi-tenant bare-metal and KVM/VM workloads.
  * **Firmware & Bootloader Checklist:**
    * [ ] **Firmware & Bootloader Source:** Provide functional binaries, reproducible build instructions, and public or private source repositories (or patches plus the exact upstream base commit) for GPL components (**U-Boot**, **Linux kernel**), **OpenSBI / EDK2** where available, and **BMC firmware (e.g., OpenBMC)** where applicable, capable of reaching a boot prompt and network boot.
    * [ ] **Remote Flashing & Recovery:**
      * *Server Track:* Out-of-band host firmware (SPI/UEFI) and BMC firmware update and recovery via BMC (e.g., Redfish `UpdateService`, BMC-controlled SPI flashing, dual-bank failover, or virtual media) without physical human intervention.
      * *Embedded / SBC Track:* Supply recovery binaries, flashing scripts, and a documented zero-touch mechanism to reliably enter DFU, bootrom, or fastboot recovery mode remotely (e.g., via software triggers or accessible `Flash`/`Reset`/`Boot` pins for external debug harnesses without physical human intervention; required for flash-mutating workloads, as PDU/relay power-cycling alone cannot recover corrupted-flash boot loops). Document dedicated USB DFU/ADB port requirements where applicable.
    * [ ] **MAC Address Persistence:** Document non-volatile storage mechanisms for preserving deterministic, unique MAC addresses (including the BMC NIC on Server Track) across reflashes and cold power cycles (factory OTP/eFuse or dedicated EEPROM is strongly preferred over U-Boot `env`, which full-flash DFU recovery may erase).
    * [ ] **Early Boot Firmware Blobs:** Temporary prebuilt non-GPL early boot firmware blobs (e.g., proprietary first-stage bootloaders/FSBL/SPL, ROM-loaded init shims, or vendor-prebuilt BSD-licensed OpenSBI/EDK2 binaries) and proprietary hardware/co-processor firmware are permitted during Stage 1 bring-up. GPL components (U-Boot, Linux kernel) must always include corresponding source code.
  * **Linux Kernel Checklist:**
    * [ ] **Kernel Enablement:** Out-of-tree vendor kernel forks (e.g., vendor Linux 6.6/6.12 LTS trees) are permitted for early bring-up, though mainline is strongly preferred. Vendors must grant repository access or supply kernel patches and the exact upstream base tree to Developer Cloud maintainers.
  * **RISC-V Architecture Checklist:**
    * [ ] **ISA & Extensions:** Clearly define and document the supported RISC-V profile (e.g., RVA22U64/RVA23S64), ISA string, platform extensions (e.g., RVV 1.0, Hypervisor `H`, AIA), and any known silicon errata requiring firmware or kernel workarounds.

* **Developer Cloud Support & Services Provided:**
  * **Private Lab Staging:** Isolated, firewalled private staging environment with no direct public IP addresses and no route to production pools. Embedded / SBC Track boards receive a dedicated Labgrid exporter allocation on a private NAT VLAN (outbound internet fetch permitted); Server Track systems receive isolated provisioning and BMC/OOB management VLANs (staging bastion or staging OpenStack/Ironic enrollment).
  * **Restricted Access Control:** Interactive SSH and console access strictly via a RISE-managed or documented site-approved jump host (bastion), using least-privileged, auditable, time-limited, revocable credentials limited to core maintainers and authorized vendor engineers during bring-up.
  * **Remote Operations Tooling:** Automated serial console logging and remote power control (switched PDU/relay control via Labgrid or BMC/Redfish power management). Authorized vendor engineers receive scoped, per-system control-plane access (never direct shared PDU/relay or standing BMC admin credentials) to power-cycle staged systems independently.

---

### Stage 2: Pilot Pool

* **Target Scope:** Automated CI runner testing, distribution packager enablement, Yocto/Android BSP CI, and kernel regression testing.
* **Vendor Requirements Checklist:**
  * **Hardware & Physical Checklist:**
    * [ ] **Verification Compliance:** Platform must pass all Stage 1 verification checks (automated power cycling, remote flashing/recovery, MAC persistence, and network boot for Embedded / SBC Track; plus BMC/Redfish power, SOL, boot-device override, and firmware update verification for Server Track).
    * [ ] **Form Factor & Fleet Allocation:**
      * *Embedded / SBC Track:* Supply 10+ physical units racked at a RISC-V Developer Cloud hosting site (custom shelf/caddy or standardized footprint such as ATX/ITX) with a 10-15% vendor spare replacement pool.
      * *Server Track Exception:* Large rackable server-class systems may be onboarded in smaller quantities (e.g., 1-2 units) with an agreed spare/FRU replacement plan.
  * **Firmware & Bootloader Checklist:**
    * [ ] **Mandatory RISE Source Mirroring:** All open-source firmware, bootloader, BMC (where applicable), and kernel sources (OpenSBI, U-Boot/EDK2, Linux kernel, and any required build/BSP layers) must be publicly accessible under **OSI-approved, upstream-compatible open-source licenses** so RISE maintainers can mirror them into **RISE-owned repositories under `riseproject-dev`** on GitHub, ensuring sources remain permanently buildable even if vendor repositories move or are archived. Any temporary non-GPL pre-boot binary blobs not yet built from `riseproject-dev` source must be covered by the Binary Sunset Plan below.
    * [ ] **Firmware Upstreaming Plan:** Provide a documented upstreaming plan outlining timelines and targeted mailing list or PR series for pushing core bootloader enablement (OpenSBI, U-Boot/EDK2, and OpenBMC where applicable) upstream.
    * [ ] **Boot Standards:**
      * *Server Track (Mandatory):* Must provide a compliant **UEFI** boot environment conforming to **RISC-V BRS-I** ([`riscv-non-isa/riscv-brs`](https://github.com/riscv-non-isa/riscv-brs): UEFI, ACPI, SMBIOS, and SBI per the RISC-V Server Platform specification, e.g., EDK2 + OpenSBI) or, for transitional pre-ACPI Device Tree-based server hardware, **EBBR** (UEFI + Device Tree via EDK2 or U-Boot with `CONFIG_EFI_LOADER=y`), with working UEFI PXE/HTTP Boot and clean software reset (`SBI SRST` / UEFI `ResetSystem`) so unmodified OS installers and Ironic boot out of the box *(UEFI Secure Boot is optional)*.
      * *Embedded / SBC Track (Preferred):* **EBBR** (Embedded Base Boot Requirements: UEFI + Device Tree via U-Boot `CONFIG_EFI_LOADER=y` or EDK2, aligned with **RISC-V BRS**) is strongly preferred so unmodified Linux distribution installers work without custom board scripts. Boards lacking UEFI may enter Stage 2 under Labgrid (using U-Boot TFTP/HTTP netboot or Yocto/Android workflows) with an explicit **Developer Tooling WG waiver** recorded in the board's compliance checklist.
    * [ ] **Binary Blob Governance & Redistribution Rights:**
      * Supply SHA256 integrity checksum manifests, reserved/payload memory maps (for resident firmware regions such as OpenSBI, AON, or DDR), and **written legal redistribution licenses** (without click-through EULAs or per-user NDAs, confirming sublicensing rights for any third-party IP such as DDR PHY or GPU/NPU firmware) permitting RISE, its CI infrastructure, and downstream open-source distributions and users to mirror, store, and publicly redistribute required binary blobs in public repositories (e.g., `riseproject-dev` or `linux-firmware`) and bootable CI/OS images.
      * Provide a documented **Binary Sunset Plan** (with timelines agreed upon with Developer Cloud maintainers) committing to open-sourcing or replacing any remaining non-GPL prebuilt early boot firmware blobs (e.g., proprietary FSBL/SPL, ROM-loaded init shims, or closed vendor SBI/UEFI components) with reproducible, source-built open-source firmware by Stage 3. Dedicated hardware subsystem firmware blobs (e.g., co-processor, DDR training, Always-On (AON), GPU/NPU, peripheral microcode, or proprietary BMC firmware accepted as an exception to OpenBMC) are exempt from the sunset requirement, provided their redistribution rights (and security-update terms for BMC firmware) are legally verified and documented.
  * **Linux Kernel Checklist:**
    * [ ] **Linux Upstreaming Plan:** Provide a documented Linux Upstreaming Plan (with timelines agreed upon with Developer Cloud maintainers) outlining active, in-progress, and planned [`lore.kernel.org`](https://lore.kernel.org/linux-riscv/) patch series for device enablement.
  * **RISC-V Architecture Checklist:**
    * [ ] **ISA Extension Validation:** Platform Device Tree (`riscv,isa-extensions`) or ACPI (`RHCT`) accurately advertises only functional hardware extensions (no false positives causing `SIGILL` faults), and userspace-visible extensions are accurately exposed via `riscv_hwprobe` (where supported by the kernel) and `/proc/cpuinfo` without regression, transitioning to mainline verification as enablement patches land.

* **Developer Cloud Support & Services Provided:**
  * **Pilot Provisioning Access:** Pilot enrollment into **Labgrid** (Embedded / SBC Track) or pilot **OpenStack Nova / Ironic** pools (Server Track).
  * **Distribution & Ecosystem Maintainer Access:** Access expanded to targeted Linux distribution packagers (e.g., Ubuntu 24.04 LTS (RVA20) and 26.04 LTS (RVA23), Debian 13, Gentoo, RHEL 10 Developer Preview) and embedded ecosystem teams (e.g., Yocto `meta-riscv` / `AutoBuilder`, AOSP).
  * **CI Runner Integration:** Integration into RISE GitHub Actions self-hosted runner pools (including [`riseproject-dev/riscv-runner`](https://github.com/riseproject-dev/riscv-runner) and Labgrid-backed hardware CI runners) for automated PR and nightly testing.
  * **Kernel Regression Testing:** Automated boot and `kselftest` validation tracking upstream [`torvalds/linux`](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git) master/rc kernels as board enablement matures.

---

### Stage 3: Production Pool

* **Target Scope:** Production bare-metal compute pool for general RISC-V developers and ecosystem maintainers (providing shared community CI execution).
* **Stage 3 Readiness & Vendor Requirements Checklist:**
  * **Platform & Control-Plane Readiness (Verified Jointly with Developer Cloud Maintainers):**
    * [ ] **Stage 2 Continuity & Stability Soak:** Platform continues to meet all Stage 2 gates (up-to-date `riseproject-dev` mirrors, fleet and spare/FRU commitments, verified blob redistribution licenses, and UEFI compliance or a confirmed WG waiver for Labgrid-managed Embedded / SBC Track pools) and passes sustained production thermal and load soak testing at the hosting site.
    * [ ] **Server Track:** On-board BMC (OpenBMC/Redfish), UEFI PXE/HTTP provisioning, and KVM/VM capabilities (where `H` is supported, with AIA preferred for hardware interrupt virtualization) pass all hardware and firmware compatibility checks required for production **OpenStack Nova / Ironic** integration by RISE maintainers.
    * [ ] **Embedded / SBC Track:** Automated power cycling, serial console, netboot/flashing, and remote DFU recovery (for flash-mutating workloads) pass reliability verification required for production **Labgrid** multi-pool scheduling and telemetry by RISE maintainers.
  * **Firmware & Bootloader Checklist:**
    * [ ] **Upstream Submission Progress:** Upstream PRs or patch series merged, queued in maintainer `-next` branches, or actively advancing through review for OpenSBI ([`riscv-software-src/opensbi`](https://github.com/riscv-software-src/opensbi)), U-Boot ([`u-boot/u-boot`](https://github.com/u-boot/u-boot)) or EDK2 ([`tianocore/edk2`](https://github.com/tianocore/edk2) / [`tianocore/edk2-platforms`](https://github.com/tianocore/edk2-platforms), including platform ACPI tables where applicable), and OpenBMC ([`openbmc/openbmc`](https://github.com/openbmc/openbmc)) where applicable.
    * [ ] **Binary Sunset Plan Completion:** Verified completion of the committed Binary Sunset Plan, replacing previous prebuilt non-GPL early boot firmware blobs with reproducible, source-built open-source firmware. Exempt hardware subsystem firmware blobs retain documented SHA256 manifests and legal redistribution clearance.
  * **Linux Kernel Checklist:**
    * [ ] **Linux Upstreaming Plan Completion:** Upstream patches merged, queued in `linux-next` / maintainer `-next` branches, or actively advancing through review for core SoC drivers (clock/reset/pin controllers or SCMI/ACPI driver bindings as applicable) and board Device Trees plus DT bindings (for DT-based platforms) targeting [`linux-riscv`](https://git.kernel.org/pub/scm/linux/kernel/git/riscv/linux.git) maintainer branches and standard [`torvalds/linux`](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git) releases.
  * **RISC-V Architecture Checklist:**
    * [ ] **Declared Architecture Compliance:** Full hardware compatibility with the platform's declared RISC-V profile (e.g., RVA22U64/RVA23S64) and declared optional or platform extensions (e.g., Vector `V`, Hypervisor `H`/`Sha`, and AIA/`Ssaia` where present, including KVM virtualization where supported), with any known silicon errata and required firmware/kernel workarounds documented.

* **Developer Cloud Support & Services Provided:**
  * **Production Pool Integration:** Multi-tenant **OpenStack Nova / Ironic** bare-metal cloud for Server Track hardware, and production **Labgrid** + `riscv-runner` bare-metal pools for Embedded / SBC Track hardware.
  * **Tier-1 CI Integration:** Production baseline (high availability subject to fleet capacity and redundancy) for GitHub Actions runner pools backing major upstream open-source projects (e.g., Linux Kernel, GCC/LLVM, CPython, PyTorch, Yocto, AOSP, CNCF, `llama.cpp`, and more).
  * **Public Developer Pool:** On-demand self-service allocation for ecosystem developers, toolchain maintainers (GCC/LLVM), and language runtime teams (OpenJDK, Rust, Go). Embedded / SBC Track boards remain on private NAT subnets accessed via secured jumpbox, ephemeral port-forwarded SSH (PAT), or control-plane proxies (no direct public IPs on target boards). Server Track workloads use isolated OpenStack tenant networking per site network policy, while BMC and provisioning interfaces remain strictly private.
  * **Production Operations Support:** Racked in production RISE partner datacenter infrastructure with agreed remote-hands hardware support and automated telemetry monitoring.
