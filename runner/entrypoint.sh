#!/usr/bin/env bash
set -euo pipefail

export RUNNER_ALLOW_RUNASROOT=1
export PATH="/opt/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

if [ -f /root/.ssh/id_ed25519 ] && [ -n "${LAB_SSH_HOST_PATTERN:-}" ]; then
  mkdir -p /etc/ssh/ssh_config.d
  cat <<SSHCFG > /etc/ssh/ssh_config.d/labgrid.conf
Host ${LAB_SSH_HOST_PATTERN}
    StrictHostKeyChecking no
    UserKnownHostsFile /dev/null
    IdentityFile /root/.ssh/id_ed25519
SSHCFG
fi

if [ ! -s /runner/.runner ] || [ ! -s /runner/.credentials ]; then
  echo "ERROR: Runner credentials missing in /runner (.runner / .credentials)." >&2
  exit 1
fi

echo "[Developer-Cloud-HW Runner] Starting listener (LG_COORDINATOR=${LG_COORDINATOR:-127.0.0.1:20408})..."
exec /runner/run.sh
