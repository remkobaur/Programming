# NAS deployment scripts

These files are copied by `release_to_nas.py` into the private project's `FundTools/NAS` folder. They use `/volume1/web_packages/docker/fund-report` for the project and `/volume1/web/fund-report` for published HTML. They do not configure DSM or Web Station.

Download `python:3.12-slim` in Container Manager first. Seed the existing portfolio workbook using the release script's `--include-input-data` option. Set `NAS_PUBLIC_PATH` in the local `.env` to the separate public share path (for example `\\NAS\web\fund-report`) so the release script creates that folder if missing; configure Web Station as described in [NAS setup](../../docs/nas-setup.md).

## Verify on the NAS

Run as a user allowed to use Docker, for example through a manually run DSM task:

```sh
/bin/sh /volume1/web_packages/docker/fund-report/FundTools/NAS/verify_runtime.sh
```

Tests run without network access, using temporary synthetic workbooks. The project is mounted read-only, and the publication folder is not mounted. This checks Linux execution and locking, but does not verify live providers, Web Station access or resource use with your real portfolio.

Each verification run saves prerequisite checks and test output to `logs/verify-*.log` in the private project folder and also sends the output to DSM. If no log appears, confirm the task actually ran, its command points to this script, and its user can write the logs folder; DSM must capture failures that occur before the script can create its log.

## Update and publish

Paste this into the DSM task's run command, and test manually before enabling its weekly schedule:

```sh
/bin/sh /volume1/web_packages/docker/fund-report/FundTools/NAS/run_update.sh
```

This refreshes the real workbook, generates and validates the report, and publishes both HTML filenames. Logs are saved under the private project's `logs` folder. Avoid manual editing, imports and code releases during updates.

## Optional overrides

The common defaults can be overridden by environment variables in the DSM run command. For example:

```sh
FUND_MEMORY=384m /bin/sh /volume1/web_packages/docker/fund-report/FundTools/NAS/run_update.sh
```

Available settings: `FUND_PROJECT`, `FUND_PUBLIC`, `FUND_DOCKER`, `FUND_IMAGE`, `FUND_MEMORY`, `FUND_CPUS`. The memory and memory-swap limits are always equal, disabling additional swap. The initial memory limit is 256 MiB; measure on the target NAS before adjusting. No hard CPU limit is used by default because some Synology kernels reject Docker NanoCPU/CFS limits. Set `FUND_CPUS=0.5` only on compatible hosts; leave it unset on this NAS.

`NAS_PROJECT_PATH` is a Windows-side release setting; it is not a Linux container path. Neither the local `.env` nor credentials are deployed. Scripts are invoked via `/bin/sh`, so executable permission is unnecessary. The release script normalizes deployed shell files to LF line endings.
