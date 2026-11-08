# Python changes for unattended NAS updates

The core changes below are implemented in the existing `FundTools` scripts and the new `update_fund_report.py`. It describes changes to make before following [nas-setup.md](nas-setup.md). The remaining deployment checks must be performed on the NAS.

## Current behavior

- `fund_online_values.py` downloads prices and rewrites the `OnlineValues` sheet in `Data/Input_Data/fund_manual_values.xlsx`.
- `fund_history_tool.py` reads that workbook and generates `Data/Web_Report/fund_history_report.html` with inline SVG. No application server is required to view it.
- Both scripts use Python's standard library. Use Python 3.11+ because `fund_online_values.py` uses `datetime.UTC`.
- Paths are already based on `pathlib`, and `DATA_PATH`/`DATA_DIR` can select the data directory. In a container, set `DATA_PATH=/app/Data`.
- The updater reuses cached responses unless `--refresh` or `FUND_ONLINE_REFRESH=true` is set. There is no cache age limit.
- The updater currently returns zero even if individual downloads fail, and replaces existing online rows with newly collected rows, including error-only rows.
- Report generation ends by calling Windows-only `os.startfile()` through `open_default_app()`. Linux raises `AttributeError`, which the existing `except OSError` does not catch.

## 1. Add headless report generation

In `fund_history_tool.py`, add this argument in `build_arg_parser()`:

```python
parser.add_argument(
    "--no-open",
    action="store_true",
    help="Generate the report without opening a desktop application.",
)
```

Replace the final unconditional `open_default_app(report_path)` call in `main()` with:

```python
if not args.no_open and os.name == "nt":
    open_default_app(report_path)
```

This preserves the Windows behavior and allows the same script to complete on a headless Linux NAS.

## 2. Make workbook and report writes atomic

`write_xlsx()` currently opens its destination ZIP directly, and `write_html_report()` writes its destination directly. A crash can leave either file incomplete.

Write to a temporary sibling file, close it successfully, then replace the destination using `os.replace()`. Use `tempfile.mkstemp()` or `NamedTemporaryFile(delete=False)` for unique names and clean up temporary files in `finally` blocks.

For the workbook, retain the current ZIP-building logic, but target the temporary file and close the ZIP before replacement. For HTML, use a helper such as:

```python
import tempfile


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temporary_path = Path(temporary)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        # Public HTML must remain readable by Web Station.
        temporary_path.chmod(0o644)
        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)
```

Use that helper instead of `path.write_text(document, encoding="utf-8")`. Keep private workbook permissions appropriate for private data rather than automatically using public HTML permissions. Replacement requires write permission on the containing directory.

Temporary and destination files must be on the same filesystem for atomic replacement. This protects readers against partial files; it is not a substitute for backups or a guarantee against every power-loss scenario.

## 3. Preserve good prices and signal download failures

Adjust `fund_online_values.py` so a failed provider request cannot silently destroy a fund's previous online history.

Recommended policy:

1. Read existing `OnlineValues` before downloading.
2. Group old and new rows by ISIN.
3. On a failed or empty download, retain that ISIN's previous rows and original quote/update timestamps. Log the refresh failure separately. If no previous rows exist, retain an explicit error row.
4. For successful downloads, merge prices by `(isin, date)` with fresh values taking precedence. This preserves legacy/imported history outside the downloaded range. Preserve compatible source/symbol metadata with the corresponding rows.
5. Do not label retained old prices as freshly downloaded. Record refresh attempt time and failure diagnostics separately from the previous successful data timestamp.
6. Return a nonzero exit code when any requested fund cannot be refreshed successfully. Decide explicitly whether a one-quote current-value fallback counts as failure for this historical report; a conservative scheduled policy treats it as incomplete.
7. Reject an empty portfolio as a configuration error in scheduled mode instead of publishing an empty report.

The initial publication policy should be conservative: if a refresh is incomplete, leave the previously published HTML untouched, log the affected ISINs, and fail the task. Successfully refreshed workbook data may be retained for the next run, provided failed funds' previous data is preserved.

Do not automatically retry aggressively: providers may rate-limit requests. The existing request delay can remain; add bounded retries only for transient failures if needed.

## 4. Add a single update orchestrator

Create `FundTools/update_fund_report.py` with this interface:

```text
python FundTools/update_fund_report.py --publish-dir /published
```

The NAS guide invokes this new file. It should perform these steps in order:

1. Load project environment settings using the existing helper and resolve the configured data directory.
2. Acquire an exclusive lock for the whole operation. On the Linux NAS, use `fcntl.flock()` with `LOCK_EX | LOCK_NB` on a private persistent lock file. Keep its descriptor open until completion; do not unlink the lock file on release. For a Windows-compatible orchestrator, provide a Windows locking implementation as well.
3. Require the input workbook to exist and contain a nonempty portfolio. Do not silently create a template in scheduled mode.
4. Create a timestamped workbook backup under a private backup folder before changing it. Use a unique timestamp/name and a documented retention policy.
5. Run the updater with fresh online requests:

   ```python
   subprocess.run(
       [sys.executable, str(script_dir / "fund_online_values.py"), "--refresh"],
       check=True,
   )
   ```

6. Only on success, run the report generator:

   ```python
   subprocess.run(
       [sys.executable, str(script_dir / "fund_history_tool.py"), "--no-open"],
       check=True,
   )
   ```

7. Validate that the generated HTML exists, is nonempty, contains the expected report structure, and reflects a nonempty portfolio. Validate quote dates and errors from workbook data rather than trusting the HTML generation timestamp alone. Different funds can legitimately have different latest trading dates.
8. Publish the validated HTML to both `fund_history_report.html` and `index.html` in `--publish-dir`. For each destination, copy/write to a unique temporary file **inside the publication directory**, set readable permissions, close it, and call `os.replace()`. Do not move a private temporary file across volumes and assume atomicity. Each URL is replaced atomically; the two replacements are not one transaction.
9. Print useful status messages and return nonzero if any step fails. Always release the lock. Keep the old public files untouched when downloading, generation, or validation fails.

Use `subprocess.run()` with argument lists and `check=True`, not concatenated shell commands. Use `sys.executable` so child scripts run with the same Python version. A container-wide runtime limit or subprocess timeouts can prevent a stuck job from blocking later updates indefinitely; set limits large enough for all funds and normal provider delays.

The lock protects orchestrator runs. Other writers, such as manual imports or the GUI, must use the same lock to coordinate automatically; otherwise, schedule them separately and avoid editing the workbook during updates.

### Resource use on the 2 GB NAS

Keep the orchestrator, downloads, and report generation sequential. Avoid parallel fund downloads or concurrent report workers initially. The NAS guide limits the entire container to 256 MiB RAM and half a CPU core; this is a starting configuration to measure against the actual workbook. The orchestrator remains resident while a child script runs, so both processes count toward the same memory limit. Release large workbook/HTML objects when they are no longer needed and avoid retaining unnecessary copies of history.

A memory-limit kill can bypass Python exception handlers and cleanup. Keep backups and atomic replacement as described above, and publish only after successful validation. A killed update must not leave a partially written public report. Existing published HTML remains available while the update container is stopped. CPU throttling can extend runtime, so allow for it when choosing subprocess timeouts.

## 5. Keep private output separate from publication

Continue using these internal defaults:

```text
DATA_PATH=/app/Data
/app/Data/Input_Data/fund_manual_values.xlsx
/app/Data/Web_Report/fund_history_report.html
/app/Data/Web_Report/cache/
```

Only publish the HTML into `/published`. Do not point the updater's `--output-dir` at the public folder: it places its cache under that directory.

Weekly scheduling controls when downloads occur. Keep the default `--interval 1d` for daily price points unless you deliberately want weekly points. Review `--period` (default `5y`) and preserve older workbook history when merging refreshed data.

Price refreshes do not import new transactions or quantity snapshots automatically. Keep DKB/import workflows separate unless you intentionally add them to the orchestrator with the same locking and backup rules.

## 6. Verify before deployment

Use a disposable copy of the workbook and a temporary publication directory for these checks. Do not test failure handling against your only live workbook.

- **Headless run:** `fund_history_tool.py --no-open` exits zero under Linux and produces a complete HTML report.
- **Successful update:** fresh price requests occur, manual sheets are preserved, and both public filenames contain the new report.
- **Provider failure:** simulate a failed download; old prices remain, the job returns nonzero, and published HTML remains unchanged.
- **History preservation:** a successful limited-range download does not remove older imported quotes.
- **Interrupted write:** fail before replacement; the original workbook/report remains readable.
- **Overlap:** start two orchestrator runs; the second fails clearly without changing data.
- **Permissions:** Web Station can read published HTML while private files remain outside its document root.
- **Missing/empty input:** the job fails without replacing the existing published report.
- **Resource limits:** run with the NAS guide's memory and CPU limits using a realistic workbook; observe peak memory and runtime. On disposable data, verify that a deliberately insufficient memory limit causes a failed task without corrupting the workbook or leaving partial public HTML.

After these pass, follow [the NAS deployment guide](nas-setup.md), run the DSM task manually once, and then enable its weekly schedule.

## Implemented compatibility and operational defaults

Existing Windows commands and GUI launcher remain supported. The orchestrator uses Windows or Linux locking conditionally, retains 30 workbook backups, and gives each child process a 60-minute timeout. Refresh diagnostics are stored privately in `Web_Report/refresh_status.json`. Failed refreshes return nonzero and preserve old quotes. The strict historical refresh policy treats one-quote results as incomplete. Manual imports and workbook editing must run separately from the orchestrator.

Automated checks performed locally cover copied-workbook report generation, GUI imports, atomic replacement failure, backup creation, and publication preservation after a child failure. Linux/container memory measurements and provider integration remain deployment checks.
