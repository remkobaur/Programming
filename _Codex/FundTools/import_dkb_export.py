from __future__ import annotations

import argparse
import csv
import datetime as dt
import re
import shutil
import sys
from pathlib import Path

from fund_history_tool import (
    ONLINE_VALUES_HEADERS,
    ONLINE_VALUES_SHEET,
    configured_input_data_dir,
    load_project_env,
    read_xlsx_rows,
    rows_from_dicts,
    workbook_has_sheet,
    write_xlsx,
)


SCALAR_HEADERS = ["isin", "name", "bank", "buy_date", "sell_date", "status", "notes"]
DATE_VALUE_HEADERS = ["isin", "series", "date", "value", "notes"]
QUANTITY_HEADERS = ["isin", "date", "quantity", "notes"]
ISIN_PATTERN = re.compile(r"^[A-Z]{2}[A-Z0-9]{10}$")


def normalize_header(value: str) -> str:
    normalized = " ".join(value.strip().lower().split())
    return (
        normalized.replace("ä", "ae")
        .replace("ö", "oe")
        .replace("ü", "ue")
        .replace("ß", "ss")
    )


def normalize_isin(value: str | None) -> str:
    isin = (value or "").strip().upper().replace(" ", "")
    return isin if ISIN_PATTERN.match(isin) else ""


def parse_german_date(value: str | None) -> str:
    text = (value or "").strip()
    if not text:
        return ""
    for pattern in ("%d.%m.%Y", "%Y-%m-%d"):
        try:
            return dt.datetime.strptime(text[:10], pattern).date().isoformat()
        except ValueError:
            pass
    return ""


def parse_german_number(value: str | None) -> float | None:
    text = (value or "").strip()
    if not text:
        return None
    cleaned = re.sub(r"[^0-9,.\-]", "", text).replace(".", "").replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return None


def format_number(value: float) -> str:
    return f"{value:.10f}".rstrip("0").rstrip(".")


def note_from(source: Path, depot_number: str, wkn: str) -> str:
    parts = [f"Imported from DKB {source.name}"]
    if depot_number:
        parts.append(f"depot {depot_number}")
    if wkn:
        parts.append(f"WKN {wkn}")
    return ", ".join(parts)


def is_example_row(row: dict[str, str]) -> bool:
    note = row.get("notes", "").strip().lower()
    return note.startswith("example ") or note == "delete this example row."


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
    if not path.exists() or not workbook_has_sheet(path, sheet_name):
        return []
    return read_xlsx_rows(path, sheet_name)


def read_dkb_csv(path: Path) -> list[dict[str, str]]:
    last_error: UnicodeDecodeError | None = None
    for encoding in ("utf-8-sig", "cp1252"):
        try:
            with path.open("r", encoding=encoding, newline="") as handle:
                sample = handle.read(4096)
                handle.seek(0)
                dialect = csv.Sniffer().sniff(sample, delimiters=";,")
                reader = csv.DictReader(handle, dialect=dialect)
                return [
                    {normalize_header(key or ""): (value or "").strip() for key, value in row.items()}
                    for row in reader
                ]
        except UnicodeDecodeError as exc:
            last_error = exc
    if last_error:
        raise last_error
    return []


def read_dkb_rows(path: Path) -> list[dict[str, str]]:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return read_dkb_csv(path)
    if suffix == ".xlsx":
        return [
            {normalize_header(key): value for key, value in row.items()}
            for row in read_xlsx_rows(path)
        ]
    raise ValueError(f"Unsupported DKB export type: {path}")


def dkb_export_files(path: Path) -> list[Path]:
    if path.is_file():
        return [path]
    return sorted(
        file
        for file in path.iterdir()
        if file.is_file() and file.suffix.lower() in {".csv", ".xlsx"}
    )


def build_import_rows(dkb_path: Path) -> list[dict[str, str]]:
    quantity_rows: list[dict[str, str]] = []

    for source in dkb_export_files(dkb_path):
        for row in read_dkb_rows(source):
            isin = normalize_isin(row.get("isin"))
            date = parse_german_date(row.get("datum der erstellung"))
            quantity = parse_german_number(row.get("stueckzahl"))
            if not isin or not date:
                continue

            depot_number = row.get("depotnummer", "").strip()
            wkn = row.get("wkn", "").strip()
            note = note_from(source, depot_number, wkn)
            if quantity is not None:
                quantity_rows.append(
                    {
                        "isin": isin,
                        "date": date,
                        "quantity": format_number(quantity),
                        "notes": note,
                    }
                )

    return quantity_rows


def integrate_dkb_export(
    dkb_path: Path,
    manual_workbook: Path,
    remove_example_rows: bool,
) -> tuple[dict[str, int], dict[str, list[dict[str, str]]]]:
    imported_quantity_rows = build_import_rows(dkb_path)
    scalar_rows = read_sheet_or_empty(manual_workbook, "ScalarValues")
    date_rows = read_sheet_or_empty(manual_workbook, "DateValuePairs")
    quantity_rows = read_sheet_or_empty(manual_workbook, "QuantityDatePairs")
    online_rows = read_sheet_or_empty(manual_workbook, ONLINE_VALUES_SHEET)

    if remove_example_rows:
        date_rows = [row for row in date_rows if not is_example_row(row)]
        quantity_rows = [row for row in quantity_rows if not is_example_row(row)]

    added_quantity_rows = append_unique(
        quantity_rows,
        imported_quantity_rows,
        ["isin", "date"],
    )

    sheets = {
        "ScalarValues": scalar_rows,
        "DateValuePairs": date_rows,
        "QuantityDatePairs": quantity_rows,
        ONLINE_VALUES_SHEET: online_rows,
    }
    stats = {
        "source_files": len(dkb_export_files(dkb_path)),
        "imported_quantity_rows": len(imported_quantity_rows),
        "added_quantity_rows": added_quantity_rows,
    }
    return stats, sheets


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
        description="Import DKB depot exports into Input_Data/fund_manual_values.xlsx."
    )
    parser.add_argument("--dkb-path", type=Path, default=input_data_dir / "DKB")
    parser.add_argument("--manual-workbook", type=Path, default=input_data_dir / "fund_manual_values.xlsx")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be imported without writing.")
    parser.add_argument("--no-backup", action="store_true", help="Do not create a timestamped .bak.xlsx file.")
    parser.add_argument(
        "--remove-example-rows",
        action="store_true",
        help="Remove rows whose notes mark them as generated example data before appending DKB data.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    load_project_env()
    args = build_arg_parser().parse_args(argv)
    dkb_path = args.dkb_path.resolve()
    manual_workbook = args.manual_workbook.resolve()

    if not dkb_path.exists():
        print(f"DKB path not found: {dkb_path}", file=sys.stderr)
        return 1
    if not manual_workbook.exists():
        print(f"Manual workbook not found: {manual_workbook}", file=sys.stderr)
        return 1

    stats, sheets = integrate_dkb_export(
        dkb_path,
        manual_workbook,
        remove_example_rows=args.remove_example_rows,
    )
    print(f"DKB export files found: {stats['source_files']}")
    print(f"Quantity rows found in DKB exports: {stats['imported_quantity_rows']}")
    print(f"Quantity rows added: {stats['added_quantity_rows']}")

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
