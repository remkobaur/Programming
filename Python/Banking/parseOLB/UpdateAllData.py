import parse_Auszüge
import parse_DepotAuszug
import parse_Erträge
import pandas as pd
import sys
from pathlib import Path


CURRENT_DIR = Path(__file__).resolve().parent
BANKING_DIR = CURRENT_DIR.parent
if str(BANKING_DIR) not in sys.path:
    sys.path.insert(0, str(BANKING_DIR))

from CL_Tables import CL_Tables


def parse_all():
    parse_Auszüge.main()
    parse_DepotAuszug.main()
    parse_Erträge.main()   


def _find_column(columns, candidates):
    lookup = {str(col).lower(): col for col in columns}
    for candidate in candidates:
        key = candidate.lower()
        if key in lookup:
            return lookup[key]
    return None


def _extract_date_series(series: pd.Series) -> pd.Series:
    raw = series.astype(str)
    
    # Try ISO format first (yyyy-mm-dd) - most unambiguous
    parsed = pd.to_datetime(raw, errors="coerce", format="%Y-%m-%d")
    if parsed.notna().any():
        return parsed
    
    # Try day-first format for ambiguous dates (dd.mm.yyyy or dd/mm/yyyy)
    parsed = pd.to_datetime(raw, errors="coerce", dayfirst=True)
    if parsed.notna().any():
        return parsed

    # Fallback for file names like 20250131_statement.pdf
    digits = raw.str.extract(r"(\d{8})", expand=False)
    return pd.to_datetime(digits, format="%Y%m%d", errors="coerce")


def create_OutputData():
    # current_dir = Path(__file__).resolve().parent
    current_dir = Path(r"E:\_NAS\0_Remko\Unterlagen\Banking\_Data\Parse_OLB")
    xlsFile = current_dir / "OutputData.xlsx"
    
    # Load data into CL_Tables instances
    auszug_table = CL_Tables()
    auszug_table.load_xlsx(current_dir / "Auszüge.xlsx")

    depot_auszug_table = CL_Tables()
    depot_auszug_table.load_xlsx(current_dir / "Depotauszug.xlsx")

    erträge_table = CL_Tables()
    erträge_table.load_xlsx(current_dir /  "Ertragsausschüttungen.xlsx")

    # get unique ISINs from all tables
    unique_isins = set(auszug_table.DB["ISIN"].dropna().astype(str).str.strip().unique()) | \
        set(depot_auszug_table.DB.get("ISIN", depot_auszug_table.DB.get("isin", pd.Series(dtype=str))).dropna().astype(str).str.strip().unique()) | \
        set(erträge_table.DB["ISIN"].dropna().astype(str).str.strip().unique())

    depot_df = depot_auszug_table.DB.copy()
    isin_col = _find_column(depot_df.columns, ["isin", "ISIN"])
    price_col = _find_column(depot_df.columns, ["price", "Preis", "kurs"])
    date_col = _find_column(depot_df.columns, ["datum", "date", "Date"])
    quant_col = _find_column(depot_df.columns, ["quantity"])


    if isin_col is None or price_col is None or date_col is None:
        raise KeyError(
            "Depot_Auszug.xlsx must contain ISIN, price, and date/file columns. "
            f"Found columns: {list(depot_df.columns)}"
        )

    depot_df[isin_col] = depot_df[isin_col].astype(str).str.strip()
    depot_df = depot_df[depot_df[isin_col].isin(unique_isins)]
    depot_df[price_col] = pd.to_numeric(depot_df[price_col], errors="coerce")
    depot_df["_date"] = _extract_date_series(depot_df[date_col])

    depot_df = depot_df.dropna(subset=["_date", isin_col, price_col])
    if depot_df.empty:
        raise ValueError("No valid depot rows with date, ISIN, and price found.")

    pivot_prices = depot_df.pivot_table(
        index="_date",
        columns=isin_col,
        values=price_col,
        aggfunc="last",
    ).sort_index()
    
    pivot_quant = depot_df.pivot_table(
        index="_date",
        columns=isin_col,
        values=quant_col,
        aggfunc="last",
    ).sort_index()

    ordered_isins = sorted(col for col in pivot_prices.columns if str(col) in unique_isins)
    if ordered_isins:
        pivot_prices = pivot_prices[ordered_isins]

    output_table = CL_Tables()
    output_table.DB = pivot_prices.reset_index().rename(columns={"_date": "Date"})
    output_table.save_xlsx(xlsFile, sheet_name="History", index=False)
    
    output_table = CL_Tables()
    output_table.DB = pivot_quant.reset_index().rename(columns={"_date": "Date"})
    output_table.save_xlsx(xlsFile, sheet_name="Quantity", index=False)
    
    
    
    depot_df = auszug_table.DB.copy()
    isin_col = _find_column(depot_df.columns, [ "ISIN"])
    price_col = _find_column(depot_df.columns, ["Betrag"])
    date_col = _find_column(depot_df.columns, ["Buchungsdatum"])
    
    depot_df[isin_col] = depot_df[isin_col].astype(str).str.strip()
    depot_df = depot_df[depot_df[isin_col].isin(unique_isins)]
    depot_df[price_col] = pd.to_numeric(depot_df[price_col], errors="coerce")
    depot_df["_date"] = _extract_date_series(depot_df[date_col])
    
    pivot_quant = depot_df.pivot_table(
        index="_date",
        columns=isin_col,
        values=price_col,
        aggfunc="last",
    ).sort_index()
    output_table.DB = pivot_quant.reset_index().rename(columns={"_date": "Date"})
    output_table.save_xlsx(xlsFile, sheet_name="Invest", index=False)
    
    print("Created OutputData.xlsxwith dates as rows and ISINs as columns.")
    return output_table.DB

    
    
if __name__ == "__main__":
    # parse_all()
    create_OutputData()