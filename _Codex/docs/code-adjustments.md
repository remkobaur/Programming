# Unattended fund report updates

The NAS support described here is implemented. See [NAS setup](nas-setup.md) for deployment. Python 3.11+ is required; the scripts use only the standard library.

## Implemented workflow

Run from the repository root:

```sh
python FundTools/NAS/refresh_and_publish_fund_report.py --publish-dir /published
```

The orchestrator loads project environment settings, requires an existing nonempty portfolio workbook, and holds an exclusive persistent workbook lock throughout the operation. Locking uses Windows byte locking or Linux `fcntl.flock`; the lock file is not deleted on release.

Before refreshing, it backs up the workbook in its sibling `backups` directory and retains the newest 30 backups. It sequentially runs `update_fund_online_values.py --refresh` and `generate_fund_report.py --no-open`, using the current Python interpreter and a 60-minute timeout per child. Fatal process, file, locking, or validation failures return nonzero and prevent publication. Individual missing or failed provider lookups are warnings and allow publication.

The updater merges successful prices by ISIN/date, retaining older imported history. Failed or empty downloads retain previous rows and their timestamps. A fund with no prior rows gets an explicit error row. One-quote results count as incomplete historical refreshes but do not block publication. Nonempty portfolios return success even when some or all providers have no data; missing/empty portfolio configuration and fatal errors still fail. Previous quotes are reused when available. Otherwise the report displays a per-fund explanation and warns that portfolio charts may be incomplete. Failure diagnostics and attempt timestamps are stored separately in `Web_Report/refresh_status.json`.

## Validation and atomic writes

Before publication, quoted prices must have valid dates and finite positive numeric values; future dates and unexpected quote errors are rejected. Explicit error-only rows without a date or price are allowed. Missing history, one-quote results, and empty filtered ranges are nonfatal when the report contains the corresponding data-availability note for every affected fund. Reports with no usable history may be published without SVG charts. No fixed maximum quote age is imposed because funds may have different trading calendars or be sold; live provider freshness still needs deployment verification.

The generated HTML must have opening and closing document, body, head, SVG and table elements, the Fund History heading, the expected portfolio count, and a fund heading for every expected ISIN. These checks detect missing funds and common truncation; they are not a full HTML validator or independent recalculation of every plotted value.

Workbook and text writes use unique temporary files in the destination directory, close and sync file contents with `os.fsync()`, and then use `os.replace()`. Temporary files are cleaned up on errors. Existing workbook mode bits are retained; published HTML is readable on Linux. Atomic replacement protects against partial files but does not guarantee survival of every power-loss scenario or preservation of filesystem ACLs.

Validated HTML is published as both `fund_history_report.html` and `index.html`. Each replacement is atomic, but the pair is not one transaction. Fatal refresh-process, generation and validation failures leave both existing public files untouched; a failure during publication can leave the two URLs on different versions.

## Paths and operation

Default private paths remain:

```text
DATA_PATH=/app/Data
/app/Data/Input_Data/fund_manual_values.xlsx
/app/Data/Web_Report/fund_history_report.html
/app/Data/Web_Report/cache/
/app/Data/Web_Report/refresh_status.json
```

Only publish HTML to `/published`. Keep caches, workbook backups and diagnostics outside the public document root. Do not set `--output-dir` to the public directory. The default download period is `5y`, with daily (`1d`) price points. Standalone updates reuse caches unless `--refresh` or `FUND_ONLINE_REFRESH=true` is set; there is no cache age limit.

Report generation opens a desktop application only on Windows and unless `--no-open` is supplied. The GUI launcher is `FundTools/GUI/run_fund_history_app.cmd`; import utilities are under `FundTools/Tools`.

The lock coordinates orchestrator processes only. Run GUI changes, manual workbook edits and imports separately. Refreshes do not import transactions or quantities.

## Verification

Run the offline suite from the repository root:

```sh
python -B -m unittest discover -s FundTools/tests -v
```

The 15-test suite uses temporary synthetic workbooks, mocked provider downloads and disposable publication directories. It covers real headless report generation, invalid quotes and incomplete reports, date filters, atomic replacement failure, successful publication and backup creation, preservation of public files after child or validation failure, retained old prices/history, missing/empty input and competing-process locking. It also verifies first publication with unavailable ISINs, publication when every fund lacks prices, and rejection of missing data-availability notes. It does not contact live providers or modify production workbooks.

Still required on the target NAS:

- Run the suite under Linux and a complete update with live providers on a disposable workbook.
- Confirm Web Station can read published HTML and private files are outside its document root with appropriate permissions.
- Measure runtime and peak memory with a realistic workbook under the NAS guide's 256 MiB memory limit (no hard CPU limit on this NAS).
- On disposable data, force container termination or an insufficient memory limit and confirm the workbook stays readable and public files are complete.
- Run the DSM task manually before enabling its weekly schedule.

The local Windows environment has no usable Linux/container runtime, so these deployment checks have not been completed locally.
