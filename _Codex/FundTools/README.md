# Fund History Tool

This tool reads ISINs, scalar values, cash-flow date/value pairs, quantity date pairs, and online value history from `Data\Input_Data\fund_manual_values.xlsx`, then writes the HTML report. Online lookups are handled by a separate updater script that only refreshes the `OnlineValues` sheet in the workbook.

Provider order:

1. Yahoo Finance symbol search and chart history
2. Onvista ISIN search and `simple_chart_history` fallback
3. Deka fund search current value fallback

Downloaded online values are normalized to EUR before they are written to `OnlineValues`.

## Run

First update the online values sheet:

```powershell
python .\FundTools\fund_online_values.py
```

Then generate the report from the workbook only:

```powershell
python .\FundTools\fund_history_tool.py
```

Outputs are written to `Data\Web_Report`:

- `fund_history_report.html`: figure/report with one SVG plot per ISIN
- `Data\Input_Data\fund_manual_values.xlsx`: editable Excel workbook for manual values and the `OnlineValues` sheet
- `cache\`: cached Yahoo Finance symbol lookups and history responses

`status`, `buy_date`, and `sell_date` come from the `ScalarValues` sheet when provided.

## GUI App

Start the local GUI app from the repository root:

```powershell
.\FundTools\run_fund_history_app.cmd
```

The app opens in the browser with four tabs:

- `Overview`: portfolio plots and the fund overview table
- `Single Funds`: fund selector with one fund plot
- `Import`: DKB quantity import preview/run buttons
- `Options`: start/end date controls and a checkbox for showing sold funds

Each plot has zoom controls. The app uses the same workbook and calculation functions as the report.

## Manual Values Template

The tool creates `FundTools\fund_manual_values.xlsx` automatically if it does not exist.

`ScalarValues` columns:

- `isin`
- `name`
- `buy_date`
- `sell_date`
- `status`
- `notes`

`DateValuePairs` columns:

- `isin`
- `series`
- `date`
- `value`
- `notes`

Accepted `series` values are `single_value`, `total_value`, `invest`, `dividend`, and `sell`. In normal use, fill `invest`, `dividend`, and `sell`; the tool already derives `single_value` and `total_value`.

`QuantityDatePairs` columns:

- `isin`
- `date`
- `quantity`
- `notes`

Use `QuantityDatePairs` to supply quantity history as explicit date/quantity pairs.

`OnlineValues` columns:

- `isin`
- `source`
- `symbol`
- `date`
- `close`
- `error`
- `updated_at`

Do not edit `OnlineValues` manually in normal use; rerun `fund_online_values.py` to replace the data in that sheet.

## Import Old DepotManager Data

To import `History.date`, `History.isin`, and `History.value` from `_old\DepotManager_DB.xlsx` into `OnlineValues`, run from the repository root:

```powershell
python .\FundTools\import_depotmanager_history.py
```

The importer creates a timestamped backup of `fund_manual_values.xlsx` before writing. To preview the import without changing the workbook:

```powershell
python .\FundTools\import_depotmanager_history.py --dry-run
```

The importer adds legacy prices only when `OnlineValues` does not already contain the same ISIN/date, so current online data takes precedence. It creates a timestamped backup before writing.

## Import DKB Depot Export

Put DKB depot exports in `Data\Input_Data\DKB`, then run from the repository root:

```powershell
python .\FundTools\import_dkb_export.py
```

The importer reads `.csv` and `.xlsx` exports from that folder, creates a timestamped backup of `fund_manual_values.xlsx`, and keeps existing workbook data. It only adds DKB quantity rows that are not already present:

- new `QuantityDatePairs` quantity snapshots

To preview the import without changing the workbook:

```powershell
python .\FundTools\import_dkb_export.py --dry-run
```

Common options:

```powershell
python .\FundTools\fund_online_values.py --period max --interval 1wk --refresh
```

Yahoo Finance and Onvista do not always resolve every ISIN. When no source can be found, the report includes that ISIN with a note instead of failing the whole run.

To correct or add a Yahoo Finance symbol manually, create a CSV file with columns `isin,symbol` and pass it with `--overrides`:

```csv
isin,symbol
LU0323578657,EXAMPLE.F
```

Then rerun:

```powershell
python .\FundTools\fund_online_values.py --overrides .\my_symbol_overrides.csv --refresh
```
