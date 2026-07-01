"""Pull funding rate history from Hyperliquid public REST API."""
import json, requests
from pathlib import Path
from src.config import HL_REST, HL_COIN, WINDOW_START_MS, WINDOW_END_MS, RAW_DIR


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


def fetch_funding(coin: str = HL_COIN) -> list:
    """Pull 14d funding history from Hyperliquid, filtered to analysis window."""
    cache_file = "funding_hyperliquid.json"
    cached = _load_raw(cache_file)

    if cached:
        in_window = [e for e in cached
                     if WINDOW_START_MS <= e["time"] <= WINDOW_END_MS]
        if in_window:
            print(f"  [cache] HL funding: {len(in_window)} entries in window "
                  f"(from {len(cached)} cached)")
            return in_window
        print(f"  [cache] HL funding: {len(cached)} cached entries but none in "
              f"2026 window, re-fetching...")

    r = requests.post(HL_REST,
        json={"type": "fundingHistory", "coin": coin, "startTime": WINDOW_START_MS},
        headers={"Content-Type": "application/json"},
    )
    r.raise_for_status()
    data = r.json()

    entries = [e for e in data if WINDOW_START_MS <= e["time"] <= WINDOW_END_MS]
    print(f"  [HL] funding: {len(entries)} entries in window "
          f"(from {len(data)} returned, startTime={WINDOW_START_MS})")
    _save_raw(cache_file, entries)
    return entries
