#!/bin/sh
# Offline tests: no provider requests, real workbook writes or publication.
set -eu

# Capture prerequisite failures as well as test output, before loading common.sh.
PROJECT=${FUND_PROJECT:-/volume1/web_packages/docker/fund-report}
mkdir -p "$PROJECT/logs"
LOG=$(mktemp "$PROJECT/logs/verify-$(date +%Y%m%d-%H%M%S)-XXXXXX.log")
echo "Verification log: $LOG"
exec 3>&1 4>&2
exec >"$LOG" 2>&1
trap 'status=$?; trap - 0; exec 1>&3 2>&4; cat "$LOG"; exit "$status"' 0
echo "Verification started: $(date)"
. "$(dirname "$0")/common.sh"

"$DOCKER" run --rm \
    --name fund-report-verify \
    --network none --read-only \
    --tmpfs /tmp:rw,nosuid,size=64m \
    --memory="$MEMORY" --memory-swap="$MEMORY" "$@" \
    --user "$(id -u):$(id -g)" \
    --env DATA_PATH=/app/Data --env TZ=Europe/Berlin \
    --volume "$PROJECT:/app:ro" --workdir /app "$IMAGE" \
    python -B -m unittest discover -s FundTools/tests -v
echo "Verification completed successfully: $(date)"
