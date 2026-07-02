# ETH Perpetual Liquidity Comparison: Orderly Network vs Hyperliquid

**Live Dashboard**: https://orderly-hl-eth-liquidity-urbd3sbweevx9w846ojyea.streamlit.app/

## Overview

This report compares ETH/USDC perpetual contract liquidity between Orderly Network and Hyperliquid over a 14-day window (June 17 to June 30, 2026). 

Data sources include CoinAPI hourly quote snapshots (672 entries), native REST API funding rate histories from both platforms (378 entries), and CoinAPI daily OHLCV candles (28 entries). ETH-USDe (different quote asset) and ETHFI-USDC (different underlying) are excluded from scope.

A critical structural difference between the two platforms shapes the entire analysis: Orderly's minimum tick size is $0.01 while Hyperliquid's is $0.10, a 10x gap. Raw basis point (bps) spreads are therefore not directly comparable. This analysis uses **tick-normalized spread** (spread / tick_size) as the primary comparison metric, measuring how tightly market makers quote relative to each platform's own price grid. Additionally, Orderly settles funding every 8 hours (annualization factor: 1095) while Hyperliquid settles hourly (factor: 8760), both verified empirically via API.

---

## Spread

Both platforms hold a median spread (P50) of 1.0 tick, meaning market makers consistently quote at the structural minimum under normal conditions. P75 remains at 1.0 tick for both, confirming this tightness holds across at least 75% of observations.

The divergence appears in the tails. Hyperliquid widens to 2.0 ticks at P95 and 4.0 ticks at P99, showing relatively contained tail behavior. Orderly maintains 1.0 tick at P95 but jumps to 28.55 ticks at P99 (equivalent to a $0.2855 spread, roughly 1.7 bps), with the single worst observation reaching 47 ticks. Orderly performs well 99% of the time, but its worst 1% is significantly more severe than Hyperliquid's.

Intraday analysis reveals that Orderly's spread deterioration clusters in two windows: UTC+8 02:00 to 06:00 and 19:00 to 23:00. These correspond to off-peak hours in the Asian trading session, during which market makers reduce quoting activity or withdraw entirely. Hyperliquid maintains 1.0 to 1.6 ticks across all hours with no comparable coverage gap.

**Volume-Weighted Average Spread (VWAS)** provides the most operationally relevant insight. Orderly's VWAS is 2.40 ticks, 2.4 times its median, indicating that the majority of actual trading volume executes during periods of wider spreads. Hyperliquid's VWAS is 1.11 ticks, closely tracking its median, meaning execution quality is consistent regardless of timing. Monitoring median spread alone would overstate Orderly's effective execution quality; VWAS should serve as the primary operational KPI.

---

## Volume

Hyperliquid recorded $11.30 billion in total notional volume over 14 days, averaging $807 million daily with a range of $235 million to $1.54 billion. Orderly recorded $233.5 million total, averaging $16.7 million daily, a gap of approximately 48x.

This gap requires context. Orderly operates as an infrastructure layer, aggregating orders from multiple Builder DEXes (WOOFi Pro, Bitget Wallet, among others) into a shared central limit order book (CLOB). Its volume represents the combined output of several front-ends. Hyperliquid is a standalone platform with a large retail trader base. The 48x difference reflects ecosystem maturity and user scale rather than a pure liquidity deficiency.

One notable anomaly: on June 29, Orderly posted $93.8 million in single-day volume, 5.6 times its daily average and accounting for 40% of the entire 14-day total. The source of this spike is unclear and may relate to a specific Builder's incentive campaign, block trading activity, or market maker rebalancing.

---

## Funding Rate

Orderly averaged 10.91% APR with a standard deviation of just 0.41%, remaining positive for 100% of all funding periods. This level of stability is unusual: in a typical market, funding rates oscillate with shifting long/short positioning. A 100% positive rate means longs consistently paid shorts throughout the entire observation window, with bearish positioning never gaining dominance. Possible explanations include an implicit floor in Orderly's funding rate mechanism, predominantly long-biased trader composition, or a different spot index anchoring methodology compared to Hyperliquid.

Hyperliquid averaged 1.38% APR with a standard deviation of 9.88%, positive in 60% of hourly periods. The frequent oscillation between positive and negative values reflects genuine two-sided positioning, a characteristic of healthy market microstructure.

The persistent divergence between the two platforms (Hyperliquid averaging 9.5 percentage points below Orderly on 8-hour aligned periods, with extremes reaching -29.7%) reveals a structural pricing gap. In theory, this creates a funding rate arbitrage opportunity: shorting on Hyperliquid while longing on Orderly to capture the rate differential in a delta-neutral position. In practice, execution depends on cross-chain capital efficiency, margin requirements, and bridging risk.

---

## Operational Implications

**Spread Coverage Gap**: Orderly market makers show clear withdrawal patterns during UTC+8 02:00 to 06:00 and 19:00 to 23:00, with P99 spreads deteriorating sharply in these windows. Time-targeted incentive mechanisms could address this gap.

**Execution Quality Monitoring**: Median spread alone is misleading given that Orderly's VWAS reaches 2.4 times its median. Volume-weighted average spread should be incorporated into the daily operations dashboard as the core metric for assessing real execution quality experienced by traders.

**Funding Rate Rebalancing**: The combination of 100% positive funding and minimal volatility suggests long/short imbalance on Orderly. Onboarding short-oriented market makers or hedging participants would help balance the position structure, reduce long-side holding costs, and bring funding rates closer to market-driven equilibrium.

**Volume Anomaly Investigation**: The June 29 volume spike warrants per-Builder breakdown analysis. Establishing automated per-Builder volume monitoring with threshold-based alerting would provide the Liquidity Ops team with the foundational capability to identify and investigate anomalous trading patterns.



# ETH 永续合约流动性对比：Orderly Network vs Hyperliquid

**仪表盘**：https://orderly-hl-eth-liquidity-urbd3sbweevx9w846ojyea.streamlit.app/

## 分析概述

本报告对比 Orderly Network 与 Hyperliquid 的 ETH/USDC 永续合约流动性表现，分析窗口为 2026年6月17日至6月30日（14个自然日）。

数据来源包括 CoinAPI 逐小时报价快照（672条）、Orderly 及 Hyperliquid 原生 REST API 资金费率历史（378条）、以及 CoinAPI 日线 OHLCV（28条）。分析排除 ETH-USDe（报价资产不同）及 ETHFI-USDC（底层资产不同）。

两平台在合约规格上存在关键差异：Orderly 最小价格变动单位（tick size）为 $0.01，Hyperliquid 为 $0.10，相差 10 倍。这意味着原始基点（bps）价差不可直接对比，本分析引入 **tick 标准化价差**（spread / tick_size）作为主要对比指标，衡量做市商在各自价格网格上的报价紧密程度。此外，Orderly 资金费率结算周期为 8 小时（年化因子 ×1095），Hyperliquid 为 1 小时（年化因子 ×8760），两项参数均通过 API 实证验证。

---

## 价差分析（Spread）

两平台中位价差（P50）均为 1.0 tick，即做市商在常态下均报至结构性极限。P75 同样保持 1.0 tick，说明 75% 以上时间两平台的报价紧密度一致。

差异出现在尾部分布。Hyperliquid P95 扩至 2.0 ticks，P99 为 4.0 ticks，尾部行为较为可控。Orderly P95 仍维持 1.0 tick，但 P99 陡升至 28.55 ticks（对应 $0.2855 价差，约 1.7 bps），最极端单次观测达 47 ticks。这意味着 Orderly 在 99% 的时间内表现优异，但最差 1% 时段的价差恶化幅度远超 Hyperliquid。

时段分析显示，Orderly 价差恶化集中于 UTC+8 02:00–06:00 及 19:00–23:00。这两个窗口对应亚洲交易时段的低谷期，做市商在此期间减少报价或完全离场，导致 spread 大幅扩张。相比之下，Hyperliquid 全天价差稳定在 1.0–1.6 ticks，做市商覆盖无明显断层。

**成交量加权价差（VWAS）** 是本分析最具区分度的指标。Orderly VWAS 为 2.40 ticks，是其中位数的 2.4 倍；Hyperliquid VWAS 为 1.11 ticks，与中位数基本持平。这一差异表明 Orderly 的大部分实际成交恰好发生在价差较宽的时段，交易者的真实执行成本显著高于中位数所暗示的水平。从运营角度看，仅监控中位价差会高估 Orderly 的执行质量，VWAS 应作为日常监控的核心 KPI。

---

## 成交量分析（Volume）

Hyperliquid 14 日总成交额 $113.0 亿，日均 $8.07 亿，日间波动范围 $2.35 亿至 $15.4 亿。Orderly 总成交额 $2.335 亿，日均 $1670 万，差距约 48 倍。

需注意两者的业务模型差异：Orderly 作为基础设施层，汇聚 WOOFi Pro、Bitget Wallet 等多个 Builder DEX 的订单至共享中央限价订单簿（CLOB），其成交量是多个前端的聚合值；Hyperliquid 是单一独立平台，拥有庞大的零售交易者基础。48 倍差距反映的是生态成熟度与用户规模的差异，而非单纯的流动性劣势。

值得关注的异常事件：6月29日 Orderly 单日成交额达 $9380 万，为日常均值的 5.6 倍，占 14 日总量的 40%。该异常峰值可能与特定 Builder DEX 的激励活动、大宗交易或做市商策略调整相关。

---

## 资金费率分析（Funding Rate）

Orderly 平均年化资金费率 10.91%，标准差仅 0.41%，14 日内 100% 为正值。这一极端稳定性不同寻常：常规市场中资金费率应随多空力量变化而波动，100% 正值意味着整个观测窗口内多头始终向空头支付费用，空方力量从未占据主导。可能成因包括：资金费率机制内置了隐性下限、平台上交易者以单向做多为主导、或定价机制对现货指数的锚定方式与 Hyperliquid 不同。

Hyperliquid 平均年化 1.38%，标准差 9.88%，正值占比 60%。资金费率频繁在正负之间切换，反映市场存在真实的多空博弈。40% 的负值时段表明空头在特定时期占据主导，这是健康市场微观结构的标志。

两平台资金费率的持续偏离（8小时对齐口径下，Hyperliquid 平均低于 Orderly 9.5 个百分点，极端偏离达 -29.7%）揭示了结构性定价差异。理论上，这一持续价差为跨平台资金费率套利提供了空间（在 Hyperliquid 做空、Orderly 做多，实现 delta 中性的同时赚取费率差），但实际执行需考虑跨链资金效率、保证金占用及桥接风险。

---

## 运营层面启示

**价差覆盖缺口**：Orderly 做市商在 UTC+8 02:00–06:00 及 19:00–23:00 存在明显的覆盖断层，P99 价差在这些时段急剧恶化。针对性的做市激励机制可有效缓解这一问题。

**执行质量监控**：中位价差作为单一指标具有误导性，Orderly VWAS 达中位数 2.4 倍的事实表明，可将成交量加权价差纳入日常运营仪表盘，作为衡量真实执行质量的核心指标。

**资金费率再平衡**：100% 正向费率与极低波动率暗示 Orderly 的多空结构失衡。引入空方导向的做市商或对冲基金参与者，有助于平衡持仓结构、降低多头持有成本，并使资金费率更贴近市场真实供需。

**异常成交量追溯**：6/29 单日成交量异常需按 Builder 维度拆分溯源。可以建立自动化的 per-Builder 成交量监控与阈值告警机制。
