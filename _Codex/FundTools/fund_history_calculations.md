# Fund History Plot Calculations

This document describes the values calculated by `fund_history_tool.py` for the
HTML report plots and the exported `extended_fund_data.json`.

## Notation

For one fund:

- `q_t`: quoted single-unit fund value on date `t`
- `Q_t`: number of fund units held on date `t`
- `V_t`: total fund value on date `t`
- `I_t`: cumulative invested amount through date `t`
- `D_t`: cumulative dividends through date `t`
- `S_t`: cumulative sell proceeds through date `t`
- `P_t`: absolute profit through date `t`
- `R_t`: relative profit through date `t`, in percent

Manual date/value series come from the workbook:

- `quantity`: fund units held from a date onward
- `invest`: cash invested on a date
- `dividend`: dividend received on a date
- `sell`: sell proceeds received on a date

Dates are compared as ISO dates (`YYYY-MM-DD`).

## Quantity At A Date

For report plots, the active quantity is the latest quantity entry with a date
less than or equal to the quote date:

```text
Q_t = latest quantity point Q_i where date_i <= t
```

If no quantity exists for `t`, no total-value or profit point is plotted for
that date.

For the `extended_fund_data.json` export, the same rule is used, except a fund
with a known sell date has quantity forced to zero after the sell date:

```text
Q_t = 0, if sell_date exists and t > sell_date
```

## Cumulative Manual Values

For cumulative series such as invested amount, dividends, and sell proceeds:

```text
I_t = sum(invest_i)   for all invest dates date_i <= t
D_t = sum(dividend_i) for all dividend dates date_i <= t
S_t = sum(sell_i)     for all sell dates date_i <= t
```

For yearly calculations, only values strictly after the year-start quote date
and up to the year-end quote date are included:

```text
I_(a,b] = sum(invest_i)   for a < date_i <= b
D_(a,b] = sum(dividend_i) for a < date_i <= b
S_(a,b] = sum(sell_i)     for a < date_i <= b
```

## Single Fund Price Plot

The left panel of each fund chart plots the raw quoted single-unit value:

```text
price_t = q_t
```

If a buy date is available, the secondary right axis labels the price relative
to the quote on or after the buy date:

```text
buy_index = first quote date t where t >= buy_date
buy_value = q_buy_index

relative_price_axis(tick) = (tick / buy_value - 1) * 100
```

This relative price is used only for axis labels, not as a plotted line.

## Single Fund Total Value Plot

The middle panel of each fund chart plots total value:

```text
V_t = q_t * Q_t
```

Only dates with a defined quantity are plotted.

## Single Fund Profit Plot

The right panel of each fund chart plots absolute profit and, when possible,
relative profit.

Absolute profit:

```text
P_t = V_t - I_t + D_t + S_t
```

Relative profit:

```text
R_t = (P_t / I_t) * 100, if I_t > 0
```

The absolute profit line uses the left axis. The relative profit line uses the
right percent axis.

## Portfolio Allocation Plot

The portfolio allocation pie chart uses the latest available total value for
each fund.

For each fund, the latest total value is:

```text
V_latest = q_latest * Q_latest
```

where `q_latest` is the most recent quote that has a defined quantity.

The portfolio total is:

```text
portfolio_total = sum(V_latest_fund)
```

Each fund share is:

```text
share_fund = V_latest_fund / portfolio_total
share_percent_fund = share_fund * 100
```

The pie slice angle is proportional to `share_fund`.

## Profit By Fund Plot

The `Profit by fund` horizontal bar plot uses the latest available value for
each fund.

Latest total value:

```text
V_latest = q_latest * Q_latest
```

Cumulative values at the latest quote date:

```text
I_latest = sum(invest_i)   where date_i <= latest_date
D_latest = sum(dividend_i) where date_i <= latest_date
S_latest = sum(sell_i)     where date_i <= latest_date
```

Absolute profit:

```text
P_latest = V_latest - I_latest + D_latest + S_latest
```

Relative profit label:

```text
R_latest = (P_latest / I_latest) * 100, if I_latest > 0
```

The bar length represents `P_latest`. The text label also includes
`R_latest` when it can be calculated.

## Relative Profit By Year Plot

The `Relative profit by year` vertical bar plot uses each fund's value at the
start and end of each calendar year found in the quote history.

For a given year:

```text
a = first quote date in the year
b = last quote date in the year
V_a = q_a * Q_a
V_b = q_b * Q_b
```

The in-year cash-flow sums are:

```text
I_(a,b] = sum(invest_i)   where a < date_i <= b
D_(a,b] = sum(dividend_i) where a < date_i <= b
S_(a,b] = sum(sell_i)     where a < date_i <= b
```

The plotted yearly relative profit is:

```text
yearly_relative_profit =
    (V_b - V_a - I_(a,b] + D_(a,b] + S_(a,b]) / V_a * 100
```

The denominator is the fund value at the start of the year. If `V_a <= 0`, the
year is skipped for that fund.

## Total Profit Over Time Plot

The `Total profit over time` plot sums absolute profit across all funds for
each report timeline date.

For each fund and date `t`, the latest quote at or before `t` is used:

```text
q_t = latest quote q_i where quote_date_i <= t
```

The fund profit at `t` is the same absolute profit used in the individual fund
profit plot:

```text
P_t = V_t - I_t + D_t + S_t
V_t = q_t * Q_t
```

The plotted portfolio profit is:

```text
portfolio_profit_t = sum(P_t_fund)
```

Funds without a quote at or before `t`, or without a defined quantity at `t`,
are skipped for that date.

The same plot also shows one vertical bar per calendar year. For a year with
first plotted date `a` and last plotted date `b`, the bar value is:

```text
year_profit = portfolio_profit_b - portfolio_profit_a
```

Year boundary grid lines are drawn at the first plotted date of each new
calendar year.

## Extended Fund Data Export

`extended_fund_data.json` is written as an output artifact. The HTML report
does not read it back in.

The exported `single_value` series is:

```text
single_value_t = q_t
```

unless a manual `single_value` series exists, in which case the manual series
is exported instead.

The exported `quantity` series is:

```text
quantity_t = manual quantity series, if present
quantity_t = workbook quantity series, otherwise
```

The exported `total_value` series is:

```text
total_value_t = q_t * Q_t
```

unless a manual `total_value` series exists, in which case the manual series is
exported instead.

For exported calculated total value, quantity is zero after the inferred or
manual sell date:

```text
Q_t = 0, if sell_date exists and t > sell_date
total_value_t = q_t * Q_t
```
