#!/usr/bin/env python3
"""Download and plot fund history for ISINs from an Excel workbook.

The tool intentionally uses only Python's standard library so it can run in a
minimal environment. It reads .xlsx files directly, resolves ISINs through
Yahoo Finance search, downloads chart data, caches results, and writes an HTML
report with inline SVG plots.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import html
import json
import math
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
from xml.etree import ElementTree as ET


NS = {
    "main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "rel": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}


@dataclass(frozen=True)
class Fund:
    isin: str
    name: str = ""


@dataclass(frozen=True)
class Quote:
    date: str
    close: float


@dataclass(frozen=True)
class QuantityPoint:
    date: str
    quantity: float


@dataclass(frozen=True)
class HistoryResult:
    source: str
    symbol: str
    quotes: list[Quote]


@dataclass(frozen=True)
class DateValue:
    date: str
    value: float


@dataclass(frozen=True)
class ManualFundData:
    scalars: dict[str, dict[str, str]]
    date_values: dict[str, dict[str, list[DateValue]]]


def column_name(cell_ref: str) -> str:
    return re.sub(r"[^A-Z]", "", cell_ref.upper())


def column_index(col: str) -> int:
    value = 0
    for char in col.upper():
        value = value * 26 + (ord(char) - ord("A") + 1)
    return value - 1


def cell_value(cell: ET.Element, shared_strings: list[str]) -> str:
    value_element = cell.find("main:v", NS)
    if value_element is None:
        inline = cell.find("main:is", NS)
        if inline is None:
            return ""
        return "".join(t.text or "" for t in inline.findall(".//main:t", NS))

    value = value_element.text or ""
    if cell.attrib.get("t") == "s" and value:
        return shared_strings[int(value)]
    return value


def read_shared_strings(workbook_zip: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in workbook_zip.namelist():
        return []
    root = ET.fromstring(workbook_zip.read("xl/sharedStrings.xml"))
    return [
        "".join(t.text or "" for t in item.findall(".//main:t", NS))
        for item in root.findall("main:si", NS)
    ]


def workbook_sheet_paths(workbook_zip: zipfile.ZipFile) -> dict[str, str]:
    workbook = ET.fromstring(workbook_zip.read("xl/workbook.xml"))
    relationships = ET.fromstring(workbook_zip.read("xl/_rels/workbook.xml.rels"))
    targets = {rel.attrib["Id"]: rel.attrib["Target"] for rel in relationships}

    sheet_paths: dict[str, str] = {}
    for sheet in workbook.findall("main:sheets/main:sheet", NS):
        rel_id = sheet.attrib[f"{{{NS['rel']}}}id"]
        target = targets[rel_id].lstrip("/")
        if not target.startswith("xl/"):
            target = f"xl/{target}"
        sheet_paths[sheet.attrib["name"]] = target
    return sheet_paths


def read_xlsx_rows(path: Path, sheet_name: str | None = None) -> list[dict[str, str]]:
    with zipfile.ZipFile(path) as workbook_zip:
        shared_strings = read_shared_strings(workbook_zip)
        sheets = workbook_sheet_paths(workbook_zip)
        selected_sheet = sheet_name or next(iter(sheets))
        if selected_sheet not in sheets:
            available = ", ".join(sheets)
            raise ValueError(f"Sheet '{selected_sheet}' not found. Available sheets: {available}")

        root = ET.fromstring(workbook_zip.read(sheets[selected_sheet]))
        parsed_rows: list[list[str]] = []
        for row in root.findall(".//main:sheetData/main:row", NS):
            values: list[str] = []
            for cell in row.findall("main:c", NS):
                ref = cell.attrib.get("r", "")
                idx = column_index(column_name(ref)) if ref else len(values)
                while len(values) <= idx:
                    values.append("")
                values[idx] = cell_value(cell, shared_strings).strip()
            parsed_rows.append(values)

    if not parsed_rows:
        return []

    headers = [header.strip().lower() for header in parsed_rows[0]]
    rows: list[dict[str, str]] = []
    for values in parsed_rows[1:]:
        rows.append({headers[i]: values[i] if i < len(values) else "" for i in range(len(headers))})
    return rows


def extract_funds(path: Path, sheet_name: str | None = None) -> list[Fund]:
    rows = read_xlsx_rows(path, sheet_name)
    funds: dict[str, Fund] = {}
    for row in rows:
        isin = row.get("isin", "").strip().upper()
        if not isin:
            continue
        name = row.get("name", "").strip()
        funds.setdefault(isin, Fund(isin=isin, name=name))
    return sorted(funds.values(), key=lambda fund: fund.isin)


def extract_quantity_history(path: Path, sheet_name: str | None = None) -> dict[str, list[QuantityPoint]]:
    rows = read_xlsx_rows(path, sheet_name)
    histories: dict[str, list[QuantityPoint]] = {}
    for row in rows:
        isin = row.get("isin", "").strip().upper()
        if not isin:
            continue
        quantity = parse_float(row.get("quantity"))
        if quantity is None:
            continue
        date = parse_excel_date(row.get("date", ""))
        if not date:
            continue
        histories.setdefault(isin, []).append(QuantityPoint(date=date, quantity=quantity))

    for isin, points in histories.items():
        histories[isin] = sorted(points, key=lambda point: point.date)
    return histories


def extract_funds_from_manual_data(manual_data: ManualFundData) -> list[Fund]:
    funds: dict[str, Fund] = {}
    for isin, scalars in manual_data.scalars.items():
        if isin:
            funds[isin] = Fund(isin=isin, name=scalars.get("name", ""))
    for isin in manual_data.date_values:
        funds.setdefault(isin, Fund(isin=isin, name=""))
    return sorted(funds.values(), key=lambda fund: fund.isin)


def extract_quantity_history_from_manual_data(manual_data: ManualFundData) -> dict[str, list[QuantityPoint]]:
    histories: dict[str, list[QuantityPoint]] = {}
    for isin, series_by_name in manual_data.date_values.items():
        quantity_values = series_by_name.get("quantity", [])
        histories[isin] = [
            QuantityPoint(date=point.date, quantity=point.value)
            for point in sorted(quantity_values, key=lambda value: value.date)
        ]
    return histories


def date_values(points: Iterable[DateValue]) -> list[dict[str, float | str]]:
    return [{"date": point.date, "value": point.value} for point in points]


def quote_values(quotes: Iterable[Quote]) -> list[dict[str, float | str]]:
    return [{"date": quote.date, "value": quote.close} for quote in quotes]


def quantity_values(points: Iterable[QuantityPoint]) -> list[dict[str, float | str]]:
    return [{"date": point.date, "value": point.quantity} for point in points]


def quantity_at(date: str, points: list[QuantityPoint], sold_after: str | None) -> float:
    if sold_after is not None and date > sold_after:
        return 0.0
    quantity = 0.0
    for point in points:
        if point.date > date:
            break
        quantity = point.quantity
    return quantity


def quote_at_or_after(date: str, quotes: list[Quote], max_days_after: int = 14) -> Quote | None:
    try:
        target_date = dt.date.fromisoformat(date)
    except ValueError:
        return None
    for quote in quotes:
        if quote.date >= date:
            try:
                quote_date = dt.date.fromisoformat(quote.date)
            except ValueError:
                return None
            if (quote_date - target_date).days <= max_days_after:
                return quote
            return None
    return None


def build_total_value_history(
    quotes: list[Quote],
    quantity_points: list[QuantityPoint],
    sold_after: str | None,
) -> list[DateValue]:
    totals: list[DateValue] = []
    for quote in quotes:
        quantity = quantity_at(quote.date, quantity_points, sold_after)
        totals.append(DateValue(date=quote.date, value=quote.close * quantity))
    return totals


def build_extended_fund_records(
    funds: list[Fund],
    quantity_histories: dict[str, list[QuantityPoint]],
    results: dict[str, HistoryResult],
    manual_data: ManualFundData,
) -> list[dict]:
    latest_workbook_date = max(
        (point.date for points in quantity_histories.values() for point in points),
        default=None,
    )
    records: list[dict] = []
    for fund in funds:
        quantity_points = quantity_histories.get(fund.isin, [])
        first_date = quantity_points[0].date if quantity_points else None
        last_date = quantity_points[-1].date if quantity_points else None
        is_sold = bool(latest_workbook_date and last_date and last_date < latest_workbook_date)
        sell_date = last_date if is_sold else None
        result = results.get(fund.isin)
        quotes = result.quotes if result else []
        manual_scalars = manual_data.scalars.get(fund.isin, {})
        manual_series = manual_data.date_values.get(fund.isin, {})
        output_name = manual_scalars.get("name") or fund.name
        output_buy_date = parse_excel_date(manual_scalars.get("buy_date", "")) or first_date
        output_sell_date = parse_excel_date(manual_scalars.get("sell_date", "")) or sell_date
        output_status = manual_scalars.get("status") or ("sold" if is_sold else "active")
        single_value = manual_series.get("single_value")
        quantity = manual_series.get("quantity")
        selected_quantity_points = (
            [QuantityPoint(point.date, point.value) for point in quantity]
            if quantity is not None
            else quantity_points
        )
        total_value = build_total_value_history(quotes, selected_quantity_points, output_sell_date)
        manual_total_value = manual_series.get("total_value")
        records.append(
            {
                "isin": fund.isin,
                "name": output_name,
                "buy_date": output_buy_date,
                "sell_date": output_sell_date,
                "sell_data": output_sell_date,
                "status": output_status,
                "source": result.source if result else None,
                "symbol": result.symbol if result else None,
                "single_value": date_values(single_value) if single_value is not None else quote_values(quotes),
                "quantity": date_values(quantity) if quantity is not None else quantity_values(quantity_points),
                "total_value": (
                    date_values(manual_total_value)
                    if manual_total_value is not None
                    else date_values(total_value)
                ),
                "invest": date_values(manual_series.get("invest", [])),
                "dividend": date_values(manual_series.get("dividend", [])),
            }
        )
    return records


def write_extended_fund_data(records: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(records, indent=2, ensure_ascii=False), encoding="utf-8")


def read_manual_fund_data(path: Path) -> ManualFundData:
    if not path.exists():
        return ManualFundData(scalars={}, date_values={})

    scalars: dict[str, dict[str, str]] = {}
    for row in read_xlsx_rows(path, "ScalarValues"):
        isin = row.get("isin", "").strip().upper()
        if not isin:
            continue
        scalars[isin] = {key: value.strip() for key, value in row.items() if value.strip()}

    date_values_by_isin: dict[str, dict[str, list[DateValue]]] = {}
    for row in read_xlsx_rows(path, "DateValuePairs"):
        isin = row.get("isin", "").strip().upper()
        series = row.get("series", "").strip().lower()
        date = parse_excel_date(row.get("date", ""))
        value = parse_float(row.get("value"))
        if not isin or not series or not date or value is None:
            continue
        date_values_by_isin.setdefault(isin, {}).setdefault(series, []).append(DateValue(date, value))

    try:
        quantity_rows = read_xlsx_rows(path, "QuantityDatePairs")
    except ValueError:
        quantity_rows = []
    for row in quantity_rows:
        isin = row.get("isin", "").strip().upper()
        date = parse_excel_date(row.get("date", ""))
        value = parse_float(row.get("quantity") or row.get("value"))
        if not isin or not date or value is None:
            continue
        date_values_by_isin.setdefault(isin, {}).setdefault("quantity", []).append(DateValue(date, value))

    for series_by_isin in date_values_by_isin.values():
        for series, values in series_by_isin.items():
            series_by_isin[series] = sorted(values, key=lambda point: point.date)
    return ManualFundData(scalars=scalars, date_values=date_values_by_isin)


def xml_escape(value: object) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def column_letter(index: int) -> str:
    index += 1
    letters = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        letters = chr(ord("A") + remainder) + letters
    return letters


def worksheet_xml(rows: list[list[object]]) -> str:
    row_xml = []
    for row_index, row in enumerate(rows, start=1):
        cells = []
        for col_index, value in enumerate(row):
            ref = f"{column_letter(col_index)}{row_index}"
            cells.append(f'<c r="{ref}" t="inlineStr"><is><t>{xml_escape(value)}</t></is></c>')
        row_xml.append(f'<row r="{row_index}">{"".join(cells)}</row>')
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <sheetData>{"".join(row_xml)}</sheetData>
</worksheet>
"""


def workbook_xml(sheet_names: list[str]) -> str:
    sheets = []
    for index, name in enumerate(sheet_names, start=1):
        sheets.append(
            f'<sheet name="{xml_escape(name)}" sheetId="{index}" '
            f'r:id="rId{index}"/>'
        )
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"
  xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets>{"".join(sheets)}</sheets>
</workbook>
"""


def workbook_relationships_xml(sheet_names: list[str]) -> str:
    relationships = []
    for index, _name in enumerate(sheet_names, start=1):
        relationships.append(
            f'<Relationship Id="rId{index}" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
            f'Target="worksheets/sheet{index}.xml"/>'
        )
    relationships.append(
        f'<Relationship Id="rId{len(sheet_names) + 1}" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" '
        'Target="styles.xml"/>'
    )
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  {"".join(relationships)}
</Relationships>
"""


def content_types_xml(sheet_count: int) -> str:
    sheet_overrides = "".join(
        f'<Override PartName="/xl/worksheets/sheet{index}.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        for index in range(1, sheet_count + 1)
    )
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
  <Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>
  {sheet_overrides}
</Types>
"""


def root_relationships_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1"
    Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument"
    Target="xl/workbook.xml"/>
</Relationships>
"""


def styles_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <fonts count="1"><font><sz val="11"/><name val="Calibri"/></font></fonts>
  <fills count="1"><fill><patternFill patternType="none"/></fill></fills>
  <borders count="1"><border/></borders>
  <cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>
  <cellXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/></cellXfs>
</styleSheet>
"""


def write_xlsx(path: Path, sheets: dict[str, list[list[object]]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    sheet_names = list(sheets)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as workbook:
        workbook.writestr("[Content_Types].xml", content_types_xml(len(sheet_names)))
        workbook.writestr("_rels/.rels", root_relationships_xml())
        workbook.writestr("xl/workbook.xml", workbook_xml(sheet_names))
        workbook.writestr("xl/_rels/workbook.xml.rels", workbook_relationships_xml(sheet_names))
        workbook.writestr("xl/styles.xml", styles_xml())
        for index, name in enumerate(sheet_names, start=1):
            workbook.writestr(f"xl/worksheets/sheet{index}.xml", worksheet_xml(sheets[name]))


def rows_from_dicts(headers: list[str], rows: list[dict[str, str]]) -> list[list[object]]:
    return [headers] + [[row.get(header, "") for header in headers] for row in rows]


def workbook_has_sheet(path: Path, sheet_name: str) -> bool:
    if not path.exists():
        return False
    with zipfile.ZipFile(path) as workbook_zip:
        return sheet_name in workbook_sheet_paths(workbook_zip)


def quantity_template_rows(funds: list[Fund]) -> list[list[object]]:
    rows: list[list[object]] = [
        ["isin", "date", "quantity", "notes"],
        ["DE000EXAMPLE1", "2024-01-15", "10", "Delete this example row."],
    ]
    for fund in funds:
        rows.append([fund.isin, "", "", ""])
    return rows


def ensure_manual_data_template(path: Path, funds: list[Fund]) -> None:
    if path.exists() and workbook_has_sheet(path, "QuantityDatePairs"):
        return

    if path.exists():
        scalar_rows = rows_from_dicts(
            ["isin", "name", "buy_date", "sell_date", "status", "notes"],
            read_xlsx_rows(path, "ScalarValues"),
        )
        pair_rows = rows_from_dicts(
            ["isin", "series", "date", "value", "notes"],
            read_xlsx_rows(path, "DateValuePairs"),
        )
        write_xlsx(
            path,
            {
                "ScalarValues": scalar_rows,
                "DateValuePairs": pair_rows,
                "QuantityDatePairs": quantity_template_rows(funds),
            },
        )
        return

    scalar_rows: list[list[object]] = [
        ["isin", "name", "buy_date", "sell_date", "status", "notes"],
    ]
    for fund in funds:
        scalar_rows.append([fund.isin, fund.name, "", "", "", ""])

    pair_rows: list[list[object]] = [
        ["isin", "series", "date", "value", "notes"],
        ["DE000EXAMPLE1", "invest", "2024-01-15", "1000.00", "Delete this example row."],
        ["DE000EXAMPLE1", "dividend", "2024-06-30", "25.00", "Delete this example row."],
    ]
    for fund in funds:
        pair_rows.append([fund.isin, "invest", "", "", ""])
        pair_rows.append([fund.isin, "dividend", "", "", ""])

    write_xlsx(
        path,
        {
            "ScalarValues": scalar_rows,
            "DateValuePairs": pair_rows,
            "QuantityDatePairs": quantity_template_rows(funds),
        },
    )


def http_get_json(url: str, timeout: int = 30) -> dict:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 fund-history-tool/1.0",
            "Accept": "application/json,text/plain,*/*",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def parse_onvista_date(timestamp_ms: int | float) -> str:
    timestamp = float(timestamp_ms) / 1000
    return dt.datetime.fromtimestamp(timestamp, tz=dt.UTC).date().isoformat()


def parse_onvista_decimal(value: str | int | float | None) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    cleaned = value.strip().replace(".", "").replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return None


def parse_float(value: str | int | float | None) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    cleaned = value.strip().replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return None


def parse_excel_date(value: str) -> str:
    value = value.strip()
    if not value:
        return ""
    serial = parse_float(value)
    if serial is not None:
        # Excel's 1900 date system includes a leap-year bug; this base mirrors
        # the date values used by openpyxl for ordinary worksheet serials.
        return (dt.date(1899, 12, 30) + dt.timedelta(days=int(serial))).isoformat()
    try:
        return dt.date.fromisoformat(value[:10]).isoformat()
    except ValueError:
        return value


def read_symbol_overrides(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        overrides: dict[str, str] = {}
        for row in reader:
            isin = (row.get("isin") or "").strip().upper()
            symbol = (row.get("symbol") or "").strip()
            if isin and symbol:
                overrides[isin] = symbol
        return overrides


def resolve_yahoo_symbol(
    isin: str,
    cache_dir: Path,
    overrides: dict[str, str],
    refresh: bool = False,
) -> str | None:
    if isin in overrides:
        return overrides[isin]

    cache_file = cache_dir / "isin_symbol_cache.json"
    cache: dict[str, str | None] = {}
    if cache_file.exists():
        cache = json.loads(cache_file.read_text(encoding="utf-8"))
    if isin in cache and not refresh:
        return cache[isin]

    params = urllib.parse.urlencode({"q": isin, "quotesCount": 10, "newsCount": 0})
    url = f"https://query2.finance.yahoo.com/v1/finance/search?{params}"
    data = http_get_json(url)
    quotes = data.get("quotes", [])
    symbol = None
    for quote in quotes:
        symbol_candidate = quote.get("symbol")
        if not symbol_candidate:
            continue
        fields = " ".join(str(quote.get(key, "")) for key in ("symbol", "shortname", "longname"))
        if isin in fields.upper() or quote.get("quoteType") in {"MUTUALFUND", "ETF", "EQUITY"}:
            symbol = symbol_candidate
            break
    if symbol is None and quotes:
        symbol = quotes[0].get("symbol")

    cache[isin] = symbol
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(json.dumps(cache, indent=2, sort_keys=True), encoding="utf-8")
    return symbol


def download_history(symbol: str, cache_dir: Path, period: str, interval: str, refresh: bool = False) -> list[Quote]:
    safe_symbol = re.sub(r"[^A-Za-z0-9_.=-]", "_", symbol)
    cache_file = cache_dir / "history" / f"{safe_symbol}_{period}_{interval}.json"
    if cache_file.exists() and not refresh:
        data = json.loads(cache_file.read_text(encoding="utf-8"))
    else:
        params = urllib.parse.urlencode({"range": period, "interval": interval, "events": "history"})
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(symbol)}?{params}"
        data = http_get_json(url)
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        cache_file.write_text(json.dumps(data), encoding="utf-8")

    result = data.get("chart", {}).get("result") or []
    if not result:
        return []
    item = result[0]
    timestamps = item.get("timestamp") or []
    quote = ((item.get("indicators") or {}).get("quote") or [{}])[0]
    closes = quote.get("close") or []

    history: list[Quote] = []
    for timestamp, close in zip(timestamps, closes):
        if close is None:
            continue
        date = dt.datetime.fromtimestamp(timestamp, tz=dt.UTC).date().isoformat()
        history.append(Quote(date=date, close=float(close)))
    return history


def search_onvista_instrument(isin: str, cache_dir: Path, refresh: bool = False) -> dict | None:
    cache_file = cache_dir / "onvista_search" / f"{isin}.json"
    if cache_file.exists() and not refresh:
        data = json.loads(cache_file.read_text(encoding="utf-8"))
    else:
        params = urllib.parse.urlencode({"searchValue": isin})
        url = f"https://api.onvista.de/api/v1/instruments/search?{params}"
        data = http_get_json(url)
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        cache_file.write_text(json.dumps(data), encoding="utf-8")

    for item in data.get("list", []):
        if item.get("entityType") == "FUND":
            return item
    return None


def fetch_onvista_snapshot(item: dict, cache_dir: Path, refresh: bool = False) -> dict:
    entity_value = item["entityValue"]
    cache_file = cache_dir / "onvista_snapshot" / f"{entity_value}.json"
    if cache_file.exists() and not refresh:
        return json.loads(cache_file.read_text(encoding="utf-8"))

    url = item.get("urls", {}).get("WEBSITE")
    if not url:
        raise ValueError("Onvista search result has no website URL.")
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 fund-history-tool/1.0",
            "Accept": "text/html,*/*",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        text = response.read().decode("utf-8", errors="replace")

    match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', text)
    if not match:
        raise ValueError("Onvista page did not contain embedded snapshot data.")
    page_data = json.loads(html.unescape(match.group(1)))
    snapshot = page_data["props"]["pageProps"]["data"]["snapshot"]
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(json.dumps(snapshot), encoding="utf-8")
    return snapshot


def download_onvista_history(isin: str, cache_dir: Path, period: str, refresh: bool = False) -> HistoryResult | None:
    item = search_onvista_instrument(isin, cache_dir, refresh)
    if not item:
        return None

    snapshot = fetch_onvista_snapshot(item, cache_dir, refresh)
    instrument = snapshot["instrument"]
    quote = snapshot.get("quote") or {}
    market = quote.get("market") or snapshot.get("chart") or {}
    id_notation = market.get("idNotation") or snapshot.get("chart", {}).get("idNotation")
    code_market = market.get("codeMarket") or snapshot.get("chart", {}).get("codeMarket")
    iso_currency = quote.get("isoCurrency") or snapshot.get("chart", {}).get("isoCurrency") or "EUR"
    entity_value = instrument["entityValue"]

    params = {
        "range": onvista_range_from_period(period),
        "idNotation": id_notation,
        "codeMarket": code_market,
        "isoCurrency": iso_currency,
        "withEarnings": "false",
    }
    params = {key: value for key, value in params.items() if value is not None}
    cache_name = f"{entity_value}_{params.get('idNotation', 'default')}_{params['range']}.json"
    cache_file = cache_dir / "onvista_history" / cache_name
    if cache_file.exists() and not refresh:
        data = json.loads(cache_file.read_text(encoding="utf-8"))
    else:
        query = urllib.parse.urlencode(params)
        url = f"https://api.onvista.de/api/v1/instruments/FUND/{entity_value}/simple_chart_history?{query}"
        data = http_get_json(url)
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        cache_file.write_text(json.dumps(data), encoding="utf-8")

    quotes: list[Quote] = []
    for timestamp, value in zip(data.get("datetimeTick", []), data.get("tick", [])):
        close = parse_onvista_decimal(value)
        if close is None:
            continue
        quotes.append(Quote(date=parse_onvista_date(timestamp), close=close))

    symbol = f"ONVISTA:{entity_value}:{id_notation or 'default'}"
    return HistoryResult(source="onvista", symbol=symbol, quotes=quotes)


def onvista_range_from_period(period: str) -> str:
    normalized = period.strip().lower()
    mapping = {
        "1mo": "M1",
        "3mo": "M3",
        "6mo": "M6",
        "1y": "Y1",
        "3y": "Y3",
        "5y": "Y5",
        "10y": "Y10",
        "max": "MAX",
    }
    return mapping.get(normalized, "Y5")


def download_deka_current_value(isin: str, cache_dir: Path, refresh: bool = False) -> HistoryResult | None:
    cache_file = cache_dir / "deka_search" / f"{isin}.json"
    if cache_file.exists() and not refresh:
        data = json.loads(cache_file.read_text(encoding="utf-8"))
    else:
        params = urllib.parse.urlencode(
            {
                "service": "fondssucheController",
                "action": "suche",
                "elementeProSeite": 10,
                "suchbegriff": isin,
            }
        )
        url = f"https://www.deka.de/privatkunden-functions/fondssuche?{params}"
        data = http_get_json(url)
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        cache_file.write_text(json.dumps(data), encoding="utf-8")

    funds = data.get("fonds") or []
    if not funds:
        return None
    fund = funds[0]
    price = parse_onvista_decimal(fund.get("rpreis") or fund.get("apreis"))
    if price is None:
        return None
    return HistoryResult(
        source="deka-current",
        symbol=f"DEKA:{fund.get('wkn') or isin}",
        quotes=[Quote(date=dt.date.today().isoformat(), close=price)],
    )


def buy_marker_markup(
    quotes: list[Quote],
    buy_date: str,
    buy_quote_index: int,
    x_at,
    y_at,
    width: int,
    pad_left: int,
    pad_right: int,
) -> str:
    quote = quotes[buy_quote_index]
    x = x_at(buy_quote_index)
    y = y_at(quote.close)
    return (
        f'<line x1="{pad_left}" y1="{y:.1f}" x2="{width - pad_right}" y2="{y:.1f}" class="buy-line"/>'
        f'<line x1="{x:.1f}" y1="{y - 10:.1f}" x2="{x:.1f}" y2="{y + 10:.1f}" class="buy-marker-line"/>'
        f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5" class="buy-point"/>'
        f'<text x="{x + 8:.1f}" y="{y - 8:.1f}" class="buy-label">buy {html.escape(buy_date)}</text>'
    )


def buy_quote_index(quotes: list[Quote], buy_date: str | None) -> int | None:
    if not buy_date:
        return None
    try:
        dt.date.fromisoformat(buy_date)
    except ValueError:
        return None
    for index, quote in enumerate(quotes):
        if quote.date >= buy_date:
            return index
    return None


def defined_quantity_at(date: str, points: list[QuantityPoint]) -> float | None:
    quantity = None
    for point in points:
        if point.date > date:
            break
        quantity = point.quantity
    return quantity


def cumulative_value_at(date: str, values: list[DateValue]) -> float:
    total = 0.0
    for point in values:
        if point.date > date:
            break
        total += point.value
    return total


def format_month_year(date_value: str) -> str:
    try:
        return dt.date.fromisoformat(date_value).strftime("%m/%Y")
    except ValueError:
        return date_value


def scaled_line_points(
    series: list[tuple[int, float]],
    quotes: list[Quote],
    x_left: int,
    x_right: int,
    y_top: int,
    plot_h: int,
    min_value: float,
    max_value: float,
) -> str:
    plot_w = x_right - x_left

    def x_at(index: int) -> float:
        if len(quotes) == 1:
            return x_left + plot_w / 2
        return x_left + plot_w * index / (len(quotes) - 1)

    def y_at(value: float) -> float:
        return y_top + plot_h - (value - min_value) * plot_h / (max_value - min_value)

    return " ".join(f"{x_at(index):.1f},{y_at(value):.1f}" for index, value in series)


def svg_line_chart(
    title: str,
    quotes: list[Quote],
    buy_date: str | None = None,
    quantity_points: list[QuantityPoint] | None = None,
    manual_series: dict[str, list[DateValue]] | None = None,
    width: int = 1700,
    height: int = 260,
) -> str:
    if not quotes:
        return f"<section><h2>{html.escape(title)}</h2><p>No history data found.</p></section>"

    pad_left, pad_top, pad_bottom = 56, 22, 34
    panel_w = 420
    main_left = pad_left
    main_right = main_left + panel_w
    relative_label_x = main_right + 8
    subplot_left = 640
    total_right = subplot_left + panel_w
    profit_left = 1220
    profit_right = profit_left + panel_w
    plot_w = panel_w
    plot_h = height - pad_top - pad_bottom
    values = [quote.close for quote in quotes]
    min_y, max_y = min(values), max(values)
    if math.isclose(min_y, max_y):
        min_y *= 0.95
        max_y *= 1.05

    def x_at(index: int) -> float:
        if len(quotes) == 1:
            return main_left + plot_w / 2
        return main_left + plot_w * index / (len(quotes) - 1)

    def y_at(value: float) -> float:
        return pad_top + plot_h - (value - min_y) * plot_h / (max_y - min_y)

    points = " ".join(f"{x_at(i):.1f},{y_at(quote.close):.1f}" for i, quote in enumerate(quotes))
    first, last = quotes[0], quotes[-1]
    x_tick_indices = sorted(
        {
            round((len(quotes) - 1) * tick_index / 3)
            for tick_index in range(4)
        }
    )
    x_tick_markup = []
    for tick_index in x_tick_indices:
        quote = quotes[tick_index]
        anchor = "middle"
        if tick_index == 0:
            anchor = "start"
        elif tick_index == len(quotes) - 1:
            anchor = "end"
        x_tick_markup.append(
            f'<text x="{x_at(tick_index):.1f}" y="{height - 10}" text-anchor="{anchor}">'
            f'{html.escape(format_month_year(quote.date))}</text>'
        )
    y_ticks = [min_y + (max_y - min_y) * i / 4 for i in range(5)]
    buy_index = buy_quote_index(quotes, buy_date)
    buy_value = quotes[buy_index].close if buy_index is not None else None
    tick_markup = []
    for tick in y_ticks:
        y = y_at(tick)
        right_axis_label = ""
        if buy_value and not math.isclose(buy_value, 0.0):
            relative_pct = (tick / buy_value - 1) * 100
            right_axis_label = (
                f'<text x="{relative_label_x}" y="{y + 4:.1f}" '
                f'text-anchor="start" class="relative-axis">{relative_pct:+.1f}%</text>'
            )
        tick_markup.append(
            f'<line x1="{main_left}" y1="{y:.1f}" x2="{main_right}" y2="{y:.1f}" class="grid"/>'
            f'<text x="{main_left - 8}" y="{y + 4:.1f}" text-anchor="end">{tick:.2f}</text>'
            f'{right_axis_label}'
        )
    axis_markup = ""
    buy_markup = ""
    if buy_index is not None and buy_date:
        axis_markup = (
            f'<line x1="{main_right}" y1="{pad_top}" '
            f'x2="{main_right}" y2="{height - pad_bottom}" class="relative-axis-line"/>'
            f'<text x="{relative_label_x}" y="{pad_top - 6}" class="relative-axis">vs buy</text>'
        )
        buy_markup = buy_marker_markup(quotes, buy_date, buy_index, x_at, y_at, main_right, main_left, 0)

    total_markup = ""
    total_series: list[tuple[int, float]] = []
    total_by_index: dict[int, float] = {}
    for index, quote in enumerate(quotes):
        quantity = defined_quantity_at(quote.date, quantity_points or [])
        if quantity is None:
            continue
        total_value = quote.close * quantity
        total_series.append((index, total_value))
        total_by_index[index] = total_value
    if total_series:
        total_values = [value for _index, value in total_series]
        total_min, total_max = min(total_values), max(total_values)
        if math.isclose(total_min, total_max):
            if math.isclose(total_min, 0.0):
                total_min, total_max = -1.0, 1.0
            else:
                total_min *= 0.95
                total_max *= 1.05

        subplot_w = panel_w

        def subplot_x(index: int) -> float:
            if len(quotes) == 1:
                return subplot_left + subplot_w / 2
            return subplot_left + subplot_w * index / (len(quotes) - 1)

        def subplot_y(value: float) -> float:
            return pad_top + plot_h - (value - total_min) * plot_h / (total_max - total_min)

        total_points = " ".join(
            f"{subplot_x(index):.1f},{subplot_y(value):.1f}"
            for index, value in total_series
        )
        total_ticks = [total_min + (total_max - total_min) * i / 4 for i in range(5)]
        total_tick_markup = []
        for tick in total_ticks:
            y = subplot_y(tick)
            total_tick_markup.append(
                f'<line x1="{subplot_left}" y1="{y:.1f}" x2="{total_right}" y2="{y:.1f}" class="grid"/>'
                f'<text x="{total_right + 8}" y="{y + 4:.1f}" text-anchor="start" class="total-axis">{tick:.0f}</text>'
            )
        total_markup = (
            f'<text x="{subplot_left}" y="{pad_top - 6}" class="total-axis">total value</text>'
            f'<line x1="{subplot_left}" y1="{pad_top}" x2="{subplot_left}" y2="{height - pad_bottom}" class="relative-axis-line"/>'
            f'<line x1="{total_right}" y1="{pad_top}" x2="{total_right}" y2="{height - pad_bottom}" class="relative-axis-line"/>'
            f'{"".join(total_tick_markup)}'
            f'<polyline points="{total_points}" fill="none" class="total-line"/>'
        )

    profit_markup = ""
    if total_by_index:
        series = manual_series or {}
        invests = series.get("invest", [])
        dividends = series.get("dividend", [])
        sells = series.get("sell", [])
        absolute_profit: list[tuple[int, float]] = []
        relative_profit: list[tuple[int, float]] = []
        for index, quote in enumerate(quotes):
            if index not in total_by_index:
                continue
            invested = cumulative_value_at(quote.date, invests)
            dividend = cumulative_value_at(quote.date, dividends)
            sell = cumulative_value_at(quote.date, sells)
            profit = total_by_index[index] - invested + dividend + sell
            absolute_profit.append((index, profit))
            if invested > 0:
                relative_profit.append((index, profit / invested * 100))

        if absolute_profit:
            profit_values = [value for _index, value in absolute_profit]
            profit_min, profit_max = min(profit_values), max(profit_values)
            if math.isclose(profit_min, profit_max):
                if math.isclose(profit_min, 0.0):
                    profit_min, profit_max = -1.0, 1.0
                else:
                    profit_min *= 0.95
                    profit_max *= 1.05

            profit_ticks = [profit_min + (profit_max - profit_min) * i / 4 for i in range(5)]
            profit_tick_markup = []
            for tick in profit_ticks:
                y = pad_top + plot_h - (tick - profit_min) * plot_h / (profit_max - profit_min)
                profit_tick_markup.append(
                    f'<line x1="{profit_left}" y1="{y:.1f}" x2="{profit_right}" y2="{y:.1f}" class="grid"/>'
                    f'<text x="{profit_left - 8}" y="{y + 4:.1f}" text-anchor="end" class="profit-axis">{tick:.0f}</text>'
                )

            absolute_points = scaled_line_points(
                absolute_profit,
                quotes,
                profit_left,
                profit_right,
                pad_top,
                plot_h,
                profit_min,
                profit_max,
            )
            relative_markup = ""
            if relative_profit:
                relative_values = [value for _index, value in relative_profit]
                relative_min, relative_max = min(relative_values), max(relative_values)
                if math.isclose(relative_min, relative_max):
                    if math.isclose(relative_min, 0.0):
                        relative_min, relative_max = -1.0, 1.0
                    else:
                        relative_min *= 0.95
                        relative_max *= 1.05
                relative_ticks = [relative_min + (relative_max - relative_min) * i / 4 for i in range(5)]
                relative_tick_markup = []
                for tick in relative_ticks:
                    y = pad_top + plot_h - (tick - relative_min) * plot_h / (relative_max - relative_min)
                    relative_tick_markup.append(
                        f'<text x="{profit_right + 8}" y="{y + 4:.1f}" text-anchor="start" class="profit-relative-axis">{tick:+.0f}%</text>'
                    )
                relative_points = scaled_line_points(
                    relative_profit,
                    quotes,
                    profit_left,
                    profit_right,
                    pad_top,
                    plot_h,
                    relative_min,
                    relative_max,
                )
                relative_markup = (
                    f'{"".join(relative_tick_markup)}'
                    f'<polyline points="{relative_points}" fill="none" class="profit-relative-line"/>'
                )

            profit_markup = (
                f'<text x="{profit_left}" y="{pad_top - 6}" class="profit-axis">profit</text>'
                f'<text x="{profit_right + 8}" y="{pad_top - 6}" class="profit-relative-axis">%</text>'
                f'<line x1="{profit_left}" y1="{pad_top}" x2="{profit_left}" y2="{height - pad_bottom}" class="relative-axis-line"/>'
                f'<line x1="{profit_right}" y1="{pad_top}" x2="{profit_right}" y2="{height - pad_bottom}" class="relative-axis-line"/>'
                f'{"".join(profit_tick_markup)}'
                f'<polyline points="{absolute_points}" fill="none" class="profit-line"/>'
                f'{relative_markup}'
            )

    return f"""
<section>
  <h2>{html.escape(title)}</h2>
  <svg viewBox="0 0 {width} {height}" role="img" aria-label="{html.escape(title)}">
    {''.join(tick_markup)}
    {axis_markup}
    {buy_markup}
    <polyline points="{points}" fill="none" class="line"/>
    <circle cx="{x_at(0):.1f}" cy="{y_at(first.close):.1f}" r="3" class="point"/>
    <circle cx="{x_at(len(quotes) - 1):.1f}" cy="{y_at(last.close):.1f}" r="3" class="point"/>
    {''.join(x_tick_markup)}
    {total_markup}
    {profit_markup}
  </svg>
</section>
""".strip()


def write_html_report(
    results: list[tuple[Fund, str | None, str | None, list[Quote], str | None]],
    path: Path,
    buy_dates: dict[str, str],
    quantity_histories: dict[str, list[QuantityPoint]],
    manual_date_values: dict[str, dict[str, list[DateValue]]],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    charts = []
    for fund, source, symbol, quotes, error in results:
        title = f"{fund.isin}"
        if source:
            title += f" / {source}"
        if symbol:
            title += f" / {symbol}"
        if fund.name:
            title += f" - {fund.name}"
        if error:
            charts.append(f"<section><h2>{html.escape(title)}</h2><p>{html.escape(error)}</p></section>")
        else:
            charts.append(
                svg_line_chart(
                    title,
                    quotes,
                    buy_dates.get(fund.isin),
                    quantity_histories.get(fund.isin, []),
                    manual_date_values.get(fund.isin, {}),
                )
            )

    document = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Fund History</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 24px; color: #18202a; background: #f7f8fa; }}
    h1 {{ margin: 0 0 4px; font-size: 28px; }}
    .meta {{ margin: 0 0 24px; color: #5d6673; }}
    section {{ margin: 0 0 22px; padding: 16px; background: #fff; border: 1px solid #dfe3e8; border-radius: 8px; }}
    h2 {{ margin: 0 0 10px; font-size: 16px; line-height: 1.35; }}
    svg {{ width: 100%; height: auto; display: block; }}
    text {{ font-size: 12px; fill: #5d6673; }}
    .grid {{ stroke: #e4e8ee; stroke-width: 1; }}
    .line {{ stroke: #1769aa; stroke-width: 2.2; }}
    .point {{ fill: #d1495b; }}
    .buy-line {{ stroke: #9aa1aa; stroke-width: 1.2; stroke-dasharray: 5 5; }}
    .buy-marker-line {{ stroke: #6c737d; stroke-width: 1.4; }}
    .buy-point {{ fill: #fff; stroke: #333942; stroke-width: 2; }}
    .buy-label {{ font-size: 12px; fill: #333942; }}
    .relative-axis-line {{ stroke: #c4c9d0; stroke-width: 1; }}
    .relative-axis {{ font-size: 12px; fill: #6c737d; }}
    .total-axis {{ font-size: 12px; fill: #4f5965; }}
    .total-line {{ stroke: #2f8f83; stroke-width: 2; }}
    .profit-axis {{ font-size: 12px; fill: #5b4b73; }}
    .profit-relative-axis {{ font-size: 12px; fill: #8b5d33; }}
    .profit-line {{ stroke: #6f5aa8; stroke-width: 2; }}
    .profit-relative-line {{ stroke: #c07a2c; stroke-width: 2; stroke-dasharray: 5 4; }}
  </style>
</head>
<body>
  <h1>Fund History</h1>
  <p class="meta">Generated {dt.datetime.now().isoformat(timespec="seconds")} for {len(results)} ISINs.</p>
  {''.join(charts)}
</body>
</html>
"""
    path.write_text(document, encoding="utf-8")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Fetch and plot fund value history per ISIN.")
    parser.add_argument("--output-dir", default="../Data/fund_history", help="Directory for cache, report, and JSON files.")
    parser.add_argument("--period", default="5y", help="Yahoo Finance range, for example 1y, 5y, 10y, max.")
    parser.add_argument("--interval", default="1d", help="Yahoo Finance interval, for example 1d, 1wk, 1mo.")
    parser.add_argument("--overrides", default=None, help="CSV with columns isin,symbol for manual Yahoo symbol mapping.")
    parser.add_argument("--manual-data", default=None, help="Excel workbook for scalar overrides and manual date/value pairs.")
    parser.add_argument("--refresh", action="store_true", help="Ignore cached ISIN resolutions and history data.")
    parser.add_argument("--sleep", type=float, default=0.4, help="Delay between online requests.")
    return parser


def main(argv: list[str] | None = None, manual_data_filename: str = "fund_manual_values.xlsx") -> int:
    args = build_arg_parser().parse_args(argv)
    base_dir = Path(__file__).resolve().parent
    output_dir = (base_dir / args.output_dir).resolve()
    cache_dir = output_dir / "cache"
    overrides_path = (base_dir / args.overrides).resolve() if args.overrides else None
    manual_data_path = (
        (base_dir / args.manual_data).resolve()
        if args.manual_data
        else base_dir / manual_data_filename
    )

    ensure_manual_data_template(manual_data_path, [])
    manual_data = read_manual_fund_data(manual_data_path)
    funds = extract_funds_from_manual_data(manual_data)
    quantity_histories = extract_quantity_history_from_manual_data(manual_data)
    overrides = read_symbol_overrides(overrides_path) if overrides_path else {}
    print(f"Found {len(funds)} unique ISINs.")
    if overrides_path:
        print(f"Using {len(overrides)} symbol overrides from {overrides_path}.")
    else:
        print("Using 0 symbol overrides.")
    print(f"Using manual fund data from {manual_data_path}.")

    report_results: list[tuple[Fund, str | None, str | None, list[Quote], str | None]] = []
    extended_results: dict[str, HistoryResult] = {}

    for fund in funds:
        try:
            result: HistoryResult | None = None
            symbol = resolve_yahoo_symbol(fund.isin, cache_dir, overrides, args.refresh)
            time.sleep(args.sleep)
            if symbol:
                yahoo_quotes = download_history(symbol, cache_dir, args.period, args.interval, args.refresh)
                time.sleep(args.sleep)
                result = HistoryResult(source="yahoo", symbol=symbol, quotes=yahoo_quotes)

            if result is None or len(result.quotes) < 2:
                onvista_result = download_onvista_history(fund.isin, cache_dir, args.period, args.refresh)
                time.sleep(args.sleep)
                if onvista_result and len(onvista_result.quotes) >= 2:
                    result = onvista_result

            if result is None or not result.quotes:
                deka_result = download_deka_current_value(fund.isin, cache_dir, args.refresh)
                time.sleep(args.sleep)
                if deka_result:
                    result = deka_result

            if result is None:
                report_results.append((fund, None, None, [], "No Yahoo Finance, Onvista, or Deka data found for this ISIN."))
                print(f"{fund.isin}: no data found")
                continue

            error = None if result.quotes else "No chart history returned."
            if len(result.quotes) == 1:
                error = "Only one current value found; no historical series available from configured sources."
            report_results.append((fund, result.source, result.symbol, result.quotes, error))
            extended_results[fund.isin] = result
            print(f"{fund.isin}: {result.source} {result.symbol}, {len(result.quotes)} points")
        except (urllib.error.URLError, TimeoutError, ValueError, KeyError, json.JSONDecodeError) as exc:
            message = f"Failed to fetch data: {exc}"
            report_results.append((fund, None, None, [], message))
            print(f"{fund.isin}: {message}", file=sys.stderr)

    buy_dates = {
        isin: parse_excel_date(scalars.get("buy_date", ""))
        for isin, scalars in manual_data.scalars.items()
    }
    write_html_report(
        report_results,
        output_dir / "fund_history_report.html",
        buy_dates,
        quantity_histories,
        manual_data.date_values,
    )
    write_extended_fund_data(
        build_extended_fund_records(funds, quantity_histories, extended_results, manual_data),
        output_dir / "extended_fund_data.json",
    )
    print(f"Wrote {output_dir / 'fund_history_report.html'}")
    print(f"Wrote {output_dir / 'extended_fund_data.json'}")
    print(f"Wrote/checked {manual_data_path}")
    return 0


if __name__ == "__main__":
    MANUAL_DATA_FILE = "fund_manual_values.xlsx"
    raise SystemExit(main(manual_data_filename=MANUAL_DATA_FILE))
