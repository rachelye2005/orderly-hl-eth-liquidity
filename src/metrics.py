"""Compute all dashboard metrics from normalized DataFrames."""
import pandas as pd
import numpy as np
import duckdb


def compute_volume_metrics(con: duckdb.DuckDBPyConnection) -> dict:
    """14d totals, daily series, ratio."""
    totals = con.execute("""
        SELECT platform,
               SUM(volume_eth) AS total_eth,
               SUM(volume_usd) AS total_usd
        FROM volume
        GROUP BY platform
    """).df()

    ord_usd = totals.loc[totals.platform == "orderly",   "total_usd"].values[0]
    hl_usd  = totals.loc[totals.platform == "hyperliquid","total_usd"].values[0]

    daily = con.execute("""
        SELECT date, platform, volume_eth, volume_usd
        FROM volume ORDER BY date, platform
    """).df()

    cum = daily.copy()
    cum["cum_usd"] = cum.groupby("platform")["volume_usd"].cumsum()

    return {
        "totals":    totals,
        "daily":     daily,
        "cum":       cum,
        "ord_usd":   ord_usd,
        "hl_usd":    hl_usd,
        "ratio_hl_ord": hl_usd / ord_usd if ord_usd > 0 else None,
    }


def compute_funding_metrics(con: duckdb.DuckDBPyConnection) -> dict:
    """Mean APR, std, directional bias, cumulative cost."""
    stats = con.execute("""
        SELECT platform,
               AVG(apr_pct)  AS mean_apr,
               STDDEV(apr_pct) AS std_apr,
               AVG(CASE WHEN rate > 0 THEN 1.0 ELSE 0.0 END) * 100 AS pct_positive
        FROM funding
        GROUP BY platform
    """).df()

    series = con.execute("""
        SELECT timestamp_utc, platform, rate, apr_pct
        FROM funding ORDER BY timestamp_utc, platform
    """).df()
    series["timestamp_utc"] = pd.to_datetime(series["timestamp_utc"])

    # Cumulative funding cost on $1 long: product of (1 + rate_per_period) - 1
    result = {}
    for plat in ["orderly", "hyperliquid"]:
        sub = series[series.platform == plat].copy().reset_index(drop=True)
        sub["cum_cost_pct"] = (1 + sub["rate"]).cumprod() - 1
        sub["cum_cost_pct"] *= 100
        result[f"cum_{plat}"] = sub

    # Divergence: HL APR - Orderly APR (resample both to 8h, match timestamps)
    ord_s  = series[series.platform == "orderly"].set_index("timestamp_utc")["apr_pct"]
    hl_s   = series[series.platform == "hyperliquid"].set_index("timestamp_utc")["apr_pct"]
    hl_8h  = hl_s.resample("8h").mean()
    div    = (hl_8h - ord_s).dropna().reset_index()
    div.columns = ["timestamp_utc", "divergence_apr_pct"]

    return {
        "stats":   stats,
        "series":  series,
        "divergence": div,
        **result,
    }


def compute_spread_metrics(con: duckdb.DuckDBPyConnection) -> dict:
    """Percentiles, spikes, hour-of-day averages."""
    pcts = con.execute("""
        SELECT platform,
               PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY tick_norm) AS p50_tick,
               PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY tick_norm) AS p75_tick,
               PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY tick_norm) AS p95_tick,
               PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY tick_norm) AS p99_tick,
               PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY raw_bps)   AS p50_bps,
               PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY raw_bps)   AS p75_bps,
               PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY raw_bps)   AS p95_bps,
               PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY raw_bps)   AS p99_bps,
               STDDEV(tick_norm) AS std_tick,
               STDDEV(raw_bps)   AS std_bps,
               COUNT(*)          AS n_obs
        FROM spread
        GROUP BY platform
    """).df()

    series = con.execute("""
        SELECT timestamp_utc, platform, bid, ask, mid, spread, raw_bps, tick_norm
        FROM spread ORDER BY timestamp_utc
    """).df()
    series["timestamp_utc"] = pd.to_datetime(series["timestamp_utc"])

    # Spike detection: > 2x platform's own median tick_norm
    spike_rows = []
    for plat in ["orderly", "hyperliquid"]:
        sub = series[series.platform == plat].copy()
        med = sub["tick_norm"].median()
        spikes = sub[sub["tick_norm"] > 2 * med].copy()
        spikes["median_tick_norm"] = med
        spike_rows.append(spikes)
    spikes_df = pd.concat(spike_rows) if spike_rows else pd.DataFrame()

    # Hour-of-day average (UTC)
    series["hour_utc"] = series["timestamp_utc"].dt.hour
    hod = series.groupby(["platform", "hour_utc"])[["tick_norm", "raw_bps"]].mean().reset_index()

    # Volume-weighted spread (joined with daily volume)
    vwas = con.execute("""
        WITH daily_spread AS (
            SELECT platform,
                   CAST(timestamp_utc AS DATE) AS date,
                   AVG(tick_norm) AS avg_tick_norm,
                   AVG(raw_bps)   AS avg_raw_bps
            FROM spread
            GROUP BY platform, CAST(timestamp_utc AS DATE)
        ),
        daily_vol AS (
            SELECT platform, date, volume_usd
            FROM volume
        )
        SELECT ds.platform,
               SUM(ds.avg_tick_norm * dv.volume_usd) / SUM(dv.volume_usd) AS vw_tick_norm,
               SUM(ds.avg_raw_bps   * dv.volume_usd) / SUM(dv.volume_usd) AS vw_raw_bps
        FROM daily_spread ds
        JOIN daily_vol dv ON ds.platform = dv.platform AND ds.date = dv.date
        GROUP BY ds.platform
    """).df()

    return {
        "percentiles": pcts,
        "series":      series,
        "spikes":      spikes_df,
        "hod":         hod,
        "vwas":        vwas,
    }


def compute_cross_metrics(con: duckdb.DuckDBPyConnection) -> dict:
    """Funding vs spread correlation per platform."""
    # Join 8h-resampled spread with funding (both on 8h cadence for Orderly)
    spread_df = con.execute("""
        SELECT platform, timestamp_utc, tick_norm, raw_bps
        FROM spread ORDER BY timestamp_utc
    """).df()
    spread_df["timestamp_utc"] = pd.to_datetime(spread_df["timestamp_utc"])

    fund_df = con.execute("""
        SELECT platform, timestamp_utc, apr_pct
        FROM funding ORDER BY timestamp_utc
    """).df()
    fund_df["timestamp_utc"] = pd.to_datetime(fund_df["timestamp_utc"])

    corr_results = {}
    for plat in ["orderly", "hyperliquid"]:
        sp = spread_df[spread_df.platform == plat].copy()
        fn = fund_df[fund_df.platform == plat].copy()
        # Floor both to the nearest hour to eliminate sub-second offsets
        sp["hour"] = sp["timestamp_utc"].dt.floor("h")
        fn["hour"] = fn["timestamp_utc"].dt.floor("h")
        sp_h = sp.groupby("hour")["tick_norm"].mean()
        fn_h = fn.groupby("hour")["apr_pct"].mean()
        # Resample to 8h so sample sizes are manageable and comparable across platforms
        sp_8h = sp_h.resample("8h", origin="start_day").mean().dropna()
        fn_8h = fn_h.resample("8h", origin="start_day").mean().dropna()
        merged = sp_8h.rename("tick_norm").to_frame().join(
            fn_8h.rename("apr_pct"), how="inner"
        ).dropna()
        if len(merged) > 5 and merged["tick_norm"].std() > 0 and merged["apr_pct"].std() > 0:
            r = merged["tick_norm"].corr(merged["apr_pct"])
        else:
            r = float("nan")
        corr_results[plat] = {"data": merged.reset_index(), "pearson_r": r}

    return corr_results
