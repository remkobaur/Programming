#!/bin/sh
# DSM task command: /bin/sh /volume1/web_packages/docker/fund-report/FundTools/NAS/run_update.sh
set -eu
. "$(dirname "$0")/common.sh"

if [ ! -d "$PUBLIC" ]; then
    echo "Missing publication folder: $PUBLIC" >&2
    exit 1
fi
if [ ! -f "$PROJECT/Data/Input_Data/fund_manual_values.xlsx" ]; then
    echo "Missing portfolio workbook: $PROJECT/Data/Input_Data/fund_manual_values.xlsx" >&2
    exit 1
fi
mkdir -p "$PROJECT/logs"
LOG=$(mktemp "$PROJECT/logs/update-$(date +%Y%m%d-%H%M%S)-XXXXXX.log")
echo "Update log: $LOG"

"$DOCKER" run --rm \
    --name fund-report-update \
    --memory="$MEMORY" --memory-swap="$MEMORY" "$@" \
    --user "$(id -u):$(id -g)" \
    --env DATA_PATH=/app/Data --env TZ=Europe/Berlin \
    --volume "$PROJECT:/app" --volume "$PUBLIC:/published" \
    --workdir /app "$IMAGE" \
    python -B /app/FundTools/NAS/refresh_and_publish_fund_report.py \
    --publish-dir /published >"$LOG" 2>&1 || {
        cat "$LOG"
        exit 1
    }
cat "$LOG"
