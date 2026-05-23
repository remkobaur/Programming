from CL_Fund import CL_Fund
from os import path
import os
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np

class CL_SubplotConfig:
        signalName: str = None  # "value_all", "rel_total", "changes_cumsum", "total"
        xlabel: str = "Date"
        ylabel: str = "<not defined>"
        title: str = "<not defined>"
        plot_mode: str = "step"
        plot_total: bool = False  # If True, plot the total fund instead of individual funds. Overrides plot_mode if True.
        def __init__(self, signalName: str=None, xlabel: str = "Date", ylabel: str = "<not defined>", title: str = "<not defined>", plot_mode: str = "step", plot_total: bool = False):
            self.signalName = signalName  
            self.xlabel = xlabel
            self.ylabel = ylabel
            self.title = title
            self.plot_mode = plot_mode
            self.plot_total = plot_total    

class CL_DepotManager:

        
    olb_path = path.realpath(path.join(path.dirname(path.abspath(__file__)),'parseOLB' ))
    olb_file_changes    = path.join(olb_path, "Auszüge.xlsx")
    olb_file_history    = path.join(olb_path, "Depotauszug.xlsx")
    xls_db_path = path.realpath(path.join(path.dirname(path.abspath(__file__)) ))
    xls_db_file = path.join(xls_db_path, "DepotManager_DB.xlsx")
    legend_mode = "isin"  # or "name"
    
    def __init__(self):
        self.funds = []
        self.total_fund = CL_Fund(isin="Total", name="Total", lineColor="black")
        self.df_history = pd.DataFrame(columns=["date", "isin","name", "quantity", "value"])
        self.df_change = pd.DataFrame(columns=["date", "isin", "value" , "description"])
        self.max_xticks = 5
        
        
    #region import/export
    def xls_export_df_data(self):
        try:
            os.makedirs(self.xls_db_path, exist_ok=True)

            with pd.ExcelWriter(self.xls_db_file, mode="w") as writer:
                self.df_history.to_excel(writer, sheet_name="History", index=False)
                self.df_change.to_excel(writer, sheet_name="Changes", index=False)

            print(f"Exported history and changes to: {self.xls_db_file}")
        except Exception as e:
            print(f"Could not export dataframes to Excel: {e}")
        
    def xls_import_df_data(self,xls_file=None):
        if xls_file is None:
            xls_file = self.xls_db_file
        # Keep a stable schema even if the source file is missing columns.
        hist_cols = ["date", "isin", "name", "quantity", "value"]
        chg_cols = ["date", "isin", "value", "description"]

        try:
            df_hist = pd.read_excel(xls_file, sheet_name="History")
            self.df_history = df_hist.loc[:, [col for col in hist_cols if col in df_hist.columns]].copy()
            for col in hist_cols:
                if col not in self.df_history.columns:
                    self.df_history[col] = pd.NA
            self.df_history = self.df_history[hist_cols]
        except Exception as e:
            print(f"Could not import history from DB file: {e}")
            self.df_history = pd.DataFrame(columns=hist_cols)

        try:
            df_chg = pd.read_excel(xls_file, sheet_name="Changes")
            self.df_change = df_chg.loc[:, [col for col in chg_cols if col in df_chg.columns]].copy()
            for col in chg_cols:
                if col not in self.df_change.columns:
                    self.df_change[col] = pd.NA
            self.df_change = self.df_change[chg_cols]
        except Exception as e:
            print(f"Could not import changes from DB file: {e}")
            self.df_change = pd.DataFrame(columns=chg_cols)

        # Normalize date columns for downstream sorting/interpolation.
        if "date" in self.df_history.columns:
            self.df_history["date"] = pd.to_datetime(self.df_history["date"], errors="coerce")
        if "date" in self.df_change.columns:
            self.df_change["date"] = pd.to_datetime(self.df_change["date"], errors="coerce")

        self.df_merge_same_date_isin_item()
        self.df_sort()
        
    def import_funds_xlsx_to_history(self, funds_xlsx_path):
            """
            Import data from Funds.xlsx (Overview, Quantity, History sheets) and append new rows to History sheet in DepotManager_DB.xlsx.
            Sheets:
                - Overview: columns [ISIN, Bezeichnung]
                - Quantity: index=date, columns=ISIN, values=quantity
                - History: index=date, columns=ISIN, values=value
            """
            try:
                overview = pd.read_excel(funds_xlsx_path, sheet_name="Overview")
                quantity = pd.read_excel(funds_xlsx_path, sheet_name="Quantity", index_col=0)
                value = pd.read_excel(funds_xlsx_path, sheet_name="History", index_col=0)
                invest = pd.read_excel(funds_xlsx_path, sheet_name="Invest", index_col=0)
            except Exception as e:
                print(f"Could not read Funds.xlsx: {e}")
                return

            # Build ISIN to name mapping
            isin_to_name = dict(zip(overview["ISIN"], overview["Bezeichnung"]))

            # Melt quantity and value to long format
            quantity_long = quantity.reset_index().melt(id_vars=quantity.index.name or "index", var_name="isin", value_name="quantity")
            quantity_long = quantity_long.rename(columns={quantity.index.name or "index": "date"})
            value_long = value.reset_index().melt(id_vars=value.index.name or "index", var_name="isin", value_name="value")
            value_long = value_long.rename(columns={value.index.name or "index": "date"})

            # Merge on date and isin
            merged = pd.merge(quantity_long, value_long, on=["date", "isin"], how="outer")
            merged["name"] = merged["isin"].map(isin_to_name)
            merged = merged[["date", "isin", "name", "quantity", "value"]]
            merged["date"] = pd.to_datetime(merged["date"], errors="coerce")

            # Remove rows with no ISIN, date, or any NaN values
            merged = merged.dropna()

            # Only add rows if (date, isin) combination doesn't already exist
            if not self.df_history.empty:
                existing_keys = set(zip(self.df_history["date"], self.df_history["isin"]))
                new_rows = merged[~merged.apply(lambda row: (row["date"], row["isin"]) in existing_keys, axis=1)]
            else:
                new_rows = merged

            if not new_rows.empty:
                if self.df_history.empty:
                    self.df_history = new_rows.reset_index(drop=True)
                else:
                    self.df_history = pd.concat([self.df_history, new_rows], ignore_index=True)
                self.df_sort()
                print(f"Added {len(new_rows)} new rows to df_history from Funds.xlsx.")
            else:
                print("No new rows to add from Funds.xlsx.")

            # Process invest sheet -> df_change
            invest_long = invest.reset_index().melt(id_vars=invest.index.name or "index", var_name="isin", value_name="value")
            invest_long = invest_long.rename(columns={invest.index.name or "index": "date"})
            invest_long["description"] = "invest"
            invest_long = invest_long[["date", "isin", "value", "description"]]
            invest_long["date"] = pd.to_datetime(invest_long["date"], errors="coerce")
            invest_long = invest_long.dropna()
            invest_long = invest_long[invest_long["value"] != 0]

            if not self.df_change.empty:
                existing_keys_chg = set(zip(self.df_change["date"], self.df_change["isin"]))
                new_change_rows = invest_long[~invest_long.apply(lambda row: (row["date"], row["isin"]) in existing_keys_chg, axis=1)]
            else:
                new_change_rows = invest_long

            if not new_change_rows.empty:
                if self.df_change.empty:
                    self.df_change = new_change_rows.reset_index(drop=True)
                else:
                    self.df_change = pd.concat([self.df_change, new_change_rows], ignore_index=True)
                self.df_sort()
                print(f"Added {len(new_change_rows)} new invest rows to df_change from Funds.xlsx.")
            else:
                print("No new invest rows to add to df_change from Funds.xlsx.")

        
    def OLB_import(self):
        # Import history
        try:
            df_hist = pd.read_excel(self.olb_file_history)
            col_map_hist = {"datum": "date", "isin": "isin", "name": "name", "quantity": "quantity", "price": "value"}
            df_hist = df_hist[[col for col in col_map_hist if col in df_hist.columns]].rename(columns=col_map_hist)
            
            # Only add rows if (date, isin) combination doesn't already exist
            if not self.df_history.empty:
                existing_keys = set(zip(self.df_history["date"], self.df_history["isin"]))
                new_rows = df_hist[~df_hist.apply(lambda row: (row["date"], row["isin"]) in existing_keys, axis=1)]
                self.df_history = pd.concat([self.df_history, new_rows], ignore_index=True)
                print(f"Imported {len(new_rows)} new history rows from OLB file.")
            else:
                self.df_history = df_hist
                print(f"Imported {len(df_hist)} new history rows from OLB file.")
        except Exception as e:
            print(f"Could not import history: {e}")
            if self.df_history.empty:
                self.df_history = pd.DataFrame(columns=["date", "isin", "name", "quantity", "value"])

        # Import changes
        try:
            df_chg = pd.read_excel(self.olb_file_changes)
            col_map_chg = {"Wertdatum": "date", "ISIN": "isin", "Betrag": "value", "Beschreibung": "description"}
            df_chg = df_chg[[col for col in col_map_chg if col in df_chg.columns]].rename(columns=col_map_chg)
            if "value" in df_chg.columns:
                df_chg["value"] = pd.to_numeric(df_chg["value"], errors="coerce")
                df_chg = df_chg[df_chg["value"] != 0]
            
            # Only add rows if (date, isin) combination doesn't already exist
            if not self.df_change.empty:
                existing_keys = set(zip(self.df_change["date"], self.df_change["isin"]))
                new_rows = df_chg[~df_chg.apply(lambda row: (row["date"], row["isin"]) in existing_keys, axis=1)]
                self.df_change = pd.concat([self.df_change, new_rows], ignore_index=True)
                print(f"Imported {len(new_rows)} new changes rows from OLB file.")
            else:
                self.df_change = df_chg
                print(f"Imported {len(df_chg)} new changes rows from OLB file.")
        except Exception as e:
            print(f"Could not import changes: {e}")
            if self.df_change.empty:
                self.df_change = pd.DataFrame(columns=["date", "isin", "value", "description"])
        
        self.df_merge_same_date_isin_item()
        self.df_sort()        
            
    def df_sort(self):
        if "date" in self.df_history.columns:
            self.df_history = self.df_history.sort_values(by="date").reset_index(drop=True)
        if "date" in self.df_change.columns:
            self.df_change = self.df_change.sort_values(by="date").reset_index(drop=True)
            
    def df_merge_same_date_isin_item(self):
        # Remove exact duplicates w.r.t. date, isin, quantity, value
        cols = [col for col in ["date", "isin", "quantity", "value"] if col in self.df_history.columns]
        self.df_history = self.df_history.drop_duplicates(subset=cols, keep="first").reset_index(drop=True)

        # Only keep one row per (date, isin), sum quantity, keep other columns from first row
        if not self.df_history.empty and {"date", "isin", "quantity"}.issubset(self.df_history.columns):
            def agg_func(group):
                row = group.iloc[0].copy()
                row["quantity"] = group["quantity"].sum()
                return row
            self.df_history = (
                self.df_history
                .groupby(["date", "isin"], as_index=False, dropna=False)
                .apply(agg_func)
                .reset_index(drop=True)
            )

    def df_filter_isin(self,isin_list=[])  :
        if not isin_list:
            return
        self.df_history = self.df_history[self.df_history["isin"].isin(isin_list)].reset_index(drop=True)
        self.df_change = self.df_change[self.df_change["isin"].isin(isin_list)].reset_index(drop=True)
    def df_filter_isin_not(self,isin_list=[])  :
        if not isin_list:
            return
        self.df_history = self.df_history[~self.df_history["isin"].isin(isin_list)].reset_index(drop=True)
        self.df_change = self.df_change[~self.df_change["isin"].isin(isin_list)].reset_index(drop=True)
    #endregion
    
    def create_funds(self):
        if "isin" not in self.df_history.columns:
            print("History data missing 'isin' column, cannot create funds.")
            return
        if "isin" not in self.df_change.columns:
            print("Changes data missing 'isin' column, cannot create funds.")
            return
        
        unique_isins = self.df_history["isin"].dropna().unique()
        # Build a larger qualitative palette so many funds still get distinct colors.
        palette_names = ["tab20", "tab20b", "tab20c", "Set3", "Dark2", "Paired", "Accent"]
        palette_colors = []
        for palette_name in palette_names:
            cmap = plt.colormaps.get_cmap(palette_name)
            if hasattr(cmap, "colors"):
                palette_colors.extend(list(cmap.colors))
            else:
                palette_colors.extend([cmap(x) for x in np.linspace(0, 1, cmap.N, endpoint=False)])

        needed = len(unique_isins)
        if needed > len(palette_colors):
            extra = plt.colormaps.get_cmap("hsv").resampled(needed - len(palette_colors))
            palette_colors.extend([extra(i) for i in range(extra.N)])

        for idx, isin in enumerate(unique_isins):
            name = "<Not Defined>"
            df_rows = self.df_history[self.df_history["isin"] == isin]
            if not df_rows.empty and "name" in df_rows.columns:
                name = df_rows.iloc[0]["name"]

            line_color = palette_colors[idx % len(palette_colors)]
            fund = CL_Fund(isin=isin, name=name, lineColor=line_color)
            fund.import_df_data(self.df_history, self.df_change)
            fund.create_signals()
            self.funds.append(fund)
            # print(f"Created fund for ISIN: {isin}, Name: {name}, with {len(df_rows)} history rows and line color: {line_color}")
            print(f"Created fund for ISIN: {isin}, Name: {name}")
        
    def create_total_fund(self):
        self.total_fund = CL_Fund(isin="TOTAL", name="Total", lineColor="black")
        self.total_fund.name = "Total"
        self.total_fund.isin = "Total"
        self.total_fund.lineColor = "black"
        for fund in self.funds:
            if fund.signals is None:
                print(f"Fund {fund.isin} has no signals, skipping in total fund creation.")
                continue    
            self.total_fund.signals.value_all = self.total_fund.signals.value_all.add(fund.signals.value_all, fill_value=0)
            self.total_fund.signals.changes_cumsum = self.total_fund.signals.changes_cumsum.add(fund.signals.changes_cumsum, fill_value=0)
            self.total_fund.signals.invest = self.total_fund.signals.invest.add(fund.signals.invest, fill_value=0)
            self.total_fund.signals.dividend = self.total_fund.signals.dividend.add(fund.signals.dividend, fill_value=0)
            self.total_fund.signals.profit = self.total_fund.signals.profit.add (fund.signals.profit, fill_value=0)
            # For relative profit, we need to handle division by zero carefully.    
            
        self.total_fund.signals.dividend = self.total_fund.signals.dividend.cumsum()
        self.total_fund.signals.invest = self.total_fund.signals.invest.cumsum()
        
    def interpolate_signals(self,freq='M'):
        """_summary_

        Args:
            freq (str, optional): _description_. Defaults to 'M': # quarterly: 'Q', monthly: 'M', daily: 'D'
        """        
        
        #find min/max date in history and change
        min_date = None
        max_date = None
        if "date" in self.df_history.columns and not self.df_history["date"].empty:
            min_date_hist = self.df_history["date"].min()
            max_date_hist = self.df_history["date"].max()
            min_date = min_date_hist if min_date is None else min(min_date, min_date_hist)
            max_date = max_date_hist if max_date is None else max(max_date, max_date_hist)
            
        #create date range as pandas series
        if min_date is not None and max_date is not None:
            date_range = pd.date_range(start=min_date, end=max_date, freq=freq) # quarterly: 'Q', monthly: 'M', daily: 'D'
        print (f"Interpolating signals with freq='{freq}' for date range: {min_date} to {max_date}, total periods: {len(date_range)}") 
        for fund in self.funds:
            fund.signals.interpolate(target_date_signal=pd.Series(index=date_range))
    #region plots
    
    #region subplots
    def create_subplot_with_total_by_signalname(self, subplot_config=CL_SubplotConfig(), ax=None):
        if not self.funds:
            print("No funds available to plot.")
            return

        created_figure = False
        if ax is None:
            fig, ax = plt.subplots()
            created_figure = True

        if subplot_config.plot_total and subplot_config.plot_mode not in ["legend_only"]:
            ax2 = ax.twinx()  # Create a second y-axis

        if subplot_config.plot_mode == "step":
            for fund in self.funds:
                signal = getattr(fund.signals, subplot_config.signalName, None)
                if signal is None or signal.empty:
                    print(f"No data to for <{subplot_config.signalName}> of fund: {fund.isin}")
                    continue

                ax.step(signal.index, signal.values, 
                        label=fund.isin if self.legend_mode == "isin" else fund.name, 
                        where='post', color=fund.lineColor)  # Use the assigned line color

        if subplot_config.plot_total:
            # Plot self.total_fund.signals on the second y-axis
            total_signal = getattr(self.total_fund.signals, subplot_config.signalName, None)
            if total_signal is not None and not total_signal.empty:
                ax2.step(total_signal.index, total_signal.values, label="Total", color=self.total_fund.lineColor, linestyle="--")
                ax2.set_ylabel("Total Signal")

        if subplot_config.plot_mode not in ["legend_only"]:
            ax.set_title(subplot_config.title)
            ax.set_xlabel(subplot_config.xlabel)
            ax.set_ylabel(subplot_config.ylabel)
            # Keep at most max_xticks labels, but recompute ticks when zooming/panning.
            max_ticks = max(int(self.max_xticks), 1)
            locator = mdates.AutoDateLocator(minticks=3, maxticks=max_ticks)
            ax.xaxis.set_major_locator(locator)
            ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(locator))
            # With shared x-axes, matplotlib hides upper subplot labels by default.
            # Re-enable them so every subplot shows x tick labels.
            ax.tick_params(axis="x", which="both", labelbottom=True)
            ax.grid()
            if self.legend_mode in ["isin", "name"]:
                ax.legend()
                if subplot_config.plot_total and subplot_config.plot_mode not in ["legend_only"]:
                    ax2.legend(loc="upper left")
        
        if subplot_config.plot_mode == "legend_only":
            for fund in self.funds:
                label = f"[{fund.isin}]  {fund.name}"
                color = fund.lineColor
                ax.plot([], [], label=label, color=color)  # Add dummy lines for legend
            # Center the legend
            if subplot_config.plot_total:
                ax.plot([], [], label="Total", color=self.total_fund.lineColor, linestyle="--")  # Add dummy lines for legend
            ax.legend(loc='center', bbox_to_anchor=(0.5, 0.5), frameon=False)
            # Hide axis and grid
            ax.set_axis_off()
            ax.grid(False)
        
        if created_figure:
            plt.show()
          
    def create_subplot_by_signalname(self, subplot_config=CL_SubplotConfig(), ax=None):
        if not self.funds:
            print("No funds available to plot.")
            return

        created_figure = False
        if ax is None:
            _, ax = plt.subplots()
            created_figure = True

        if subplot_config.plot_mode == "step":
            for fund in self.funds:
                signal = getattr(fund.signals, subplot_config.signalName, None)
                if signal is None or signal.empty:
                    print(f"No data to for <{subplot_config.signalName}> of fund: {fund.isin}")
                    continue

                ax.step(signal.index, signal.values, 
                        label=fund.isin if self.legend_mode == "isin" else fund.name, 
                        # marker=".",
                        where='post', color=fund.lineColor)  # Use the assigned line color
        elif subplot_config.plot_mode == "stem":
            for fund in self.funds:
                signal = getattr(fund.signals, subplot_config.signalName, None)
                if signal is None or signal.empty:
                    print(f"No data to for <{subplot_config.signalName}> of fund: {fund.isin}")
                    continue

                markerline, stemlines, baseline = ax.stem(
                        signal.index, signal.values,
                        label=fund.isin if self.legend_mode == "isin" else fund.name,
                        linefmt='-', markerfmt='', basefmt=' ')
                markerline.set_color(fund.lineColor)
                stemlines.set_color(fund.lineColor)
        elif subplot_config.plot_mode == "combined":
            combined = None
            for fund in self.funds:
                signal = getattr(fund.signals, subplot_config.signalName, None)
                if signal is None or signal.empty:
                    continue
                combined = signal if combined is None else combined.add(signal, fill_value=0)

                if combined is None or combined.empty:
                    print(f"No <{subplot_config.signalName}> data available to plot.")
                    return

                ax.step(combined.index, combined.values, label=fund.isin if self.legend_mode == "isin" else fund.name, 
                        where='post', color=fund.lineColor)  # Use the assigned line color
        elif subplot_config.plot_mode == "total":            
            signal = getattr(self.total_fund.signals, subplot_config.signalName, None)
            if signal is None or signal.empty:
                print(f"Total plot: No <{subplot_config.signalName}> data available to plot.")
                return
            
            ax.step(signal.index, signal.values, label=self.total_fund.isin if self.legend_mode == "isin" else self.total_fund.name, 
                        where='post', color=self.total_fund.lineColor)  # Use the assigned line color 
        elif subplot_config.plot_mode == "sum_absolute":
            combined = None
            for fund in self.funds:
                signal = getattr(fund.signals, subplot_config.signalName, None)
                if signal is None or signal.empty:
                    continue
                combined = signal if combined is None else combined.add(signal, fill_value=0)

            if combined is None or combined.empty:
                print(f"No <{subplot_config.signalName}> data available to plot.")
                return
            relative = combined
            ax.step(relative.index, relative.values, where='post', label='Sum Absolute', color='red')
        elif subplot_config.plot_mode == "sum_relative":
            combined = None
            for fund in self.funds:
                signal = getattr(fund.signals, subplot_config.signalName, None)
                if signal is None or signal.empty:
                    continue
                combined = signal if combined is None else combined.add(signal, fill_value=0)

            if combined is None or combined.empty:
                print(f"No <{subplot_config.signalName}> data available to plot.")
                return

            # Find the first valid (non-NaN, non-zero) value for normalization
            first_valid_value = combined[combined.first_valid_index()] if combined.first_valid_index() is not None else None
            if first_valid_value is None or first_valid_value == 0:
                print("Cannot create relative sum plot because the first valid value is zero or missing.")
                return

            relative = combined / first_valid_value
            ax.step(relative.index, relative.values, where='post', label='Sum Relative', color='red')

        elif subplot_config.plot_mode == "legend_only":
            for fund in self.funds:
                label = f"[{fund.isin}]  {fund.name}"
                color = fund.lineColor
                ax.plot([], [], label=label, color=color)  # Add dummy lines for legend
            # Center the legend
            if subplot_config.plot_total:
                ax.plot([], [], label="Total", color=self.total_fund.lineColor, linestyle="--")  # Add dummy lines for legend
            ax.legend(loc='center', bbox_to_anchor=(0.5, 0.5), frameon=False)
            # Hide axis and grid
            ax.set_axis_off()
            ax.grid(False)
        else:
            print(f"Unknown plot mode: {subplot_config.plot_mode}")
            
        if subplot_config.plot_mode not in ["legend_only"]:
            ax.set_title(subplot_config.title)
            ax.set_xlabel(subplot_config.xlabel)
            ax.set_ylabel(subplot_config.ylabel)
            # Keep at most max_xticks labels, but recompute ticks when zooming/panning.
            max_ticks = max(int(self.max_xticks), 1)
            locator = mdates.AutoDateLocator(minticks=3, maxticks=max_ticks)
            ax.xaxis.set_major_locator(locator)
            ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(locator))
            # With shared x-axes, matplotlib hides upper subplot labels by default.
            # Re-enable them so every subplot shows x tick labels.
            ax.tick_params(axis="x", which="both", labelbottom=True)
            ax.grid()
            if self.legend_mode in ["isin", "name"]:
                ax.legend() 
        if created_figure:
            plt.show()
          
    def subplot_legend_only(self, ax=None):
        self.create_subplot_by_signalname(subplot_config=CL_SubplotConfig(
            signalName="-", 
            xlabel="", 
            ylabel="", 
            title="Legend",
            plot_mode="legend_only",
            plot_total=True
            ), ax=ax)
        
    def subplot_Funds_relative_value(self, ax=None):
        self.create_subplot_by_signalname(subplot_config=CL_SubplotConfig(
            signalName="rel_single", 
            xlabel="Date", 
            ylabel="Relative Single [%]", 
            title="Relative Value for each Fund",
            plot_mode="step"
            ), ax=ax)
    def subplot_Funds_single_value(self, ax=None):
        self.create_subplot_by_signalname(subplot_config=CL_SubplotConfig(
            signalName="value_single", 
            xlabel="Date", 
            ylabel="Single Value [EUR]", 
            title="Single Value for each Fund",
            plot_mode="step"
            ), ax=ax)
    
    def subplot_Funds_relative_total(self, ax=None):
        self.create_subplot_by_signalname(subplot_config=CL_SubplotConfig(
            signalName="rel_total", 
            xlabel="Date", 
            ylabel="Relative Total [%]", 
            title="Relative Value for each Fund",
            plot_mode="step"
            ), ax=ax)
    def subplot_Funds_quantity(self, ax=None):
        self.create_subplot_by_signalname(subplot_config=CL_SubplotConfig(
            signalName="quantity", 
            xlabel="Date", 
            ylabel="Quantity [-]", 
            title="Quantity for each Fund",
            plot_mode="step"
            ), ax=ax)
    def subplot_Funds_profit(self, ax=None):
        self.create_subplot_by_signalname(subplot_config=CL_SubplotConfig(
            signalName="profit", 
            xlabel="Date", 
            ylabel="Profit [EUR]", 
            title="Profit for each Fund",
            plot_mode="step"
            ), ax=ax)
    def subplot_Funds_profit_relative(self, ax=None):
        self.create_subplot_by_signalname(subplot_config=CL_SubplotConfig(
            signalName="profit_relative", 
            xlabel="Date", 
            ylabel="Relative Profit [%]", 
            title="Relative Profit for each Fund",
            plot_mode="step"
            ), ax=ax)
    def subplot_Funds_absolute(self, ax=None):
        self.create_subplot_by_signalname(subplot_config=CL_SubplotConfig(
            signalName="value_all", 
            xlabel="Date", 
            ylabel="Absolute Value [EUR]", 
            title="Absolute Value for each Fund",
            plot_mode="step"
            ), ax=ax)
    
    def subplot_Funds_change(self, ax=None):
        self.create_subplot_by_signalname(subplot_config=CL_SubplotConfig(
            signalName="changes", 
            xlabel="Date", 
            ylabel="Change [EUR]", 
            title="Change for each Fund",
            plot_mode="stem"
            ), ax=ax)       
        
    def subplot_Funds_dividend(self, ax=None):
        self.create_subplot_by_signalname(subplot_config=CL_SubplotConfig(
            signalName="dividend", 
            xlabel="Date", 
            ylabel="Dividend [EUR]", 
            title="Dividend for each Fund",
            plot_mode="step"
            ), ax=ax)  
        
    def subplot_Funds_invest(self, ax=None):
        self.create_subplot_by_signalname(subplot_config=CL_SubplotConfig(
            signalName="invest", 
            xlabel="Date", 
            ylabel="Invest", 
            title="Invest for each Fund",
            plot_mode="step"
            ), ax=ax)  
    
    def subplot_Funds_total(self, ax=None):
        self.create_subplot_by_signalname(subplot_config=CL_SubplotConfig(
            signalName="total", 
            xlabel="Date", 
            ylabel="Total Value", 
            title="Total Value for each Fund",
            plot_mode="step"
            ), ax=ax)     
                         
    # def subplot_sum_total(self, ax=None):
    #     self.create_subplot_by_signalname(subplot_config=CL_SubplotConfig(
    #         signalName="total", 
    #         xlabel="Date", 
    #         ylabel="Total Value", 
    #         title="Sum Total Value for All Funds",
    #         plot_mode="combined"
    #         ), ax=ax)     
    def subplot_total_profit(self, ax=None):
        self.create_subplot_by_signalname(subplot_config=CL_SubplotConfig(
            signalName="profit", 
            xlabel="Date", 
            ylabel="Profit [euro]", 
            title="Absolute Profit over all Funds",
            plot_mode="sum_absolute"
            ), ax=ax)             
    def subplot_sum_absolute(self, ax=None):
        self.create_subplot_by_signalname(subplot_config=CL_SubplotConfig(
            signalName="total", 
            xlabel="Date", 
            ylabel="Absolute Total Value [%]", 
            title="Total Win (sum)",
            plot_mode="sum_absolute"
            ), ax=ax)     
    
    def subplot_sum_relative(self, ax=None):
        self.create_subplot_by_signalname(subplot_config=CL_SubplotConfig(
            signalName="total", 
            xlabel="Date", 
            ylabel="Relative Total Value [%]", 
            title="Relative Sum Total Value for All Funds",
            plot_mode="sum_relative"
            ), ax=ax)     
        
    #endregion # subplots
    
    def plot_all(self):
        self.legend_mode = "none"  # "name" or "isin" or "none"
        fig, axs = plt.subplots(3, 3, figsize=(15, 10), sharex=True)
        
        #region column 1 
        self.create_subplot_with_total_by_signalname(subplot_config=CL_SubplotConfig(
            signalName="value_all", 
            xlabel="Date", 
            ylabel="sum value [EUR]", 
            title="Sum Value of each Fund",
            plot_mode="step",
            plot_total=True
            ), ax=axs[0,0])
        # self.subplot_Funds_absolute(ax=axs[0, 0])    
        # self.subplot_Funds_change(ax=axs[1, 0])   
        # self.subplot_Funds_invest(ax=axs[1, 0])       
        self.create_subplot_with_total_by_signalname(subplot_config=CL_SubplotConfig(
            signalName="invest", 
            xlabel="Date", 
            ylabel="invest [EUR]", 
            title="Invest of each Fund",
            plot_mode="step",
            plot_total=True
            ), ax=axs[1,0])    

        self.create_subplot_with_total_by_signalname(subplot_config=CL_SubplotConfig(
            signalName="dividend", 
            xlabel="Date", 
            ylabel="dividend [EUR]", 
            title="Dividend of each Fund",
            plot_mode="step",
            plot_total=True
            ), ax=axs[2,0])    
        # self.subplot_Funds_total(ax=axs[2, 0])                 
        # self.subplot_Funds_dividend(ax=axs[2, 0]) 
        #endregion
           
        #region column 2         

        self.create_subplot_with_total_by_signalname(subplot_config=CL_SubplotConfig(
            signalName="value_single_rel", 
            xlabel="Date", 
            ylabel="relative value [-]", 
            title="relative single value of each Fund",
            plot_mode="step",
            plot_total=False
            ), ax=axs[1, 1])
        self.create_subplot_with_total_by_signalname(subplot_config=CL_SubplotConfig(
            signalName="quantity", 
            xlabel="Date", 
            ylabel="Quantity [-]", 
            title="Quantity of each Fund",
            plot_mode="step",
            plot_total=False
            ), ax=axs[2, 1])
        #endregion
        
        #region column 3 
        self.create_subplot_with_total_by_signalname(subplot_config=CL_SubplotConfig(
            signalName="profit", 
            xlabel="Date", 
            ylabel="Profit [EUR]", 
            title="Profit for each Fund",
            plot_mode="step",
            plot_total=True
            ), ax=axs[0, 2])
        
        self.create_subplot_with_total_by_signalname(subplot_config=CL_SubplotConfig(
            signalName="profit_relative", 
            xlabel="Date", 
            ylabel="Profit [EUR]", 
            title="Relative Profit for each Fund",
            plot_mode="step",
            plot_total=False
            ), ax=axs[1, 2])
        
        self.create_subplot_with_total_by_signalname(subplot_config=CL_SubplotConfig(
            signalName="Legend", 
            xlabel="Date", 
            ylabel="Profit [EUR]", 
            title="Profit for each Fund",
            plot_mode="legend_only",
            plot_total=True
            ), ax=axs[2, 2])
        #endregion
        plt.tight_layout()
        plt.show()  
        
    #endregion # plots

if __name__ == "__main__":
    dm = CL_DepotManager()
    # dm.legend_mode = "isin"  # "name"  or "isin" or "none"
    # dm.xls_import_df_data()
    dm.xls_import_df_data(path.join(dm.olb_path, "DepotManager_DB_Degussa_old.xlsx"))
    # dm.import_funds_xlsx_to_history(path.join(dm.olb_path, "Funds.xlsx"))
    dm.OLB_import()
    dm.xls_export_df_data()
    # dm.df_filter_isin(isin_list=["LU0323578657","LU0553164731"])  # LU only
    # dm.df_filter_isin(isin_list=["DE000DK09V66","DE000DK09WE5"])  # DEKA only
    # dm.df_filter_isin(isin_list=["DE000PF99QV6","DE0009769794"])  # e.g.["DE000DK09V66","DE000DK09WE5","DE0009769794"]
    dm.df_filter_isin_not(isin_list=["DE000A1A6QU4","DE000PF99QV6"])  # e.g. ["DE000A0Q4R37", "DE000A0Q4R38"]
    dm.create_funds()
    dm.interpolate_signals("M")    
    dm.create_total_fund()    
    dm.plot_all()