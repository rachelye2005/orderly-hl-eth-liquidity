"""Convert raw API data into normalized DataFrames ready for DuckDB."""
import pandas as pd
from src.config import (
    ORDERLY_TICK, HL_TICK,
    ORDERLY_FUNDING_FACTOR, HL_FUNDING_FACTOR,
)


def normalize_ohlcv(raw: list, platform: str) -> pd.DataFrame:
    """Convert CoinAPI OHLCV candles to volume DataFrame."""
    rows = []
    for c in raw:
        o, h, l, cl = c["price_open"], c["price_high"], c["price_low"], c["price_close"]
        typical_price = (o + h + l + cl) / 4
        vol_base = c["volume_traded"]
        vol_usd  = vol_base * typical_price
        rows.append({
            "date":       c["time_period_start"][:10],
            "platform":   platform,
            "volume_eth": vol_base,
            "volume_usd": vol_usd,
            "open":       o,
            "high":       h,
            "low":        l,
            "close":      cl,
        })
    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"])
    return df.sort_values("date").reset_index(drop=True)


def normalize_quotes_hourly(raw: list, platform: str) -> pd.DataFrame:
    """Convert merged hourly quote snapshots to spread DataFrame."""
    return normalize_quotes(raw, platform)


def normalize_quotes(raw: list, platform: str) -> pd.DataFrame:
    """Convert CoinAPI quote snapshots to spread DataFrame."""
    tick = ORDERLY_TICK if platform == "orderly" else HL_TICK
    rows = []
    for q in raw:
        bid = q.get("bid_price")
        ask = q.get("ask_price")
        if bid is None or ask is None or bid <= 0 or ask <= 0:
            continue
        mid = (bid + ask) / 2
        spread = ask - bid
        raw_bps   = (spread / mid) * 10_000
        tick_norm = spread / tick
        rows.append({
            "timestamp_utc": q["time_exchange"],
            "platform":      platform,
            "bid":           bid,
            "ask":           ask,
            "mid":           mid,
            "spread":        spread,
            "raw_bps":       raw_bps,
            "tick_norm":     tick_norm,
        })
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df["timestamp_utc"] = pd.to_datetime(df["timestamp_utc"], utc=True)
    return df.sort_values("timestamp_utc").reset_index(drop=True)


def normalize_ohlcv_hourly(raw: list, platform: str) -> pd.DataFrame:
    """Convert 1HRS OHLCV to hourly spread-range DataFrame (14-day trend proxy)."""
    tick = ORDERLY_TICK if platform == "orderly" else HL_TICK
    rows = []
    for c in raw:
        o, h, l, cl = c["price_open"], c["price_high"], c["price_low"], c["price_close"]
        mid = (h + l) / 2
        hl_range = h - l
        if mid <= 0:
            continue
        raw_bps   = (hl_range / mid) * 10_000
        tick_norm = hl_range / tick
        rows.append({
            "timestamp_utc": c["time_period_start"],
            "platform":      platform,
            "hl_range":      hl_range,
            "mid":           mid,
            "raw_bps":       raw_bps,
            "tick_norm":     tick_norm,
        })
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df["timestamp_utc"] = pd.to_datetime(df["timestamp_utc"], utc=True)
    return df.sort_values("timestamp_utc").reset_index(drop=True)


def normalize_funding_orderly(raw: list) -> pd.DataFrame:
    """Convert Orderly funding history to funding DataFrame."""
    if not raw:
        return pd.DataFrame(columns=["timestamp_utc", "platform", "rate", "apr_pct", "interval_hours"])
    rows = []
    for r in raw:
        rate = r["funding_rate"]
        apr  = rate * ORDERLY_FUNDING_FACTOR * 100   # as %
        rows.append({
            "timestamp_utc": pd.to_datetime(r["funding_rate_timestamp"], unit="ms", utc=True),
            "platform":      "orderly",
            "rate":          rate,
            "apr_pct":       apr,
            "interval_hours": 8,
        })
    return pd.DataFrame(rows).sort_values("timestamp_utc").reset_index(drop=True)


def normalize_funding_hl(raw: list) -> pd.DataFrame:
    """Convert Hyperliquid funding history to funding DataFrame."""
    rows = []
    for r in raw:
        rate = float(r["fundingRate"])
        apr  = rate * HL_FUNDING_FACTOR * 100   # as %
        rows.append({
            "timestamp_utc": pd.to_datetime(r["time"], unit="ms", utc=True),
            "platform":      "hyperliquid",
            "rate":          rate,
            "apr_pct":       apr,
            "interval_hours": 1,
        })
    return pd.DataFrame(rows).sort_values("timestamp_utc").reset_index(drop=True)
