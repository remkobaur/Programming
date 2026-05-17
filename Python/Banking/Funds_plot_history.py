from CL_Tables import CL_Tables
from pathlib import Path
import matplotlib.pyplot as plt
import pandas as pd

current_dir = Path(__file__).resolve().parent
current_dir = r"E:\_NAS\0_Remko\Unterlagen\Banking"
workbook_name = "Funds.xlsx"
funds_sheet_name = "Overview"
history_sheet_name = "History"
date_column_name = "Date"

use_relative_derivation = False

ov = CL_Tables()
ov.set_path(current_dir)
ov.load_xlsx(workbook_name, funds_sheet_name)
# ov.show_colnames()
# ov.show_table()

invest_db = CL_Tables()
invest_db.set_path(current_dir)
invest_db.load_xlsx(workbook_name, "Invest")
invest_db.show_table()

# Process invest data to get total invested per date
invest_data = invest_db.DB.copy()
if date_column_name in invest_data.columns:
	invest_data[date_column_name] = pd.to_datetime(invest_data[date_column_name], errors="coerce")
	invest_data = invest_data.dropna(subset=[date_column_name])
	
	# Sum all investments by date (skip ISIN column and Date column)
	numeric_cols = [col for col in invest_data.columns if col != date_column_name and pd.api.types.is_numeric_dtype(invest_data[col])]
	invest_totals = invest_data.groupby(date_column_name)[numeric_cols].sum().sum(axis=1)
	invest_totals.index.name = date_column_name
	invest_totals = invest_totals.sort_index()
	invest_cumsum = invest_totals.cumsum()
else:
	invest_totals = pd.Series()
	invest_cumsum = pd.Series()


def normalize_isin(value):
	return str(value).strip()


isin_to_name = {}
if "ISIN" in ov.DB.columns and "Bezeichnung" in ov.DB.columns:
	for _, row in ov.DB[["ISIN", "Bezeichnung"]].dropna(subset=["ISIN"]).iterrows():
		isin = normalize_isin(row["ISIN"])
		name = str(row.get("Bezeichnung", "")).strip()
		if isin and name:
			isin_to_name[isin] = name

isin_to_bestand = {}
if "ISIN" in ov.DB.columns and "Bestand" in ov.DB.columns:
	for _, row in ov.DB[["ISIN", "Bestand"]].dropna(subset=["ISIN"]).iterrows():
		isin = normalize_isin(row["ISIN"])
		bestand = pd.to_numeric(row.get("Bestand"), errors="coerce")
		if isin and pd.notna(bestand):
			isin_to_bestand[isin] = float(bestand)

tab = CL_Tables()
tab.set_path(current_dir)
tab.load_xlsx(workbook_name, history_sheet_name)
# tab.show_colnames()
# tab.show_table()

db = tab.DB.copy()

if date_column_name not in db.columns:
	raise KeyError(f"Missing required date column: {date_column_name}")

db[date_column_name] = pd.to_datetime(db[date_column_name], errors="coerce")
db = db.dropna(subset=[date_column_name]).sort_values(by=date_column_name)
db = db.set_index(date_column_name)

isin_columns = [col for col in db.columns if col != date_column_name]
if not isin_columns:
	raise ValueError("No ISIN columns found to plot.")

for col in isin_columns:
	db[col] = pd.to_numeric(db[col], errors="coerce")


def interpolate_from_first_valid(series: pd.Series) -> pd.Series:
	result = series.copy()
	first_valid_idx = result.first_valid_index()
	if first_valid_idx is None:
		return result

	# Interpolate only from the first valid value onward (time-aware on Date index).
	result.loc[first_valid_idx:] = result.loc[first_valid_idx:].interpolate(method="index").ffill()
	return result


for col in isin_columns:
	db[col] = interpolate_from_first_valid(db[col])

db = db.reset_index()

# Align invest_totals and invest_cumsum to all dates in db (History)
if not invest_totals.empty:
	db_dates = pd.DatetimeIndex(pd.to_datetime(db[date_column_name]))
	all_dates = db_dates.union(invest_totals.index).sort_values()
	# Keep raw invest values as "last known value" on missing dates.
	invest_totals = invest_totals.reindex(all_dates).ffill().reindex(db_dates).fillna(0)
	invest_cumsum = invest_cumsum.reindex(all_dates).ffill().reindex(db_dates).fillna(0)

fig, (ax_top, ax_middle, ax_bottom) = plt.subplots(
	3, 1, figsize=(12, 12), sharex=True, gridspec_kw={"height_ratios": [3, 1, 1]}
)

plotted_any = False
scaled_db = pd.DataFrame({date_column_name: db[date_column_name]})
plot_db = pd.DataFrame({date_column_name: db[date_column_name]})
scaled_columns = []
for col in isin_columns:
	valid_rows = db[[date_column_name, col]].dropna()
	if valid_rows.empty:
		continue
	isin = normalize_isin(col)
	scale = isin_to_bestand.get(isin, 1.0)
	scaled_db[col] = db[col] * scale / 1000

	if use_relative_derivation:
		first_valid_idx = scaled_db[col].first_valid_index()
		if first_valid_idx is None:
			continue
		first_value = scaled_db.at[first_valid_idx, col]
		if pd.isna(first_value) or first_value == 0:
			continue
		plot_db[col] = (scaled_db[col] / first_value - 1.0) * 100.0
	else:
		plot_db[col] = scaled_db[col]

	scaled_columns.append(col)
	legend_label = isin_to_name.get(isin, isin)
	valid_plot_rows = plot_db[[date_column_name, col]].dropna()
	ax_top.plot(valid_plot_rows[date_column_name], valid_plot_rows[col], marker="o", linewidth=2, label=legend_label)
	plotted_any = True

if not plotted_any:
	raise ValueError("No numeric ISIN data available to plot.")

# Summarize all ISIN lines as one total value series per date.
summary_raw_series = scaled_db[scaled_columns].sum(axis=1, skipna=True, min_count=1)
if use_relative_derivation:
	summary_first_valid = summary_raw_series.first_valid_index()
	if summary_first_valid is None:
		raise ValueError("No summarized data available to plot.")
	summary_first_value = summary_raw_series.loc[summary_first_valid]
	if pd.isna(summary_first_value) or summary_first_value == 0:
		raise ValueError("Summary first valid value is invalid for relative derivation.")
	summary_series = (summary_raw_series / summary_first_value - 1.0) * 100.0
else:
	summary_series = summary_raw_series

summary_rows = pd.DataFrame({date_column_name: scaled_db[date_column_name], "Total": summary_series}).dropna()

if summary_rows.empty:
	raise ValueError("No summarized data available to plot.")

if use_relative_derivation:
	ax_top.set_title("Fund History by ISIN (Relative to First Valid Value)")
	ax_top.set_ylabel("Relative Change [%]")
else:
	ax_top.set_title("Fund History by ISIN (Scaled by Bestand)")
	ax_top.set_ylabel("Scaled Value [kEur]")
ax_top.grid(True, alpha=0.3)
ax_top.legend(title="Bezeichnung", loc="best")

ax_middle.step(
	summary_rows[date_column_name],
	summary_rows["Total"],
	color="black",
	marker="o",
	linewidth=2,
    where="post",
	label="Total",
)
if not invest_totals.empty:
	invest_plot = invest_totals.reindex(pd.DatetimeIndex(pd.to_datetime(summary_rows[date_column_name]))).fillna(0) / 1000
	ax_middle.step(
		summary_rows[date_column_name],
		-1*invest_plot.values,
		color="blue",
		marker="o",
		linewidth=2,
		linestyle="--",
		where="post",
		label="Invested",
	)
if use_relative_derivation:
	ax_middle.set_title("Summary (Relative Portfolio Change)")
	ax_middle.set_ylabel("Relative Change [%]")
else:
	ax_middle.set_title("Summary (Sum of Scaled ISIN Series)")
	ax_middle.set_ylabel("Total [kEur]")
ax_middle.grid(True, alpha=0.3)
ax_middle.legend(loc="best")

# Calculate and plot the difference between absolute sum and invested amount
if not invest_totals.empty:
	# Align invest_totals with summary_rows by date
	summary_with_invest = summary_rows.copy()
	summary_with_invest[date_column_name] = pd.to_datetime(summary_with_invest[date_column_name])
	summary_with_invest = summary_with_invest.set_index(date_column_name)
	
	# Create difference series: absolute_sum - cumulative invested
	invested_cum_aligned = invest_cumsum.reindex(summary_with_invest.index).fillna(0) / 1000
	difference_series = (summary_with_invest["Total"] + invested_cum_aligned).dropna()
	
	if not difference_series.empty:
		difference_df = pd.DataFrame({
			date_column_name: difference_series.index,
			"Difference": difference_series.values
		})
		
		ax_bottom.plot(
			difference_df[date_column_name],
			difference_df["Difference"],
			color="red",
			marker="s",
			linewidth=2,
			label="Absolute Sum - Invested",
		)

ax_bottom.set_title("Difference: Absolute Sum minus Cumulative Invested")
ax_bottom.set_ylabel("Difference [kEur]")
ax_bottom.set_xlabel("Date")
ax_bottom.grid(True, alpha=0.3)
handles, labels = ax_bottom.get_legend_handles_labels()
if handles:
	ax_bottom.legend(loc="best")

plt.tight_layout()
plt.show()

