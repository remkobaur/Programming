# Synology NAS setup: fund history report

This guide hosts the report on a Synology DS225+ using its LAN IP and a dedicated port. It uses Web Station for the static HTML, a temporary Python container for updates, and DSM Task Scheduler for a weekly run. No subdomain, DNS configuration, or reverse proxy is required.

Complete [the code changes](code-adjustments.md) before enabling scheduled updates. The core Python changes are now implemented; verify them locally and on the NAS before enabling scheduling.

## 1. Prepare DSM and folders

1. Install **Web Station** and **Container Manager** from Package Center. Install any dependencies requested by DSM. A static site does not need PHP or a database.
2. Reserve the NAS IP in your router, for example `192.168.1.50`.
3. Create these folders using File Station. Replace `volume1` throughout this guide if your shares are on another volume.

```text
/volume1/docker/fund-report/
    FundTools/                  Python scripts
    Data/
        Input_Data/             fund_manual_values.xlsx and optional imports
        Web_Report/             private generated report and cache
    logs/
/volume1/web/fund-report/        published HTML only
```

Copy your `FundTools` folder and `Data/Input_Data` into the private project folder. Keep the existing workbook: an empty replacement will not contain your portfolio. Copy optional symbol override CSV files if you use them.

Do not publish the project directory, workbook, cache, logs, backups, or `.env` through Web Station. Do not copy a Windows `.env` unchanged: Windows paths do not work inside the Linux container. The command below supplies `DATA_PATH` explicitly. Add any desired date filters explicitly as container environment variables, and review fixed end dates so future updates are not hidden.

## 2. Configure Web Station

DSM labels can vary by package version.

1. Open **Web Station > Web Service** and create a **static website**.
2. Set its document root to `/volume1/web/fund-report` and use the available static HTTP backend.
3. Give Web Station's service account (normally the internal `http` group) read/traverse permission on this folder. It does not need write access.
4. In **Web Portal**, create a **port-based** portal for this service.
5. Choose an unused HTTP port, for example `8088`. Do not reuse DSM's administration ports.
6. Copy the existing `Data/Web_Report/fund_history_report.html` to the document root as `index.html` for the first test.

Open:

```text
http://192.168.1.50:8088/
```

The update job below publishes both `index.html` and `fund_history_report.html`, so either URL works.

## 3. Limit access to the LAN

- In **Control Panel > Security > Firewall**, allow the selected TCP port from your actual LAN subnet, for example `192.168.1.0/24`, and deny it from other sources. Rule ordering matters; retain the rules needed to administer DSM.
- Do not configure router port forwarding for the report. Remove any existing forwarding that exposes this service.
- Anyone who can reach this static service can read the report. DSM account login does not automatically protect it.
- HTTP is suitable only if you accept unencrypted access within your trusted LAN. If encryption is required, configure an HTTPS portal and a certificate trusted by your clients for the chosen IP address.

## 4. Prepare the Python image

In Container Manager, download `python:3.12-slim` from the registry before the first run. The scripts use the standard library, so no pip installation is needed. They require Python 3.11 or newer because the updater uses `datetime.UTC`.

The container requires outbound DNS and HTTPS access to the configured price providers. It needs no inbound port mapping: Web Station serves the finished report.

### Running with 2 GB RAM

This workload should be workable with 2 GB RAM, depending on the NAS's other services. The scripts' peak memory usage has not been measured. The Python container runs only during an update and exits afterward; Web Station continues serving the static HTML, and charts render in the visitor's browser. Container Manager itself adds some ongoing background overhead.

The command below starts with a **256 MiB memory limit**, **no additional container swap**, and **half a CPU core**. These are initial limits to validate, not measured requirements. They apply to the update container, including its child processes, rather than to Web Station or Container Manager. The CPU limit may make updates take longer.

During the first manual run, watch **DSM Resource Monitor** for RAM use, swap activity, and NAS responsiveness. If the container exceeds its memory limit, it may be killed and the update will fail. Check the logs and memory usage before increasing the limit, for example to `384m` or `512m`; increase both `--memory` and `--memory-swap` to the same value to keep additional container swap disabled. An exit status of 137 can indicate a killed process, but does not by itself prove an out-of-memory condition.

Schedule updates outside backups, indexing, and media processing. A RAM upgrade is not a prerequisite for this report; measure first. If the NAS is already under memory pressure, an alternative is to generate the report on your PC and copy only the finished HTML to Web Station. Running directly on a suitable NAS Python installation also avoids Container Manager overhead, but requires managing that Python installation separately.

## 5. Create and test the update task

In **Control Panel > Task Scheduler > Create > Scheduled Task > User-defined script**, create a task named `Update fund report`.

The task needs permission to run Docker and write the project/publication folders. On a typical DSM installation, running this task as `root` is the straightforward option because Docker requires privileged access. The command below runs trusted local scripts and mounts only the project and publication directory. Do not mount the Docker socket inside the container.

Paste this script into **Task Settings > Run command**:

```sh
#!/bin/sh
set -eu

PROJECT=/volume1/docker/fund-report
PUBLIC=/volume1/web/fund-report
DOCKER=/usr/local/bin/docker

test -x "$DOCKER"
test -d "$PROJECT/FundTools"
test -d "$PUBLIC"
mkdir -p "$PROJECT/logs"
LOG="$PROJECT/logs/update-$(date +%Y%m%d-%H%M%S).log"

"$DOCKER" run --rm \
  --name fund-report-update \
  --memory=256m \
  --memory-swap=256m \
  --cpus=0.5 \
  --user "$(id -u):$(id -g)" \
  --env DATA_PATH=/app/Data \
  --env TZ=Europe/Berlin \
  --volume "$PROJECT:/app" \
  --volume "$PUBLIC:/published" \
  --workdir /app \
  python:3.12-slim \
  python /app/FundTools/update_fund_report.py \
    --publish-dir /published >"$LOG" 2>&1 || {
      cat "$LOG"
      exit 1
    }

cat "$LOG"
```

`update_fund_report.py` is the new orchestrator described in [code-adjustments.md](code-adjustments.md). Validate it with your workbook before using this task. `TZ` requests the local timezone; verify logged timestamps in the selected image, as timezone data availability can affect the result. Scheduling itself uses DSM's timezone.

Check the Docker executable location on your NAS if the initial `test -x` fails; adjust `DOCKER` to the installed path. Do not change DSM-managed system files.

The fixed container name prevents two copies of this scheduled container from running simultaneously. Do not delete an existing named container to bypass a conflict until you have checked whether an update is still running. The Python lock described in the code guide also protects against other orchestrator invocations.

Run the task manually once. Verify:

- The task exits successfully and the log lists refreshed prices.
- The workbook still contains your manual portfolio data.
- The report is accessible at `http://192.168.1.50:8088/`.
- A browser reload shows the new generation time and expected latest quote dates.
- The public directory contains only the intended HTML files.
- Resource Monitor shows acceptable RAM use, swap activity, and responsiveness during the update; the configured memory limit is sufficient for the real workbook.

If the container runs as a non-root user, give that numeric UID/GID write access to the mounted private folders and publication folder. Ensure published HTML is readable by Web Station regardless of who generated it.

## 6. Enable weekly scheduling

Set the task to run weekly, for example Sunday at 06:00. Check DSM's timezone and configure task output/failure notifications if DSM notifications are available.

The NAS must be awake and connected to the internet at the scheduled time. Account for any NAS shutdown schedule. A failed update should leave the previous published report in place; review the failure log rather than assuming its displayed prices are current.

Keep workbook backups using the code workflow and/or Synology backup facilities. Review log and backup retention periodically. Avoid editing or synchronizing the workbook while an update is running; import new transactions separately when needed. Weekly price updates do not automatically discover purchases or new DKB exports.

## Troubleshooting

| Symptom | Check |
| --- | --- |
| Connection refused | Portal enabled, correct NAS IP/port, firewall, unused port |
| 403 or missing page | Document root, `index.html`, Web Station read/traverse permissions |
| Old prices after success | `--refresh`, quote dates, provider errors, fixed date filters, browser cache |
| Container fails immediately | Image downloaded, Docker path, mounts, Python changes implemented |
| Container is killed during an update | Logs, memory usage and configured memory limit; verify whether it ran out of memory before raising the limit |
| NAS becomes sluggish | Resource Monitor, swapping, overlapping backups/indexing, and container CPU/memory limits |
| Permission denied | Task user, numeric container UID/GID, share ACLs and file permissions |
| Provider failures | NAS DNS, clock, HTTPS access, provider availability or rate limits |

## References

- [Synology Container Manager compatibility](https://www.synology.com/en-in/dsm/packages/ContainerManager)
- [Synology static website setup](https://kb.synology.com/en-au/insights/Create_a_static_website)
- [Web Station portals](https://kb.synology.com/index.php/en-us/DSM/help/WebStation/application_webserv_virtualhost?version=7)
- [DSM Task Scheduler](https://kb.synology.com/index.php/en-ro/DSM/help/DSM/AdminCenter/system_taskscheduler?version=7)
- [Docker CPU, memory, and swap limits](https://docs.docker.com/engine/containers/resource_constraints)
