# RISE Developer Cloud (Board Farm) — Current Status & Hardware Reference

> **Last Updated:** 2026-11-13
> **Weekly Progress Log:** [`2026_weekly_progress.md`](2026_weekly_progress.md)
> **Live Telemetry & Reservation Dashboard:** [https://riseproject-dev.github.io/board-farm/hub/static/](https://riseproject-dev.github.io/board-farm/hub/static/)
> **Internal Companion Docs (Google Drive — Request Access from Maintainers):**
> * *`RISE Developer Cloud & Build Farm — Internal Network, Host IPs & Admin Companion`* (internal subnet/IPs, hostnames, relay admin, and secret manager notes)
> * *`RISE Governing Board, Budgets, Contracts & Strategic Hosting (Confidential)`* (server/runner budgets, hardware pricing, POs/RFPs, and strategic hosting agreements)
> * *`RISE Meetings, Recordings & Internal Docs Master Directory (2026)`* (Zoom recordings, Gemini meeting notes, and WG/TSC/GB slide decks)

This living document is the single source of truth for the current hardware, control-plane, and CI state of the **RISE Developer Cloud (Board Farm)** at the **Oregon State University Open Source Lab (OSU-OSL)**. It consolidates updates across RISE and OSU-OSL, provides direct links to OSU-OSL's underlying engineering files in [`osuosl/a210-linux`](https://git.osuosl.org/osuosl/a210-linux), and reconciles any outdated or conflicting notes in older runbooks.

---

## 1. Quick Links & Repositories

| Resource | URL | Purpose |
| :--- | :--- | :--- |
| **Live Public Dashboard** | [riseproject-dev.github.io/board-farm/hub/static/](https://riseproject-dev.github.io/board-farm/hub/static/) | Real-time VPN-free board status, Labgrid tags, OS/kernel telemetry, and reservation state |
| **RISE Board Farm Repo** | [github.com/riseproject-dev/developer-cloud](https://github.com/riseproject-dev/developer-cloud) | Labgrid configs (`boards/`), telemetry hub (`hub/`), CI actions (`.github/`), and architecture docs (`docs/`) |
| **OSU-OSL A210 Repo** | [git.osuosl.org/osuosl/a210-linux](https://git.osuosl.org/osuosl/a210-linux) | OSU-OSL CAD/3D models, electrical wiring harnesses, BOM, Debian installer, and weekly OSL status reports |
| **RISE Kernel Fork** | [github.com/riseproject-dev/linux](https://github.com/riseproject-dev/linux) | Kernel repository (`v7.2.12-a210` with OpenSBI `/reserved-memory` `no-map` DTB fix) used by Yocto CI |
| **Upstream Yocto Hardware CI** | [test-zhihe-a210.yml](https://github.com/riscv/meta-riscv/actions/workflows/test-zhihe-a210.yml) | Nightly `riscv/meta-riscv` build + physical A210 TFTP RAM netboot smoke test at OSU-OSL (`pool=a210-yocto`) |
| **RISE Android 17 (AOSP)** | [github.com/riseproject-dev/android_manifest](https://github.com/riseproject-dev/android_manifest/releases/tag/android-17-v1.0) | BayLibre Android 17 (`android-17-v1.0`) manifest, prebuilts, U-Boot `v2024.10-a210`, and OpenSBI `v1.5-a210` |
| **WG Infrastructure Repo** | [github.com/riseproject-dev/developer-infrastructure-wg](https://github.com/riseproject-dev/developer-infrastructure-wg) | Developer Tooling / Infrastructure Working Group charter, Build Farm docs, and cross-WG tracking |

---

## 2. Hardware Fleet Inventory & Rollout Status (OSU-OSL)

### 2.1 Bench Fleet — 5× Alibaba Zhihe A210 (Online)

Five early-batch Zhihe A210 boards (`a210-1` through `a210-5`) are live on the OSU-OSL lab backend subnet (`<assigned-by-dhcp>`) and managed via the OSU-OSL Labgrid controller host (`board-farm-controller`).

| Hostname | Labgrid Place | Active Tags / Pool | Current OS & Kernel | Storage & Peripherals | Console & Power | Current Role & Notes |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`a210-1`** | `a210-board-01` | `board=zhihe-a210`<br>`pool=a210-android` | **Android 17** (`android-17-v1.0`, Linux `6.6`) | 64 GB eMMC | USB-TTL (`ID_PATH`), Manual power | Dedicated **AOSP 17 test board** (confirmed 2026-11-09 to stay on Android). Ethernet driver is not enabled in the current Android kernel build; ADB uses USB-C or Wi-Fi. |
| **`a210-2`** | `a210-board-02` | `board=zhihe-a210` | **Debian 13 (Trixie)** (`7.2.8` + OpenSBI DTB fix) | 64 GB eMMC | USB-TTL (`ID_PATH`), Manual power | General development & testing; carries the OpenSBI 2 MB `/reserved-memory` (`no-map`) DTB fix. |
| **`a210-3`** | `a210-board-03` | `board=zhihe-a210`<br>`pool=a210-yocto` | **Yocto TFTP Netboot** (`v7.2.12-a210` in RAM) / Debian `7.2.8` on eMMC | 64 GB eMMC | USB-TTL (`pci-0000:00:1a.0-usb-0:1.2.4.2:1.0`), Manual power | Primary **`riscv/meta-riscv` nightly hardware CI target** ([`boards/zhihe-a210/exporter.yaml`](../../boards/zhihe-a210/exporter.yaml)). Netboots kernel + `core-image-minimal` initramfs into RAM via U-Boot TFTP without modifying eMMC. |
| **`a210-4`** | `a210-board-04` | `board=zhihe-a210` | **Debian 13 (Trixie)** (`7.2.8`) | 64 GB eMMC | USB-TTL (`ID_PATH`), Manual power | General development & netboot testing (reset and verified online 2026-11-05). |
| **`a210-5`** | `a210-board-05` | `board=zhihe-a210` | **Debian 13 (Trixie)** (`7.2.8` + OpenSBI DTB fix) | 64 GB eMMC + **1 TB USB-C SATA SSD** | USB-TTL (`ID_PATH`), Manual power | Persistent self-hosted GitHub Actions runner & flashing testbed; OpenSBI `/reserved-memory` fix resolved container-pull resets. |

> **Reconciling Kernel & Power Notes on the Bench Fleet:**
> * **Why bench boards run `7.2.8` on eMMC while CI uses `v7.2.12-a210`:** Kernel `v7.2.12-a210` (with the OpenSBI 2 MB `/reserved-memory` `no-map` fix) is built and staged on the install server and in [`riseproject-dev/linux`](https://github.com/riseproject-dev/linux), and is booted every night in RAM by Yocto CI. In-place updating of the bench boards' local eMMC from `7.2.8` to `7.2.12` was intentionally dropped on `2026-11-08` because `a210-2` and `a210-5` already have the DTB fix applied, `a210-1` runs Android 17, and `a210-3` netboots `v7.2.12-a210` over TFTP.
> * **Why bench boards lack relay power:** The 5 bench boards are early-batch units without the factory `R1113` auto-power-on resistor modification, so toggling 12V DC does not cold-boot them without a physical `K3` button press (`ManualPowerDriver`). All 100 production shelf boards have the factory `R1113` modification and boot automatically when 12V DC is applied by their relay.

---

### 2.2 Shelf 1 — 10× Zhihe A210 Standard Netboot Shelf (In Assembly)

Shelf 1 (`a210-s1-b01` to `a210-s1-b10`, labeled `B1`–`B10` in hardware diagrams) is the first 10-board production tray using 3D-printed vertical carriers, central 12V fused power distribution, and per-board Ethernet relay power control (`Devantech ETH008-B`).

* **Actual Assembly State (as of 2026-11-13):**
  * **Board Preparation (Done):** All 10 A210 boards have been prepped at the bench (factory phase-change pads replaced with Arctic MX-4 non-conductive thermal paste and heatsinks installed). Both 5-board 3D-printed carrier ranks passed their 4-bolt fit check in the steel shelf tray. *(Clarification: Earlier meeting notes stated "all 10 boards mounted"; the boards are prepped and fit-checked, and remain off the tray while rear gear-zone power wiring is completed.)*
  * **Gear-Zone & Power Assembly (Stage 3 / Step 30 of 121):** Following the 14-stage [`SHELF-INSTALL-MANUAL.md`](https://git.osuosl.org/osuosl/a210-linux/-/blob/main/docs/SHELF-INSTALL-MANUAL.md), the rear wall, IEC C14 inlet, fuse plate (`P9 v1`), relay stands with heat-set inserts, one `ETH008-B` relay board, the front 3×80mm fan wall, and the `Mean Well LRS-350-12` PSU (set to `115V` for office 120V bench bring-up) are mounted in the tray. Stages 3 and 4 (AC/earth wiring and DC fuse/relay wiring) are scheduled for bench completion on `2026-11-13`.
  * **3D-Printed Parts (`CEOAS` Print Service):** Batch 7 test coupons (`2026-11-09`) caught overly stiff fuse-holder clips and sliding WAGO pockets; the OpenSCAD models were updated and **Batch 8** (`P9 v2` fuse plate, second fan wall, both vented deck halves, `P3` rear wall half, and switch foot rings) was printed `2026-11-12` and picked up `2026-11-13`. Two spools of black PETG filament were ordered `2026-11-13` to replenish CEOAS stock (arriving `2026-11-16`).
  * **UART Console Harness:** The first spliced FTDI USB-TTL console cable (`CON1` for `B1`) is built, continuity-tested, and verified on the board header; `CON2`–`CON10` will be assembled once `B1` boots under Labgrid.
* **Rollout Milestones:**
  1. **~2026-11-18 — First Relay-Controlled Shelf Board (`a210-s1-b01` / `B1`) Online:** Complete Stages 3–8 and 10–12 of the installation manual to bring `B1` online with `ETH008-B` relay power (`<shelf-eth008-relay-host>`), in-shelf `MikroTik CRS326-24G-2S+IN` switch, FTDI console through the 10-port USB hub, and a PR adding `a210-s1-b01` to [`boards/zhihe-a210/exporter.yaml`](../../boards/zhihe-a210/exporter.yaml).
  2. **December 2026 — Full 10-Board Shelf 1 Burn-In & 208V Thermal Soak:** Wire `B2`–`B10`, swap in the Batch 8 final prints during a single planned teardown, switch the `LRS-350-12` voltage selector from `115V` to `230V` (verified by photo), and run a 10-board full-load thermal soak on `208V` in the OSU-OSL office rack using the `UNI-T UT320D` dual-channel thermocouple thermometer before moving Shelf 1 to the production data center.

---

### 2.3 Shelf 2 — 10× Zhihe A210 DFU & BayLibre Copilot Pilot Shelf (Planned)

While Shelf 1 uses standard U-Boot TFTP/HTTP netboot and `ETH008-B` 12V relays (which cannot physically press the `Flash` recovery button), **Shelf 2** is designated as a **DFU-capable shelf** for Android 17 (AOSP) CI, bootloader (`U-Boot` / `OpenSBI`) flashing, and automated recovery from bricked firmware or corrupted GPT partition tables.

* **Hardware Stack per Board (Open-Hardware [BayLibre Copilot](https://github.com/BayLibre/Copilot)):**
  * **[Copilot Lite Baseboard](https://github.com/BayLibre/Copilot):** Single USB-C uplink to the Labgrid Exporter providing a serialized FTDI UART console + 4× GPIOs (`GPIO 0` switches 12V barrel-jack board power up to 5A).
  * **[Triple Relays Hat](https://github.com/BayLibre/Copilot_Extension_Triple_Relays):** 3× signal relays driven by Copilot GPIOs to actuate the A210 `Flash` (USB DFU recovery) and `Reset` buttons remotely.
  * **[Triple USB 2.0 Hat](https://github.com/BayLibre/Copilot-extension-triple-usb-2.0):** GPIO-switched USB 2.0 pass-through ports.
* **USB Topology per Shelf (3× 10-Port Industrial USB Hubs → Exporter Host):**
  * Because an A210 in BROM DFU recovery mode does not expose a unique USB serial number, boards in recovery are matched deterministically by fixed physical USB hub port paths (`ID_PATH`):
    1. **1× USB per board** for the BayLibre Copilot Lite (UART console + GPIO/relay actuation).
    2. **1× USB per board** to the A210 **USB-A port** (BROM DFU flashing).
    3. **1× USB per board** to the A210 **USB-C port** (Android `ADB` / `fastboot`).
* **Pilot Rollout Sequence (Agreed 2026-11-11):**
  1. **Mid/Late November 2026 (after Shelf 1 `B1` is online):** 1-board bench pilot at OSU-OSL using the on-hand BayLibre Copilot Lite + Triple Relays Hat kit on a bench A210 (verifying AlmaLinux 10 `libgpiod`/`sysfs` GPIO support and evaluating whether Copilot's built-in 12V power switch can replace the `ETH008-B` relays on Shelf 2).
  2. **December 2026 – Q1 2027:** Expand to a 3-board CI tray and full 10-board Shelf 2 deployment (`pool=a210-android` and Yocto BSP bootloader CI).

---

### 2.4 Shelves 3–10 — 80× Zhihe A210 Standard Shelves (Q1 2027)

* Following Shelf 1 validation, Shelves 3–10 (8× standard netboot shelves, 10 boards each) will be assembled at a target pace of **~3 shelves/month in Q1 2027** with assistance from an OSU-OSL student worker starting in early 2027.
* Bulk DigiKey hardware for Shelf 2 (M3 heat-set inserts, spacers, 3A fuses, barrel pigtails, ring terminals) arrived on `2026-11-09`; remaining bulk shelf orders are held pending completion of the Shelf 1 thermal soak and replacement PSU sourcing (DigiKey halted Mean Well distribution; Amazon/Mouser/TME available).

---

### 2.5 SpacemiT K3 Boards & SiFive 2U Servers

* **SpacemiT K3 Fleet at OSU-OSL (7 boards on hand):**
  * **Inventory & RAM Sizing Policy:** **5× 16 GB SpacemiT K3** boards (in enclosures) + **2× 32 GB Firefly/SpacemiT K3** boards (uncased) are physically on hand at OSU-OSL. *(8 GB K3 boards were ruled out because 8 GB cannot compile large C++ workloads without heavy swap wear; 16 GB is the minimum for general workloads and 32 GB is preferred for 8-core developer/CI nodes.)*
  * **Hardware & Firmware Characteristics:** Powered via 2-pin ATX 12V or USB-PD (~18–35W per board under load, meaning a 10-board K3 shelf exceeds a single 350W `LRS-350-12` PSU); requires Copilot + Relay Hat DFU/fastboot actuation from day 1 (`threexc/boardgarden` [k3-fastboot-setup.md](https://github.com/threexc/boardgarden/blob/main/docs/k3-fastboot-setup.md)). Work is also underway on an **EFI firmware fix for K3** (`2026-11-12`) so software `reboot` commands cleanly reset the board without requiring a physical power cycle.
  * **Two-Phase Rollout Plan (`2026-11-12`):**
    * **Phase 1 (First Half of December 2026):** Bring up **1× 32 GB and 1–2× 16 GB K3 boards** at the bench with SSH and serial console access over OSU-OSL's VPN (matching the bench A210 setup), plus a thermocouple load test on a cased unit to check whether all 7 boards should be decased onto an open carrier shelf.
    * **Phase 2 (Q1 2027):** Assemble a dedicated open K3 shelf under Labgrid with BayLibre Copilot DFU automation using the incoming early-2027 student worker.
  * **Additional K3 Procurement:** Community-wide K3 shortages continue; CoM260 stock was identified on the Banana Pi store (`2026-11-11`) for potential expansion.
* **SiFive Big Sky 2U Servers, Global Hosting & Long-Term Exporter Reuse:**
  * **SiFive 2U Servers:** Planning data-center racking and 2027 hosting at OSU-OSL for 2U SiFive server-class machines (`DC-1`).
  * **Global Hosting Sites:** Physical hardware co-location spans **OSU-OSL** (NORAM/USA), **Scaleway** (EMEA/France), and **SOPIC / ISCAS** (APAC/China) *(hosting agreements, Strategic Member terms, and budget details are tracked in `RISE Governing Board, Budgets, Contracts & Strategic Hosting (Confidential)`)*.
  * **Long-Term A210 Reuse as Labgrid Exporters:** As newer RVA23 boards populate the farm, non-RVA23 Zhihe A210 boards can also be repurposed as dedicated Labgrid Exporter / management controllers and RISC-V runner hosts.

---

## 3. Lab Host, Network & Control-Plane Architecture

Full specification and diagrams: [`docs/architecture-design/tftp-boot-gha-and-flashing-design.md`](../architecture-design/tftp-boot-gha-and-flashing-design.md) and [`docs/architecture-design/build-centric-tftp-and-release-lifecycle.md`](../architecture-design/build-centric-tftp-and-release-lifecycle.md).

### 3.1 Three-Tier x86 Host Topology at OSU-OSL

To isolate public CI runner workloads from lab infrastructure services and stay within the 5-meter passive USB 2.0 cable limit per rack, the OSU-OSL host architecture is split into three tiers:

| Tier | Host / Role | Current State (`2026-11`) | Target Production State (`Q4 2026 / Q1 2027`) | Management & Ownership |
| :--- | :--- | :--- | :--- | :--- |
| **Tier 1: Control Node & Jumpbox** | Labgrid Coordinator (`:20408`), DHCP, TFTP (`/var/lib/tftpboot`), Apache HTTP (`/var/www/html/a210`) | OSU-OSL Labgrid Controller Host (AlmaLinux 10.2) | Allocated 1U OSU-OSL Data Center Server | **OSU-OSL** via Chef (`osl-labgrid`, `osl-netboot`, `osl-apache`, `proj-rise`) |
| **Tier 2: Labgrid Exporters** | `labgrid-exporter` + `ser2net` physically wired via USB 2.0 (`<= 5m`) to shelf USB hubs | Co-located on controller host (`labgrid-26.0-1.el10` RPM) | **~4× Rackable 1U Dell x86 Exporters** (1 per 2–3 shelves across A210 & K3 racks) | Tracked under `CTRL-2`; exporter OS ownership (OSL Chef vs. RISE) being finalized |
| **Tier 3: GitHub Actions Runner Host** | Containerized self-hosted GHA runners (`gha-runner-meta-riscv`, Android org runner) & `board-farm-hub` | Co-located on controller host (3 Docker runners + `/opt/board-farm-hub` on `:8080`) | **1× Dedicated Rackable x86 Server** (16–32 cores, 64 GB RAM, NVMe; no public IP required) | **RISE / OSU-OSL** (2-pass Chef adoption agreed `2026-11-05`) |

### 3.2 Two-Pass Chef Configuration Management (`osl-labgrid` + `proj-rise`)

Agreed between RISE and OSU-OSL (`2026-11-05` / `2026-11-09`):
1. **Pass 1 (In Progress):** OSU-OSL adopts `labgrid-coordinator` and `labgrid-exporter` on the controller host into Chef **unchanged** using two cookbooks:
   * **`osl-labgrid`:** Generic AlmaLinux 10 RPM installation (`labgrid-26.0-1.el10` + `ser2net` from OSL's internal yum repo, no `pip`/`venv`), systemd units, and `0660` `dialout` group udev rules for `/dev/ttyUSB*`.
   * **`proj-rise`:** Deploys `/etc/labgrid/exporter.yaml` directly from **this GitHub repository (`riseproject-dev/developer-cloud`)** as the single source of truth. RISE Board Farm maintainers receive contributor access to `proj-rise` on `git.osuosl.org`.
2. **Pass 2:** Adopt the containerized GitHub Actions runners and `board-farm-hub` telemetry service once Pass 1 and the dedicated runner host (`CTRL-2`) are in place.
3. **Version Lockstep Rule (Decided `2026-11-11`):** `labgrid-client` (on the GHA runners), `labgrid-exporter`, and `labgrid-coordinator` must be upgraded together in lockstep (especially when upgrading to upstream Labgrid `master` for `ADBDriver` support).

---

## 4. Electrical, Mechanical & Per-Board Interface Summary

This table summarizes the physical and electrical interfaces for each board shelf so engineers, student workers, and AI assistants can verify wiring without digging through multiple CAD/OpenSCAD files:

| Subsystem | Specification / Component | Details & Safety Rules | Primary OSU-OSL Reference |
| :--- | :--- | :--- | :--- |
| **Shelf AC Input & PSU** | **1× Mean Well LRS-350-12** (12V DC, 29A, 348W) fed via **Qualtek 703W** IEC C14 inlet | • **Bench (Office):** Selector switch at **`115V`** (120V AC 5-15R).<br>• **Data Center (208V PDU):** Selector switch **MUST** be moved to **`230V`** and photographed before connecting to 208V C13 PDU outlets.<br>• **Earth Bond:** 12 AWG green protective earth (`W3b`) bonds powder-coated steel tray to PSU Pin 3. | [`SHELF-POWER.md`](https://git.osuosl.org/osuosl/a210-linux/-/blob/main/docs/SHELF-POWER.md)<br>[`SHELF-INSTALL-MANUAL.md`](https://git.osuosl.org/osuosl/a210-linux/-/blob/main/docs/SHELF-INSTALL-MANUAL.md) |
| **DC Fuse Distribution** | **Blue Sea 5026** 12-circuit ST-Blade fuse block + **Printed Fuse Plate (`P9 v2`)** | • **Per-Board Branches (`B1`–`B10`):** 10× **3A** automotive blade fuses (`Littelfuse 0287003`).<br>• **Gear Branches:** Inline fused taps off PSU terminals (`1A` for relays, `3A` for switch/hub, `5A` unswitched branch for fans). | [`SHELF-WIRING.md`](https://git.osuosl.org/osuosl/a210-linux/-/blob/main/docs/SHELF-WIRING.md)<br>[`shelf-harness-power.svg`](https://git.osuosl.org/osuosl/a210-linux/-/blob/main/hardware/electrical/shelf-harness-power.svg) |
| **Per-Board Power Relay (Shelf 1)** | **2× Devantech ETH008-B** (8-channel Ethernet relays; 5 boards per relay) | • **`RELAY-B` (`<shelf-eth008-relay-b>`):** Controls front rank `B1`–`B5` (`index: 1..5`).<br>• **`RELAY-A` (`<shelf-eth008-relay-a>`):** Controls rear rank `B6`–`B10` (`index: 1..5`).<br>• **Labgrid Driver:** Stock `eth008` `NetworkPowerDriver`.<br>• **A210 Barrel Plug:** **5.5 mm OD × 2.5 mm ID** center-positive (`Tensility 053-0185R` 18 AWG pigtail) — *not* 5.5×2.1 mm. | [`POWER-ACTUATION.md`](https://git.osuosl.org/osuosl/a210-linux/-/blob/main/docs/POWER-ACTUATION.md)<br>[`SHELF-WIRING-RUNBOOK.md`](https://git.osuosl.org/osuosl/a210-linux/-/blob/main/docs/SHELF-WIRING-RUNBOOK.md) |
| **In-Shelf Ethernet Switch** | **1× MikroTik CRS326-24G-2S+IN** (RouterOS) | Mounted on gear deck; powered from 12V PSU via 3A inline fuse (`5.5×2.1mm` right-angle plug). Consolidates 10× board GbE + 2× `ETH008-B` relay ports into a single SFP+ / RJ45 rack uplink. | [`GEAR-ZONE-HARDWARE.md`](https://git.osuosl.org/osuosl/a210-linux/-/blob/main/docs/GEAR-ZONE-HARDWARE.md) |
| **Cooling & Airflow** | **6× Sunon PF80251V1-1000U-A99** (80×80×25 mm 12V DC fans, 3.72W each) | Mounted in 2× 3D-printed 3-fan shroud walls; wired via **WAGO 221-415** lever-nuts on an unswitched 5A fused 12V bus (always on whenever shelf is energized). | [`CARRIER-COUPON-RUNBOOK.md`](https://git.osuosl.org/osuosl/a210-linux/-/blob/main/docs/CARRIER-COUPON-RUNBOOK.md) |
| **UART Serial Console** | **Adafruit #70** (FTDI `TTL-232R-3V3`) spliced to **4-pin JST-XH (2.5 mm)** female socket | • **A210 Debug UART Header Pinout:**<br>  - `Pin 1 (NC)`: Leave empty (**NEVER** connect FTDI Red +5V; cap Red/Brown/Green with heat-shrink).<br>  - `Pin 2 (Board TX)` ← **FTDI Yellow (`RXD`)**<br>  - `Pin 3 (Board RX)` ← **FTDI Orange (`TXD`)**<br>  - `Pin 4 (GND)` ← **FTDI Black (`GND`)**<br>• **USB Hub:** **CoolGear CG-10U2AML** 10-port industrial screw-lock USB 2.0 hub in shelf → single USB 2.0 uplink (`<= 5m`) to Exporter. Matched in Labgrid by unique FTDI `ID_SERIAL_SHORT` (shelf) or USB `ID_PATH` (bench). | [`CONSOLE-CABLE.md`](https://git.osuosl.org/osuosl/a210-linux/-/blob/main/docs/CONSOLE-CABLE.md)<br>[`REFERENCE.md`](https://git.osuosl.org/osuosl/a210-linux/-/blob/main/docs/REFERENCE.md) |
| **MAC Address Scheme & Partition Layout** | Deterministic MAC `48:da:00:00:BB:0P` + 4-partition eMMC GPT | • **MAC:** `BB` = hex board ID (`01`–`0a`), `P` = port (`0`=`eth0`, `1`=`eth1`), stored in U-Boot `fnv`.<br>• **Debian eMMC GPT:** Partition 1 `factory` + Partition 2 `uboot_env` preserved verbatim; Partition 3 `boot` (256 MiB ext4); Partition 4 `rootfs` (remaining ~58 GiB ext4).<br>• **M.2 & Mini-PCIe Storage:** M.2 slot is **B-Key SATA only (2242 length)** — does *not* support NVMe; mini-PCIe is also unused for NVMe because PCIe is not enabled in the current A210 kernel config. | [`MAC_SCHEME.md`](https://git.osuosl.org/osuosl/a210-linux/-/blob/main/docs/MAC_SCHEME.md)<br>[`PARTITIONS.md`](https://git.osuosl.org/osuosl/a210-linux/-/blob/main/docs/PARTITIONS.md) |

---

## 5. Active CI Workloads, Software Stack & Kernel Upstreaming

### 5.1 Upstream Yocto Hardware CI (`riscv/meta-riscv` → `pool=a210-yocto`) & Yocto `AutoBuilder`
* **Merged Upstream PRs & `meta-riscv` Alignment:**
  * [`riscv/meta-riscv#724`](https://github.com/riscv/meta-riscv/pull/724): Added `zhihe-a210` machine BSP configuration.
  * [`riscv/meta-riscv#744`](https://github.com/riscv/meta-riscv/pull/744), [`#746`](https://github.com/riscv/meta-riscv/pull/746), [`#748`](https://github.com/riscv/meta-riscv/pull/748): Pointed kernel recipe to [`riseproject-dev/linux`](https://github.com/riseproject-dev/linux) (`v7.2.12-a210`) and enabled the automated OSU-OSL Labgrid hardware netboot workflow ([`test-zhihe-a210.yml`](https://github.com/riscv/meta-riscv/actions/workflows/test-zhihe-a210.yml)).
  * **Mainline Kernel Policy & RVA20/22/23 Tunes:** `meta-riscv` is officially mirrored on `git.yoctoproject.org` and deprecated legacy vendor-kernel boards (`VisionFive`, `Star64`, `Nezha D1`) to enforce mainline kernel support (`Zhihe A210` on `7.2.12`, `SpacemiT K3 Pico-ITX` on `7.3.1`, and `SiFive Premier P550`). `openembedded-core` merged the `riscv64gc` default and `riscv64gcv` vector tunes, with standardized `RVA20`, `RVA22`, and `RVA23` profile tunes under test across `meta-riscv` boards.
* **Execution Flow (`meta-riscv` Hardware CI):**
  * Runs nightly (`cron: 30 4 * * *` UTC) and on `zhihe-a210` BSP PRs.
  * Reserves a board from `pool=a210-yocto` via `gha-runner-meta-riscv`, stages the built `Image`, `a210-dev.dtb`, and `core-image-minimal.cpio.gz` into `/var/lib/tftpboot/yocto-ci/<board>/`, drives U-Boot over serial to TFTP-boot into RAM (leaving eMMC untouched), and runs [`boards/zhihe-a210/pytest/test_yocto_netboot.py`](../../boards/zhihe-a210/pytest/test_yocto_netboot.py) over the serial console.
  * **Security Decision (`2026-11-11`):** Dropbear SSH is intentionally omitted from Yocto test images; all verification runs strictly over serial console via Labgrid.
* **Two Distinct Yocto Infrastructure Tracks:**
  1. **`meta-riscv` BSP CI (Dedicated x86 Builder + OSU-OSL Board Farm + `resulttool`):** Reprovisioning Hetzner `CCX63` server `rise-python-ci-1.di.riseproject.dev` (48 vCPU, 192 GB RAM, 960 GB NVMe) as a dedicated Yocto x86 builder with persistent `sstate-cache` and `downloads` directories (reducing `meta-riscv` build times from ~2–7 hours to minutes), paired with physical hardware boot testing on OSU-OSL `A210` and `K3` boards. Yocto's **`resulttool`** was also patched so test results from the RISE Board Farm can be fed back into the upstream Yocto `AutoBuilder`.
  2. **Official Yocto Project `AutoBuilder` (`openembedded-core`):** Yocto added **2 `meta-riscv` BSPs (`SpacemiT K3 Pico-ITX` and `Milk-V Duo`)** to be built on the upstream `AutoBuilder`, and an upstream QEMU RISC-V TLB-flush optimization sped up `qemuriscv64` TCG `ptest` runs by **30–40%** (`coreutils` +38%). To eliminate remaining software-emulation timeouts, KVM-accelerated `ptest` runs are being benchmarked on a `K3 Pico-ITX` to scope a **dedicated RVA23 server** for the official Yocto `AutoBuilder`.

### 5.2 Android 17 (AOSP) CI (`riseproject-dev/android_*` → `pool=a210-android`)
* **Release & Boot Verification:** Android 17 release ([`android-17-v1.0`](https://github.com/riseproject-dev/android_manifest/releases/tag/android-17-v1.0), including `u-boot v2024.10-a210` and `opensbi v1.5-a210` with `Zicbom`/`Zicboz` & `STCE` fixes) is published under `riseproject-dev` and verified booting to `sys.boot_completed=1` on `a210-1`.
* **Telemetry & Runner Integration:**
  * [`hub/app/telemetry.py`](../../hub/app/telemetry.py) automatically detects Android boards and collects telemetry via ADB or UART serial fallback.
  * Organization-level GitHub Actions runner registration under `riseproject-dev` (scoped to the Android repositories) was approved on `2026-11-11`.

### 5.3 Zhihe A210 Mainline Linux Kernel Upstreaming
* **Current Farm Kernel:** Standardized on [`riseproject-dev/linux`](https://github.com/riseproject-dev/linux) tag **`v7.2.12-a210`** (rebased by OSU-OSL from `7.2.8` with the OpenSBI 2 MB `/reserved-memory` `no-map` DTB fix merged on `2026-10-23`).
* **Mainline LKML Progress (Alibaba / ISCAS):** Following the RVCK 6.6 merges, Han Gao and Zhiguo Zhu posted the mainline LKML v3 series on `2026-11-03` ([`20261103-a210-scmi-v3`](https://patch.msgid.link/20261103-a210-scmi-v3-0-ee6b31580808@iscas.ac.cn)) and split out the A210 pinctrl series on `2026-11-07` (under review by Conor Dooley).

---

## 6. Guide to OSU-OSL (`osuosl/a210-linux`) Docs & Known Caveats

When clicking into OSU-OSL's GitLab repository ([`https://git.osuosl.org/osuosl/a210-linux`](https://git.osuosl.org/osuosl/a210-linux)), use the table below to jump directly to the authoritative files while keeping these known caveats in mind:

| OSU-OSL Document | Direct Link | What It Covers & Known Caveats / Corrections |
| :--- | :--- | :--- |
| **Master Task Plan** | [`TODO.md`](https://git.osuosl.org/osuosl/a210-linux/-/blob/main/TODO.md) | Comprehensive task ledger (`T0`–`T8`, `HW-1`–`HW-5`, `CTRL-0`–`CTRL-2`, `CI-1`, `K3-1`, `DC-1`). **Current and actively updated**, though older task headers retain historical June–August notes above the `2026-11` status lines. |
| **Weekly OSL Status Reports** | [`docs/status/`](https://git.osuosl.org/osuosl/a210-linux/-/tree/main/docs/status) | Weekly written updates from OSU-OSL (`STATUS-2026-05-29.md` through [`STATUS-2026-11-11.md`](https://git.osuosl.org/osuosl/a210-linux/-/blob/main/docs/status/STATUS-2026-11-11.md)). See [`2026_weekly_progress.md`](2026_weekly_progress.md) for our synthesized summary combining OSL + RISE CI updates. |
| **Shelf 1 Installation Manual** | [`docs/SHELF-INSTALL-MANUAL.md`](https://git.osuosl.org/osuosl/a210-linux/-/blob/main/docs/SHELF-INSTALL-MANUAL.md) | **Authoritative** 14-stage, 121-step build-order manual generated from the 3D CAD model (supersedes the older section-ordered [`SHELF-WIRING-RUNBOOK.md`](https://git.osuosl.org/osuosl/a210-linux/-/blob/main/docs/SHELF-WIRING-RUNBOOK.md) for Milestone 1 up to `B1`). |
| **Shelf Power & BOM** | [`docs/SHELF-POWER.md`](https://git.osuosl.org/osuosl/a210-linux/-/blob/main/docs/SHELF-POWER.md) | Full electrical design, fuse sizing, `LRS-350-12` wiring schedule, and BOM. *Caveat:* Early sections still mention "120V only"; for the data center (`208V`), the PSU selector must be switched to `230V`. |
| **UART Console Cable Guide** | [`docs/CONSOLE-CABLE.md`](https://git.osuosl.org/osuosl/a210-linux/-/blob/main/docs/CONSOLE-CABLE.md) | Step-by-step splicing guide for Adafruit #70 FTDI USB-TTL cables to 4-pin JST-XH (`2.5 mm`) sockets. |
| **RISE CI Design Draft** | [`docs/RISE-CI.md`](https://git.osuosl.org/osuosl/a210-linux/-/blob/main/docs/RISE-CI.md) | `2026-11-05` summary of Phase 1 CI pools and open questions for RISE (see Section 3 & Section 5 above for the settled answers from the `2026-11-11` sync). |
| **Labgrid & Chef Handoff** | [`docs/LABGRID.md`](https://git.osuosl.org/osuosl/a210-linux/-/blob/main/docs/LABGRID.md)<br>[`docs/LABGRID-CHEF-HANDOFF.md`](https://git.osuosl.org/osuosl/a210-linux/-/blob/main/docs/LABGRID-CHEF-HANDOFF.md) | Documents the OSU-OSL Labgrid controller host (AlmaLinux 10.2) and the `osl-labgrid` + `proj-rise` Chef cookbooks. *Caveat:* Sections written in June 2026 refer to AlmaLinux 9 and an OSL GitLab artifact pull pipeline; read the `2026-11-05` callout boxes at the top of each section. |
| **RISE Alignment Matrix** | [`docs/RISE-ALIGNMENT.md`](https://git.osuosl.org/osuosl/a210-linux/-/blob/main/docs/RISE-ALIGNMENT.md) | Cross-references OSL's build against RISE architecture docs. *Caveat:* Its `2026-11-05` update correctly notes that Shelf 2 reverses the older [`docs/REMOTE-FLASHING.md`](https://git.osuosl.org/osuosl/a210-linux/-/blob/main/docs/REMOTE-FLASHING.md) "no remote button actuation" stance by adopting BayLibre Copilot + Relay Hat. |
| **Debian Provisioning & Partitions** | [`docs/PROVISION_RUNBOOK.md`](https://git.osuosl.org/osuosl/a210-linux/-/blob/main/docs/PROVISION_RUNBOOK.md)<br>[`docs/PARTITIONS.md`](https://git.osuosl.org/osuosl/a210-linux/-/blob/main/docs/PARTITIONS.md) | Per-board Debian 13 (Trixie) HTTP initramfs installer (`install_url=http://<tftp-http-server>/a210/`), `SHA256SUMS` verification, and 4-partition eMMC GPT layout. |
