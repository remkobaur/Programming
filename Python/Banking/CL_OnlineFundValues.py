import argparse
import calendar
import os
import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any, Optional

import requests


YAHOO_SEARCH_URL = "https://query2.finance.yahoo.com/v1/finance/search"
YAHOO_QUOTE_URL = "https://query1.finance.yahoo.com/v7/finance/quote"
YAHOO_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
OPENFIGI_MAPPING_URL = "https://api.openfigi.com/v3/mapping"
STOOQ_DAILY_URL = "https://stooq.com/q/d/l/"
ISIN_PATTERN = re.compile(r"^[A-Z]{2}[A-Z0-9]{9}[0-9]$")
_QUOTE_CACHE: dict[tuple[str, str], "QuoteResult"] = {}
_HIST_CACHE: dict[tuple[str, str, str], "QuoteResult"] = {}


@dataclass
class QuoteResult:
    isin: str
    symbol: str
    name: str
    price: float
    currency: str
    exchange: str
    market_state: str
    timestamp_utc: str


def _validate_isin(isin: str) -> str:
    isin_norm = isin.strip().upper()
    if not ISIN_PATTERN.match(isin_norm):
        raise ValueError(f"Invalid ISIN format: {isin}")
    return isin_norm


def _session() -> requests.Session:
    s = requests.Session()
    s.headers.update(
        {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0 Safari/537.36"
            ),
            "Accept": "application/json",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://finance.yahoo.com/",
        }
    )
    return s


def _search_symbol_by_isin(
    isin: str, s: requests.Session, preferred_currency: Optional[str] = None
) -> dict[str, Any]:
    params = {"q": isin, "quotesCount": 20, "newsCount": 0}
    res = s.get(YAHOO_SEARCH_URL, params=params, timeout=20)
    res.raise_for_status()
    data = res.json()

    quotes = data.get("quotes", [])
    if not quotes:
        fallback = _search_symbol_by_isin_via_openfigi(
            isin=isin, s=s, preferred_currency=preferred_currency
        )
        if fallback:
            return fallback
        raise LookupError(f"No instrument found for ISIN {isin}")

    preferred_currency = preferred_currency.upper() if preferred_currency else None

    def score(q: dict[str, Any]) -> int:
        sc = 0
        quote_type = (q.get("quoteType") or "").upper()
        if quote_type in {"ETF", "MUTUALFUND", "EQUITY", "INDEX"}:
            sc += 20
        if q.get("isYahooFinance"):
            sc += 5
        if q.get("symbol"):
            sc += 5
        currency = (q.get("currency") or "").upper()
        if preferred_currency and currency == preferred_currency:
            sc += 5
        return sc

    ranked = sorted(quotes, key=score, reverse=True)
    best = ranked[0]
    if not best.get("symbol"):
        raise LookupError(f"No tradable symbol resolved for ISIN {isin}")
    return best


def _search_symbol_by_isin_via_openfigi(
    isin: str, s: requests.Session, preferred_currency: Optional[str] = None
) -> Optional[dict[str, Any]]:
    payload = [{"idType": "ID_ISIN", "idValue": isin}]
    try:
        res = s.post(OPENFIGI_MAPPING_URL, json=payload, timeout=20)
        res.raise_for_status()
        rows = (res.json() or [{}])[0].get("data", [])
    except Exception:
        return None

    if not rows:
        return None

    preferred_currency = preferred_currency.upper() if preferred_currency else None
    candidates: list[dict[str, Any]] = []
    seen: set[str] = set()

    for row in rows:
        ticker = row.get("ticker")
        if not ticker or ticker in seen:
            continue
        seen.add(ticker)

        sr = s.get(
            YAHOO_SEARCH_URL,
            params={"q": ticker, "quotesCount": 20, "newsCount": 0},
            timeout=20,
        )
        if sr.status_code != 200:
            continue
        y_quotes = sr.json().get("quotes", [])

        for q in y_quotes:
            symbol = q.get("symbol")
            if not symbol:
                continue
            # Prefer exact ticker match before exchange suffix (e.g. S6TB.MU).
            if not (symbol == ticker or symbol.startswith(ticker + ".")):
                continue
            candidates.append(q)

    if not candidates:
        return None

    def score(q: dict[str, Any]) -> int:
        sc = 0
        quote_type = (q.get("quoteType") or "").upper()
        if quote_type in {"MUTUALFUND", "ETF", "EQUITY"}:
            sc += 20
        if q.get("isYahooFinance"):
            sc += 5
        currency = (q.get("currency") or "").upper()
        if preferred_currency and currency == preferred_currency:
            sc += 5
        return sc

    ranked = sorted(candidates, key=score, reverse=True)
    best = ranked[0]
    if not best.get("symbol"):
        return None
    return best


def _fetch_quote(symbol: str, s: requests.Session) -> dict[str, Any]:
    params = {"symbols": symbol}
    res = s.get(YAHOO_QUOTE_URL, params=params, timeout=20)

    # Some symbols/regions return 401 on quote API. Fall back to chart API.
    if res.status_code in {401, 403}:
        return _fetch_quote_from_chart(symbol, s)

    res.raise_for_status()
    payload = res.json()
    results = payload.get("quoteResponse", {}).get("result", [])
    if not results:
        return _fetch_quote_from_chart(symbol, s)
    return results[0]


def _fetch_quote_from_chart(symbol: str, s: requests.Session) -> dict[str, Any]:
    url = YAHOO_CHART_URL.format(symbol=symbol)
    params = {"interval": "1d", "range": "1d"}
    res = s.get(url, params=params, timeout=20)
    res.raise_for_status()

    payload = res.json()
    result = payload.get("chart", {}).get("result", [])
    if not result:
        raise LookupError(f"No chart data returned for symbol {symbol}")

    meta = result[0].get("meta", {})
    ts = meta.get("regularMarketTime")
    return {
        "symbol": meta.get("symbol") or symbol,
        "regularMarketPrice": meta.get("regularMarketPrice"),
        "previousClose": meta.get("previousClose"),
        "currency": meta.get("currency"),
        "fullExchangeName": meta.get("exchangeName"),
        "marketState": meta.get("marketState"),
        "regularMarketTime": ts,
        "shortName": meta.get("shortName"),
        "longName": meta.get("longName"),
    }


def _fetch_historical_quote_for_date(
    symbol: str, s: requests.Session, target_date: date
) -> dict[str, Any]:
    def _extract_quote_from_chart_payload(payload: dict[str, Any]) -> Optional[dict[str, Any]]:
        result = payload.get("chart", {}).get("result", [])
        if not result:
            return None

        chart = result[0]
        timestamps = chart.get("timestamp") or []
        quote_data = (chart.get("indicators", {}).get("quote") or [{}])[0]
        closes = quote_data.get("close") or []

        valid_rows: list[tuple[int, float]] = []
        for ts, close in zip(timestamps, closes):
            if close is None:
                continue
            valid_rows.append((int(ts), float(close)))

        if not valid_rows:
            return None

        target_end = datetime(
            target_date.year, target_date.month, target_date.day, 23, 59, 59, tzinfo=timezone.utc
        )
        target_end_ts = int(target_end.timestamp())
        past_or_equal = [row for row in valid_rows if row[0] <= target_end_ts]
        if not past_or_equal:
            return None
        chosen_ts, chosen_close = past_or_equal[-1]

        meta = chart.get("meta", {})
        return {
            "symbol": meta.get("symbol") or symbol,
            "regularMarketPrice": chosen_close,
            "currency": meta.get("currency"),
            "fullExchangeName": meta.get("exchangeName"),
            "marketState": "HISTORICAL",
            "regularMarketTime": chosen_ts,
            "shortName": meta.get("shortName"),
            "longName": meta.get("longName"),
        }

    url = YAHOO_CHART_URL.format(symbol=symbol)

    # First try daily candles around target date.
    start_dt = datetime(target_date.year, target_date.month, target_date.day, tzinfo=timezone.utc) - timedelta(days=7)
    end_dt = datetime(target_date.year, target_date.month, target_date.day, tzinfo=timezone.utc) + timedelta(days=1)
    daily_params = {
        "interval": "1d",
        "period1": int(start_dt.timestamp()),
        "period2": int(end_dt.timestamp()),
    }
    res = s.get(url, params=daily_params, timeout=20)
    res.raise_for_status()
    out = _extract_quote_from_chart_payload(res.json())
    if out is not None:
        return out

    # Fallback: some funds expose only sparse monthly NAV history.
    monthly_params = {"interval": "1mo", "range": "10y"}
    res = s.get(url, params=monthly_params, timeout=20)
    res.raise_for_status()
    out = _extract_quote_from_chart_payload(res.json())
    if out is not None:
        return out

    raise LookupError(f"No historical close prices available for symbol {symbol}")


def _candidate_symbols_for_history(
    primary_symbol: str, s: requests.Session
) -> list[str]:
    candidates: list[str] = [primary_symbol]
    seen = {primary_symbol}

    base_ticker = primary_symbol.split(".")[0]
    sr = s.get(
        YAHOO_SEARCH_URL,
        params={"q": base_ticker, "quotesCount": 20, "newsCount": 0},
        timeout=20,
    )
    if sr.status_code == 200:
        for q in sr.json().get("quotes", []):
            sym = q.get("symbol")
            if not sym:
                continue
            if not (sym == base_ticker or sym.startswith(base_ticker + ".")):
                continue
            if sym in seen:
                continue
            seen.add(sym)
            candidates.append(sym)

    return candidates


def _candidate_stooq_symbols(primary_symbol: str) -> list[str]:
    # Stooq symbols often differ by exchange suffix; try practical variants.
    lower_symbol = primary_symbol.lower()
    base = primary_symbol.split(".")[0].lower()
    candidates = [
        lower_symbol,
        base,
        f"{base}.de",
        f"{base}.f",
        f"{base}.du",
        f"{base}.be",
        f"{base}.mu",
    ]
    seen: set[str] = set()
    unique: list[str] = []
    for sym in candidates:
        if sym in seen:
            continue
        seen.add(sym)
        unique.append(sym)
    return unique


def _fetch_historical_quote_from_stooq(
    stooq_symbol: str,
    target_date: date,
    api_key: str,
) -> dict[str, Any]:
    start = target_date - timedelta(days=40)
    params = {
        "s": stooq_symbol,
        "i": "d",
        "d1": start.strftime("%Y%m%d"),
        "d2": target_date.strftime("%Y%m%d"),
        "apikey": api_key,
    }
    res = requests.get(STOOQ_DAILY_URL, params=params, timeout=20)
    res.raise_for_status()
    text = res.text.strip()

    if not text:
        raise LookupError(f"No Stooq response data for {stooq_symbol}")
    if "Get your apikey" in text:
        raise PermissionError("Stooq API key missing or invalid.")
    if text.startswith("<"):
        raise LookupError(f"Unexpected Stooq response for {stooq_symbol}")

    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if len(lines) < 2:
        raise LookupError(f"No Stooq rows for {stooq_symbol}")

    rows: list[tuple[date, float]] = []
    for ln in lines[1:]:
        parts = ln.split(",")
        if len(parts) < 5:
            continue
        d_raw = parts[0].strip()
        c_raw = parts[4].strip()
        if not d_raw or c_raw in {"", "N/D", "nan", "NaN"}:
            continue
        try:
            d = datetime.strptime(d_raw, "%Y-%m-%d").date()
            c = float(c_raw)
        except Exception:
            continue
        if d <= target_date:
            rows.append((d, c))

    if not rows:
        raise LookupError(f"No Stooq historical close rows for {stooq_symbol}")

    chosen_date, chosen_close = sorted(rows, key=lambda x: x[0])[-1]
    chosen_ts = int(datetime(chosen_date.year, chosen_date.month, chosen_date.day, tzinfo=timezone.utc).timestamp())

    return {
        "symbol": stooq_symbol,
        "regularMarketPrice": chosen_close,
        "currency": None,
        "fullExchangeName": "STOOQ",
        "marketState": "HISTORICAL_STOOQ",
        "regularMarketTime": chosen_ts,
        "shortName": stooq_symbol,
        "longName": stooq_symbol,
    }


def get_current_value_by_isin(
    isin: str, preferred_currency: Optional[str] = None
) -> QuoteResult:
    isin_norm = _validate_isin(isin)
    currency_key = (preferred_currency or "").upper()
    cache_key = (isin_norm, currency_key)
    cached = _QUOTE_CACHE.get(cache_key)
    if cached is not None:
        return QuoteResult(**vars(cached))

    s = _session()

    instrument = _search_symbol_by_isin(isin_norm, s, preferred_currency)
    symbol = instrument["symbol"]
    quote = _fetch_quote(symbol, s)

    price = (
        quote.get("regularMarketPrice")
        or quote.get("navPrice")
        or quote.get("ask")
        or quote.get("bid")
        or quote.get("previousClose")
    )
    if price is None:
        raise LookupError(f"No price field available for symbol {symbol}")

    ts = quote.get("regularMarketTime")
    if ts is not None:
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        timestamp_utc = dt.isoformat()
    else:
        timestamp_utc = datetime.now(timezone.utc).isoformat()

    result = QuoteResult(
        isin=isin_norm,
        symbol=symbol,
        name=quote.get("longName")
        or quote.get("shortName")
        or instrument.get("shortname")
        or symbol,
        price=float(price),
        currency=(quote.get("currency") or instrument.get("currency") or "").upper(),
        exchange=quote.get("fullExchangeName")
        or instrument.get("exchange")
        or "unknown",
        market_state=quote.get("marketState") or "unknown",
        timestamp_utc=timestamp_utc,
    )
    _QUOTE_CACHE[cache_key] = result
    return QuoteResult(**vars(result))


def get_value_by_isin_on_date(
    isin: str,
    target_date: date,
    preferred_currency: Optional[str] = None,
) -> QuoteResult:
    isin_norm = _validate_isin(isin)
    currency_key = (preferred_currency or "").upper()
    cache_key = (isin_norm, currency_key, target_date.isoformat())
    cached = _HIST_CACHE.get(cache_key)
    if cached is not None:
        return QuoteResult(**vars(cached))

    s = _session()
    instrument = _search_symbol_by_isin(isin_norm, s, preferred_currency)
    symbol = instrument["symbol"]

    quote = None
    used_symbol = symbol
    last_error: Optional[Exception] = None
    for candidate_symbol in _candidate_symbols_for_history(symbol, s):
        try:
            quote = _fetch_historical_quote_for_date(candidate_symbol, s, target_date)
            used_symbol = candidate_symbol
            break
        except Exception as err:
            last_error = err

    # Optional second provider fallback: Stooq (requires STOOQ_API_KEY).
    if quote is None:
        stooq_api_key = os.getenv("STOOQ_API_KEY", "").strip()
        if stooq_api_key:
            for stooq_symbol in _candidate_stooq_symbols(symbol):
                try:
                    quote = _fetch_historical_quote_from_stooq(
                        stooq_symbol=stooq_symbol,
                        target_date=target_date,
                        api_key=stooq_api_key,
                    )
                    used_symbol = stooq_symbol
                    break
                except Exception as err:
                    last_error = err

    if quote is None:
        raise LookupError(
            f"No historical data available near {target_date.isoformat()} for ISIN {isin_norm} "
            f"(tried symbols from base ticker {symbol})."
        ) from last_error

    price = quote.get("regularMarketPrice") or quote.get("previousClose")
    if price is None:
        raise LookupError(f"No historical price field available for symbol {used_symbol}")

    ts = quote.get("regularMarketTime")
    if ts is not None:
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        timestamp_utc = dt.isoformat()
    else:
        timestamp_utc = datetime.now(timezone.utc).isoformat()

    result = QuoteResult(
        isin=isin_norm,
        symbol=used_symbol,
        name=quote.get("longName")
        or quote.get("shortName")
        or instrument.get("shortname")
        or symbol,
        price=float(price),
        currency=(quote.get("currency") or preferred_currency or instrument.get("currency") or "").upper(),
        exchange=quote.get("fullExchangeName")
        or instrument.get("exchange")
        or "unknown",
        market_state=quote.get("marketState") or "HISTORICAL",
        timestamp_utc=timestamp_utc,
    )
    _HIST_CACHE[cache_key] = result
    return QuoteResult(**vars(result))


def get_value_by_isin_for_month(
    isin: str,
    year: int,
    month: int,
    preferred_currency: Optional[str] = None,
) -> QuoteResult:
    if month < 1 or month > 12:
        raise ValueError(f"Invalid month: {month}. Use 1..12.")
    last_day = calendar.monthrange(year, month)[1]
    month_end = date(year, month, last_day)
    quote = get_value_by_isin_on_date(isin, month_end, preferred_currency)
    quote_dt = datetime.fromisoformat(quote.timestamp_utc.replace("Z", "+00:00"))
    if quote_dt.year != year or quote_dt.month != month:
        raise LookupError(
            f"No value found in {year:04d}-{month:02d} for ISIN {isin}. "
            f"Nearest available point is {quote_dt.date().isoformat()}."
        )
    return quote


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Get the latest fund/ETF value by ISIN via Yahoo Finance lookup."
    )
    parser.add_argument("isin", help="ISIN, e.g. IE00B4L5Y983")
    parser.add_argument(
        "--currency",
        help="Preferred quote currency (e.g. EUR, USD) when multiple matches exist.",
    )
    args = parser.parse_args()

    result = get_current_value_by_isin(args.isin, args.currency)
    print(f"ISIN:      {result.isin}")
    print(f"Name:      {result.name}")
    print(f"Symbol:    {result.symbol}")
    print(f"Value:     {result.price:.6g} {result.currency}")
    print(f"Exchange:  {result.exchange}")
    print(f"State:     {result.market_state}")
    print(f"Timestamp: {result.timestamp_utc}")


if __name__ == "__main__":
    main()
