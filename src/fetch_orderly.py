"""Pull funding rate history from Orderly public REST API."""
import json, requests
from pathlib import Path
from src.config import ORDERLY_REST, ORDERLY_SYMBOL, WINDOW_START_MS, WINDOW_END_MS, RAW_DIR


def _load_raw(name):
    path = Path(RAW_DIR) / name
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return None


def _save_raw(name, data):
    Path(RAW_DIR).mkdir(parents=True, exist_ok=True)
    with open(Path(RAW_DIR) / name, "w") as f:
        json.dump(data, f)


def fetch_funding(symbol: str = ORDERLY_SYMBOL) -> list:
    """
    Pull funding history for the 14-day window.
    Strategy: fetch without end_t (returns most recent N entries chronologically
    descending), then filter to window. One request covers months of history.
    Falls back to cached data if available.
    """
    cache_file = "funding_orderly.json"
    cached = _load_raw(cache_file)

    if cached:
        # Filter to window (cached file may contain entries outside window)
        in_window = [r for r in cached
                     if WINDOW_START_MS <= r["funding_rate_timestamp"] <= WINDOW_END_MS]
        if in_window:
            print(f"  [cache] Orderly funding: {len(in_window)} entries in window (from {len(cached)} cached)")
            return in_window
        # Cache exists but doesn't cover window - re-fetch
        print(f"  [cache] Orderly funding: cached {len(cached)} entries but none in window, re-fetching...")

    all_rows = []
    page = 1
    while True:
        r = requests.get(
            f"{ORDERLY_REST}/v1/public/funding_rate_history",
            params={"symbol": symbol, "start_t": WINDOW_START_MS,
                    "end_t": WINDOW_END_MS, "page": page, "size": 500},
        )
        r.raise_for_status()
        data = r.json()
        rows = data.get("data", {}).get("rows", [])
        print(f"  [Orderly] funding page {page}: {len(rows)} rows")
        all_rows.extend(rows)
        if len(rows) < 500:
            break
        page += 1

    _save_raw(cache_file, all_rows)
    print(f"  Orderly funding total: {len(all_rows)} entries")
    return all_rows
