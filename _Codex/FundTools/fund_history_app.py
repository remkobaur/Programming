from __future__ import annotations

import argparse
import datetime as dt
import html
import shutil
import sys
import threading
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from fund_history_tool import (
    DateValue,
    Fund,
    QuantityPoint,
    Quote,
    configured_data_dir,
    configured_input_data_dir,
    ensure_manual_data_template,
    extract_funds_from_manual_data,
    extract_quantity_history_from_manual_data,
    fund_chart_markup,
    html_scalar_values_table,
    is_sold_fund,
    load_project_env,
    parse_excel_date,
    read_manual_fund_data,
    read_online_value_results,
    read_xlsx_rows,
    resolve_path,
    svg_portfolio_pie_chart,
    svg_portfolio_profit_bar_chart,
    svg_portfolio_total_profit_chart,
    svg_yearly_relative_profit_bar_chart,
)
from import_dkb_export import integrate_dkb_export, write_manual_workbook


Result = tuple[Fund, str | None, str | None, list[Quote], str | None]


def filter_quotes(quotes: list[Quote], start_date: str, end_date: str) -> list[Quote]:
    return [
        quote
        for quote in quotes
        if (not start_date or quote.date >= start_date)
        and (not end_date or quote.date <= end_date)
    ]


def filter_results(results: list[Result], start_date: str, end_date: str) -> list[Result]:
    return [
        (fund, source, symbol, filter_quotes(quotes, start_date, end_date), error)
        for fund, source, symbol, quotes, error in results
    ]


def all_quote_dates(results: list[Result]) -> list[str]:
    return sorted({quote.date for _fund, _source, _symbol, quotes, _error in results for quote in quotes})


def selected_tab(params: dict[str, list[str]]) -> str:
    tab = value_for(params, "tab", "overview")
    return tab if tab in {"overview", "single", "import", "options"} else "overview"


def value_for(params: dict[str, list[str]], name: str, default: str = "") -> str:
    values = params.get(name)
    return values[0] if values else default


def checked(params: dict[str, list[str]], name: str, default: bool = False) -> bool:
    if name not in params:
        return default
    return value_for(params, name).lower() in {"1", "true", "yes", "on"}


def query_with(params: dict[str, list[str]], **updates: str) -> str:
    merged = {key: values[:] for key, values in params.items()}
    for key, value in updates.items():
        if value == "":
            merged.pop(key, None)
        else:
            merged[key] = [value]
    return urllib.parse.urlencode(merged, doseq=True)


class FundHistoryApp:
    def __init__(self, manual_data_path: Path, dkb_path: Path) -> None:
        self.manual_data_path = manual_data_path
        self.dkb_path = dkb_path
        self.last_import_message = ""

    def load_data(self) -> tuple[
        list[dict[str, str]],
        list[Result],
        dict[str, str],
        dict[str, str],
        dict[str, str],
        dict[str, list[QuantityPoint]],
        dict[str, dict[str, list[DateValue]]],
    ]:
        ensure_manual_data_template(self.manual_data_path, [])
        manual_data = read_manual_fund_data(self.manual_data_path)
        scalar_rows = read_xlsx_rows(self.manual_data_path, "ScalarValues")
        funds = extract_funds_from_manual_data(manual_data)
        quantity_histories = extract_quantity_history_from_manual_data(manual_data)
        results = read_online_value_results(self.manual_data_path, funds)
        buy_dates = {
            isin: parse_excel_date(scalars.get("buy_date", ""))
            for isin, scalars in manual_data.scalars.items()
        }
        sell_dates = {
            isin: parse_excel_date(scalars.get("sell_date", ""))
            for isin, scalars in manual_data.scalars.items()
        }
        statuses = {
            isin: scalars.get("status", "")
            for isin, scalars in manual_data.scalars.items()
        }
        return scalar_rows, results, buy_dates, sell_dates, statuses, quantity_histories, manual_data.date_values

    def run_dkb_import(self, dry_run: bool) -> str:
        stats, sheets = integrate_dkb_export(
            self.dkb_path,
            self.manual_data_path,
            remove_example_rows=False,
        )
        lines = [
            f"DKB export files found: {stats['source_files']}",
            f"Quantity rows found in DKB exports: {stats['imported_quantity_rows']}",
            f"Quantity rows added: {stats['added_quantity_rows']}",
        ]
        if dry_run:
            lines.append("Preview only; workbook was not changed.")
            return "\n".join(lines)

        backup_path = self.manual_data_path.with_name(
            f"{self.manual_data_path.stem}.{dt.datetime.now().strftime('%Y%m%d_%H%M%S')}.bak.xlsx"
        )
        shutil.copy2(self.manual_data_path, backup_path)
        write_manual_workbook(self.manual_data_path, sheets)
        lines.append(f"Wrote backup: {backup_path}")
        lines.append(f"Wrote workbook: {self.manual_data_path}")
        return "\n".join(lines)

    def render(self, params: dict[str, list[str]]) -> str:
        scalar_rows, results, buy_dates, sell_dates, statuses, quantity_histories, manual_date_values = self.load_data()
        dates = all_quote_dates(results)
        default_start = dates[0] if dates else ""
        default_end = dates[-1] if dates else ""
        start_date = value_for(params, "start", default_start)
        end_date = value_for(params, "end", default_end)
        show_sold = checked(params, "show_sold", False)
        tab = selected_tab(params)

        visible_results = [
            result for result in results
            if show_sold or not is_sold_fund(result[0].isin, statuses, sell_dates)
        ]
        ranged_results = filter_results(visible_results, start_date, end_date)
        selected_isin = value_for(params, "fund")
        if not selected_isin and ranged_results:
            selected_isin = ranged_results[0][0].isin

        body = {
            "overview": self.render_overview(
                ranged_results,
                scalar_rows,
                quantity_histories,
                manual_date_values,
            ),
            "single": self.render_single(
                ranged_results,
                selected_isin,
                buy_dates,
                sell_dates,
                quantity_histories,
                manual_date_values,
                params,
            ),
            "import": self.render_import(),
            "options": self.render_options(params, dates, start_date, end_date, show_sold),
        }[tab]

        return self.document(
            tab,
            params,
            body,
            dates,
            start_date,
            end_date,
            show_sold,
            len(visible_results),
        )

    def render_overview(
        self,
        results: list[Result],
        scalar_rows: list[dict[str, str]],
        quantity_histories: dict[str, list[QuantityPoint]],
        manual_date_values: dict[str, dict[str, list[DateValue]]],
    ) -> str:
        charts = [
            svg_portfolio_pie_chart(results, quantity_histories),
            svg_portfolio_profit_bar_chart(results, quantity_histories, manual_date_values),
            svg_yearly_relative_profit_bar_chart(results, quantity_histories, manual_date_values),
            svg_portfolio_total_profit_chart(results, quantity_histories, manual_date_values),
            html_scalar_values_table(scalar_rows, quantity_histories),
        ]
        return "".join(charts)

    def render_single(
        self,
        results: list[Result],
        selected_isin: str,
        buy_dates: dict[str, str],
        sell_dates: dict[str, str],
        quantity_histories: dict[str, list[QuantityPoint]],
        manual_date_values: dict[str, dict[str, list[DateValue]]],
        params: dict[str, list[str]],
    ) -> str:
        options = []
        for fund, _source, _symbol, _quotes, _error in results:
            selected = " selected" if fund.isin == selected_isin else ""
            label = fund.name or fund.isin
            options.append(f'<option value="{html.escape(fund.isin)}"{selected}>{html.escape(label)}</option>')

        selected_result = next((result for result in results if result[0].isin == selected_isin), None)
        if selected_result is None:
            chart = "<section><h2>Single fund</h2><p>No fund is available for the selected options.</p></section>"
        else:
            fund, source, symbol, quotes, error = selected_result
            chart = fund_chart_markup(
                fund,
                source,
                symbol,
                quotes,
                error,
                buy_dates,
                sell_dates,
                quantity_histories,
                manual_date_values,
                interactive_points=True,
                show_data_markers=True,
            )

        hidden = hidden_inputs(params, exclude={"tab", "fund"})
        return f"""
<section class="toolbar">
  <form method="get">
    <input type="hidden" name="tab" value="single">
    {hidden}
    <label for="fund">Fund</label>
    <select id="fund" name="fund" onchange="this.form.submit()">{''.join(options)}</select>
  </form>
</section>
{chart}
""".strip()

    def render_import(self) -> str:
        message = (
            f"<pre>{html.escape(self.last_import_message)}</pre>"
            if self.last_import_message
            else "<p>No import has been run in this app session.</p>"
        )
        return f"""
<section>
  <h2>DKB quantity import</h2>
  <p class="compact">Source folder: <code>{html.escape(str(self.dkb_path))}</code></p>
  <p class="compact">Target workbook: <code>{html.escape(str(self.manual_data_path))}</code></p>
  <form method="post" action="/import/dkb">
    <button type="submit" name="mode" value="preview">Preview</button>
    <button type="submit" name="mode" value="run">Import quantities</button>
  </form>
  {message}
</section>
""".strip()

    def render_options(
        self,
        params: dict[str, list[str]],
        dates: list[str],
        start_date: str,
        end_date: str,
        show_sold: bool,
    ) -> str:
        hidden = hidden_inputs(params, exclude={"tab", "start", "end", "show_sold"})
        checked_attr = " checked" if show_sold else ""
        min_index = 0
        max_index = max(0, len(dates) - 1)
        start_index = dates.index(start_date) if start_date in dates else min_index
        end_index = dates.index(end_date) if end_date in dates else max_index
        return f"""
<section>
  <h2>Options</h2>
  <form method="get" class="options-form">
    <input type="hidden" name="tab" value="overview">
    {hidden}
    <div class="date-pair">
      <label for="start">Start date</label>
      <input id="start" name="start" type="date" value="{html.escape(start_date)}">
      <label for="end">End date</label>
      <input id="end" name="end" type="date" value="{html.escape(end_date)}">
    </div>
    <div class="range-pair" aria-label="Start and end date range">
      <div class="range-track"></div>
      <input id="startSlider" class="range-start" type="range" min="{min_index}" max="{max_index}" value="{start_index}">
      <input id="endSlider" class="range-end" type="range" min="{min_index}" max="{max_index}" value="{end_index}">
    </div>
    <label class="checkline">
      <input type="checkbox" name="show_sold" value="1"{checked_attr}>
      Show sold funds
    </label>
    <button type="submit">Apply</button>
  </form>
</section>
""".strip()

    def document(
        self,
        tab: str,
        params: dict[str, list[str]],
        body: str,
        dates: list[str],
        start_date: str,
        end_date: str,
        show_sold: bool,
        fund_count: int,
    ) -> str:
        nav = []
        for key, label in (
            ("overview", "Overview"),
            ("single", "Single Funds"),
            ("import", "Import"),
            ("options", "Options"),
        ):
            active = " active" if tab == key else ""
            nav.append(f'<a class="tab{active}" href="/?{query_with(params, tab=key)}">{label}</a>')
        sold_text = "including sold funds" if show_sold else "active funds only"
        return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Fund History App</title>
  <style>{APP_CSS}</style>
</head>
<body>
  <header>
    <h1>Fund History</h1>
    <p>{html.escape(start_date)} to {html.escape(end_date)} &middot; {fund_count} funds &middot; {sold_text}</p>
  </header>
  <nav>{''.join(nav)}</nav>
  <main>{body}</main>
  <script>
    window.availableDates = {dates!r};
    {APP_JS}
  </script>
</body>
</html>
"""


def hidden_inputs(params: dict[str, list[str]], exclude: set[str]) -> str:
    fields = []
    for key, values in params.items():
        if key in exclude:
            continue
        for value in values:
            fields.append(f'<input type="hidden" name="{html.escape(key)}" value="{html.escape(value)}">')
    return "".join(fields)


APP_CSS = """
body { margin: 0; font-family: Arial, sans-serif; color: #18202a; background: #f5f7f9; }
header { padding: 18px 24px 12px; background: #ffffff; border-bottom: 1px solid #dfe3e8; }
h1 { margin: 0 0 4px; font-size: 24px; }
header p { margin: 0; color: #5d6673; }
nav { display: flex; gap: 4px; padding: 8px 16px 0; background: #ffffff; border-bottom: 1px solid #dfe3e8; }
.tab { padding: 10px 14px; color: #384250; text-decoration: none; border: 1px solid transparent; border-bottom: 0; border-radius: 8px 8px 0 0; }
.tab.active { background: #f5f7f9; border-color: #dfe3e8; font-weight: 700; }
main { padding: 18px; }
section { margin: 0 0 18px; padding: 16px; background: #fff; border: 1px solid #dfe3e8; border-radius: 8px; }
h2 { margin: 0 0 10px; font-size: 16px; line-height: 1.35; }
.toolbar form, .options-form { display: grid; grid-template-columns: minmax(280px, 560px); gap: 12px; align-items: center; }
.options-form button, .toolbar button, section button { width: fit-content; }
select, input, button { font: inherit; padding: 7px 9px; }
button { cursor: pointer; border: 1px solid #aeb6c2; background: #ffffff; border-radius: 6px; }
button:hover { background: #eef2f6; }
.date-pair { display: grid; grid-template-columns: max-content minmax(140px, 1fr) max-content minmax(140px, 1fr); gap: 8px 10px; align-items: center; }
.range-pair { position: relative; height: 34px; margin: 2px 0 4px; }
.range-track { position: absolute; left: 8px; right: 8px; top: 16px; height: 4px; background: #d6dbe2; border-radius: 999px; }
.range-pair input[type="range"] { position: absolute; left: 0; right: 0; top: 5px; width: 100%; padding: 0; margin: 0; background: transparent; pointer-events: none; appearance: none; }
.range-pair input[type="range"]::-webkit-slider-thumb { appearance: none; width: 16px; height: 16px; border-radius: 50%; border: 2px solid #1769aa; background: #fff; pointer-events: auto; cursor: pointer; }
.range-pair input[type="range"]::-moz-range-thumb { width: 14px; height: 14px; border-radius: 50%; border: 2px solid #1769aa; background: #fff; pointer-events: auto; cursor: pointer; }
.range-pair input[type="range"]::-webkit-slider-runnable-track { background: transparent; }
.range-pair input[type="range"]::-moz-range-track { background: transparent; }
.range-start { z-index: 2; }
.range-end { z-index: 3; }
.checkline { display: flex; align-items: center; gap: 8px; }
.compact { margin: 4px 0; }
pre { white-space: pre-wrap; background: #f2f5f8; border: 1px solid #dfe3e8; padding: 12px; border-radius: 6px; }
code { background: #f2f5f8; padding: 2px 4px; border-radius: 4px; }
.chart-tooltip { position: fixed; z-index: 30; display: none; max-width: 260px; padding: 6px 8px; background: #18202a; color: #fff; border-radius: 5px; font-size: 12px; pointer-events: none; box-shadow: 0 4px 12px rgba(24, 32, 42, 0.22); }
.hover-target { fill: transparent; stroke: transparent; pointer-events: all; cursor: crosshair; }
.cursor-line { stroke: #384250; stroke-width: 1; stroke-dasharray: 4 4; pointer-events: none; opacity: 0.65; }
.cursor-dot { fill: #fff; stroke: #1769aa; stroke-width: 2; pointer-events: none; }
.table-wrap { overflow-x: auto; }
table { width: 100%; border-collapse: collapse; font-size: 12px; }
th, td { padding: 7px 9px; border-bottom: 1px solid #e4e8ee; text-align: left; vertical-align: top; }
th { background: #f2f5f8; color: #384250; font-weight: 700; white-space: nowrap; }
td { color: #384250; }
.fund-overview tr.sold-fund td { color: #8a919b; }
svg { width: 100%; height: auto; display: block; }
text { font-size: 12px; fill: #5d6673; }
.grid { stroke: #e4e8ee; stroke-width: 1; }
.line { stroke: #1769aa; stroke-width: 2.2; }
.point { fill: #d1495b; }
.buy-line { stroke: #9aa1aa; stroke-width: 1.2; stroke-dasharray: 5 5; }
.buy-marker-line { stroke: #6c737d; stroke-width: 1.4; }
.buy-point { fill: #fff; stroke: #333942; stroke-width: 2; }
.buy-label { font-size: 12px; fill: #333942; }
.sell-line { stroke: #d5a4aa; stroke-width: 1.2; stroke-dasharray: 5 5; }
.sell-marker-line { stroke: #b54b5a; stroke-width: 1.4; }
.sell-point { fill: #fff; stroke: #b54b5a; stroke-width: 2; }
.sell-label { font-size: 12px; fill: #8f3441; }
.relative-axis-line { stroke: #c4c9d0; stroke-width: 1; }
.relative-axis { font-size: 12px; fill: #6c737d; }
.total-axis { font-size: 12px; fill: #4f5965; }
.total-line { stroke: #2f8f83; stroke-width: 2; }
.quantity-axis { font-size: 12px; fill: #526b78; }
.quantity-line { stroke: #527f91; stroke-width: 2; }
.dividend-axis { font-size: 12px; fill: #9a5a7d; }
.dividend-stem { stroke: #9a5a7d; stroke-width: 1.8; }
.dividend-point { fill: #9a5a7d; }
.dividend-zero-line { stroke: #d8c8d2; stroke-width: 1; stroke-dasharray: 3 4; }
.profit-axis { font-size: 12px; fill: #5b4b73; }
.profit-relative-axis { font-size: 12px; fill: #8b5d33; }
.profit-line { stroke: #6f5aa8; stroke-width: 2; }
.profit-relative-line { stroke: #c07a2c; stroke-width: 2; stroke-dasharray: 5 4; }
.portfolio-profit-line { stroke: #2d6f4f; stroke-width: 2.4; }
.portfolio-profit-bar-positive { fill: #2f8f83; opacity: 0.28; }
.portfolio-profit-bar-negative { fill: #d1495b; opacity: 0.28; }
.pie-outline { stroke: #fff; stroke-width: 2; }
.pie-total { font-size: 14px; font-weight: 700; fill: #18202a; }
.pie-header { font-size: 12px; font-weight: 700; fill: #384250; }
.pie-legend { font-size: 12px; fill: #384250; }
.bar-grid { stroke: #d6dbe2; stroke-width: 1; }
.bar-axis { font-size: 12px; fill: #5d6673; }
.bar-label { font-size: 12px; fill: #384250; }
.yearly-profit-legend { font-size: 10px; fill: #384250; }
.bar-value { font-size: 12px; fill: #384250; }
.profit-bar-positive { fill: #2f8f83; }
.profit-bar-negative { fill: #d1495b; }
@media print {
  .fund-overview-section {
    break-before: page;
    page-break-before: always;
    break-inside: auto;
    page-break-inside: auto;
  }
  .fund-overview-section .table-wrap { overflow: visible; }
  .fund-overview {
    width: 100%;
    table-layout: fixed;
    font-size: 9px;
  }
  .fund-overview thead { display: table-header-group; }
  .fund-overview tr {
    break-inside: avoid;
    page-break-inside: avoid;
  }
  .fund-overview th,
  .fund-overview td {
    min-width: 0;
    padding: 4px;
    white-space: normal;
    overflow-wrap: anywhere;
  }
  .fund-section {
    break-before: page;
    page-break-before: always;
  }
}
"""


APP_JS = """
const tooltip = document.createElement('div');
tooltip.className = 'chart-tooltip';
document.body.appendChild(tooltip);

document.querySelectorAll('svg').forEach((svg) => {
  const points = Array.from(svg.querySelectorAll('.hover-target[data-tooltip]'));
  if (!points.length) return;
  const cursorLine = document.createElementNS('http://www.w3.org/2000/svg', 'line');
  cursorLine.setAttribute('class', 'cursor-line');
  cursorLine.style.display = 'none';
  const cursorDot = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
  cursorDot.setAttribute('class', 'cursor-dot');
  cursorDot.setAttribute('r', '4');
  cursorDot.style.display = 'none';
  svg.appendChild(cursorLine);
  svg.appendChild(cursorDot);

  function svgPoint(event) {
    const point = svg.createSVGPoint();
    point.x = event.clientX;
    point.y = event.clientY;
    return point.matrixTransform(svg.getScreenCTM().inverse());
  }

  svg.addEventListener('mousemove', (event) => {
    const mouse = svgPoint(event);
    let nearest = null;
    let nearestDistance = Infinity;
    points.forEach((point) => {
      const x = Number(point.getAttribute('cx'));
      const y = Number(point.getAttribute('cy'));
      const distance = Math.hypot(x - mouse.x, y - mouse.y);
      if (distance < nearestDistance) {
        nearest = point;
        nearestDistance = distance;
      }
    });
    if (!nearest || nearestDistance > 35) {
      tooltip.style.display = 'none';
      cursorLine.style.display = 'none';
      cursorDot.style.display = 'none';
      return;
    }
    const x = Number(nearest.getAttribute('cx'));
    const y = Number(nearest.getAttribute('cy'));
    const viewBox = svg.viewBox.baseVal;
    cursorLine.setAttribute('x1', String(x));
    cursorLine.setAttribute('x2', String(x));
    cursorLine.setAttribute('y1', String(viewBox.y));
    cursorLine.setAttribute('y2', String(viewBox.y + viewBox.height));
    cursorDot.setAttribute('cx', String(x));
    cursorDot.setAttribute('cy', String(y));
    cursorLine.style.display = '';
    cursorDot.style.display = '';
    tooltip.textContent = nearest.dataset.tooltip || '';
    tooltip.style.left = `${event.clientX + 12}px`;
    tooltip.style.top = `${event.clientY + 12}px`;
    tooltip.style.display = 'block';
  });
  svg.addEventListener('mouseleave', () => {
    tooltip.style.display = 'none';
    cursorLine.style.display = 'none';
    cursorDot.style.display = 'none';
  });
});

const dates = window.availableDates || [];
function bindDateRange() {
  const startDate = document.getElementById('start');
  const endDate = document.getElementById('end');
  const startSlider = document.getElementById('startSlider');
  const endSlider = document.getElementById('endSlider');
  if (!startDate || !endDate || !startSlider || !endSlider || !dates.length) return;

  function syncFromSliders(changed) {
    let start = Number(startSlider.value);
    let end = Number(endSlider.value);
    if (start > end) {
      if (changed === 'start') {
        end = start;
        endSlider.value = String(end);
      } else {
        start = end;
        startSlider.value = String(start);
      }
    }
    startDate.value = dates[start] || startDate.value;
    endDate.value = dates[end] || endDate.value;
  }

  function syncFromDate(input, slider) {
    const index = dates.indexOf(input.value);
    if (index >= 0) {
      slider.value = String(index);
      syncFromSliders(slider === startSlider ? 'start' : 'end');
    }
  }

  startSlider.addEventListener('input', () => syncFromSliders('start'));
  endSlider.addEventListener('input', () => syncFromSliders('end'));
  startDate.addEventListener('change', () => syncFromDate(startDate, startSlider));
  endDate.addEventListener('change', () => syncFromDate(endDate, endSlider));
}
bindDateRange();
"""


class AppRequestHandler(BaseHTTPRequestHandler):
    app: FundHistoryApp

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path not in {"/", ""}:
            self.send_error(404)
            return
        params = urllib.parse.parse_qs(parsed.query)
        try:
            document = self.app.render(params)
        except Exception as exc:  # noqa: BLE001
            document = f"<pre>{html.escape(str(exc))}</pre>"
            self.send_response(500)
        else:
            self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(document.encode("utf-8"))

    def do_POST(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path != "/import/dkb":
            self.send_error(404)
            return
        length = int(self.headers.get("Content-Length", "0"))
        params = urllib.parse.parse_qs(self.rfile.read(length).decode("utf-8"))
        mode = value_for(params, "mode", "preview")
        try:
            self.app.last_import_message = self.app.run_dkb_import(dry_run=mode != "run")
        except Exception as exc:  # noqa: BLE001
            self.app.last_import_message = f"Import failed: {exc}"
        self.send_response(303)
        self.send_header("Location", "/?tab=import")
        self.end_headers()

    def log_message(self, _format: str, *_args: object) -> None:
        return


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the Fund History GUI app.")
    parser.add_argument("--manual-data", default=None, help="Excel workbook to read and update.")
    parser.add_argument("--dkb-path", default=None, help="Folder or file with DKB depot exports.")
    parser.add_argument("--port", type=int, default=8765, help="Local HTTP port.")
    parser.add_argument("--no-open", action="store_true", help="Do not open the browser automatically.")
    return parser


def main(argv: list[str] | None = None) -> int:
    load_project_env()
    args = build_arg_parser().parse_args(argv)
    data_dir = configured_data_dir()
    input_data_dir = configured_input_data_dir()
    manual_data_path = (
        resolve_path(args.manual_data, input_data_dir)
        if args.manual_data
        else input_data_dir / "fund_manual_values.xlsx"
    )
    dkb_path = (
        resolve_path(args.dkb_path, input_data_dir)
        if args.dkb_path
        else input_data_dir / "DKB"
    )
    if manual_data_path is None or dkb_path is None:
        print("Could not resolve app paths.", file=sys.stderr)
        return 1

    app = FundHistoryApp(manual_data_path.resolve(), dkb_path.resolve())
    AppRequestHandler.app = app
    server = ThreadingHTTPServer(("127.0.0.1", args.port), AppRequestHandler)
    url = f"http://127.0.0.1:{args.port}/"
    print(f"Using data directory {data_dir}.")
    print(f"Using manual workbook {manual_data_path.resolve()}.")
    print(f"Fund History App running at {url}")
    if not args.no_open:
        threading.Timer(0.4, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped Fund History App.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
