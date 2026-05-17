from CL_Banking import CL_Banking
from pathlib import Path
import calendar
from CL_Tables import CL_Tables
import pandas as pd

current_dir = Path(__file__).resolve().parent
workbook_name = "Funds.xlsx"
fallback_workbook_name = "Funds.updated.xlsx"
funds_sheet_name = "Overview"
history_sheet_name = "History"
date_column_name = "Date"

bk = CL_Banking()
bk.tab.set_path(current_dir)
bk.tab.load_xlsx(workbook_name, funds_sheet_name)
bk.tab.reduce_columns(['Bezeichnung','ISIN','WKN'])
bk.tab.show_colnames()
bk.tab.show_table()

tab = CL_Tables()
tab.set_path(current_dir)
tab.load_xlsx(workbook_name, history_sheet_name)


target_year = 2015
target_month = 5
target_month_name = calendar.month_name[target_month]


def normalize_isin(raw_isin):
    return str(raw_isin).strip()


def ensure_history_table(history_tab, isin_values):
    columns = list(history_tab.DB.columns)
    looks_like_funds_sheet = set(['Bezeichnung', 'ISIN', 'WKN']).issubset(columns)

    if history_tab.DB.empty or (looks_like_funds_sheet and date_column_name not in columns):
        history_tab.DB = pd.DataFrame(columns=[date_column_name])

    if date_column_name not in history_tab.DB.columns:
        history_tab.DB.insert(0, date_column_name, pd.Series(dtype="object"))

    for isin in isin_values:
        if isin not in history_tab.DB.columns:
            history_tab.DB[isin] = pd.NA

    ordered_isin_columns = [isin for isin in isin_values if isin in history_tab.DB.columns]
    other_columns = [
        col for col in history_tab.DB.columns
        if col not in [date_column_name] + ordered_isin_columns
    ]
    history_tab.DB = history_tab.DB[[date_column_name] + ordered_isin_columns + other_columns]


isin_list = [normalize_isin(isin) for isin in bk.tab.DB['ISIN'] if pd.notna(isin)]
ensure_history_table(tab, isin_list)

target_day = calendar.monthrange(target_year, target_month)[1]
target_date = f"{target_year:04d}-{target_month:02d}-{target_day:02d}"
row_data = {column: pd.NA for column in tab.DB.columns}
row_data[date_column_name] = target_date

for ISIN in isin_list:
    try:
        quote = bk.get_fund_quote_by_isin_for_month(ISIN, target_year, target_month, "EUR")
        row_data[ISIN] = quote.price
        print(
            f"{quote.isin}:\t{quote.name}:\t{quote.price} {quote.currency}:\t"
            f"{quote.timestamp_utc}"
        )
    except Exception as err:
        row_data[ISIN] = pd.NA
        print(f"{ISIN}:\tNo {target_month_name} historical value ({err}) -> NaN")

existing_rows = tab.DB[date_column_name].astype(str) == target_date
new_row_df = pd.DataFrame([row_data])
if existing_rows.any():
    tab.DB.loc[existing_rows, list(row_data.keys())] = new_row_df.iloc[0].tolist()
else:
    tab.DB.loc[len(tab.DB)] = row_data

try:
    tab.save_xlsx(workbook_name, history_sheet_name)
    print(f"Saved updated history sheet to {current_dir / workbook_name}")
except PermissionError:
    tab.save_xlsx(fallback_workbook_name, history_sheet_name)
    print(
        f"Workbook is locked. Saved updated history sheet to "
        f"{current_dir / fallback_workbook_name} instead."
    )

tab.show_table()

    

