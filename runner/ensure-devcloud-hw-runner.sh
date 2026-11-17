#!/usr/bin/env bash
# Ensures a Developer-Cloud-HW GitHub Actions runner container is running using
# its permanent RSA credentials stored on the host (no registration token needed).
#
# Usage: sudo ./ensure-devcloud-hw-runner.sh [INDEX]
set -euo pipefail

ENV_FILE="${ENV_FILE:-/etc/default/gha-runner-devcloud-hw}"
if [ -f "${ENV_FILE}" ]; then
  # shellcheck disable=SC1090
  source "${ENV_FILE}"
fi

INDEX="${1:-0}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONTAINER_NAME="${CONTAINER_PREFIX:-gha-runner-devcloud-hw}-${INDEX}"
STATE_DIR="${STATE_BASE_DIR:-/opt/gha-runner-devcloud-hw}-${INDEX}-state"
IMAGE="${RUNNER_IMAGE:-gha-runner-devcloud-hw:base}"
TFTP_ROOT="${TFTP_ROOT:-/var/lib/tftpboot}"
LG_COORDINATOR="${LG_COORDINATOR:-127.0.0.1:20408}"
SSH_KEY_FILE="${SSH_KEY_FILE:-}"
LAB_SSH_HOST_PATTERN="${LAB_SSH_HOST_PATTERN:-}"

for f in .runner .credentials .credentials_rsaparams; do
  if [ ! -s "${STATE_DIR}/${f}" ]; then
    if [ -s "${STATE_DIR}/immutable-backup/${f}" ]; then
      cp -f "${STATE_DIR}/immutable-backup/${f}" "${STATE_DIR}/${f}"
      chmod 600 "${STATE_DIR}/${f}"
    else
      echo "ERROR: Missing ${STATE_DIR}/${f} and no immutable-backup found. Run register-devcloud-hw-runner.sh first." >&2
      exit 1
    fi
  fi
done

if ! docker image inspect "${IMAGE}" >/dev/null 2>&1; then
  echo "Building ${IMAGE} from ${SCRIPT_DIR}/Dockerfile..."
  docker build -t "${IMAGE}" "${SCRIPT_DIR}"
fi

if docker ps --format '{{.Names}}' | grep -qx "${CONTAINER_NAME}"; then
  echo "${CONTAINER_NAME} is already running."
  exit 0
fi

if docker ps -a --format '{{.Names}}' | grep -qx "${CONTAINER_NAME}"; then
  echo "Starting existing ${CONTAINER_NAME} container..."
  docker start "${CONTAINER_NAME}"
  exit 0
fi

EXTRA_ARGS=()
if [ -d /dev/serial ]; then
  EXTRA_ARGS+=(-v /dev/serial:/dev/serial:ro)
fi
if [ -n "${SSH_KEY_FILE}" ] && [ -f "${SSH_KEY_FILE}" ]; then
  EXTRA_ARGS+=(-v "${SSH_KEY_FILE}:/root/.ssh/id_ed25519:ro")
fi
if [ -n "${LAB_SSH_HOST_PATTERN}" ]; then
  EXTRA_ARGS+=(-e "LAB_SSH_HOST_PATTERN=${LAB_SSH_HOST_PATTERN}")
fi

mkdir -p "${TFTP_ROOT}/builds" "${TFTP_ROOT}/labels" "${TFTP_ROOT}/releases" "${TFTP_ROOT}/ci"

echo "Creating ${CONTAINER_NAME} container from ${IMAGE} and ${STATE_DIR}..."
docker run -d \
  --name "${CONTAINER_NAME}" \
  --restart unless-stopped \
  --network host \
  -v "${STATE_DIR}/.runner:/runner/.runner:rw" \
  -v "${STATE_DIR}/.credentials:/runner/.credentials:rw" \
  -v "${STATE_DIR}/.credentials_rsaparams:/runner/.credentials_rsaparams:rw" \
  -v "${TFTP_ROOT}/builds:/var/lib/tftpboot/builds:rw" \
  -v "${TFTP_ROOT}/labels:/var/lib/tftpboot/labels:rw" \
  -v "${TFTP_ROOT}/releases:/var/lib/tftpboot/releases:rw" \
  -v "${TFTP_ROOT}/ci:/var/lib/tftpboot/ci:rw" \
  "${EXTRA_ARGS[@]}" \
  -e "LG_COORDINATOR=${LG_COORDINATOR}" \
  "${IMAGE}"
