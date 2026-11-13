# RISE Developer Cloud (Board Farm) — 2026 Weekly Progress Log

> **Living Snapshot:** See [`current_status.md`](current_status.md) for the current state of all hardware, hosts, electrical interfaces, and active CI pools.
> **Ordering:** Reverse chronological (newest week at the top). Covers both the weekly Wednesday **OSL/RVI/RISE Board Farm** syncs and Board Farm items from the bi-weekly Thursday **RISE Developer Tooling WG** calls.
> **Internal Companion Docs (Google Drive):** Confidential details (internal IPs/hostnames, budgets, pricing, contracts/POs, and meeting recordings) are tracked in *`RISE Developer Cloud & Build Farm — Internal Network, Host IPs & Admin Companion`*, *`RISE Governing Board, Budgets, Contracts & Strategic Hosting (Confidential)`*, and *`RISE Meetings, Recordings & Internal Docs Master Directory (2026)`*.

---

## 2026-11-11 — Weekly Board Farm Sync & Written Update (Nov 11–13)

* **OSU-OSL Written Report:** [`STATUS-2026-11-11.md`](https://git.osuosl.org/osuosl/a210-linux/-/blob/main/docs/status/STATUS-2026-11-11.md)

### 1. Hardware & Shelf 1 Assembly (OSU-OSL)
* **Clarification on Shelf 1 Board Mounting:** Earlier meeting notes stated that all 10 boards were already mounted in Shelf 1. OSU-OSL clarified that all 10 Zhihe A210 boards are **prepped at the bench** (thermal paste applied, heatsinks installed, and both 5-board 3D-printed carrier ranks fit-checked in the steel tray), **but remain off the shelf tray** while the rear gear-zone power harness is wired.
* **Shelf 1 Power & Mechanical Progress:**
  * Completed through **Step 30 (Stage 3)** of the 14-stage [`SHELF-INSTALL-MANUAL.md`](https://git.osuosl.org/osuosl/a210-linux/-/blob/main/docs/SHELF-INSTALL-MANUAL.md): the `Mean Well LRS-350-12` PSU is mounted on its supports with the voltage selector set to `115V` for office `120V` bring-up (`230V` selector switch + photo verification is a mandatory gate before connecting to `208V` data-center PDUs).
  * **3D Print Batches 7 & 8 (`CEOAS`):** Batch 7 test coupons (`2026-11-09`) identified two CAD issues before printing full parts: the fuse-holder clip pocket was too stiff (snapping a finger) and the fan-wall WAGO pockets allowed connectors to slide out the front. Both were fixed in OpenSCAD, and **Batch 8** (`P9 v2` fuse plate, second fan wall, both vented deck halves, `P3` rear wall half, switch foot rings) was printed `2026-11-12` and picked up `2026-11-13`. Two spools of black PETG filament were ordered `2026-11-13` to replenish CEOAS stock.
  * **DigiKey Order Arrived (`2026-11-09`):** Received 100× M3 heat-set inserts (for Shelf 1's rear wall + ~8 future shelves) along with Shelf 2's spacers, 3A fuses, barrel pigtails, and ring terminals.
  * **Next Milestone (`~2026-11-18`):** Wiring Stages 3 & 4 (AC/earth + DC distribution) on `2026-11-13` to bring the first relay-controlled shelf board (**`a210-s1-b01` / `B1`**) online under Labgrid (`ETH008-B` relay), followed by all 10 Shelf 1 boards and a 208V 10-board thermal soak test in December 2026.

### 2. Bench Fleet & Control Plane
* **Bench Fleet State:** `a210-1`, `a210-2`, and `a210-4` were reset and verified online (`a210-3` and `a210-5` remained online).
  * **`a210-1` (`a210-board-01`):** Confirmed (`2026-11-09`) to remain on **Android 17 (`android-17-v1.0`)**. Because the current Android kernel build lacks the A210 Ethernet driver, ADB currently uses USB-C (to the controller host) or Wi-Fi.
  * **Bench eMMC `7.2.12` Rollout Dropped:** In-place upgrading of the bench boards' local eMMC from `7.2.8` to `7.2.12` was dropped since `a210-2` and `a210-5` already carry the OpenSBI `/reserved-memory` DTB fix, `a210-1` runs Android, and `a210-3` netboots `v7.2.12-a210` over TFTP into RAM.
* **Labgrid & Chef Adoption:**
  * Stopped the legacy `/dev/ttyUSB4` serial logger loop and stale `labgrid-suggest` processes on the controller host.
  * Agreed on a **2-pass Chef rollout**: Pass 1 adopts `labgrid-coordinator` and `labgrid-exporter` unchanged via `osl-labgrid` + `proj-rise` (deploying [`boards/zhihe-a210/exporter.yaml`](../../boards/zhihe-a210/exporter.yaml) from this repo and moving `/dev/ttyUSB*` to `0660` group `dialout` once all runner/user accounts are verified in `dialout`); Pass 2 covers the GHA runners and `board-farm-hub`.
  * **Version Lockstep:** Agreed that `labgrid-client` (on GHA runners), `labgrid-exporter`, and `labgrid-coordinator` must be upgraded in lockstep.

### 3. CI Workloads (Yocto & Android 17) & DFU Pilot Sequencing
* **Upstream Yocto Nightly CI (`riscv/meta-riscv`):**
  * Merged [`riscv/meta-riscv#744`](https://github.com/riscv/meta-riscv/pull/744) (`2026-11-07`, switching kernel `SRC_URI` to `riseproject-dev/linux` and adding the OSU-OSL hardware workflow) and [`#748`](https://github.com/riscv/meta-riscv/pull/748) (`2026-11-10`, expanded path filters + `readlink -f` symlink resolution).
  * Synced [`boards/zhihe-a210/`](../../boards/zhihe-a210/) and [`.github/workflows/yocto-zhihe-a210.yml`](../../.github/workflows/yocto-zhihe-a210.yml) in this repo, fixing a UART command-echo regex bug (`931cca1`). Nightly run [`#42960106706`](https://github.com/riscv/meta-riscv/actions/runs/42960106706) (`2026-11-11`) passed end-to-end.
  * **Decision — No SSH in Yocto Test Images:** Decided against adding Dropbear SSH to Yocto test images to avoid security exposure; tests will continue running strictly over serial console via Labgrid.
  * **Dedicated Yocto Builder (`rise-python-ci-1.di.riseproject.dev`):** Reprovisioning Hetzner host `rise-python-ci-1.di.riseproject.dev` with a persistent `sstate-cache` and `downloads` directory to cut `meta-riscv` build times from ~2–7 hours to minutes, while keeping the build job on Hetzner and the hardware test job running on OSU-OSL's local runner.
* **Android 17 (AOSP) CI:**
  * Approved registering an organization-level GitHub Actions runner under `riseproject-dev` with a token scoped to the Android repositories.
  * Updated [`hub/app/telemetry.py`](../../hub/app/telemetry.py) (`a054ebb`, `0f7ddfa`) to detect Android boards over ADB/UART and publish Labgrid tags with interactive filtering on the public dashboard.
* **Shelf 2 DFU Pilot Sequencing:**
  * **Decision:** Prioritize finishing Shelf 1 (`B1` online) first before running the 1-board bench DFU trial with BayLibre's Copilot Lite + Triple Relays Hat (already on hand at OSL).
* **SpacemiT K3 Rollout Plan & EFI Firmware:**
  * Outlined a 2-phase K3 plan: **Phase 1 (first half of Dec 2026)** brings up 1× 32 GB and 1–2× 16 GB K3 boards on VPN/SSH/serial at the bench; **Phase 2 (Q1 2027)** builds an open K3 shelf with Copilot DFU using the incoming student worker. CoM260 availability on the Banana Pi store was also identified to address community K3 shortages.
  * Developing an **EFI firmware fix for the K3** so software `reboot` commands cleanly reset the board without requiring a physical power cycle.

### 4. Governance, Global Hosting, Budget, Documentation & Naming
* **Governing Board Deep Dive & Budget/Hosting Approvals (`2026-11-12`):**
  * Presented the Developer Tooling Deep Dive (`Developer Cloud / Board Farm`, `Build Farm`, and `Simulator/Emulator`) to the RISE Governing Board.
  * Confirmed initial upstream workload priority on the OSU-OSL Developer Cloud as **Yocto CI → Android 17 CI → Linux Kernel CI**, to be followed by broader upstream project requests.
  * Discussed and approved the Strategic Member hosting tier (NORAM/OSU-OSL, EMEA/Scaleway, APAC/China hosting options), GitHub-hosted larger runners budget reallocation, and Cross-Distro Stages RFP *(details recorded in `RISE Governing Board, Budgets, Contracts & Strategic Hosting (Confidential)`)*.
* **Decision — GitHub Documentation & Status Tracking:** Agreed to maintain Board Farm and Build Farm status, hardware/interface maps, and weekly progress tracking in GitHub (`riseproject-dev/developer-cloud` and `riseproject-dev/developer-infrastructure-wg`) so both maintainers and AI assistants have a version-controlled source of truth.
* **Decision — "RISC-V Developer Cloud" Naming:** Updated repository branding ([`README.md`](../../README.md), `7efa4f0`) from *RISE Board Farm* to *RISC-V Developer Cloud* (`riseproject-dev/riscv-runner` remains a separate repository layered on top of Developer Cloud, Scaleway, and cloud providers).

---

## 2026-11-05 — Bi-Weekly Developer Tooling WG & Weekly Board Farm Sync (Nov 4–5)

* **OSU-OSL Written Report:** [`STATUS-2026-11-04.md`](https://git.osuosl.org/osuosl/a210-linux/-/blob/main/docs/status/STATUS-2026-11-04.md)
* **OSU-OSL CI Design Draft:** [`docs/RISE-CI.md`](https://git.osuosl.org/osuosl/a210-linux/-/blob/main/docs/RISE-CI.md) & [`docs/RISE-ALIGNMENT.md`](https://git.osuosl.org/osuosl/a210-linux/-/blob/main/docs/RISE-ALIGNMENT.md)

### 1. Architecture & Shelf Standardization Decisions
* **9× Standard Shelves + 1× DFU/Copilot Shelf:**
  * Aligned on keeping **Shelf 1** (and Shelves 3–10) as standard U-Boot TFTP/HTTP netboot shelves with `Devantech ETH008-B` 12V relays, and designating **Shelf 2** (10× A210) as the **DFU / BayLibre Copilot shelf** (1× Copilot Lite + 1× Triple Relays Hat per board, requiring 3× USB ports per board across 3× 10-port USB hubs: Copilot UART/GPIO, A210 USB-A DFU, and A210 USB-C ADB).
* **3-Tier OSU-OSL x86 Host Split (`CTRL-2`):**
  * Agreed to separate the OSU-OSL x86 infrastructure into: (1) 1U OSL Control Node / Jumpbox (`labgrid-coordinator`, DHCP, TFTP, Apache HTTP), (2) ~4× rackable Dell 1U Labgrid Exporters (1 per 2–3 shelves), and (3) 1× dedicated 16–32 core, 64 GB RAM x86 GitHub Actions Runner host isolated from the coordinator.
* **3-Stage Hardware Gating Policy:**
  * Established the 3-stage hardware onboarding model for Developer Cloud donations: **Stage 1 (Isolated Bench)** → **Stage 2 (Pilot Pool: EBBR/BBR UEFI, Binary Blob Sunset Plan, Mainline Upstreaming Plan, zero-touch power/DFU, 10+ units)** → **Stage 3 (Production OpenStack/Ironic Pool: 100% open-source bootline + mainline Linux)**.

### 2. Yocto CI Alignment, Android & Build Farm Rebalancing
* **Yocto Project Alignment (`meta-riscv` & `openembedded-core`):**
  * **`meta-riscv` Mainline Policy & Profile Tunes:** `meta-riscv` is now mirrored on `git.yoctoproject.org`, deprecated legacy vendor-kernel boards (`VisionFive`, `Star64`, `Nezha D1`) in favor of mainline kernels (`Zhihe A210` on OSU-OSL's `7.2.12`, `SpacemiT K3 Pico-ITX` on `7.3.1`), merged `riscv64gc`/`riscv64gcv` tunes into `openembedded-core`, and opened a draft PR in `meta-riscv` for standardized `RVA20`, `RVA22`, and `RVA23` tuning profiles.
  * **Two Distinct Yocto Hardware Requirements Identified:**
    1. **`meta-riscv` BSP CI:** Requires a **dedicated x86 build machine** (to build images quickly for GitHub Actions) paired with **RISE Board Farm hardware testing** on OSU-OSL `A210` and `K3` boards.
    2. **Official Yocto Project `AutoBuilder` (`openembedded-core`):** Requires a **dedicated RVA23 server with KVM acceleration** because upstream `qemuriscv64` `ptest` runs currently execute under software emulation and time out. KVM-accelerated `ptest` speedups are being benchmarked on a `K3 Pico-ITX`.
* **Upstream Yocto BSP Merged:** Merged [`riscv/meta-riscv#724`](https://github.com/riscv/meta-riscv/pull/724) (Zhihe A210 machine BSP) and validated the end-to-end self-hosted GitHub Actions workflow (`Run #41810778447`).
* **Repurposing `rise-python-ci-1.di.riseproject.dev` for Yocto CI:** Decided during the Nov 5 WG review of the 19 Hetzner `CCX63` servers to retain `rise-python-ci-1.di.riseproject.dev` under its grandfathered pricing and reprovision it as the dedicated Yocto x86 CI builder *(server IP/admin details in `RISE Developer Cloud & Build Farm — Internal Network, Host IPs & Admin Companion`; pricing details in `RISE Governing Board, Budgets, Contracts & Strategic Hosting (Confidential)`)*.
* **Alibaba A210 Mainline Kernel v3:** Han Gao (ISCAS/Alibaba) posted the mainline LKML v3 A210 SCMI series (`2026-11-03`) and split A210 pinctrl series (`2026-11-07`).

---

## 2026-10-28 — Weekly Board Farm Sync

* **OSU-OSL Written Report:** [`STATUS-2026-10-28.md`](https://git.osuosl.org/osuosl/a210-linux/-/blob/main/docs/status/STATUS-2026-10-28.md)

### 1. Shelf 1 Bench Prep & 14-Stage Installation Manual
* **All 10 Shelf 1 Boards Prepped:** Replaced factory heatsink pads with Arctic MX-4 thermal paste on all 10 boards; verified both 5-board carrier ranks take all 4 mounting bolts through the steel shelf tray simultaneously; built and verified the first spliced FTDI UART console cable (`CON1`).
* **14-Stage Installation Manual (`SHELF-INSTALL-MANUAL.md`):** Rewrote the section-based wiring runbook into a 14-stage, 121-step build-order installation manual generated from the 3D CAD model, targeting a working 1-board slice (`B1` + switch + both relays + front fan wall + USB hub) before wiring `B2`–`B10`.
* **CAD Refinements (Batch 7 Sent `2026-10-27`):** Redesigned the fuse plate (`P9 v2`) so inline fuse holders face their wire routing direction without cable ties, moved the rear wall (`P4`) feet to the tray's vertical slot orientation, and added WAGO connector pockets under the fan walls.

### 2. Kernel `v7.2.12`, GitLab Access & Hosting Contract
* **OSU-OSL GitLab Access & Kernel Rebase:** Merged the OpenSBI 2 MB `/reserved-memory` (`no-map`) DTB fix and rebased the OSU-OSL A210 kernel from `7.2.8` to stable **`7.2.12`** (published to [`riseproject-dev/linux`](https://github.com/riseproject-dev/linux) as tag `v7.2.12-a210`).
* **Hosting Purchase Order & 2027 Quote:** Confirmed the 2026 hosting PO and initiated scoping for the 2027 expansion quote *(tracked in `RISE Governing Board, Budgets, Contracts & Strategic Hosting (Confidential)`)*.

---

## 2026-10-22 — Bi-Weekly Developer Tooling WG & Weekly Board Farm Sync (Oct 21–22)

* **OSU-OSL Written Report:** [`STATUS-2026-10-21.md`](https://git.osuosl.org/osuosl/a210-linux/-/blob/main/docs/status/STATUS-2026-10-21.md)

### 1. OpenSBI Reserved-Memory Fix & Storage Findings
* **Resolved `a210-5` Container-Pull Crashes (`65eed4c`):** Root-caused `a210-5`'s kernel panics under heavy GitHub Actions runner workloads to Linux overwriting OpenSBI's 2 MB firmware memory region (`0x80000000`–`0x80200000`) and fixed it by adding the `/reserved-memory` (`no-map`) Device Tree node.
* **A210 Storage Architecture (`M.2 B-Key SATA` vs. Mini-PCIe vs. USB):** Confirmed that the A210's M.2 slot is **B-Key SATA only (`2242` form factor)** and does not support NVMe, and that PCIe is not enabled in the current A210 kernel for the mini-PCIe slot; attached a 1 TB USB SSD to `a210-5` (~17 MB/s measured over USB 2.0) and agreed not to pursue NVMe drives for the A210 fleet.

### 2. Public Telemetry Relay, NAT/PAT Architecture & Exporter Reuse
* **Public Dashboard Relay Merged (`4db1646`):** Merged the Google Apps Script cache relay (`hub/gas/Code.gs`) and outbound pusher (`hub/app/relay.py`) so `board-farm-hub` pushes 3-second reservation changes and 30-second board telemetry to the public GitHub Pages dashboard ([`riseproject-dev.github.io/board-farm/hub/static/`](https://riseproject-dev.github.io/board-farm/hub/static/)) without exposing OSU-OSL's private network.
* **Private NAT + Ephemeral Port-Forwarded SSH (`PAT`) Concept:** Because all boards sit on a private NAT subnet behind the Jumpbox/Coordinator, evaluated adding on-demand Port Address Translation (`PAT`) for future interactive developer leases (mapping a temporary external port on a single NAT IP to port `22` on the leased board for the duration of the reservation).
* **Long-Term Reuse of A210s as Labgrid Exporters:** As newer RVA23 boards arrive, non-RVA23 A210 boards can be repurposed as dedicated Labgrid Exporter/management controllers and RISC-V runner hosts.
* **Build-Centric TFTP & Release Lifecycle Design (`67ddeb5`, `4abff8b`):** Published [`docs/architecture-design/build-centric-tftp-and-release-lifecycle.md`](../architecture-design/build-centric-tftp-and-release-lifecycle.md) defining immutable per-build TFTP staging directories, 10-build circular buffer / 90-day retention, and monthly eMMC golden image updates.

---

## 2026-10-08 — Bi-Weekly Developer Tooling WG & Weekly Board Farm Sync (Oct 7–8)

* **OSU-OSL Written Report:** [`STATUS-2026-10-07.md`](https://git.osuosl.org/osuosl/a210-linux/-/blob/main/docs/status/STATUS-2026-10-07.md)

### 1. Shelf 1 CAD / Carrier Prototyping & Kernel Upgrade Mechanism
* **Carrier Coupon & Manufacturer 3D CAD Models:** OSU-OSL printed and test-fit the first 3D-printed A210 board carrier coupon, switched to manufacturer 3D CAD models for accurate shelf geometry, and published the initial shelf wiring diagram (`docs/SHELF-WIRING-RUNBOOK.md`).
* **In-Place Kernel Upgrade & Yocto TFTP Netboot:** Verified upgrading the bench boards' kernel without full eMMC reflashing, and demonstrated the first Yocto image booting over U-Boot TFTP netboot.

### 2. Why PDU Alone Cannot Recover Corrupted-Flash Boot Loops (Origin of DFU Shelf)
* **Android Common Kernel Boot-Loop Analysis:** When an Android Common Kernel test build entered a reboot loop and lost both UART and SSH, analysis showed that a network PDU/relay power toggle alone cannot break a corrupted-flash boot loop because the board immediately reboots the same broken flash image upon power restoration — establishing the requirement for remote `Flash`/`Reset` button actuation (which became the BayLibre Copilot + Triple Relays Hat design on Shelf 2).

### 3. SpacemiT K3 RAM Sizing Policy & Cross-Distro Developer Images
* **SpacemiT K3 RAM Policy (`16 GB` Minimum / `32 GB` Preferred):** Evaluated 8 GB vs. 16 GB vs. 32 GB K3 board pricing and ruled out 8 GB boards because 8 GB cannot compile modern C++ projects without heavy SSD swap wear and rapid obsolescence, establishing 16 GB / 32 GB as the target for the Developer Cloud K3 fleet *(pricing comparison in `RISE Governing Board, Budgets, Contracts & Strategic Hosting (Confidential)`)*.
* **Cross-Distro Developer Images Proposal:** Initiated the proposal for automated bootable RISC-V developer images (Ubuntu, Red Hat, Debian) paired with board-specific U-Boot/OpenSBI for the Board Farm *(RFP details in `RISE Governing Board, Budgets, Contracts & Strategic Hosting (Confidential)`)*.

---

## 2026-09-24 — Bi-Weekly Developer Tooling WG & Weekly Board Farm Sync (Sep 23–24)

* **OSU-OSL Written Report:** [`STATUS-2026-09-23.md`](https://git.osuosl.org/osuosl/a210-linux/-/blob/main/docs/status/STATUS-2026-09-23.md)

### 1. Hardware Gating Criteria (`board-farm#2`): Embedded vs. Server Track & Source Mirroring
* **Embedded Track (`Labgrid` + `U-Boot`) vs. Server Track (`OpenStack/Ironic` + `UEFI/BMC/OCP`):**
  * Clarified the long-term control-plane split during the review of the 3-Stage Hardware Onboarding PR (`board-farm#2`):
    * **Embedded / SBC Track (`A210`, `K3`, Yocto/Android/Kernel CI):** Boards without a BMC (and using U-Boot) will **remain on Labgrid** long-term, as Labgrid handles U-Boot/serial/DFU workflows directly whereas OpenStack Ironic requires UEFI and Redfish/BMC.
    * **Server Track (`SiFive 2U`, future `OCP` RVA23 servers):** Server-class hardware with BMCs and UEFI will use **OpenStack + Ironic** from day one.
* **Mandatory Source Mirroring in `riseproject-dev`:**
  * Stage 2 onboarding mandates mirroring kernel, U-Boot, and OpenSBI sources into **RISE-owned GitHub repositories (`riseproject-dev`)** so board support sources remain permanently available even if upstream vendor repositories are archived.
* **Binary Blob Redistribution Licensing & Fleet-Size Exceptions:**
  * Added two Stage 2 requirements: (1) explicit verification of legal redistribution rights for any closed binary blobs (DDR/co-processor firmware), and (2) an exception to the 10-board minimum fleet size for large server-class systems (where 1–2 units may be onboarded).

### 2. Tiered Storage Strategy for `riscv-runner` Pods & Initial Yocto/Dashboard Bring-Up
* **Selective 128 GB SSD Expansion for `riscv-runner` Boards:**
  * Enabled the missing kernel flags for Kubernetes on the bench A210 and noted that the `riscv-runner` Ubuntu container image (~4 GB compressed, ~30 GB uncompressed) fills the 58 GB eMMC rootfs if not garbage-collected.
  * Adopted a **tiered storage policy**: rather than adding 1 TB SSDs to all 100 A210 boards, add **128 GB SSDs** (matching Scaleway `EM-RV1`) only to the subset of A210 boards dedicated to GitHub Actions `riscv-runner` pods (e.g., ~40 boards), leaving the remaining ~60 netboot CI boards on their internal 64 GB eMMC.
* **First Local Yocto Boot, U-Boot `fastboot` over UDP & Local Dashboard Prototype:**
  * Verified the first local Yocto boot on an A210, verified U-Boot `fastboot` over UDP, and demonstrated the first read-only local Board Farm telemetry dashboard.

### 3. Yocto `AutoBuilder` Integration & 30–40% QEMU `ptest` Speedup
* **Yocto `AutoBuilder` & `resulttool`:**
  * Following the RISE–Yocto sync, Yocto agreed to build **two `meta-riscv` BSPs (`SpacemiT K3 Pico-ITX` and `Milk-V Duo`)** directly on the official Yocto Project `AutoBuilder`, mirror `meta-riscv` on `git.yoctoproject.org`, and evaluate feeding RISE Board Farm test results into the upstream `AutoBuilder` via **`resulttool`**.
* **30–40% QEMU `qemuriscv64` `ptest` Runtime Reduction:**
  * Submitted an upstream QEMU patch optimizing RISC-V TLB flushing in TCG mode, reducing `qemuriscv64` `ptest` runtimes by **30–40%** (`coreutils` `ptest` improved by **38%**).
