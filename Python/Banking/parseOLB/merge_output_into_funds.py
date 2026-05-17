from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


DEFAULT_TABS = ("History", "Quantity", "Invest")


def _normalize_date_column(df: pd.DataFrame) -> pd.DataFrame:
    if "Date" in df.columns:
        df = df.copy()
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    return df


def _date_first_sorted_columns(df: pd.DataFrame) -> pd.DataFrame:
    if "Date" not in df.columns:
        return df
    other_cols = sorted([col for col in df.columns if col != "Date"], key=lambda value: str(value))
    return df[["Date"] + other_cols]


def _merge_tab(funds_df: pd.DataFrame, output_df: pd.DataFrame) -> pd.DataFrame:
    funds_df = _normalize_date_column(funds_df)
    output_df = _normalize_date_column(output_df)

    if "Date" not in funds_df.columns or "Date" not in output_df.columns:
        return funds_df

    merged = pd.concat([funds_df, output_df], ignore_index=True, sort=False)
    merged = merged.dropna(subset=["Date"])

    # Keep the row from OutputData when both files contain the same Date.
    merged = merged.drop_duplicates(subset=["Date"], keep="last")
    merged = merged.sort_values("Date").reset_index(drop=True)
    merged = _date_first_sorted_columns(merged)
    return merged


def merge_output_into_funds(
    funds_path: Path,
    output_path: Path,
    tabs: tuple[str, ...] = DEFAULT_TABS,
) -> dict[str, tuple[int, int]]:
    if not funds_path.exists():
        raise FileNotFoundError(f"Funds file not found: {funds_path}")
    if not output_path.exists():
        raise FileNotFoundError(f"Output file not found: {output_path}")

    funds_xl = pd.ExcelFile(funds_path)
    output_xl = pd.ExcelFile(output_path)

    funds_sheets = {sheet: pd.read_excel(funds_path, sheet_name=sheet) for sheet in funds_xl.sheet_names}
    output_sheets = {sheet: pd.read_excel(output_path, sheet_name=sheet) for sheet in output_xl.sheet_names}

    stats: dict[str, tuple[int, int]] = {}
    for tab in tabs:
        if tab not in funds_sheets or tab not in output_sheets:
            continue
        before_rows = len(funds_sheets[tab])
        merged = _merge_tab(funds_sheets[tab], output_sheets[tab])
        after_rows = len(merged)
        funds_sheets[tab] = merged
        stats[tab] = (before_rows, after_rows)

    with pd.ExcelWriter(funds_path, engine="openpyxl", mode="w") as writer:
        for sheet in funds_xl.sheet_names:
            funds_sheets[sheet].to_excel(writer, sheet_name=sheet, index=False)

    return stats


def _parse_args() -> argparse.Namespace:
    current_dir = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(
        description="Merge matching tabs from OutputData.xlsx into Funds.xlsx by Date."
    )
    parser.add_argument(
        "--funds",
        type=Path,
        default=current_dir / "Funds.xlsx",
        help="Path to Funds workbook (default: parseOLB/Funds.xlsx)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=current_dir / "OutputData.xlsx",
        help="Path to OutputData workbook (default: parseOLB/OutputData.xlsx)",
    )
    parser.add_argument(
        "--tabs",
        nargs="+",
        default=list(DEFAULT_TABS),
        help="Sheet names to merge (default: History Quantity Invest)",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    stats = merge_output_into_funds(
        funds_path=args.funds,
        output_path=args.output,
        tabs=tuple(args.tabs),
    )

    if not stats:
        print("No matching tabs were merged.")
        return

    print(f"Updated workbook: {args.funds}")
    for tab, (before_rows, after_rows) in stats.items():
        print(f"{tab}: {before_rows} -> {after_rows} rows")


if __name__ == "__main__":
    main()
