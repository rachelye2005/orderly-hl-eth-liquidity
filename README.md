# ETH Perpetual Liquidity: Orderly vs Hyperliquid

**14-Day Analysis | June 17-30, 2026 (UTC) | Liquidity Operations Assessment**

Live dashboard: [orderly-hl-eth-liquidity.streamlit.app](https://orderly-hl-eth-liquidity-urbd3sbweevx9w846ojyea.streamlit.app/)

---

## Key Findings

| Metric | Orderly | Hyperliquid |
|---|---|---|
| 14d Notional Volume | $233.5M | $11.30B |
| Median Spread (tick-norm) | 1.00 tick | 1.00 tick |
| P95 Spread (ticks) | 1.00 | 2.00 |
| Vol-Weighted Spread (ticks) | 2.40 | 1.11 |
| Mean Funding APR | 10.91% | 1.38% |
| Positive Funding Periods | 100% | 60% |

---

## Executive Summary

Over 14 days, Hyperliquid ETH-perp recorded $11.30B notional vs. Orderly PERP_ETH_USDC at $233.5M (48x ratio). Both venues share a 1.0-tick median spread under normal conditions, but Orderly is more stable at the tails (P95 = 1.0 tick vs. 2.0 ticks for Hyperliquid). Orderly's vol-weighted spread of 2.40 ticks exceeds its median, indicating spread widening concentrated in higher-volume periods. Orderly funding was positive 100% of periods at 10.9% APR, signalling persistent structural long-side demand.

## Liquidity Ops Implications

- **MM coverage gaps:** Spread widens during high-volume windows on Orderly. Targeting maker incentives at those hours is the direct lever to reduce effective transaction cost.
- **Funding calibration:** 100% positive funding creates carry drag for delta-neutral market makers. Rebate structures should offset this, or cross-venue funding arbitrage can be integrated into MM strategy design.
- **Volume decomposition:** The $233.5M aggregate masks per-builder and per-chain performance. Decomposing via the broker API is the recommended next step to identify underperforming venues.
- **Tick size advantage:** Orderly's $0.01 tick offers 10x finer price granularity vs. Hyperliquid's $0.10 tick - a structural precision advantage worth emphasizing in MM onboarding.

## Methodology

Data sources: CoinAPI (336 hourly bid-ask snapshots per platform), Orderly public REST, Hyperliquid public REST. Spread primary metric: tick-normalized = (ask-bid)/tick\_size. Funding intervals verified empirically: Orderly = 8h (factor 1095), Hyperliquid = 1h (factor 8760). Volume = base\_vol x (O+H+L+C)/4. Orderly aggregates all builder DEXes on its shared CLOB.
