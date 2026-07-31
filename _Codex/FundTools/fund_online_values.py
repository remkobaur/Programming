#!/usr/bin/env python3
"""Update the OnlineValues sheet in fund_manual_values.xlsx."""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import html
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from fund_history_tool import (
    ONLINE_VALUES_HEADERS,
    ONLINE_VALUES_SHEET,
    Fund,
    HistoryResult,
    Quote,
    configured_data_dir,
    configured_input_data_dir,
    ensure_manual_data_template,
    extract_funds_from_manual_data,
    load_project_env,
    quantity_template_rows,
    quote_at_or_before,
    read_manual_fund_data,
    read_xlsx_rows,
    resolve_path,
    rows_from_dicts,
    workbook_has_sheet,
    write_xlsx,
)


CACHE_STATS = {
    "cache_reads": 0,
    "online_requests": 0,
}

DEFAULT_SYMBOL_OVERRIDES = {
    # Yahoo search often returns the London listing first; the depot values are EUR.
    "IE00B6R52259": "IUSQ.DE",
}


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


def read_json_cache(cache_file: Path, refresh: bool) -> dict | None:
    if cache_file.exists() and not refresh:
        CACHE_STATS["cache_reads"] += 1
        return json.loads(cache_file.read_text(encoding="utf-8"))
    return None


def write_json_cache(cache_file: Path, data: dict) -> None:
    CACHE_STATS["online_requests"] += 1
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(json.dumps(data), encoding="utf-8")


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


def yahoo_symbol_score(isin: str, quote: dict) -> tuple[int, str]:
    symbol = str(quote.get("symbol") or "")
    symbol_upper = symbol.upper()
    fields = " ".join(str(quote.get(key, "")) for key in ("symbol", "shortname", "longname")).upper()
    score = 0
    if isin in fields:
        score += 100
    if quote.get("quoteType") in {"MUTUALFUND", "ETF", "EQUITY"}:
        score += 10
    if symbol_upper.endswith(".DE"):
        score += 40
    elif symbol_upper.endswith(".F"):
        score += 35
    elif symbol_upper.endswith((".BE", ".DU", ".HA", ".HM", ".MU", ".SG")):
        score += 25
    elif symbol_upper.endswith(".L"):
        score -= 25
    return score, symbol


def resolve_yahoo_symbol(
    isin: str,
    cache_dir: Path,
    overrides: dict[str, str],
    refresh: bool = False,
) -> str | None:
    if isin in overrides:
        return overrides[isin]
    if isin in DEFAULT_SYMBOL_OVERRIDES:
        return DEFAULT_SYMBOL_OVERRIDES[isin]

    cache_file = cache_dir / "isin_symbol_cache.json"
    cache: dict[str, str | None] = {}
    if cache_file.exists():
        cache = json.loads(cache_file.read_text(encoding="utf-8"))
    if isin in cache and not refresh:
        CACHE_STATS["cache_reads"] += 1
        return cache[isin]

    params = urllib.parse.urlencode({"q": isin, "quotesCount": 10, "newsCount": 0})
    url = f"https://query2.finance.yahoo.com/v1/finance/search?{params}"
    CACHE_STATS["online_requests"] += 1
    data = http_get_json(url)
    quotes = data.get("quotes", [])
    candidates = [quote for quote in quotes if quote.get("symbol")]
    symbol = max(candidates, key=lambda quote: yahoo_symbol_score(isin, quote)).get("symbol") if candidates else None

    cache[isin] = symbol
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(json.dumps(cache, indent=2, sort_keys=True), encoding="utf-8")
    return symbol


def download_yahoo_chart_data(symbol: str, cache_dir: Path, period: str, interval: str, refresh: bool = False) -> dict:
    safe_symbol = re.sub(r"[^A-Za-z0-9_.=-]", "_", symbol)
    cache_file = cache_dir / "history" / f"{safe_symbol}_{period}_{interval}.json"
    data = read_json_cache(cache_file, refresh)
    if data is None:
        params = urllib.parse.urlencode({"range": period, "interval": interval, "events": "history"})
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(symbol)}?{params}"
        data = http_get_json(url)
        write_json_cache(cache_file, data)
    return data


def yahoo_history_from_chart_data(data: dict) -> tuple[list[Quote], str | None]:
    result = data.get("chart", {}).get("result") or []
    if not result:
        return [], None
    item = result[0]
    currency = (item.get("meta") or {}).get("currency")
    timestamps = item.get("timestamp") or []
    quote = ((item.get("indicators") or {}).get("quote") or [{}])[0]
    closes = quote.get("close") or []

    history: list[Quote] = []
    for timestamp, close in zip(timestamps, closes):
        if close is None:
            continue
        date = dt.datetime.fromtimestamp(timestamp, tz=dt.UTC).date().isoformat()
        history.append(Quote(date=date, close=float(close)))
    return history, currency


def normalized_yahoo_currency(currency: str | None) -> tuple[str | None, float]:
    if not currency:
        return None, 1.0
    raw_currency = currency.strip()
    normalized = raw_currency.upper()
    if raw_currency in {"GBp", "GBX"} or normalized == "GBX":
        return "GBP", 0.01
    if normalized in {"GBP", "GBP=X"}:
        return "GBP", 1.0
    return normalized, 1.0


def convert_quotes_to_eur(
    quotes: list[Quote],
    currency: str | None,
    cache_dir: Path,
    period: str,
    interval: str,
    refresh: bool = False,
) -> list[Quote]:
    normalized_currency, unit_factor = normalized_yahoo_currency(currency)
    if normalized_currency in {None, "EUR"}:
        return [
            Quote(date=quote.date, close=quote.close * unit_factor)
            for quote in quotes
        ]

    fx_symbol = f"{normalized_currency}EUR=X"
    fx_data = download_yahoo_chart_data(fx_symbol, cache_dir, period, interval, refresh)
    fx_quotes, _fx_currency = yahoo_history_from_chart_data(fx_data)
    if not fx_quotes:
        raise ValueError(f"No EUR exchange-rate history found for {normalized_currency}.")

    converted: list[Quote] = []
    for quote in quotes:
        fx_quote = quote_at_or_before(quote.date, fx_quotes)
        if fx_quote is None:
            continue
        converted.append(Quote(date=quote.date, close=quote.close * unit_factor * fx_quote.close))
    return converted


def download_history(symbol: str, cache_dir: Path, period: str, interval: str, refresh: bool = False) -> list[Quote]:
    data = download_yahoo_chart_data(symbol, cache_dir, period, interval, refresh)
    history, currency = yahoo_history_from_chart_data(data)
    return convert_quotes_to_eur(history, currency, cache_dir, period, interval, refresh)


def search_onvista_instrument(isin: str, cache_dir: Path, refresh: bool = False) -> dict | None:
    cache_file = cache_dir / "onvista_search" / f"{isin}.json"
    data = read_json_cache(cache_file, refresh)
    if data is None:
        params = urllib.parse.urlencode({"searchValue": isin})
        url = f"https://api.onvista.de/api/v1/instruments/search?{params}"
        data = http_get_json(url)
        write_json_cache(cache_file, data)

    for item in data.get("list", []):
        if item.get("entityType") == "FUND":
            return item
    return None


def fetch_onvista_snapshot(item: dict, cache_dir: Path, refresh: bool = False) -> dict:
    entity_value = item["entityValue"]
    cache_file = cache_dir / "onvista_snapshot" / f"{entity_value}.json"
    data = read_json_cache(cache_file, refresh)
    if data is not None:
        return data

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
    write_json_cache(cache_file, snapshot)
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
    entity_value = instrument["entityValue"]

    params = {
        "range": onvista_range_from_period(period),
        "idNotation": id_notation,
        "codeMarket": code_market,
        "isoCurrency": "EUR",
        "withEarnings": "false",
    }
    params = {key: value for key, value in params.items() if value is not None}
    cache_name = f"{entity_value}_{params.get('idNotation', 'default')}_{params['range']}.json"
    cache_file = cache_dir / "onvista_history" / cache_name
    data = read_json_cache(cache_file, refresh)
    if data is None:
        query = urllib.parse.urlencode(params)
        url = f"https://api.onvista.de/api/v1/instruments/FUND/{entity_value}/simple_chart_history?{query}"
        data = http_get_json(url)
        write_json_cache(cache_file, data)

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
    data = read_json_cache(cache_file, refresh)
    if data is None:
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
        write_json_cache(cache_file, data)

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


def download_best_history(
    fund: Fund,
    cache_dir: Path,
    overrides: dict[str, str],
    period: str,
    interval: str,
    refresh: bool,
    sleep_seconds: float,
) -> HistoryResult | None:
    result: HistoryResult | None = None
    symbol = resolve_yahoo_symbol(fund.isin, cache_dir, overrides, refresh)
    time.sleep(sleep_seconds)
    if symbol:
        yahoo_quotes = download_history(symbol, cache_dir, period, interval, refresh)
        time.sleep(sleep_seconds)
        result = HistoryResult(source="yahoo", symbol=symbol, quotes=yahoo_quotes)

    if result is None or len(result.quotes) < 2:
        onvista_result = download_onvista_history(fund.isin, cache_dir, period, refresh)
        time.sleep(sleep_seconds)
        if onvista_result and len(onvista_result.quotes) >= 2:
            result = onvista_result

    if result is None or not result.quotes:
        deka_result = download_deka_current_value(fund.isin, cache_dir, refresh)
        time.sleep(sleep_seconds)
        if deka_result:
            result = deka_result

    return result


def sheet_rows(path: Path, sheet_name: str, headers: list[str]) -> list[list[object]]:
    if path.exists() and workbook_has_sheet(path, sheet_name):
        return rows_from_dicts(headers, read_xlsx_rows(path, sheet_name))
    return [headers]


def write_online_values(path: Path, rows: list[dict[str, str]]) -> None:
    manual_data = read_manual_fund_data(path)
    funds = extract_funds_from_manual_data(manual_data)
    online_rows = [ONLINE_VALUES_HEADERS] + [
        [row.get(header, "") for header in ONLINE_VALUES_HEADERS]
        for row in rows
    ]
    write_xlsx(
        path,
        {
            "ScalarValues": sheet_rows(
                path,
                "ScalarValues",
                ["isin", "name", "bank", "buy_date", "sell_date", "status", "notes"],
            ),
            "DateValuePairs": sheet_rows(
                path,
                "DateValuePairs",
                ["isin", "series", "date", "value", "notes"],
            ),
            "QuantityDatePairs": (
                sheet_rows(path, "QuantityDatePairs", ["isin", "date", "quantity", "notes"])
                if workbook_has_sheet(path, "QuantityDatePairs")
                else quantity_template_rows(funds)
            ),
            ONLINE_VALUES_SHEET: online_rows,
        },
    )


def online_rows_from_result(fund: Fund, result: HistoryResult | None, error: str | None, updated_at: str) -> list[dict[str, str]]:
    if result is None:
        return [{
            "isin": fund.isin,
            "source": "",
            "symbol": "",
            "date": "",
            "close": "",
            "error": error or "No Yahoo Finance, Onvista, or Deka data found for this ISIN.",
            "updated_at": updated_at,
        }]

    if not result.quotes:
        return [{
            "isin": fund.isin,
            "source": result.source,
            "symbol": result.symbol,
            "date": "",
            "close": "",
            "error": error or "No chart history returned.",
            "updated_at": updated_at,
        }]

    return [
        {
            "isin": fund.isin,
            "source": result.source,
            "symbol": result.symbol,
            "date": quote.date,
            "close": f"{quote.close:.8f}".rstrip("0").rstrip("."),
            "error": error or "",
            "updated_at": updated_at,
        }
        for quote in result.quotes
    ]


def env_flag(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Update OnlineValues in fund_manual_values.xlsx.")
    parser.add_argument("--output-dir", default=None, help="Directory for cache files.")
    parser.add_argument("--period", default="5y", help="Yahoo Finance range, for example 1y, 5y, 10y, max.")
    parser.add_argument("--interval", default="1d", help="Yahoo Finance interval, for example 1d, 1wk, 1mo.")
    parser.add_argument("--overrides", default=None, help="CSV with columns isin,symbol for manual Yahoo symbol mapping.")
    parser.add_argument("--manual-data", default=None, help="Excel workbook to update.")
    parser.add_argument(
        "--refresh",
        action="store_true",
        default=env_flag("FUND_ONLINE_REFRESH"),
        help="Ignore cached ISIN resolutions and history data (or set FUND_ONLINE_REFRESH=true).",
    )
    parser.add_argument("--sleep", type=float, default=0.4, help="Delay between online requests.")
    return parser


def main(argv: list[str] | None = None) -> int:
    CACHE_STATS["cache_reads"] = 0
    CACHE_STATS["online_requests"] = 0
    args = build_arg_parser().parse_args(argv)
    
    data_dir = configured_data_dir()
    input_data_dir = configured_input_data_dir()
    output_dir = (
        resolve_path(args.output_dir, Path.cwd())
        if args.output_dir
        else (data_dir / "Web_Report").resolve()
    )
    cache_dir = output_dir / "cache"
    manual_data_path = (
        resolve_path(args.manual_data, input_data_dir)
        if args.manual_data
        else input_data_dir / "fund_manual_values.xlsx"
    )
    overrides_path = resolve_path(args.overrides, input_data_dir)

    ensure_manual_data_template(manual_data_path, [])
    manual_data = read_manual_fund_data(manual_data_path)
    funds = extract_funds_from_manual_data(manual_data)
    overrides = read_symbol_overrides(overrides_path) if overrides_path else {}
    updated_at = dt.datetime.now().isoformat(timespec="seconds")
    rows: list[dict[str, str]] = []

    print(f"Found {len(funds)} unique ISINs.")
    print(f"Using manual fund data from {manual_data_path}.")
    if overrides_path:
        print(f"Using {len(overrides)} symbol overrides from {overrides_path}.")
    else:
        print("Using 0 symbol overrides.")

    for fund in funds:
        try:
            result = download_best_history(
                fund,
                cache_dir,
                overrides,
                args.period,
                args.interval,
                args.refresh,
                args.sleep,
            )
            if result is None:
                rows.extend(online_rows_from_result(fund, None, None, updated_at))
                print(f"{fund.isin}: no data found")
                continue

            error = None if result.quotes else "No chart history returned."
            if len(result.quotes) == 1:
                error = "Only one current value found; no historical series available from configured sources."
            rows.extend(online_rows_from_result(fund, result, error, updated_at))
            print(f"{fund.isin}: {result.source} {result.symbol}, {len(result.quotes)} points")
        except (urllib.error.URLError, TimeoutError, ValueError, KeyError, json.JSONDecodeError) as exc:
            message = f"Failed to fetch data: {exc}"
            rows.extend(online_rows_from_result(fund, None, message, updated_at))
            print(f"{fund.isin}: {message}", file=sys.stderr)

    write_online_values(manual_data_path, rows)
    print(f"Updated {ONLINE_VALUES_SHEET} in {manual_data_path}.")
    print(
        "Data cache: "
        f"{CACHE_STATS['cache_reads']} cached reads, "
        f"{CACHE_STATS['online_requests']} online requests."
    )
    return 0


if __name__ == "__main__":
    load_project_env()
    raise SystemExit(main())
