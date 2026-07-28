"""Market data adapter — one seam for all price history and live quotes.

Providers:
  yfinance (default)  — no key needed; Yahoo sometimes blocks datacenter IPs
  tiingo              — set DATA_PROVIDER=tiingo and TIINGO_API_KEY
                        (free tier: 1,000 req/day, 50 symbols/hr — ample
                        for the 10-ticker universe at 13 scans/day)

Resilience: whichever provider is primary, the other is the automatic
fallback. A failing provider is benched for a cooldown window so a dead
API doesn't add a timeout to every symbol in a scan.

Schema contract (what every caller can rely on):
  DataFrame with columns Open, High, Low, Close, Volume;
  tz-naive normalized DatetimeIndex; dividend/split adjusted
  (yfinance auto_adjust ≡ Tiingo adj* fields).

Options chains and analyst data are NOT routed here — Tiingo's free tier
has neither, so the engine keeps using yfinance for those with its
existing graceful degradation.
"""

import logging
import math
import os
import time
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)

_TIINGO_BASE = "https://api.tiingo.com"
_COOLDOWN_SECONDS = 120

# provider name -> unix time until which it's benched
_benched: dict = {}


def _provider() -> str:
    return os.getenv("DATA_PROVIDER", "yfinance").strip().lower()


def _tiingo_key() -> str:
    return os.getenv("TIINGO_API_KEY", "").strip()


def _is_benched(name: str) -> bool:
    return _benched.get(name, 0) > time.time()


def _bench(name: str, err: Exception) -> None:
    _benched[name] = time.time() + _COOLDOWN_SECONDS
    logger.warning("market_data: %s failed (%s) — benched %ds",
                   name, err, _COOLDOWN_SECONDS)


def _period_to_days(period: str) -> int:
    p = period.strip().lower()
    try:
        if p.endswith("mo"):
            return int(p[:-2]) * 31
        if p.endswith("y"):
            return int(p[:-1]) * 366
        if p.endswith("d"):
            return int(p[:-1])
    except ValueError:
        pass
    return 366  # safe default: 1 year


# ── yfinance ─────────────────────────────────────────────────

def _fetch_yfinance(symbol: str, period: str) -> Optional[pd.DataFrame]:
    import yfinance as yf

    df = yf.Ticker(symbol).history(period=period, auto_adjust=True)
    if df is None or df.empty:
        return None
    df = df[["Open", "High", "Low", "Close", "Volume"]].copy()
    df = df[df["Close"].notna()]   # drop forming/placeholder bars (Close=NaN)
    df.index = pd.to_datetime(df.index).tz_localize(None).normalize()
    return df


def _live_yfinance(symbol: str) -> Optional[float]:
    import yfinance as yf

    fast = yf.Ticker(symbol).fast_info
    return fast.get("last_price") or fast.get("previous_close")


# ── Tiingo ───────────────────────────────────────────────────

def _fetch_tiingo(symbol: str, period: str) -> Optional[pd.DataFrame]:
    import requests

    key = _tiingo_key()
    if not key:
        raise RuntimeError("TIINGO_API_KEY not set")

    start = (pd.Timestamp.utcnow() - pd.Timedelta(days=_period_to_days(period))).strftime("%Y-%m-%d")
    resp = requests.get(
        f"{_TIINGO_BASE}/tiingo/daily/{symbol}/prices",
        params={"startDate": start, "format": "json", "token": key},
        timeout=10,
    )
    resp.raise_for_status()
    rows = resp.json()
    if not rows:
        return None

    df = pd.DataFrame(rows)
    # adj* fields = dividend/split adjusted, matching yfinance auto_adjust
    df = df.rename(columns={
        "adjOpen": "Open", "adjHigh": "High", "adjLow": "Low",
        "adjClose": "Close", "adjVolume": "Volume",
    })[["date", "Open", "High", "Low", "Close", "Volume"]]
    df["date"] = pd.to_datetime(df["date"]).dt.tz_localize(None).dt.normalize()
    df = df.set_index("date").sort_index()
    df = df[df["Close"].notna()]   # drop any bar with no settled Close
    df["Volume"] = df["Volume"].astype(float)
    return df


def _live_tiingo(symbol: str) -> Optional[float]:
    import requests

    key = _tiingo_key()
    if not key:
        raise RuntimeError("TIINGO_API_KEY not set")
    resp = requests.get(
        f"{_TIINGO_BASE}/iex/",
        params={"tickers": symbol, "token": key},
        timeout=10,
    )
    resp.raise_for_status()
    rows = resp.json()
    if not rows:
        return None
    row = rows[0]
    return row.get("last") or row.get("tngoLast") or row.get("prevClose")


# ── Public API ───────────────────────────────────────────────

_FETCHERS = {"yfinance": _fetch_yfinance, "tiingo": _fetch_tiingo}
_LIVE = {"yfinance": _live_yfinance, "tiingo": _live_tiingo}


def _ordered_providers() -> list:
    primary = _provider() if _provider() in _FETCHERS else "yfinance"
    fallback = "tiingo" if primary == "yfinance" else "yfinance"
    order = [primary, fallback]
    # A keyless tiingo can never succeed — don't waste a timeout on it.
    return [p for p in order if not (p == "tiingo" and not _tiingo_key())]


def get_daily_history(symbol: str, period: str = "1y") -> Optional[pd.DataFrame]:
    """Daily OHLCV per the schema contract, or None. Tries the primary
    provider, then the fallback; benches whichever one errors."""
    last_err = None
    for name in _ordered_providers():
        if _is_benched(name):
            continue
        try:
            df = _FETCHERS[name](symbol, period)
            if df is not None and not df.empty:
                return df
        except Exception as e:
            last_err = e
            _bench(name, e)
    if last_err:
        logger.warning("market_data: all providers failed for %s: %s", symbol, last_err)
    return None


def get_live_price(symbol: str) -> Optional[float]:
    """Last trade / latest price, provider-routed with fallback."""
    for name in _ordered_providers():
        if _is_benched(name):
            continue
        try:
            price = _LIVE[name](symbol)
            if price:
                return float(price)
        except Exception as e:
            _bench(name, e)
    return None


def append_live_bar(df: pd.DataFrame, symbol: str) -> pd.DataFrame:
    """If the daily history ends before today (Tiingo EOD updates after the
    close), append a provisional bar at the live price so intraday scans see
    today's move. Volume is NaN — deliberately: fabricating volume would
    fake out the volume-spike signal, NaN just makes it sit out."""
    if df is None or df.empty:
        return df
    today = pd.Timestamp.now(tz="America/New_York").normalize().tz_localize(None)
    if df.index[-1] >= today:
        return df
    price = get_live_price(symbol)
    # `not price` does NOT catch NaN (not float('nan') is False), so a NaN live
    # price would slip through and create a provisional bar with Close=NaN —
    # which poisons every downstream calc (price, indicators, market_context,
    # predictions, scan). Guard NaN/inf/<=0 explicitly: fall back to settled
    # history rather than append a junk bar.
    if not price or not math.isfinite(price) or price <= 0:
        return df
    bar = pd.DataFrame(
        {"Open": [price], "High": [price], "Low": [price],
         "Close": [price], "Volume": [float("nan")]},
        index=[today],
    )
    return pd.concat([df, bar])
