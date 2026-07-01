"""Orchestrate all data pulls and write to DuckDB. Run once to populate the database."""
import os, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import duckdb
import pandas as pd
import requests as req_lib

from src.config import DB_PATH, WINDOW_START_MS, WINDOW_END_MS, ORDERLY_REST, ORDERLY_SYMBOL
from src.fetch_coinapi import fetch_ohlcv, fetch_quotes_hourly, fetch_ohlcv_hourly, get_request_count
from src.fetch_orderly import fetch_funding as orderly_funding
from src.fetch_hyperliquid import fetch_funding as hl_funding
from src.normalize import (
    normalize_ohlcv, normalize_ohlcv_hourly,
    normalize_quotes, normalize_quotes_hourly,
    normalize_funding_orderly, normalize_funding_hl,
)


def run():
    Path("data").mkdir(exist_ok=True)
    Path("data/raw").mkdir(exist_ok=True)

    print("\n=== PHASE 2: Data Pipeline ===\n")

    # ── Fetch ────────────────────────────────────────────────────────────────
    print("[1/5] Daily OHLCV (CoinAPI)...")
    ohlcv_ord = fetch_ohlcv("orderly")
    ohlcv_hl  = fetch_ohlcv("hyperliquid")

    print("\n[2/5] Hourly OHLCV for spread trend (CoinAPI)...")
    ohlcv_1h_ord = fetch_ohlcv_hourly("orderly")
    ohlcv_1h_hl  = fetch_ohlcv_hourly("hyperliquid")

    print("\n[3/5] Hourly quote snapshots for spread statistics...")
    quotes_ord = fetch_quotes_hourly("orderly")
    quotes_hl  = fetch_quotes_hourly("hyperliquid")

    print("\n[4/5] Funding - Orderly (native REST)...")
    fund_ord_raw = orderly_funding()

    print("\n[5/5] Funding - Hyperliquid (native REST)...")
    fund_hl_raw  = hl_funding()

    # ── Normalize ────────────────────────────────────────────────────────────
    print("\n--- Normalizing ---")
    vol_df = pd.concat([
        normalize_ohlcv(ohlcv_ord, "orderly"),
        normalize_ohlcv(ohlcv_hl,  "hyperliquid"),
    ], ignore_index=True)

    spread_hourly_df = pd.concat([
        normalize_ohlcv_hourly(ohlcv_1h_ord, "orderly"),
        normalize_ohlcv_hourly(ohlcv_1h_hl,  "hyperliquid"),
    ], ignore_index=True)

    spread_df = pd.concat([
        normalize_quotes_hourly(quotes_ord, "orderly"),
        normalize_quotes_hourly(quotes_hl,  "hyperliquid"),
    ], ignore_index=True)

    fund_df = pd.concat([
        normalize_funding_orderly(fund_ord_raw),
        normalize_funding_hl(fund_hl_raw),
    ], ignore_index=True)

    print(f"  volume rows: {len(vol_df)}")
    print(f"  spread (quotes) rows: {len(spread_df)}")
    print(f"  spread_hourly rows: {len(spread_hourly_df)}")
    print(f"  funding rows: {len(fund_df)}")

    # ── Store to DuckDB ───────────────────────────────────────────────────────
    print("\n--- Writing to DuckDB ---")
    con = duckdb.connect(DB_PATH)

    for tbl in ["volume", "spread", "spread_hourly", "funding"]:
        con.execute(f"DROP TABLE IF EXISTS {tbl}")

    con.execute("""
        CREATE TABLE volume (
            date        DATE,
            platform    VARCHAR,
            volume_eth  DOUBLE,
            volume_usd  DOUBLE,
            open        DOUBLE,
            high        DOUBLE,
            low         DOUBLE,
            close       DOUBLE
        )
    """)
    con.execute("""
        CREATE TABLE spread (
            timestamp_utc   TIMESTAMPTZ,
            platform        VARCHAR,
            bid             DOUBLE,
            ask             DOUBLE,
            mid             DOUBLE,
            spread          DOUBLE,
            raw_bps         DOUBLE,
            tick_norm       DOUBLE
        )
    """)
    con.execute("""
        CREATE TABLE spread_hourly (
            timestamp_utc   TIMESTAMPTZ,
            platform        VARCHAR,
            hl_range        DOUBLE,
            mid             DOUBLE,
            raw_bps         DOUBLE,
            tick_norm       DOUBLE
        )
    """)
    con.execute("""
        CREATE TABLE funding (
            timestamp_utc   TIMESTAMPTZ,
            platform        VARCHAR,
            rate            DOUBLE,
            apr_pct         DOUBLE,
            interval_hours  INTEGER
        )
    """)

    con.execute("INSERT INTO volume SELECT * FROM vol_df")
    con.execute("INSERT INTO spread SELECT * FROM spread_df")
    con.execute("INSERT INTO spread_hourly SELECT * FROM spread_hourly_df")
    con.execute("INSERT INTO funding SELECT * FROM fund_df")

    # ── CP4: Row counts ───────────────────────────────────────────────────────
    print("\n=== CP4: Data Quality Report ===")
    for tbl in ["volume", "spread", "spread_hourly", "funding"]:
        rows = con.execute(
            f"SELECT platform, COUNT(*) as n FROM {tbl} GROUP BY platform ORDER BY platform"
        ).df()
        print(f"\n  {tbl}:")
        print(rows.to_string(index=False))

    # Date range check
    print("\n  spread date range per platform:")
    rng = con.execute("""
        SELECT platform,
               MIN(timestamp_utc)::DATE AS first_day,
               MAX(timestamp_utc)::DATE AS last_day
        FROM spread GROUP BY platform
    """).df()
    print(rng.to_string(index=False))

    # ── Cross-validation: CoinAPI daily vol vs Orderly native kline ──────────
    print("\n--- Cross-validation: Orderly CoinAPI vol vs native kline (June 29) ---")
    r = req_lib.get(f"{ORDERLY_REST}/v1/public/kline",
                    params={"symbol": ORDERLY_SYMBOL, "type": "1d",
                            "start_t": WINDOW_START_MS, "end_t": WINDOW_END_MS})
    if r.status_code == 200:
        raw = r.json()
        # Orderly kline response structure varies; handle both dict and list
        data = raw.get("data", raw)
        native_rows = data.get("rows", data) if isinstance(data, dict) else data
        if native_rows:
            print(f"  Native kline returned {len(native_rows)} rows")
            # Find June 29 in both
            coinapi_june29 = con.execute("""
                SELECT date, ROUND(volume_eth,2) AS vol_eth_coinapi, ROUND(volume_usd,0) AS vol_usd_coinapi
                FROM volume WHERE platform='orderly' AND date='2026-06-29'
            """).df()
            print(f"  CoinAPI June 29: {coinapi_june29.to_string(index=False)}")
            print(f"  Native kline first row sample: {native_rows[0]}")
    else:
        print(f"  Native kline request failed: {r.status_code}")

    con.close()
    print(f"\nTotal CoinAPI requests used in pipeline: {get_request_count()}")
    print(f"DuckDB written to: {DB_PATH}")
    print("\n=== Pipeline complete ===")


if __name__ == "__main__":
    run()
