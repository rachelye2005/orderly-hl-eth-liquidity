"""Central constants for the pipeline. All values verified empirically in Phase 1."""
import os
from dotenv import load_dotenv

load_dotenv()

# ── CoinAPI (env var takes priority; falls back to Streamlit secrets if running on Cloud) ──
def _get_coinapi_key():
    key = os.getenv("COINAPI_KEY")
    if key:
        return key
    try:
        import streamlit as st
        return st.secrets.get("COINAPI_KEY", "")
    except Exception:
        return ""

COINAPI_KEY = _get_coinapi_key()
COINAPI_BASE = "https://rest.coinapi.io"

ORDERLY_SYMBOL_COINAPI = "ORDERLYNETWORK_PERP_ETH_USDC"
HL_SYMBOL_COINAPI      = "HYPERLIQUID_PERP_ETH_USDC"

# ── Native API symbols ───────────────────────────────────────────────────────
ORDERLY_SYMBOL = "PERP_ETH_USDC"
HL_COIN        = "ETH"

ORDERLY_REST = "https://api.orderly.org"
HL_REST      = "https://api.hyperliquid.xyz/info"

# ── Analysis window (14 full days, UTC) ─────────────────────────────────────
WINDOW_START_UTC = "2026-06-17T00:00:00"
WINDOW_END_UTC   = "2026-06-30T23:59:59"

WINDOW_START_MS = 1781654400000   # 2026-06-17 00:00:00 UTC in ms
WINDOW_END_MS   = 1782863999000   # 2026-06-30 23:59:59 UTC in ms

# ── Tick sizes (verified from native APIs) ───────────────────────────────────
ORDERLY_TICK = 0.01   # $0.01 price tick
HL_TICK      = 0.10   # $0.10 price tick

# ── Funding (verified empirically + from /info endpoint) ────────────────────
ORDERLY_FUNDING_INTERVAL_H = 8
ORDERLY_FUNDING_FACTOR     = 1095   # 24/8 * 365

HL_FUNDING_INTERVAL_H = 1
HL_FUNDING_FACTOR     = 8760   # 24 * 365

# ── Storage ──────────────────────────────────────────────────────────────────
DB_PATH  = "data/liquidity.duckdb"
RAW_DIR  = "data/raw"

# ── Dashboard colors ─────────────────────────────────────────────────────────
COLOR_ORDERLY = "#7B3FF2"
COLOR_HL      = "#50D2C1"
