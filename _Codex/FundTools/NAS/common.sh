#!/bin/sh
# Shared defaults. FUND_* variables may override these in DSM Task Scheduler.
set -eu

PROJECT=${FUND_PROJECT:-/volume1/web_packages/docker/fund-report}
PUBLIC=${FUND_PUBLIC:-/volume1/web/fund-report}
DOCKER=${FUND_DOCKER:-/usr/local/bin/docker}
IMAGE=${FUND_IMAGE:-python:3.12-slim}
MEMORY=${FUND_MEMORY:-256m}
# Some Synology kernels cannot enforce Docker NanoCPU/CFS limits.
# Leave unset by default; opt in only on hosts that support --cpus.
CPUS=${FUND_CPUS:-}
set --
if [ -n "$CPUS" ]; then
    set -- --cpus "$CPUS"
fi

if [ ! -x "$DOCKER" ]; then
    echo "Docker executable not found: $DOCKER" >&2
    exit 1
fi
if [ ! -d "$PROJECT/FundTools" ]; then
    echo "Missing deployed scripts: $PROJECT/FundTools" >&2
    exit 1
fi
# Require the image downloaded in Container Manager; do not pull during a task.
"$DOCKER" image inspect "$IMAGE" >/dev/null
