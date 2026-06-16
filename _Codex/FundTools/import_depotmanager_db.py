from __future__ import annotations

import argparse
import math
import re
import shutil
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from fund_history_tool import parse_excel_date, parse_float, read_xlsx_rows, rows_from_dicts, write_xlsx


SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent
DEFAULT_OLD_WORKBOOK = ROOT_DIR / "_old" / "DepotManager_DB.xlsx"
DEFAULT_MANUAL_WORKBOOK = SCRIPT_DIR / "fund_manual_values.xlsx"
#
# DEFAULT_OLD_WORKBOOK = Path(r"C:\Users\remko\Desktop\0_Nas\1_Remko\Unterlagen\Banking\_Data\DepotManager_DB.xlsx")
# DEFAULT_MANUAL_WORKBOOK = Path(r"C:\Users\remko\Desktop\0_Nas\1_Remko\Unterlagen\Banking\_Data") / "fund_manual_values.xlsx"
#
SCALAR_HEADERS = ["isin", "name", "buy_date", "sell_date", "status", "notes"]
DATE_VALUE_HEADERS = ["isin", "series", "date", "value", "notes"]
QUANTITY_HEADERS = ["isin", "date", "quantity", "notes"]
ISIN_PATTERN = re.compile(r"^[A-Z]{2}[A-Z0-9]{10}$")


def normalize_isin(value: str | None) -> str:
    isin = (value or "").strip().upper().replace(" ", "")
    return isin if ISIN_PATTERN.match(isin) else ""


def format_number(value: float) -> str:
    return f"{value:.10f}".rstrip("0").rstrip(".")


def note_from(description: str, source: str) -> str:
    description = " ".join((description or "").split())
    if len(description) > 900:
        description = description[:900] + "..."
    if description:
        return f"Imported from {source}: {description}"
    return f"Imported from {source}"


def is_example_row(row: dict[str, str]) -> bool:
    note = row.get("notes", "").strip().lower()
    return note.startswith("example ") or note == "delete this example row."


def classify_change(description: str, value: float) -> tuple[str, float]:
    text = (description or "").lower()
    if "sell" in text or "verkauf" in text:
        return "sell", abs(value)
    if "buy" in text or "kauf" in text:
        return "invest", abs(value)
    if (
        "dividend" in text
        or "ertrag" in text
        or "aussch" in text
        or "zins" in text
    ):
        return "dividend", value
    if value < 0:
        return "invest", abs(value)
    return "dividend", value


def append_unique(rows: list[dict[str, str]], new_rows: list[dict[str, str]], key_fields: list[str]) -> int:
    existing = {
        tuple(row.get(field, "").strip() for field in key_fields)
        for row in rows
    }
    added = 0
    for row in new_rows:
        key = tuple(row.get(field, "").strip() for field in key_fields)
        if key in existing:
            continue
        rows.append(row)
        existing.add(key)
        added += 1
    return added


def read_sheet_or_empty(path: Path, sheet_name: str) -> list[dict[str, str]]:
    if not path.exists():
        return []
    try:
        return read_xlsx_rows(path, sheet_name)
    except ValueError:
        return []


def first_date(*date_lists: list[str]) -> str:
    dates = sorted(date for dates in date_lists for date in dates if date)
    return dates[0] if dates else ""


def last_date(dates: list[str]) -> str:
    return max((date for date in dates if date), default="")


def compressed_quantity_rows(
    rows_by_isin: dict[str, list[tuple[str, float]]],
    source_name: str,
) -> list[dict[str, str]]:
    imported_rows: list[dict[str, str]] = []
    for isin, points in rows_by_isin.items():
        previous_quantity: float | None = None
        for date, quantity in sorted(points):
            if previous_quantity is not None and math.isclose(previous_quantity, quantity):
                continue
            imported_rows.append(
                {
                    "isin": isin,
                    "date": date,
                    "quantity": format_number(quantity),
                    "notes": note_from("quantity from History sheet", source_name),
                }
            )
            previous_quantity = quantity
    return imported_rows


def build_import_rows(old_workbook: Path) -> tuple[
    dict[str, str],
    dict[str, list[str]],
    dict[str, list[str]],
    list[dict[str, str]],
    list[dict[str, str]],
]:
    source_name = old_workbook.name
    names: dict[str, str] = {}
    history_dates: dict[str, list[str]] = defaultdict(list)
    invest_dates: dict[str, list[str]] = defaultdict(list)
    sell_dates: dict[str, list[str]] = defaultdict(list)
    quantity_points: dict[str, list[tuple[str, float]]] = defaultdict(list)
    date_value_rows: list[dict[str, str]] = []

    for row in read_xlsx_rows(old_workbook, "History"):
        isin = normalize_isin(row.get("isin"))
        date = parse_excel_date(row.get("date", ""))
        if not isin or not date:
            continue

        name = row.get("name", "").strip()
        if name and isin not in names:
            names[isin] = name
        history_dates[isin].append(date)

        quantity = parse_float(row.get("quantity"))
        if quantity is not None:
            quantity_points[isin].append((date, quantity))

    for row in read_xlsx_rows(old_workbook, "Changes"):
        isin = normalize_isin(row.get("isin"))
        date = parse_excel_date(row.get("date", ""))
        value = parse_float(row.get("value"))
        if not isin or not date or value is None:
            continue

        series, imported_value = classify_change(row.get("description", ""), value)
        if series == "invest":
            invest_dates[isin].append(date)
        elif series == "sell":
            sell_dates[isin].append(date)

        date_value_rows.append(
            {
                "isin": isin,
                "series": series,
                "date": date,
                "value": format_number(imported_value),
                "notes": note_from(row.get("description", ""), source_name),
            }
        )

    quantity_rows = compressed_quantity_rows(quantity_points, source_name)
    return names, history_dates, invest_dates, sell_dates, date_value_rows, quantity_rows


def integrate_depotmanager_db(
    old_workbook: Path,
    manual_workbook: Path,
    keep_example_rows: bool,
    remove_imported_single_values: bool,
) -> tuple[dict[str, int], dict[str, list[dict[str, str]]]]:
    names, history_dates, invest_dates, sell_dates, imported_date_rows, imported_quantity_rows = build_import_rows(
        old_workbook
    )

    scalar_rows = read_sheet_or_empty(manual_workbook, "ScalarValues")
    date_rows = read_sheet_or_empty(manual_workbook, "DateValuePairs")
    quantity_rows = read_sheet_or_empty(manual_workbook, "QuantityDatePairs")

    if not keep_example_rows:
        date_rows = [row for row in date_rows if not is_example_row(row)]
        quantity_rows = [row for row in quantity_rows if not is_example_row(row)]

    removed_single_value_rows = 0
    if remove_imported_single_values:
        filtered_date_rows = []
        for row in date_rows:
            imported_from_old = old_workbook.name in row.get("notes", "")
            is_single_value = row.get("series", "").strip().lower() == "single_value"
            if imported_from_old and is_single_value:
                removed_single_value_rows += 1
                continue
            filtered_date_rows.append(row)
        date_rows = filtered_date_rows

    known_isins = set(names) | set(history_dates) | set(invest_dates) | set(sell_dates)
    scalar_by_isin = {
        normalize_isin(row.get("isin")): dict(row)
        for row in scalar_rows
        if normalize_isin(row.get("isin"))
    }

    for isin in sorted(known_isins):
        row = scalar_by_isin.setdefault(
            isin,
            {"isin": isin, "name": "", "buy_date": "", "sell_date": "", "status": "", "notes": ""},
        )
        can_replace_example = not keep_example_rows and is_example_row(row)
        if names.get(isin) and (not row.get("name") or can_replace_example):
            row["name"] = names[isin]

        buy_date = first_date(invest_dates.get(isin, []), history_dates.get(isin, []))
        if buy_date and (not row.get("buy_date") or can_replace_example):
            row["buy_date"] = buy_date

        imported_sell_date = last_date(sell_dates.get(isin, []))
        if imported_sell_date and (not row.get("sell_date") or row.get("sell_date") == "not sold" or can_replace_example):
            row["sell_date"] = imported_sell_date

        if not row.get("sell_date"):
            row["sell_date"] = "not sold"
        if not row.get("status") or can_replace_example:
            row["status"] = "sold" if row.get("sell_date") != "not sold" else "active"
        if not row.get("notes") or can_replace_example:
            row["notes"] = f"Imported from {old_workbook.name}"

    scalar_rows = [scalar_by_isin[isin] for isin in sorted(scalar_by_isin)]
    added_date_rows = append_unique(
        date_rows,
        imported_date_rows,
        ["isin", "series", "date", "value"],
    )
    added_quantity_rows = append_unique(
        quantity_rows,
        imported_quantity_rows,
        ["isin", "date", "quantity"],
    )

    scalar_rows.sort(key=lambda row: row.get("isin", ""))
    date_rows.sort(key=lambda row: (row.get("isin", ""), row.get("series", ""), row.get("date", "")))
    quantity_rows.sort(key=lambda row: (row.get("isin", ""), row.get("date", "")))

    sheets = {
        "ScalarValues": scalar_rows,
        "DateValuePairs": date_rows,
        "QuantityDatePairs": quantity_rows,
    }
    stats = {
        "scalar_rows": len(scalar_rows),
        "imported_cash_flow_rows": len(imported_date_rows),
        "added_cash_flow_rows": added_date_rows,
        "imported_quantity_rows": len(imported_quantity_rows),
        "added_quantity_rows": added_quantity_rows,
        "removed_imported_single_value_rows": removed_single_value_rows,
    }
    return stats, sheets


def write_manual_workbook(path: Path, sheets: dict[str, list[dict[str, str]]]) -> None:
    write_xlsx(
        path,
        {
            "ScalarValues": rows_from_dicts(SCALAR_HEADERS, sheets["ScalarValues"]),
            "DateValuePairs": rows_from_dicts(DATE_VALUE_HEADERS, sheets["DateValuePairs"]),
            "QuantityDatePairs": rows_from_dicts(QUANTITY_HEADERS, sheets["QuantityDatePairs"]),
        },
    )


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Import _old/DepotManager_DB.xlsx data into FundTools/fund_manual_values.xlsx."
    )
    parser.add_argument("--old-workbook", type=Path, default=DEFAULT_OLD_WORKBOOK)
    parser.add_argument("--manual-workbook", type=Path, default=DEFAULT_MANUAL_WORKBOOK)
    parser.add_argument("--dry-run", action="store_true", help="Show what would be imported without writing.")
    parser.add_argument("--no-backup", action="store_true", help="Do not create a timestamped .bak.xlsx file.")
    parser.add_argument(
        "--keep-example-rows",
        action="store_true",
        help="Keep rows whose notes mark them as generated example data.",
    )
    parser.add_argument(
        "--keep-imported-single-values",
        action="store_true",
        help="Keep older imported DateValuePairs rows with series=single_value.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    old_workbook = args.old_workbook.resolve()
    manual_workbook = args.manual_workbook.resolve()

    if not old_workbook.exists():
        print(f"Old workbook not found: {old_workbook}", file=sys.stderr)
        return 1
    if not manual_workbook.exists():
        print(f"Manual workbook not found: {manual_workbook}", file=sys.stderr)
        return 1

    stats, sheets = integrate_depotmanager_db(
        old_workbook,
        manual_workbook,
        keep_example_rows=args.keep_example_rows,
        remove_imported_single_values=not args.keep_imported_single_values,
    )
    print(f"Scalar rows after import: {stats['scalar_rows']}")
    print(f"Cash-flow rows found in old workbook: {stats['imported_cash_flow_rows']}")
    print(f"Cash-flow rows added: {stats['added_cash_flow_rows']}")
    print(f"Quantity rows found in old workbook: {stats['imported_quantity_rows']}")
    print(f"Quantity rows added: {stats['added_quantity_rows']}")
    print(f"Imported single_value rows removed: {stats['removed_imported_single_value_rows']}")

    if args.dry_run:
        print("Dry run only; workbook was not changed.")
        return 0

    if not args.no_backup:
        backup_path = manual_workbook.with_name(
            f"{manual_workbook.stem}.{datetime.now().strftime('%Y%m%d_%H%M%S')}.bak.xlsx"
        )
        shutil.copy2(manual_workbook, backup_path)
        print(f"Wrote backup: {backup_path}")

    write_manual_workbook(manual_workbook, sheets)
    print(f"Wrote manual workbook: {manual_workbook}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
