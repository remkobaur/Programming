# Fund History Tool

This tool reads ISINs, scalar values, cash-flow date/value pairs, and quantity date pairs from `FundTools\fund_manual_values.xlsx`, downloads historical values, and writes output files.

Provider order:

1. Yahoo Finance symbol search and chart history
2. Onvista ISIN search and `simple_chart_history` fallback
3. Deka fund search current value fallback

## Run

From `FundTools`:

```powershell
python .\fund_history_tool.py
```

Outputs are written to `Data\fund_history`:

- `fund_history_report.html`: figure/report with one SVG plot per ISIN
- `extended_fund_data.json`: extended per-ISIN structure with position dates, status, and value arrays
- `FundTools\fund_manual_values.xlsx`: editable Excel template for scalar overrides and manual date/value pairs
- `cache\`: cached Yahoo Finance symbol lookups and history responses

`extended_fund_data.json` contains one object per ISIN:

- `isin`, `name`, `buy_date`, `sell_date`, `sell_data`, `status`
- `single_value`: downloaded date/value price history
- `quantity`: quantity date pairs from `fund_manual_values.xlsx`
- `total_value`: `single_value * latest known quantity`
- `invest`: manual date/value pairs from `fund_manual_values.xlsx`
- `dividend`: manual date/value pairs from `fund_manual_values.xlsx`

`status`, `buy_date`, and `sell_date` come from the `ScalarValues` sheet when provided.

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

Accepted `series` values are `single_value`, `total_value`, `invest`, and `dividend`. In normal use, fill `invest` and `dividend`; the tool already derives `single_value` and `total_value`.

`QuantityDatePairs` columns:

- `isin`
- `date`
- `quantity`
- `notes`

Use `QuantityDatePairs` to supply quantity history as explicit date/quantity pairs.

Common options:

```powershell
python .\fund_history_tool.py --period max --interval 1wk --refresh
```

Yahoo Finance and Onvista do not always resolve every ISIN. When no source can be found, the report includes that ISIN with a note instead of failing the whole run.

To correct or add a Yahoo Finance symbol manually, create a CSV file with columns `isin,symbol` and pass it with `--overrides`:

```csv
isin,symbol
LU0323578657,EXAMPLE.F
```

Then rerun:

```powershell
python .\fund_history_tool.py --overrides .\my_symbol_overrides.csv --refresh
```
