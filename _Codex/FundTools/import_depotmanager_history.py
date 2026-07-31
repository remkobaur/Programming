#!/usr/bin/env python3
"""Import legacy DepotManager History prices into the OnlineValues sheet."""

from __future__ import annotations

import argparse
import datetime as dt
import shutil
import sys
from pathlib import Path

from fund_history_tool import (
    ONLINE_VALUES_HEADERS,
    ONLINE_VALUES_SHEET,
    configured_input_data_dir,
    ensure_manual_data_template,
    load_project_env,
    parse_excel_date,
    parse_float,
    read_xlsx_rows,
    rows_from_dicts,
    workbook_has_sheet,
    write_xlsx,
)


SCALAR_HEADERS = ["isin", "name", "bank", "buy_date", "sell_date", "status", "notes"]
DATE_VALUE_HEADERS = ["isin", "series", "date", "value", "notes"]
QUANTITY_HEADERS = ["isin", "date", "quantity", "notes"]
IMPORT_SOURCE = "depotmanager-history"


def read_sheet_or_empty(path: Path, sheet_name: str) -> list[dict[str, str]]:
    return read_xlsx_rows(path, sheet_name) if workbook_has_sheet(path, sheet_name) else []


def format_number(value: float) -> str:
    return f"{value:.10f}".rstrip("0").rstrip(".")


def history_online_rows(path: Path, updated_at: str) -> list[dict[str, str]]:
    if not workbook_has_sheet(path, "History"):
        raise ValueError(f"History sheet not found in {path}.")

    imported: list[dict[str, str]] = []
    for row in read_xlsx_rows(path, "History"):
        date = parse_excel_date(row.get("date", ""))
        isin = row.get("isin", "").strip().upper()
        value = parse_float(row.get("value"))
        if not date or not isin or value is None:
            continue
        imported.append(
            {
                "isin": isin,
                "source": IMPORT_SOURCE,
                "symbol": isin,
                "date": date,
                "close": format_number(value),
                "error": "",
                "updated_at": updated_at,
            }
        )
    return imported


def integrate_history(
    legacy_workbook: Path,
    manual_workbook: Path,
) -> tuple[dict[str, int], dict[str, list[dict[str, str]]]]:
    imported_rows = history_online_rows(
        legacy_workbook,
        dt.datetime.now().isoformat(timespec="seconds"),
    )
    scalar_rows = read_sheet_or_empty(manual_workbook, "ScalarValues")
    date_rows = read_sheet_or_empty(manual_workbook, "DateValuePairs")
    quantity_rows = read_sheet_or_empty(manual_workbook, "QuantityDatePairs")
    online_rows = read_sheet_or_empty(manual_workbook, ONLINE_VALUES_SHEET)

    retained_online_rows = [
        row for row in online_rows
        if row.get("source", "").strip().lower() != IMPORT_SOURCE
    ]
    existing_dates = {
        (row.get("isin", "").strip().upper(), parse_excel_date(row.get("date", "")))
        for row in retained_online_rows
        if row.get("isin", "").strip() and parse_excel_date(row.get("date", ""))
    }
    new_rows: list[dict[str, str]] = []
    occupied_dates = existing_dates.copy()
    for row in imported_rows:
        key = (row["isin"], row["date"])
        if key in occupied_dates:
            continue
        new_rows.append(row)
        occupied_dates.add(key)

    return {
        "history_rows": len(imported_rows),
        "added_online_rows": len(new_rows),
        "skipped_existing_dates": len(imported_rows) - len(new_rows),
    }, {
        "ScalarValues": scalar_rows,
        "DateValuePairs": date_rows,
        "QuantityDatePairs": quantity_rows,
        ONLINE_VALUES_SHEET: [*retained_online_rows, *new_rows],
    }


def write_manual_workbook(path: Path, sheets: dict[str, list[dict[str, str]]]) -> None:
    write_xlsx(
        path,
        {
            "ScalarValues": rows_from_dicts(SCALAR_HEADERS, sheets["ScalarValues"]),
            "DateValuePairs": rows_from_dicts(DATE_VALUE_HEADERS, sheets["DateValuePairs"]),
            "QuantityDatePairs": rows_from_dicts(QUANTITY_HEADERS, sheets["QuantityDatePairs"]),
            ONLINE_VALUES_SHEET: rows_from_dicts(ONLINE_VALUES_HEADERS, sheets[ONLINE_VALUES_SHEET]),
        },
    )


def build_arg_parser() -> argparse.ArgumentParser:
    input_data_dir = configured_input_data_dir()
    parser = argparse.ArgumentParser(
        description="Import DepotManager History date/isin/value rows into OnlineValues."
    )
    parser.add_argument(
        "--legacy-workbook",
        type=Path,
        default=input_data_dir / "_old" / "DepotManager_DB.xlsx",
        help="Legacy DepotManager workbook containing the History sheet.",
    )
    parser.add_argument(
        "--manual-workbook",
        type=Path,
        default=input_data_dir / "fund_manual_values.xlsx",
        help="Destination fund manual-values workbook.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Show import counts without writing.")
    parser.add_argument("--no-backup", action="store_true", help="Do not create a timestamped backup before writing.")
    return parser


def main(argv: list[str] | None = None) -> int:
    load_project_env()
    args = build_arg_parser().parse_args(argv)
    legacy_workbook = args.legacy_workbook.resolve()
    manual_workbook = args.manual_workbook.resolve()
    if not legacy_workbook.exists():
        print(f"Legacy workbook not found: {legacy_workbook}", file=sys.stderr)
        return 1

    ensure_manual_data_template(manual_workbook, [])
    stats, sheets = integrate_history(legacy_workbook, manual_workbook)
    print(f"History price rows found: {stats['history_rows']}")
    print(f"OnlineValues rows added: {stats['added_online_rows']}")
    print(f"Rows skipped because an online value already exists for that ISIN/date: {stats['skipped_existing_dates']}")
    if args.dry_run:
        print("Dry run only; workbook was not changed.")
        return 0

    if not args.no_backup:
        backup_path = manual_workbook.with_name(
            f"{manual_workbook.stem}.{dt.datetime.now().strftime('%Y%m%d_%H%M%S')}.bak.xlsx"
        )
        shutil.copy2(manual_workbook, backup_path)
        print(f"Wrote backup: {backup_path}")
    write_manual_workbook(manual_workbook, sheets)
    print(f"Wrote manual workbook: {manual_workbook}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
