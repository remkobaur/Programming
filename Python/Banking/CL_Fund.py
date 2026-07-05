import pandas as pd

class CL_Fund_Signals:
    def __init__(self):
        self.rel_single = pd.Series(dtype=float)
        self.quantity = pd.Series(dtype=float)
        self.rel_quantity = pd.Series(dtype=float)
        self.value_single = pd.Series(dtype=float)
        self.value_all = pd.Series(dtype=float)
        self.changes = pd.Series(dtype=float)
        self.invest = pd.Series(dtype=float)
        self.dividend = pd.Series(dtype=float)
        self.changes_cumsum = pd.Series(dtype=float)
        self.total = pd.Series(dtype=float)
        self.rel_total = pd.Series(dtype=float)
        self.profit= pd.Series(dtype=float)
        self.profit_relative = pd.Series(dtype=float)
        self.invest = pd.Series(dtype=float)
        self.dividend = pd.Series(dtype=float)
        self.start_date = None
        self.start_value = None
        
        
    def interpolate(self, target_date_signal: pd.Series):
        def _prepare_series(signal: pd.Series) -> pd.Series:
            if signal.empty:
                return signal
            # reindex with method=ffill requires unique, monotonic index
            signal = signal.sort_index()
            signal = signal[~signal.index.duplicated(keep="last")]
            return signal

        # Align all signals to one shared, sorted target index.
        idx = pd.DatetimeIndex(target_date_signal.index).drop_duplicates().sort_values()
        active_mask = pd.Series(True, index=idx)

        # Derive the active holding window from quantity and reuse it for all signals.
        zero_quantity_date = None
        if not self.quantity.empty:
            self.quantity = _prepare_series(self.quantity)
            q_src = pd.to_numeric(self.quantity, errors="coerce")
            zero_idx = q_src[q_src == 0].index
            if len(zero_idx) > 0:
                zero_quantity_date = zero_idx.min()
            # Treat zero quantity as missing before interpolation so it is ignored in value_all.
            q_src = q_src.mask(q_src == 0, float('nan'))
            q_idx = q_src.index.union(idx).sort_values()
            q = q_src.reindex(q_idx).interpolate(method="time").ffill().reindex(idx)
            first_date = q_src.first_valid_index()
            if first_date is not None:
                q[q.index < first_date] = float('nan')
            if zero_quantity_date is not None:
                q[q.index > zero_quantity_date] = float('nan')  # !!!!!!!!!!!!!!!!!!!!!!!!!
                # q[q.index >= zero_quantity_date] = float('nan')  # !!!!!!!!!!!!!!!!!!!!!!!!!
            self.quantity = q
            active_mask = self.quantity.notna()
        if not self.value_single.empty:
            self.value_single = _prepare_series(self.value_single)
            v_src = pd.to_numeric(self.value_single, errors="coerce")
            v_idx = v_src.index.union(idx).sort_values()
            v = v_src.reindex(v_idx).interpolate(method="time").ffill().reindex(idx)
            first_date = self.value_single.first_valid_index()
            if first_date is not None:
                v[v.index < first_date] = float('nan')
            # Use the same active quantity mask for consistent interpretation.
            v[~active_mask] = float('nan')
            self.value_single = v
        if not self.changes.empty:
            self.changes = _prepare_series(self.changes)
            c_src = pd.to_numeric(self.changes, errors="coerce")
            # Resample changes to the new index, summing values in each interval
            # The target idx must be sorted and unique
            idx_sorted = idx
            # Extend left boundary so events at or before idx_sorted[0] are captured
            # Use -infinity as leftmost bin edge so all early events are included in the first bin
            extended_bins = pd.Index([pd.Timestamp.min]).append(idx_sorted)
            # Bin the changes into the intervals defined by idx
            binned = pd.cut(c_src.index, bins=extended_bins, right=True, labels=idx_sorted)
            summed = c_src.groupby(binned, observed=False).sum()
            # Create a new series aligned to idx, fill with summed values, 0 elsewhere
            c = pd.Series(0.0, index=idx_sorted, dtype=float)
            c.loc[summed.index] = summed.values
            # Use the same active quantity mask for consistent interpretation.
            c[~active_mask.reindex(c.index, fill_value=False)] = float('nan')
            self.changes = c
        
        # # Mask quantity, value_single, and changes where quantity is 0 or NaN
        # if not self.quantity.empty:
        #     zero_mask = (self.quantity == 0) | self.quantity.isna()
        #     self.quantity[zero_mask] = float('nan')
        #     if not self.value_single.empty:
        #         self.value_single[zero_mask] = float('nan')
        #     if not self.changes.empty:
        #         self.changes[zero_mask] = float('nan')
        
        self.calculate()
            
    def calculate(self,reset_profit=False):        
        # changes_cumsum 
        self.changes_cumsum = self.changes.cumsum()                
        # value_all      
        if not self.quantity.empty and not self.value_single.empty:
            self.value_all = self.quantity * self.value_single
            # Find first valid value and timestamp in value_all
            first_idx = self.value_all.first_valid_index()
            if first_idx is not None:
                first_value = self.value_all.loc[first_idx]
                self.start_date = first_idx
                self.start_value = first_value
                # print(f"First valid value_all - timestamp: {first_idx}, value: {first_value}")
            
        start_value_index = self.value_all.first_valid_index() 
        if start_value_index is None:    
            print("No valid value_all found to determine start_value for profit_relative calculation.")
            return
        start_value = self.value_all.loc[start_value_index] 
        
        # total 
        if not self.value_all.empty and not self.changes_cumsum.empty:
            self.total = self.value_all + self.changes_cumsum
        # rel_single
        if not self.value_single.empty:
            idx0 = self.value_single.first_valid_index()
            if idx0 is not None:
                v0 = self.value_single.loc[idx0]
                if v0 != 0:
                    self.rel_single = (self.value_single - v0) / v0 * 100
        # rel_total
        t0 = None
        if not self.total.empty:
            idx0 = self.total.first_valid_index()            
            if idx0 is not None:
                t0 = self.total.loc[idx0]
                if t0 != 0:
                    self.rel_total = (self.total-t0) /t0 *100
        # invest/dividend
        if not self.changes.empty:
            self.invest = self.changes.apply(lambda x: -x if x < 0 else 0)
            self.dividend = self.changes.apply(lambda x: x if x > 0 else 0)    
        # profit            
        self.profit= self.value_all - self.invest.cumsum() + self.dividend.cumsum() 
        
        idx0 = self.profit.first_valid_index()
        if idx0 is None:
            return        
        p0 = self.profit.loc[idx0]
        
        if reset_profit or (p0/start_value > 0.5):  # if initial profit is more than 50%, it is likely that we missed the initial invest event, so we reset profit to 0 at the first valid timestamp
            self.profit -= p0   
        
        
        start_value_index = self.value_all.first_valid_index() 
        if start_value_index is not None:    
            self.profit_relative = self.profit/ start_value * 100
        
        
        
        if not self.quantity.empty :
            # find max value in quantity
            max_quantity = self.quantity.max()
            if max_quantity > 0:
                self.rel_quantity = self.quantity / max_quantity * 100
    
    def to_dataframe(self) -> pd.DataFrame:
        df = pd.DataFrame({
            "quantity": self.quantity,
            "value_single": self.value_single,
            "value_all": self.value_all,
            "changes": self.changes,
            "changes_cumsum": self.changes_cumsum,
            "total": self.total,
            "rel_single": self.rel_single,
            "rel_total": self.rel_total,
            "invest": self.invest,
            "dividend": self.dividend,
            "profit": self.profit,
            "profit_relative": self.profit_relative
        })
        return df


class CL_Fund:    
    def __init__(self, isin, name=None, quantity=None, start_date=None, lineColor="blue"):
        self.isin = isin
        self.name = name
        self.quantity = quantity
        self.start_date = start_date
        self.sold = False
        self.purchase_price = None
        self.df_history = pd.DataFrame(columns=["date", "quantity", "value"])
        self.df_change = pd.DataFrame(columns=["date", "value"])
        self.df_total = pd.DataFrame(columns=["date", "total_value"]) 
        self.lineColor = lineColor
        self.signals = CL_Fund_Signals()

    def import_df_data(self, df_history: pd.DataFrame, df_change: pd.DataFrame):
        # Filter by ISIN if column exists, then keep only required columns
        if "isin" in df_history.columns:
            df_history = df_history[df_history["isin"] == self.isin]
        if "isin" in df_change.columns:
            df_change = df_change[df_change["isin"] == self.isin]
        self.df_history = df_history.loc[:, [col for col in ["date", "quantity", "value"] if col in df_history.columns]].copy()
        self.df_change = df_change.loc[:, [col for col in ["date", "value"] if col in df_change.columns]].copy()

    def create_signals(self,start_date=None, end_date=None):
        if self.df_history.empty:
            return

        self.signals.quantity = self.df_history.set_index("date")["quantity"]
        self.signals.value_single = self.df_history.set_index("date")["value"] 
        
        if self.df_change.empty:
            return
        self.signals.changes = self.df_change.set_index("date")["value"]
        
        if start_date is not None:
            self.signals.quantity = self.signals.quantity[self.signals.quantity.index >= start_date]
            self.signals.value_single = self.signals.value_single[self.signals.value_single.index >= start_date]
            self.signals.changes = self.signals.changes[self.signals.changes.index >= start_date]
        if end_date is not None:
            self.signals.quantity = self.signals.quantity[self.signals.quantity.index <= end_date]
            self.signals.value_single = self.signals.value_single[self.signals.value_single.index <= end_date]
            self.signals.changes = self.signals.changes[self.signals.changes.index <= end_date]
            
        self.signals.calculate()
        
        # self.signals.interpolate()
    