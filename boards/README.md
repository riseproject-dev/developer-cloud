# Target Hardware Catalog

This directory contains onboarding requirements, board specifications, compliance checklists, and Labgrid hardware CI configurations for physical platforms integrated into the **RISC-V Developer Cloud**.

## Hardware Support Matrix

| Board Model | Vendor | Onboarding Track | Architecture | Active Stage | Documentation |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Zhihe A210** | Alibaba / Zhihe | Embedded / SBC (Labgrid) | RV64GCV (RVV 1.0) | Stage 1 (Isolated Bring-up Bench) | [zhihe-a210/README.md](zhihe-a210/README.md) |

### Column Definitions
* **Onboarding Track:** Long-term control-plane model defined in the onboarding policy (Embedded / SBC Track via Labgrid vs. Server Track via OpenStack Nova / Ironic).
* **Active Stage:** Lab Integration Stage (Stage 1 Isolated Bring-up Bench, Stage 2 Pilot Pool, Stage 3 Production Pool).

---

## Key Onboarding Policies

* **[compliance-requirements.md](compliance-requirements.md):** Target hardware onboarding tracks, Stage 1-3 operational and legal compliance gates, RISE source mirroring rules, binary blob sunset clauses, and upstreaming requirements.
