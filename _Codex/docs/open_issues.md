# Open issues

The code fixes and 15 offline tests pass locally on Windows. The following deployment checks remain open because the local environment has no usable Linux/container runtime or target NAS access.

Use a disposable workbook and temporary publication directory for testing.

- [ ] **Linux compatibility:** Run `python -B -m unittest discover -s FundTools/tests -v` on Linux, including the competing-process lock test.
- [ ] **Live providers:** Run `FundTools/NAS/refresh_and_publish_fund_report.py` with real provider requests. Confirm current prices, retained older history, and successful publication of both HTML filenames. Simulate missing provider data and confirm previous prices are retained and a report is published with notes for unavailable funds. Confirm fatal process or validation errors still preserve the previous published report.
- [ ] **NAS permissions:** Verify Web Station can read published HTML. Confirm workbooks, backups, caches, lock files, and refresh diagnostics stay outside the public document root with appropriate private permissions.
- [ ] **Resource limits:** Measure peak memory and runtime using a realistic workbook with the NAS guide's 256 MiB memory limit (no hard CPU limit on this NAS). Adjust deployment limits or timeouts if necessary.
- [ ] **Forced termination:** On disposable data, terminate the container during an update or enforce an insufficient memory limit. Confirm the workbook remains readable and published files contain complete reports.
- [ ] **DSM scheduling:** Run the configured DSM task manually and inspect its exit status and logs before enabling the weekly schedule.

See [implementation and verification details](code-adjustments.md) and [NAS setup](nas-setup.md).

## Known operational limitations

- The orchestrator lock does not coordinate GUI edits, manual imports, or external workbook editing; schedule these separately.
- The two public HTML filenames are replaced atomically individually, not together. A failure during publication can leave them on different versions.
- File synchronization and atomic replacement do not guarantee survival of every power-loss scenario or preservation of filesystem ACLs.
- Quote validation does not enforce a maximum quote age. Freshness must account for trading calendars and sold funds.
