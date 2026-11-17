#!/usr/bin/env bash
# Registers a self-hosted GitHub Actions runner in the riseproject-dev
# Developer-Cloud-HW organization runner group, locks an immutable backup of its
# RSA credentials, and starts the container via ensure-devcloud-hw-runner.sh.
#
# Usage: sudo ./register-devcloud-hw-runner.sh <ORG_REGISTRATION_TOKEN> [INDEX] [--force-re-register]
set -euo pipefail

ENV_FILE="${ENV_FILE:-/etc/default/gha-runner-devcloud-hw}"
if [ -f "${ENV_FILE}" ]; then
  # shellcheck disable=SC1090
  source "${ENV_FILE}"
fi

TOKEN="${1:?Usage: $0 <ORG_REGISTRATION_TOKEN> [INDEX] [--force-re-register]}"
INDEX="${2:-0}"
FORCE="${3:-}"

GITHUB_ORG="${GITHUB_ORG:-riseproject-dev}"
RUNNER_GROUP="${RUNNER_GROUP:-Developer-Cloud-HW}"
RUNNER_PREFIX="${RUNNER_PREFIX:-osuosl-hw}"
RUNNER_NAME="${RUNNER_NAME:-${RUNNER_PREFIX}-${INDEX}}"
RUNNER_LABELS="${RUNNER_LABELS:-a210-aosp,a210-yocto,board-farm-controller,osuosl}"

CONTAINER_PREFIX="${CONTAINER_PREFIX:-gha-runner-devcloud-hw}"
STATE_DIR="${STATE_BASE_DIR:-/opt/gha-runner-devcloud-hw}-${INDEX}-state"
REG_CONTAINER="${CONTAINER_PREFIX}-${INDEX}-reg"
ACTIVE_CONTAINER="${CONTAINER_PREFIX}-${INDEX}"
IMAGE="${RUNNER_IMAGE:-gha-runner-devcloud-hw:base}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ -f "${STATE_DIR}/immutable-backup/.runner" ] && [ "${FORCE}" != "--force-re-register" ]; then
  echo "ABORT: ${RUNNER_NAME} is already registered (${STATE_DIR}/immutable-backup/.runner exists)." >&2
  echo "Use ${SCRIPT_DIR}/ensure-devcloud-hw-runner.sh ${INDEX} to start/restore it without a token, or pass --force-re-register." >&2
  exit 1
fi

if ! docker image inspect "${IMAGE}" >/dev/null 2>&1; then
  echo "Building ${IMAGE} from ${SCRIPT_DIR}/Dockerfile..."
  docker build -t "${IMAGE}" "${SCRIPT_DIR}"
fi

docker rm -f "${REG_CONTAINER}" 2>/dev/null || true
docker run -d --name "${REG_CONTAINER}" --network host --entrypoint sleep "${IMAGE}" 600

cleanup_reg() {
  docker rm -f "${REG_CONTAINER}" >/dev/null 2>&1 || true
}
trap cleanup_reg EXIT

docker exec \
  -e RUNNER_ALLOW_RUNASROOT=1 \
  -e REG_TOKEN="${TOKEN}" \
  -e REG_ORG="${GITHUB_ORG}" \
  -e REG_GROUP="${RUNNER_GROUP}" \
  -e REG_NAME="${RUNNER_NAME}" \
  -e REG_LABELS="${RUNNER_LABELS}" \
  "${REG_CONTAINER}" bash -c '
    set -euo pipefail
    cd /runner
    rm -f .runner .runner_migrated .credentials .credentials_rsaparams
    ./config.sh \
      --url "https://github.com/${REG_ORG}" \
      --token "${REG_TOKEN}" \
      --runnergroup "${REG_GROUP}" \
      --name "${REG_NAME}" \
      --no-default-labels \
      --labels "${REG_LABELS}" \
      --work "_work" \
      --unattended \
      --replace
    ls -la .runner .credentials .credentials_rsaparams
  '

mkdir -p "${STATE_DIR}/immutable-backup"
if [ "${FORCE}" = "--force-re-register" ]; then
  chattr -i "${STATE_DIR}/immutable-backup/.runner" \
            "${STATE_DIR}/immutable-backup/.credentials" \
            "${STATE_DIR}/immutable-backup/.credentials_rsaparams" 2>/dev/null || true
fi

for f in .runner .credentials .credentials_rsaparams; do
  docker cp "${REG_CONTAINER}:/runner/${f}" "${STATE_DIR}/${f}"
  chmod 600 "${STATE_DIR}/${f}"
  cp -f "${STATE_DIR}/${f}" "${STATE_DIR}/immutable-backup/${f}"
  chmod 400 "${STATE_DIR}/immutable-backup/${f}"
  chattr +i "${STATE_DIR}/immutable-backup/${f}"
done

docker rm -f "${REG_CONTAINER}"
trap - EXIT

docker rm -f "${ACTIVE_CONTAINER}" 2>/dev/null || true
"${SCRIPT_DIR}/ensure-devcloud-hw-runner.sh" "${INDEX}"

sleep 4
docker logs "${ACTIVE_CONTAINER}"
