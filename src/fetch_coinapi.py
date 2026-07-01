"""Pull OHLCV and historical quotes from CoinAPI. Saves raw JSON to data/raw/."""
import os, json, time, requests
from pathlib import Path
from src.config import (
    COINAPI_KEY, COINAPI_BASE,
    ORDERLY_SYMBOL_COINAPI, HL_SYMBOL_COINAPI,
    WINDOW_START_UTC, WINDOW_END_UTC, RAW_DIR,
)

_session = requests.Session()
_session.headers.update({"X-CoinAPI-Key": COINAPI_KEY, "Accept": "application/json"})
_request_count = 0


def _get(path, params=None, retries=3):
    global _request_count
    time.sleep(2)   # respect free-tier concurrency limit of 1
    url = f"{COINAPI_BASE}{path}"
    for attempt in range(retries):
        r = _session.get(url, params=params)
        _request_count += 1
        print(f"  [CoinAPI req #{_request_count}] GET {path} -> {r.status_code}")
        if r.status_code == 200:
            return r.json()
        if r.status_code == 429:
            wait = 5 * (attempt + 1)
            print(f"    Rate limited, sleeping {wait}s ...")
            time.sleep(wait)
            continue
        r.raise_for_status()
    raise RuntimeError(f"CoinAPI {path} failed after {retries} retries")


def _save_raw(name, data):
    Path(RAW_DIR).mkdir(parents=True, exist_ok=True)
    path = os.path.join(RAW_DIR, name)
    with open(path, "w") as f:
        json.dump(data, f)
    print(f"    Saved {len(data) if isinstance(data, list) else 1} records -> {path}")


def _load_raw(name):
    path = os.path.join(RAW_DIR, name)
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return None


def fetch_ohlcv(platform: str) -> list:
    """Pull 14d daily OHLCV. Returns list of candle dicts."""
    sym = ORDERLY_SYMBOL_COINAPI if platform == "orderly" else HL_SYMBOL_COINAPI
    cache_file = f"ohlcv_{platform}.json"
    cached = _load_raw(cache_file)
    if cached:
        print(f"  [cache] OHLCV {platform}: {len(cached)} candles from disk")
        return cached

    data = _get(f"/v1/ohlcv/{sym}/history", {
        "period_id": "1DAY",
        "time_start": WINDOW_START_UTC,
        "time_end":   WINDOW_END_UTC,
        "limit": 20,
    })
    _save_raw(cache_file, data)
    return data


def fetch_quotes(platform: str) -> list:
    """Pull 14d historical quotes (bid/ask snapshots). Returns list of quote dicts."""
    sym = ORDERLY_SYMBOL_COINAPI if platform == "orderly" else HL_SYMBOL_COINAPI
    cache_file = f"quotes_{platform}.json"
    cached = _load_raw(cache_file)
    if cached:
        print(f"  [cache] Quotes {platform}: {len(cached)} entries from disk")
        return cached

    data = _get(f"/v1/quotes/{sym}/history", {
        "time_start": WINDOW_START_UTC,
        "time_end":   WINDOW_END_UTC,
        "limit": 100000,
    })
    _save_raw(cache_file, data)
    return data


def fetch_quotes_hourly(platform: str) -> list:
    """Load the complete 14d hourly bid-ask snapshot file (336 entries per platform)."""
    cache_file = f"quotes_hourly_{platform}_full.json"
    cached = _load_raw(cache_file)
    if cached:
        print(f"  [cache] Quotes hourly {platform}: {len(cached)} entries from disk")
        return cached
    raise FileNotFoundError(
        f"Missing {cache_file}. Run pull_spread_full.py first."
    )


def fetch_ohlcv_hourly(platform: str) -> list:
    """Pull 14d hourly OHLCV for spread trend analysis. 336 candles, fits in 1 request."""
    sym = ORDERLY_SYMBOL_COINAPI if platform == "orderly" else HL_SYMBOL_COINAPI
    cache_file = f"ohlcv_1h_{platform}.json"
    cached = _load_raw(cache_file)
    if cached:
        print(f"  [cache] OHLCV_1H {platform}: {len(cached)} candles from disk")
        return cached

    data = _get(f"/v1/ohlcv/{sym}/history", {
        "period_id": "1HRS",
        "time_start": WINDOW_START_UTC,
        "time_end":   WINDOW_END_UTC,
        "limit": 500,
    })
    _save_raw(cache_file, data)
    return data


def get_request_count() -> int:
    return _request_count
