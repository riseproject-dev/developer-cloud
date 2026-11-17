# Developer Cloud Hardware Runner (`Developer-Cloud-HW`)

Containerized GitHub Actions self-hosted runner setup for executing lightweight hardware orchestration jobs (`labgrid-client`, TFTP staging, fastboot/ADB checks, and pytest suites) against RISC-V Developer Cloud board farms without performing heavy compilation on lab gateway hosts.

## Naming & Concurrency (`<site>-hw-<index>`)

Runner names follow `<site>-hw-<index>` (for example `osuosl-hw-0`, `osuosl-hw-1`, `sopic-hw-0`):

* **`<site>`** (`osuosl`, `sopic`, `scaleway`): Identifies which physical lab hosts the runner container.
* **`hw`**: Distinguishes lightweight lab hardware-orchestration runners from cloud compile runners (such as `rise-aosp-builder-0`).
* **`<index>`** (`0`, `1`, ...): 0-based worker listener index on that host (not a board ID). Because a single GitHub Actions `Runner.Listener` process executes **one job at a time**, running multiple worker containers (`0`, `1`, ...) allows independent board pools (for example `pool=a210-aosp` on `a210-board-01` and `pool=a210-yocto` on `a210-board-03`) to run hardware tests in parallel.

All runners register into the `riseproject-dev` **`Developer-Cloud-HW`** organization runner group with `--no-default-labels` so generic `runs-on: self-hosted` workflows never land on lab hosts unintentionally.

## Quick Start

### 1. Optional Site Configuration (`/etc/default/gha-runner-devcloud-hw`)

Override defaults per lab host if needed:

```bash
RUNNER_GROUP="Developer-Cloud-HW"
RUNNER_PREFIX="osuosl-hw"
RUNNER_LABELS="a210-aosp,a210-yocto,board-farm-controller,osuosl"
LG_COORDINATOR="127.0.0.1:20408"
TFTP_ROOT="/var/lib/tftpboot"
```

### 2. Register Worker Instance(s)

Generate a 1-hour organization runner registration token from `https://github.com/organizations/riseproject-dev/settings/actions/runners/new` and run:

```bash
# Register worker 0 (osuosl-hw-0)
sudo ./runner/register-devcloud-hw-runner.sh "<ORG_REGISTRATION_TOKEN>" 0

# Optional: register a second parallel worker (osuosl-hw-1) with the same 1-hour token
sudo ./runner/register-devcloud-hw-runner.sh "<ORG_REGISTRATION_TOKEN>" 1
```

If the `gha-runner-devcloud-hw:base` Docker image is not present locally yet, the script builds [`runner/Dockerfile`](Dockerfile) automatically.

### 3. Token-Free Restart & Credential Protection

Registration stores the runner's RSA credentials in `/opt/gha-runner-devcloud-hw-<index>-state/` and locks a read-only copy under `immutable-backup/` with `chattr +i` (`.runner`, `.credentials`, `.credentials_rsaparams`).

To start or recreate a stopped/removed runner container after a host reboot or image rebuild **without** needing a new GitHub registration token:

```bash
sudo ./runner/ensure-devcloud-hw-runner.sh 0
```

Never run `./config.sh remove` inside a registered container unless intentionally decommissioning that runner identity.

### 4. Optional `systemd` Boot Integration

```bash
sudo mkdir -p /opt/developer-cloud
sudo cp -r runner /opt/developer-cloud/
sudo cp runner/gha-runner-devcloud-hw@.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now gha-runner-devcloud-hw@0
```
