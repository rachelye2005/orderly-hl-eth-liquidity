"""Streamlit dashboard: ETH Perp Liquidity Comparison - Orderly vs Hyperliquid."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import duckdb
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st
from datetime import timezone

from src.config import DB_PATH, COLOR_ORDERLY, COLOR_HL
from src.metrics import (
    compute_volume_metrics,
    compute_funding_metrics,
    compute_spread_metrics,
    compute_cross_metrics,
)

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="ETH Perp Liquidity: Orderly vs Hyperliquid",
    page_icon="📊",
    layout="wide",
)

PLATFORM_COLORS = {"orderly": COLOR_ORDERLY, "hyperliquid": COLOR_HL}
PLATFORM_LABELS = {"orderly": "Orderly", "hyperliquid": "Hyperliquid"}

# ── Load data ─────────────────────────────────────────────────────────────────
@st.cache_resource
def get_connection():
    return duckdb.connect(DB_PATH, read_only=True)

@st.cache_data
def load_metrics():
    con = duckdb.connect(DB_PATH, read_only=True)
    vol  = compute_volume_metrics(con)
    fund = compute_funding_metrics(con)
    sprd = compute_spread_metrics(con)
    cross = compute_cross_metrics(con)
    con.close()
    return vol, fund, sprd, cross

vol, fund, sprd, cross = load_metrics()

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("ETH Perp Liquidity")
    st.caption("Orderly vs Hyperliquid")
    st.divider()
    st.markdown("**Analysis window**")
    st.markdown("2026-06-17 00:00 UTC+8  \n2026-06-30 23:59 UTC+8")
    st.divider()
    st.markdown("**Methodology**")
    st.markdown(
        "- Spread: tick-normalized bid-ask (primary), raw bps (secondary)  \n"
        "- Orderly tick: $0.01 | HL tick: $0.10  \n"
        "- Funding annualization: Orderly 8h (×1095), HL 1h (×8760)  \n"
        "- Volume: USD notional = base vol × typical price  \n"
        "- Orderly volume aggregates all builder DEXes on shared CLOB  \n"
        "- Spread source: 336 hourly CoinAPI bid-ask snapshots per platform"
    )
    st.divider()
    st.markdown("**Data sources**")
    st.markdown("CoinAPI · Orderly REST · Hyperliquid REST")

# ── Helpers ───────────────────────────────────────────────────────────────────
def fmt_usd(v):
    if v >= 1e9: return f"${v/1e9:.2f}B"
    if v >= 1e6: return f"${v/1e6:.1f}M"
    return f"${v:,.0f}"

def kpi_card(col, label, val_ord, val_hl, note=""):
    with col:
        st.markdown(f"**{label}**")
        c1, c2 = st.columns(2)
        c1.metric("Orderly", val_ord)
        c2.metric("Hyperliquid", val_hl)
        if note:
            st.caption(note)

# ── Tab layout ────────────────────────────────────────────────────────────────
tab_ov, tab_vol, tab_fund, tab_sprd, tab_cross = st.tabs(
    ["Overview", "Volume", "Funding", "Spread", "Cross-Analysis"]
)

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1: OVERVIEW
# ═══════════════════════════════════════════════════════════════════════════════
with tab_ov:
    st.header("14-Day Summary: ETH Perpetual Liquidity")
    st.caption("June 17 – June 30, 2026 (UTC+8) | Orderly PERP_ETH_USDC vs Hyperliquid ETH")

    # KPI row
    c1, c2, c3, c4 = st.columns(4)

    ord_vol_str = fmt_usd(vol["ord_usd"])
    hl_vol_str  = fmt_usd(vol["hl_usd"])
    ratio_str   = f"HL/Ord ratio: {vol['ratio_hl_ord']:.1f}x"

    sprd_pcts = sprd["percentiles"].set_index("platform")
    ord_p50_tick = sprd_pcts.loc["orderly",     "p50_tick"]
    hl_p50_tick  = sprd_pcts.loc["hyperliquid", "p50_tick"]
    ord_p50_bps  = sprd_pcts.loc["orderly",     "p50_bps"]
    hl_p50_bps   = sprd_pcts.loc["hyperliquid", "p50_bps"]

    fund_stats = fund["stats"].set_index("platform")
    ord_apr = fund_stats.loc["orderly",     "mean_apr"]
    hl_apr  = fund_stats.loc["hyperliquid", "mean_apr"]

    vwas = sprd["vwas"].set_index("platform")
    ord_vw_tick = vwas.loc["orderly",     "vw_tick_norm"]
    hl_vw_tick  = vwas.loc["hyperliquid", "vw_tick_norm"]

    kpi_card(c1, "14d Volume (USD notional)", ord_vol_str, hl_vol_str, ratio_str)
    kpi_card(c2, "Median Spread (tick-normalized)", f"{ord_p50_tick:.2f} ticks", f"{hl_p50_tick:.2f} ticks",
             f"Orderly {ord_p50_bps:.3f} bps | HL {hl_p50_bps:.3f} bps")
    kpi_card(c3, "Mean Funding APR", f"{ord_apr:.2f}%", f"{hl_apr:.2f}%",
             "Orderly 8h interval | HL 1h interval")
    kpi_card(c4, "Vol-Weighted Spread (ticks)", f"{ord_vw_tick:.2f}", f"{hl_vw_tick:.2f}",
             "Higher volume periods weighted more")

    st.divider()

    # Summary table
    st.subheader("Comparison Table")
    summary = pd.DataFrame({
        "Metric": [
            "14d Volume (USD)", "Daily Avg Volume",
            "Median Spread (ticks)", "P95 Spread (ticks)",
            "Median Spread (bps)", "P95 Spread (bps)",
            "Vol-Weighted Spread (ticks)",
            "Mean Funding APR (%)", "Funding Std Dev (%)",
            "% Periods Positive Funding",
        ],
        "Orderly": [
            fmt_usd(vol["ord_usd"]),
            fmt_usd(vol["ord_usd"] / 14),
            f"{ord_p50_tick:.2f}",
            f"{sprd_pcts.loc['orderly','p95_tick']:.2f}",
            f"{ord_p50_bps:.4f}",
            f"{sprd_pcts.loc['orderly','p95_bps']:.4f}",
            f"{ord_vw_tick:.2f}",
            f"{ord_apr:.3f}",
            f"{fund_stats.loc['orderly','std_apr']:.3f}",
            f"{fund_stats.loc['orderly','pct_positive']:.1f}%",
        ],
        "Hyperliquid": [
            fmt_usd(vol["hl_usd"]),
            fmt_usd(vol["hl_usd"] / 14),
            f"{hl_p50_tick:.2f}",
            f"{sprd_pcts.loc['hyperliquid','p95_tick']:.2f}",
            f"{hl_p50_bps:.4f}",
            f"{sprd_pcts.loc['hyperliquid','p95_bps']:.4f}",
            f"{hl_vw_tick:.2f}",
            f"{hl_apr:.3f}",
            f"{fund_stats.loc['hyperliquid','std_apr']:.3f}",
            f"{fund_stats.loc['hyperliquid','pct_positive']:.1f}%",
        ],
    })
    st.dataframe(summary, use_container_width=True, hide_index=True)

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2: VOLUME
# ═══════════════════════════════════════════════════════════════════════════════
with tab_vol:
    st.header("Volume")

    st.info(
        "Orderly volume aggregates all builder DEXes (WOOFi Pro, Bitget Wallet, etc.) "
        "routing into the shared CLOB. Hyperliquid represents a single venue.",
        icon="ℹ️",
    )

    daily = vol["daily"].copy()
    daily["date_str"] = daily["date"].astype(str)

    # Grouped bar chart
    fig_bar = go.Figure()
    for plat, label in PLATFORM_LABELS.items():
        d = daily[daily.platform == plat]
        fig_bar.add_trace(go.Bar(
            x=d["date_str"], y=d["volume_usd"],
            name=label,
            marker_color=PLATFORM_COLORS[plat],
        ))
    fig_bar.update_layout(
        barmode="group",
        title="Daily Volume (USD Notional)",
        xaxis_title="Date (UTC)",
        yaxis_title="Volume (USD)",
        legend=dict(orientation="h", y=1.08),
        height=420,
    )
    st.plotly_chart(fig_bar, use_container_width=True)

    # Cumulative line chart
    cum = vol["cum"].copy()
    cum["date_str"] = cum["date"].astype(str)
    fig_cum = go.Figure()
    for plat, label in PLATFORM_LABELS.items():
        d = cum[cum.platform == plat]
        fig_cum.add_trace(go.Scatter(
            x=d["date_str"], y=d["cum_usd"],
            name=label,
            line=dict(color=PLATFORM_COLORS[plat], width=2),
            mode="lines",
        ))
    fig_cum.update_layout(
        title="Cumulative Volume (USD Notional)",
        xaxis_title="Date (UTC)",
        yaxis_title="Cumulative Volume (USD)",
        legend=dict(orientation="h", y=1.08),
        height=380,
    )
    st.plotly_chart(fig_cum, use_container_width=True)

    # Stats
    c1, c2 = st.columns(2)
    c1.metric("Orderly 14d Total", fmt_usd(vol["ord_usd"]))
    c2.metric("Hyperliquid 14d Total", fmt_usd(vol["hl_usd"]))
    st.metric("HL / Orderly volume ratio", f"{vol['ratio_hl_ord']:.1f}x")
    st.caption(
        "Volume converted to USD using typical price = (O+H+L+C)/4 per daily candle. "
        "Source: CoinAPI OHLCV."
    )

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3: FUNDING
# ═══════════════════════════════════════════════════════════════════════════════
with tab_fund:
    st.header("Funding Rates")
    st.caption(
        "Orderly: 8h interval, annualization ×1095. "
        "Hyperliquid: 1h interval, annualization ×8760. "
        "Both verified empirically from historical data."
    )

    series = fund["series"].copy()
    series["ts_str"] = series["timestamp_utc"].dt.strftime("%Y-%m-%d %H:%M")

    # Time series overlay
    fig_ts = go.Figure()
    for plat, label in PLATFORM_LABELS.items():
        d = series[series.platform == plat]
        fig_ts.add_trace(go.Scatter(
            x=d["ts_str"], y=d["apr_pct"],
            name=label,
            line=dict(color=PLATFORM_COLORS[plat], width=1.5),
            mode="lines",
        ))
    fig_ts.add_hline(y=0, line_dash="dash", line_color="gray", line_width=1)
    fig_ts.update_layout(
        title="Funding Rate APR (%) Over Time",
        xaxis_title="Timestamp (UTC)",
        yaxis_title="Annualized Funding Rate (%)",
        legend=dict(orientation="h", y=1.08),
        height=420,
    )
    st.plotly_chart(fig_ts, use_container_width=True)

    col1, col2 = st.columns(2)

    with col1:
        # Distribution histogram
        fig_hist = go.Figure()
        for plat, label in PLATFORM_LABELS.items():
            d = series[series.platform == plat]["apr_pct"]
            fig_hist.add_trace(go.Histogram(
                x=d, name=label,
                marker_color=PLATFORM_COLORS[plat],
                opacity=0.7, nbinsx=40,
            ))
        fig_hist.update_layout(
            barmode="overlay",
            title="APR Distribution",
            xaxis_title="APR (%)",
            yaxis_title="Count",
            legend=dict(orientation="h", y=1.08),
            height=360,
        )
        st.plotly_chart(fig_hist, use_container_width=True)

    with col2:
        # Divergence chart (HL - Orderly, resampled 8h)
        div = fund["divergence"]
        fig_div = go.Figure()
        fig_div.add_trace(go.Bar(
            x=div["timestamp_utc"].dt.strftime("%Y-%m-%d %H:%M"),
            y=div["divergence_apr_pct"],
            marker_color=div["divergence_apr_pct"].apply(
                lambda v: COLOR_HL if v >= 0 else COLOR_ORDERLY
            ),
            name="HL minus Orderly APR",
        ))
        fig_div.add_hline(y=0, line_dash="dash", line_color="gray", line_width=1)
        fig_div.update_layout(
            title="Funding Divergence: HL minus Orderly APR (%)",
            xaxis_title="Timestamp (UTC)",
            yaxis_title="APR Difference (%)",
            height=360,
        )
        st.plotly_chart(fig_div, use_container_width=True)

    # Cumulative cost
    st.subheader("Cumulative Funding Cost on $1 Long Position")
    fig_cum = go.Figure()
    for plat, label in PLATFORM_LABELS.items():
        d = fund[f"cum_{plat}"]
        fig_cum.add_trace(go.Scatter(
            x=d["timestamp_utc"].dt.strftime("%Y-%m-%d %H:%M"),
            y=d["cum_cost_pct"],
            name=label,
            line=dict(color=PLATFORM_COLORS[plat], width=2),
        ))
    fig_cum.add_hline(y=0, line_dash="dash", line_color="gray", line_width=1)
    fig_cum.update_layout(
        xaxis_title="Timestamp (UTC)",
        yaxis_title="Cumulative Cost (%)",
        legend=dict(orientation="h", y=1.08),
        height=360,
    )
    st.plotly_chart(fig_cum, use_container_width=True)

    # Stats table
    st.subheader("Funding Statistics")
    stats = fund["stats"].copy()
    stats["platform"] = stats["platform"].map(PLATFORM_LABELS)
    stats.columns = ["Platform", "Mean APR (%)", "Std APR (%)", "% Positive Periods"]
    stats = stats.round(4)
    st.dataframe(stats, use_container_width=True, hide_index=True)

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 4: SPREAD
# ═══════════════════════════════════════════════════════════════════════════════
with tab_sprd:
    st.header("Top-of-Book Spread")

    view = st.radio(
        "Spread view",
        ["Tick-Normalized (primary)", "Raw BPS", "Effective BPS"],
        horizontal=True,
    )
    y_col    = "tick_norm" if "Tick" in view else "raw_bps"
    y_label  = "Spread (ticks)" if "Tick" in view else "Spread (bps)"
    pct_col  = "p{}_tick" if "Tick" in view else "p{}_bps"

    st.info(
        "Tick-normalized spread = (ask - bid) / tick_size. "
        "Orderly tick = $0.01, Hyperliquid tick = $0.10 (10x difference). "
        "Both platforms at 1.00 tick = equivalent maker cost per spread.",
        icon="ℹ️",
    )

    series_s = sprd["series"].copy()
    series_s["ts_str"] = series_s["timestamp_utc"].dt.strftime("%Y-%m-%d %H:%M")

    # Time series
    fig_ts = go.Figure()
    for plat, label in PLATFORM_LABELS.items():
        d = series_s[series_s.platform == plat]
        fig_ts.add_trace(go.Scatter(
            x=d["ts_str"], y=d[y_col],
            name=label,
            line=dict(color=PLATFORM_COLORS[plat], width=1.2),
            mode="lines",
        ))
    fig_ts.update_layout(
        title=f"Spread Time Series ({y_label})",
        xaxis_title="Timestamp (UTC)",
        yaxis_title=y_label,
        legend=dict(orientation="h", y=1.08),
        height=400,
    )
    st.plotly_chart(fig_ts, use_container_width=True)

    col1, col2 = st.columns(2)

    with col1:
        # Percentile bar chart
        pcts = sprd["percentiles"].set_index("platform")
        suffix = "tick" if "Tick" in view else "bps"
        perc_data = []
        for plat, label in PLATFORM_LABELS.items():
            for pct_label, pct_key in [("P50","p50"), ("P75","p75"), ("P95","p95"), ("P99","p99")]:
                perc_data.append({
                    "Percentile": pct_label,
                    "Platform": label,
                    "Value": pcts.loc[plat, f"{pct_key}_{suffix}"],
                    "color": PLATFORM_COLORS[plat],
                })
        perc_df = pd.DataFrame(perc_data)
        fig_pct = px.bar(
            perc_df, x="Percentile", y="Value", color="Platform",
            barmode="group",
            color_discrete_map={v: PLATFORM_COLORS[k] for k, v in PLATFORM_LABELS.items()},
            title=f"Spread Percentiles ({y_label})",
            labels={"Value": y_label},
        )
        fig_pct.update_layout(height=360, legend=dict(orientation="h", y=1.08))
        st.plotly_chart(fig_pct, use_container_width=True)

    with col2:
        # Hour-of-day heatmap
        hod = sprd["hod"].copy()
        hod_col = "tick_norm" if "Tick" in view else "raw_bps"
        fig_hod = go.Figure()
        for plat, label in PLATFORM_LABELS.items():
            d = hod[hod.platform == plat].sort_values("hour_utc")
            fig_hod.add_trace(go.Scatter(
                x=d["hour_utc"], y=d[hod_col],
                name=label,
                mode="lines+markers",
                line=dict(color=PLATFORM_COLORS[plat], width=2),
            ))
        fig_hod.update_layout(
            title=f"Avg Spread by Hour of Day (UTC)",
            xaxis_title="Hour (UTC)",
            yaxis_title=y_label,
            xaxis=dict(tickmode="linear", dtick=4),
            legend=dict(orientation="h", y=1.08),
            height=360,
        )
        st.plotly_chart(fig_hod, use_container_width=True)

    # Spike events
    if not sprd["spikes"].empty:
        st.subheader("Spread Spike Events (> 2x platform median)")
        spikes = sprd["spikes"].copy()
        spikes["timestamp_utc"] = spikes["timestamp_utc"].dt.strftime("%Y-%m-%d %H:%M UTC")
        spikes["platform"] = spikes["platform"].map(PLATFORM_LABELS)
        st.dataframe(
            spikes[["timestamp_utc", "platform", "tick_norm", "raw_bps", "median_tick_norm"]]
            .rename(columns={
                "timestamp_utc": "Timestamp",
                "platform": "Platform",
                "tick_norm": "Tick-Norm Spread",
                "raw_bps": "Raw BPS",
                "median_tick_norm": "Platform Median (ticks)",
            })
            .round(4),
            use_container_width=True, hide_index=True,
        )
    else:
        st.info("No spread spikes detected (no observations > 2x platform median).")

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 5: CROSS-ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════════
with tab_cross:
    st.header("Cross-Analysis")

    # Funding vs Spread scatter
    st.subheader("Funding APR vs Spread (Tick-Normalized)")
    fig_scat = go.Figure()
    for plat, label in PLATFORM_LABELS.items():
        d = cross[plat]["data"]
        r = cross[plat]["pearson_r"]
        fig_scat.add_trace(go.Scatter(
            x=d["apr_pct"], y=d["tick_norm"],
            mode="markers",
            name=f"{label} (r={r:.3f})",
            marker=dict(color=PLATFORM_COLORS[plat], size=6, opacity=0.6),
        ))
        # regression line
        if len(d) > 5 and not np.isnan(r):
            m, b = np.polyfit(d["apr_pct"], d["tick_norm"], 1)
            x_range = np.linspace(d["apr_pct"].min(), d["apr_pct"].max(), 50)
            fig_scat.add_trace(go.Scatter(
                x=x_range, y=m * x_range + b,
                mode="lines",
                line=dict(color=PLATFORM_COLORS[plat], width=1.5, dash="dash"),
                showlegend=False,
            ))
    fig_scat.update_layout(
        xaxis_title="Funding APR (%)",
        yaxis_title="Spread (ticks)",
        legend=dict(orientation="h", y=1.08),
        height=420,
    )
    st.plotly_chart(fig_scat, use_container_width=True)

    # Volume-weighted vs median spread comparison
    st.subheader("Volume-Weighted Spread vs Simple Median")
    vwas = sprd["vwas"].set_index("platform")
    pcts = sprd["percentiles"].set_index("platform")
    cmp_data = []
    for plat, label in PLATFORM_LABELS.items():
        cmp_data.append({
            "Platform": label,
            "Simple Median (ticks)": round(pcts.loc[plat, "p50_tick"], 4),
            "Vol-Weighted Spread (ticks)": round(vwas.loc[plat, "vw_tick_norm"], 4),
            "Difference": round(vwas.loc[plat, "vw_tick_norm"] - pcts.loc[plat, "p50_tick"], 4),
        })
    st.dataframe(pd.DataFrame(cmp_data), use_container_width=True, hide_index=True)
    st.caption(
        "A vol-weighted spread higher than the simple median indicates spread tends "
        "to widen during high-volume periods, which increases effective transaction cost."
    )

    # Liquidity Ops interpretation
    st.divider()
    st.subheader("Liquidity Operations Interpretation")
    st.markdown(
        """
**Volume:** Hyperliquid's 14-day notional is significantly larger than Orderly's aggregate.
However, Orderly's volume represents a multi-venue sum across all builder DEXes on a shared CLOB,
making per-venue depth and market maker incentive design the relevant levers, not raw headline volume.

**Spread:** Both platforms maintain near-minimum tick spread (1.00 tick) under normal conditions,
indicating active market maker coverage. Divergence between tick-normalized and raw bps views reflects
the 10x tick size difference: Orderly's tighter $0.01 tick translates to lower absolute spread cost
for traders despite equal tick-normalized depth.

**Funding:** Persistent positive funding on either platform signals net long bias in the market.
For Liquidity Ops, this creates an asymmetric incentive environment: market makers absorbing short
delta face structural funding drag, which informs incentive rate calibration for delta-hedged strategies.

**Actionable levers for Liquidity Ops:**
- Hours with elevated spread (hour-of-day chart) are candidates for targeted MM incentive windows
- Funding divergence between platforms signals potential cross-venue arbitrage flow affecting CLOB depth
- Volume-weighted spread exceeding median spread warrants investigation into MM dropout during volatility
"""
    )
