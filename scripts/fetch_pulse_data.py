#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "yfinance>=0.2.36",
#     "fredapi>=0.5.1",
#     "pandas>=2.0.0",
# ]
# ///
"""
Fetch macro data for Pulse dashboard.
Sources: yfinance (market data), FRED API (economic indicators).

Usage:
    # Fetch all API-sourced metrics:
    export FRED_API_KEY=your_key_here
    uv run scripts/fetch_pulse_data.py

    # Load manual metrics from CSV (add new rows to CSV, then re-run):
    uv run scripts/fetch_pulse_data.py backfill china_pmi data/backfill/china_pmi.csv

Output: assets/data/pulse/metrics.json
"""

import argparse
import csv
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

import yfinance as yf
from fredapi import Fred

# ─── Configuration ───────────────────────────────────────────────────────────

FRED_API_KEY = os.environ.get("FRED_API_KEY")
OUTPUT_PATH = Path(__file__).resolve().parent.parent / "assets" / "data" / "pulse" / "metrics.json"
LOOKBACK_YEARS = 5

# ─── Metric definitions ─────────────────────────────────────────────────────

# Each metric: key → config dict
# source_type: "yfinance", "fred", "computed", "manual"
METRICS = {
    # ── Currencies ──
    "dxy": {
        "name": "US Dollar Index",
        "name_zh": "美元指数",
        "description": "Dollar vs a basket of major fiat currencies (euro-heavy). A relative measure — if all currencies debase together, DXY stays flat while purchasing power erodes.",
        "source_type": "yfinance",
        "ticker": "DX-Y.NYB",
        "unit": "index",
    },
    "eurusd": {
        "name": "EUR/USD",
        "name_zh": "欧元/美元",
        "description": "The euro is DXY's largest component (~58%). EUR/USD rising = dollar weakening in its most liquid pair. Also reflects relative ECB vs Fed policy divergence.",
        "source_type": "yfinance",
        "ticker": "EURUSD=X",
        "unit": "rate",
    },
    "usdcny": {
        "name": "USD/CNY",
        "name_zh": "美元/人民币",
        "description": "Dollar-yuan exchange rate. Falling = yuan strengthening. A sustained move below 7.00 signals meaningful capital flow shift toward China.",
        "source_type": "yfinance",
        "ticker": "CNY=X",
        "unit": "rate",
    },
    "usd_reserves_share": {
        "name": "USD Share of Reserves",
        "name_zh": "美元储备占比",
        "description": "How much of global central bank reserves are held in dollars (IMF COFER data, quarterly, lagged). Dropped from 72% in 2000 — slow-moving but structural and largely irreversible.",
        "source_type": "manual",
        "frequency": "quarterly",
        "unit": "%",
        "note": "Quarterly, lagged — IMF COFER",
    },

    # ── Rates & Yields ──
    "us_10y": {
        "name": "US 10Y Yield",
        "name_zh": "美国十年期国债收益率",
        "description": "The stress thermometer for US fiscal health. Rising yields = market demanding more compensation to hold US debt. Above 5% is a yellow flag, above 6% likely forces Fed intervention.",
        "source_type": "yfinance",
        "ticker": "^TNX",
        "unit": "%",
        "change_mode": "bp",
    },
    "yield_curve": {
        "name": "10Y-2Y Spread",
        "name_zh": "收益率曲线（10Y-2Y利差）",
        "description": "The classic recession signal. Inverted (negative) = market pricing rate cuts ahead. Re-steepening after inversion historically precedes recessions within 6-18 months.",
        "source_type": "fred",
        "series": "T10Y2Y",
        "unit": "% spread",
        "change_mode": "bp",
    },
    "tips_5y": {
        "name": "US 5Y TIPS (Real Yield)",
        "name_zh": "五年期实际利率（TIPS）",
        "description": "The real cost of money after inflation. When negative, holding cash loses purchasing power — the engine that drives capital into gold and hard assets. Gromen's key metric for fiscal dominance.",
        "source_type": "fred",
        "series": "DFII5",
        "unit": "%",
        "change_mode": "bp",
    },
    "breakeven_10y": {
        "name": "10Y Breakeven Inflation",
        "name_zh": "十年期盈亏平衡通胀率",
        "description": "Market-implied inflation expectation for the next 10 years. Rising breakevens = market pricing structurally higher inflation. Directly validates or challenges the debasement thesis.",
        "source_type": "fred",
        "series": "T10YIE",
        "unit": "%",
        "change_mode": "bp",
    },
    "hy_spread": {
        "name": "HY Credit Spread (OAS)",
        "name_zh": "高收益债利差",
        "description": "High-yield bond spread over Treasuries. Widening = stress in credit markets, risk-off. Tight spreads = complacency. A spike above 5% historically signals recession risk.",
        "source_type": "fred",
        "series": "BAMLH0A0HYM2",
        "unit": "%",
        "change_mode": "bp",
    },

    # ── Liquidity & Fiscal ──
    "fed_balance_sheet": {
        "name": "Fed Balance Sheet",
        "name_zh": "美联储资产负债表",
        "description": "The ammo reserve of the buyer of last resort. Currently shrinking (QT), but any Treasury market stress forces re-expansion. Direction tells you whether fiscal dominance has gone from implicit to explicit.",
        "source_type": "fred",
        "series": "WALCL",
        "unit": "$T",
        "transform": lambda v: round(v / 1_000_000, 2),  # millions → trillions
    },
    "debt_to_gdp": {
        "name": "US Debt/GDP",
        "name_zh": "美国债务/GDP",
        "description": "The denominator matters as much as the numerator. If GDP grows faster than debt, the ratio stabilizes. If not, the compounding math takes over. As long as this number climbs, all other pressures persist.",
        "source_type": "fred",
        "series": "GFDEGDQ188S",
        "unit": "%",
        "note": "Quarterly, interpolated",
    },
    "tga": {
        "name": "Treasury General Account",
        "name_zh": "财政部一般账户（TGA）",
        "description": "The US government's checking account at the Fed. Drawdowns inject liquidity into markets (bullish). Refills (post-debt-ceiling) drain it. Liquidity plumbing that moves risk assets.",
        "source_type": "fred",
        "series": "WTREGEN",
        "unit": "$B",
        "transform": lambda v: round(v / 1_000, 1),  # millions → billions
    },

    # ── Metals ──
    "gold": {
        "name": "Gold",
        "name_zh": "黄金",
        "description": "The trust scoreboard. When gold rises alongside rising yields and a falling dollar, the market is pricing loss of confidence in the fiscal trajectory. Central banks buying gold = voting with their reserves.",
        "source_type": "yfinance",
        "ticker": "GC=F",
        "unit": "$/oz",
    },
    "silver": {
        "name": "Silver",
        "name_zh": "白银",
        "description": "Dual identity: monetary metal (like gold) AND industrial metal (solar panels, electronics). The silver market is in structural deficit. Outperforms gold in bull runs, more volatile.",
        "source_type": "yfinance",
        "ticker": "SI=F",
        "unit": "$/oz",
    },
    "copper": {
        "name": "Copper",
        "name_zh": "铜",
        "description": "The electrification bellwether. EVs use 3-4x more copper than ICE vehicles. Data centers, wind turbines, grid upgrades all need copper. Supply growth structurally constrained (mines take 7-15 years). Goldman calls it 'the new oil.'",
        "source_type": "yfinance",
        "ticker": "HG=F",
        "unit": "$/lb",
    },
    "uranium": {
        "name": "Uranium (URA ETF)",
        "name_zh": "铀（URA ETF）",
        "description": "Global X Uranium ETF. Proxy for the nuclear renaissance thesis — 30+ countries committed to tripling nuclear capacity. Supply constrained: Russia controls 40% of global enrichment.",
        "source_type": "yfinance",
        "ticker": "URA",
        "unit": "$",
    },

    # ── Energy ──
    "oil": {
        "name": "WTI Crude",
        "name_zh": "WTI原油",
        "description": "West Texas Intermediate crude oil. The one commodity with significant political suppression risk (Saudi deals, SPR releases). Tension between political will to lower prices and geological reality of tight supply.",
        "source_type": "yfinance",
        "ticker": "CL=F",
        "unit": "$/bbl",
    },
    "natgas": {
        "name": "Natural Gas",
        "name_zh": "天然气",
        "description": "Key energy source for power generation. AI data centers are driving massive new electricity demand, tightening the gas market. Also a geopolitical commodity (Russia/Europe, LNG exports).",
        "source_type": "yfinance",
        "ticker": "NG=F",
        "unit": "$/MMBtu",
    },
    "energy_cpi": {
        "name": "Energy Services CPI YoY",
        "name_zh": "能源服务CPI（同比）",
        "description": "Year-over-year change in energy services prices (BLS). The hottest CPI component — directly tied to AI data center power demand. Above 7% creates real political backlash against AI deployment.",
        "source_type": "fred",
        "series": "CUSR0000SEHF",
        "unit": "% YoY",
        "note": "Monthly, lagged",
        "transform_yoy": True,
    },

    # ── US Equities & Sectors ──
    "sp500": {
        "name": "S&P 500",
        "name_zh": "标普500",
        "description": "The broad US equity benchmark. Tracks overall market health. Compare with QQQ/SMH to see whether tech is leading or lagging the broader market.",
        "source_type": "yfinance",
        "ticker": "^GSPC",
        "unit": "index",
    },
    "qqq": {
        "name": "Nasdaq 100 ETF",
        "name_zh": "纳斯达克100 ETF",
        "description": "Tracks the 100 largest Nasdaq-listed non-financial companies. AI-heavy (Mag7 dominant). Watch QQQ vs SMH divergence to gauge whether AI beneficiary rotation is underway.",
        "source_type": "yfinance",
        "ticker": "QQQ",
        "unit": "$",
    },
    "smh": {
        "name": "Semiconductor ETF",
        "name_zh": "半导体ETF",
        "description": "VanEck Semiconductor ETF. The AI picks-and-shovels trade (Nvidia, TSMC, ASML). If SMH underperforms QQQ, leadership is rotating from builders to enablers/adopters.",
        "source_type": "yfinance",
        "ticker": "SMH",
        "unit": "$",
    },
    "xlu": {
        "name": "Utilities ETF (XLU)",
        "name_zh": "公用事业ETF",
        "description": "The 'boring' AI winner. Data centers need massive electricity — utilities are the enablers. XLU outperforming tech = market rotating into AI infrastructure over AI hype.",
        "source_type": "yfinance",
        "ticker": "XLU",
        "unit": "$",
    },
    "gsci_spy_ratio": {
        "name": "Commodities / S&P 500",
        "name_zh": "大宗商品/标普500比率",
        "description": "GSG/SPY ratio — the broadest measure of real vs financial asset performance. A sustained move above 1.0 confirms the regime change from financial assets to hard assets. Currently turning from decades-long lows.",
        "source_type": "computed",
        "components": ["GSG", "SPY"],
        "unit": "ratio",
    },

    # ── Sentiment & Alternatives ──
    "vix": {
        "name": "VIX",
        "name_zh": "恐慌指数",
        "description": "The 'fear gauge'. Measures S&P 500 implied volatility. Below 15 = complacency, above 25 = elevated fear, above 35 = panic. Spikes tend to be short-lived but signal regime shifts.",
        "source_type": "yfinance",
        "ticker": "^VIX",
        "unit": "index",
    },
    "btc": {
        "name": "Bitcoin",
        "name_zh": "比特币",
        "description": "Digital debasement hedge. Correlates with global liquidity — when central banks expand balance sheets, BTC tends to rise. Also a barometer of risk appetite and monetary system distrust.",
        "source_type": "yfinance",
        "ticker": "BTC-USD",
        "unit": "$",
    },
    "cb_gold_buying": {
        "name": "Central Bank Gold Buying",
        "name_zh": "央行购金量",
        "description": "Quarterly data from World Gold Council. Central banks have been net buyers since 2010, accelerating post-2022 (sanctions on Russia). This is the structural floor under gold — sovereign entities voting to de-dollarize.",
        "source_type": "manual",
        "frequency": "quarterly",
        "unit": "tonnes/yr",
        "note": "Quarterly, lagged — World Gold Council",
    },

    # ── EM & China ──
    "csi300": {
        "name": "CSI 300",
        "name_zh": "沪深300",
        "description": "China's benchmark equity index (top 300 A-shares). The cleanest signal of whether domestic and foreign capital is returning to Chinese markets.",
        "source_type": "yfinance",
        "ticker": "000300.SS",
        "unit": "index",
    },
    "hsi": {
        "name": "Hang Seng Index",
        "name_zh": "恒生指数",
        "description": "Hong Kong's benchmark — the offshore window into Chinese equities. More sensitive to global capital flows and foreign sentiment toward China than onshore CSI 300.",
        "source_type": "yfinance",
        "ticker": "^HSI",
        "unit": "index",
    },
    "kweb": {
        "name": "China Internet ETF",
        "name_zh": "中概互联网ETF",
        "description": "KraneShares CSI China Internet ETF. Tracks Chinese tech (Alibaba, Tencent, PDD, etc.). A proxy for foreign investor sentiment on Chinese tech and regulatory risk.",
        "source_type": "yfinance",
        "ticker": "KWEB",
        "unit": "$",
    },
    "china_pmi": {
        "name": "China Mfg PMI",
        "name_zh": "中国制造业PMI",
        "description": "NBS Manufacturing PMI. 50 = expansion/contraction line. Sustained above 51 confirms recovery is real; below 49 signals contraction.",
        "source_type": "manual",
        "frequency": "monthly",
        "unit": "index",
        "note": "NBS monthly",
    },
    "china_retail_sales": {
        "name": "China Retail Sales YoY",
        "name_zh": "中国社零同比",
        "description": "Monthly year-over-year growth in Chinese retail sales (NBS). The key gauge for whether China's consumption pivot thesis is playing out. Needs to sustain 4%+ and ideally move toward 5-6%.",
        "source_type": "manual",
        "frequency": "monthly",
        "unit": "% YoY",
        "note": "NBS monthly",
    },
    "eem": {
        "name": "MSCI Emerging Markets ETF",
        "name_zh": "新兴市场ETF",
        "description": "Broad EM equity benchmark. Tracks whether capital is flowing into or out of developing markets. EM outperforming DM = dollar-weakness + fragmentation trade working.",
        "source_type": "yfinance",
        "ticker": "EEM",
        "unit": "$",
    },

    # ── Volatility & Macro Signals ──
    "move": {
        "name": "MOVE Index",
        "name_zh": "国债波动率指数",
        "description": "ICE BofA MOVE Index — measures Treasury market implied volatility across 2Y, 5Y, 10Y, and 30Y maturities. The bond market's version of VIX. Above 120 = elevated stress, above 150 = potential basis trade unwinds and forced Fed intervention. 🔗 Weak Dollar thesis: MOVE spikes force the Fed to step in as buyer of last resort, expanding the balance sheet.",
        "source_type": "manual",
        "frequency": "daily",
        "unit": "index",
        "note": "ICE BofA — backfill required",
    },
    "us_ism_pmi": {
        "name": "US Manufacturing PMI",
        "name_zh": "美国制造业PMI（ISM）",
        "description": "ISM Manufacturing PMI — the oldest and most-watched US manufacturing indicator. Above 50 = expansion, below 50 = contraction. January 2026 reading of 52.6 triggered a 'manufacturing recovery signal' — historical median 12-month returns after this signal: COPX +82%, DBC +44%. 🔗 Fragmentation thesis: onshoring and supply chain diversification drive US manufacturing recovery.",
        "source_type": "fred",
        "series": "NAPM",
        "unit": "index",
        "note": "Monthly — ISM via FRED",
    },

    # ── AI & Rotation ──
    "bigtech_capex": {
        "name": "Big Tech CapEx",
        "name_zh": "大型科技公司资本开支",
        "description": "Combined capital expenditures of MSFT, GOOGL, AMZN, META, and ORCL. Grew from $239B (2024) to $390B (2025) to $674B estimate (2026), ~2.2% of US GDP. The single most important metric for the AI thesis: follow the capex, not the capex spenders. 🔗 AI thesis: rising capex = infrastructure buildout accelerating.",
        "source_type": "manual",
        "frequency": "quarterly",
        "unit": "$B",
        "note": "Quarterly, compiled from earnings — MSFT+GOOGL+AMZN+META+ORCL",
    },
    "iwf_iwd": {
        "name": "Growth / Value",
        "name_zh": "成长/价值比率",
        "description": "Ratio of iShares Russell 1000 Growth (IWF) to Russell 1000 Value (IWD). Rising = growth outperforming, falling = value outperforming. A clean measure of the market's preference between tech/financial assets and real-economy/physical assets. Also a ~80% proxy for 'Atoms vs Bits.' 🔗 Hard Assets thesis: expect this ratio to decline as regime shifts from growth to value.",
        "source_type": "computed",
        "components": ["IWF", "IWD"],
        "unit": "ratio",
    },
}


# ─── Data fetching ───────────────────────────────────────────────────────────

def fetch_yfinance(ticker: str, start: str, end: str) -> list[tuple[str, float]]:
    """Fetch daily close from yfinance. Returns list of (date_str, value)."""
    try:
        t = yf.Ticker(ticker)
        df = t.history(start=start, end=end, auto_adjust=True)
        if df.empty:
            print(f"  ⚠ yfinance: no data for {ticker}")
            return []
        result = []
        for idx, row in df.iterrows():
            date_str = idx.strftime("%Y-%m-%d")
            val = round(float(row["Close"]), 4)
            result.append((date_str, val))
        return result
    except Exception as e:
        print(f"  ✗ yfinance error for {ticker}: {e}")
        return []


def fetch_fred(series_id: str, start: str, end: str, fred: Fred) -> list[tuple[str, float]]:
    """Fetch series from FRED. Returns list of (date_str, value)."""
    try:
        s = fred.get_series(series_id, observation_start=start, observation_end=end)
        s = s.dropna()
        if s.empty:
            print(f"  ⚠ FRED: no data for {series_id}")
            return []
        result = []
        for idx, val in s.items():
            date_str = idx.strftime("%Y-%m-%d")
            result.append((date_str, round(float(val), 4)))
        return result
    except Exception as e:
        print(f"  ✗ FRED error for {series_id}: {e}")
        return []


def compute_ratio(ticker_a: str, ticker_b: str, start: str, end: str) -> list[tuple[str, float]]:
    """Compute ratio of two yfinance tickers (A/B). Returns weekly samples."""
    try:
        a = yf.Ticker(ticker_a).history(start=start, end=end, auto_adjust=True)
        b = yf.Ticker(ticker_b).history(start=start, end=end, auto_adjust=True)
        if a.empty or b.empty:
            print(f"  ⚠ computed ratio: missing data for {ticker_a}/{ticker_b}")
            return []
        # Align on common dates
        a = a["Close"]
        b = b["Close"]
        common = a.index.intersection(b.index)
        ratio = (a[common] / b[common]).dropna()
        result = []
        for idx, val in ratio.items():
            result.append((idx.strftime("%Y-%m-%d"), round(float(val), 4)))
        return result
    except Exception as e:
        print(f"  ✗ computed ratio error: {e}")
        return []


def downsample_weekly(data: list[tuple[str, float]]) -> list[tuple[str, float]]:
    """Downsample daily data to weekly (keep last trading day of each week)."""
    if len(data) <= 260:
        return data
    weekly = {}
    for date_str, val in data:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        # ISO week key
        week_key = dt.isocalendar()[:2]
        weekly[week_key] = (date_str, val)  # last entry per week wins
    return sorted(weekly.values(), key=lambda x: x[0])


def compute_ytd_change(data: list[tuple[str, float]], mode: str = "pct") -> dict:
    """Compute YTD change from history data."""
    if not data:
        return {}

    year = datetime.now().year
    year_start = f"{year}-01-01"

    # Find first data point of current year (or closest after Jan 1)
    start_val = None
    for date_str, val in data:
        if date_str >= year_start:
            start_val = val
            break

    if start_val is None or start_val == 0:
        return {}

    end_val = data[-1][1]

    if mode == "bp":
        bp = round((end_val - start_val) * 100)
        return {"change_ytd_bp": bp}
    else:
        pct = round((end_val - start_val) / abs(start_val) * 100, 1)
        return {"change_ytd_pct": pct}


def apply_transform(data: list[tuple[str, float]], config: dict) -> list[tuple[str, float]]:
    """Apply value transforms (e.g., millions → trillions)."""
    transform = config.get("transform")
    if transform and callable(transform):
        return [(d, transform(v)) for d, v in data]
    return data


def compute_yoy(data: list[tuple[str, float]]) -> list[tuple[str, float]]:
    """Compute YoY percent change for monthly data."""
    if len(data) < 13:
        return data
    # Assumes monthly data sorted by date
    result = []
    for i in range(12, len(data)):
        date_str = data[i][0]
        curr = data[i][1]
        prev = data[i - 12][1]
        if prev != 0:
            yoy = round((curr - prev) / abs(prev) * 100, 1)
            result.append((date_str, yoy))
    return result


# ─── Main pipeline ───────────────────────────────────────────────────────────

def main():
    if not FRED_API_KEY:
        print("✗ FRED_API_KEY not set. Export it: export FRED_API_KEY=your_key")
        sys.exit(1)

    fred = Fred(api_key=FRED_API_KEY)
    now = datetime.now()
    end_date = now.strftime("%Y-%m-%d")
    start_date = (now - timedelta(days=LOOKBACK_YEARS * 365 + 30)).strftime("%Y-%m-%d")

    print(f"Fetching data: {start_date} → {end_date}")
    print(f"Output: {OUTPUT_PATH}\n")

    # Load existing file to preserve manual metrics
    existing = {}
    if OUTPUT_PATH.exists():
        with open(OUTPUT_PATH) as f:
            existing = json.load(f).get("metrics", {})

    result_metrics = {}
    errors = []

    for metric_id, config in METRICS.items():
        source = config["source_type"]
        print(f"  [{metric_id}] ({source}) ...", end=" ", flush=True)

        history = []

        if source == "yfinance":
            history = fetch_yfinance(config["ticker"], start_date, end_date)

        elif source == "fred":
            history = fetch_fred(config["series"], start_date, end_date, fred)
            if config.get("transform_yoy"):
                history = compute_yoy(history)

        elif source == "computed":
            components = config["components"]
            history = compute_ratio(components[0], components[1], start_date, end_date)

        elif source == "manual":
            # Keep existing data for manual metrics
            if metric_id in existing:
                print("manual (kept)")
                result_metrics[metric_id] = existing[metric_id]
                continue
            else:
                print("manual (no existing data)")
                result_metrics[metric_id] = {
                    "name": config["name"],
                    "name_zh": config.get("name_zh", ""),
                    "description": config["description"],
                    "value": None,
                    "direction": "flat",
                    "unit": config["unit"],
                    "history": [],
                    "source": f"manual",
                    "note": config.get("note", ""),
                }
                continue

        # Apply transforms
        history = apply_transform(history, config)

        if not history:
            errors.append(metric_id)
            print("✗ no data")
            # Fall back to existing
            if metric_id in existing:
                result_metrics[metric_id] = existing[metric_id]
            continue

        # Downsample to weekly for storage efficiency
        history_weekly = downsample_weekly(history)

        # Current value
        current_value = history[-1][1]

        # Direction
        if len(history) >= 2:
            direction = "up" if history[-1][1] >= history[-2][1] else "down"
        else:
            direction = "flat"

        # YTD change
        change_mode = config.get("change_mode", "pct")
        ytd = compute_ytd_change(history, change_mode)

        # Build metric object
        m = {
            "name": config["name"],
            "name_zh": config.get("name_zh", ""),
            "description": config["description"],
            "value": current_value,
            "direction": direction,
            "unit": config["unit"],
            "history": history_weekly,  # [[date, value], ...]
            "source": f"{source}:{config.get('ticker') or config.get('series') or config.get('components', [''])[0]}",
        }
        m.update(ytd)

        if "note" in config:
            m["note"] = config["note"]

        result_metrics[metric_id] = m
        count = len(history_weekly)
        print(f"✓ {count} points, value={current_value}")

    # Build output
    output = {
        "updated": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "metrics": result_metrics,
    }

    # Write
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\n✓ Wrote {len(result_metrics)} metrics to {OUTPUT_PATH}")
    if errors:
        print(f"⚠ Failed metrics: {', '.join(errors)}")
    print(f"  File size: {OUTPUT_PATH.stat().st_size / 1024:.0f} KB")


def backfill_from_csv(metric_id: str, csv_path: str) -> None:
    """Backfill historical data for a manual metric from a CSV file.

    CSV format: date,value (one row per data point)
    Example:
        date,value
        2021-01-31,51.3
        2021-02-28,50.6
    """
    manual_ids = [k for k, v in METRICS.items() if v["source_type"] == "manual"]

    if metric_id not in METRICS:
        print(f"✗ Unknown metric: {metric_id}")
        print(f"  Available manual metrics: {', '.join(manual_ids)}")
        sys.exit(1)

    if METRICS[metric_id]["source_type"] != "manual":
        print(f"✗ '{metric_id}' is not a manual metric (it's {METRICS[metric_id]['source_type']}-sourced).")
        sys.exit(1)

    csv_file = Path(csv_path)
    if not csv_file.exists():
        print(f"✗ File not found: {csv_path}")
        sys.exit(1)

    config = METRICS[metric_id]

    # Read CSV
    rows = []
    with open(csv_file, newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames or "date" not in reader.fieldnames or "value" not in reader.fieldnames:
            print(f"✗ CSV must have 'date' and 'value' columns.")
            print(f"  Got columns: {reader.fieldnames}")
            sys.exit(1)
        for row in reader:
            date_str = (row.get("date") or "").strip()
            val_str = (row.get("value") or "").strip()
            if not date_str or not val_str or date_str.startswith("#"):
                continue
            try:
                # Validate date format
                datetime.strptime(date_str, "%Y-%m-%d")
                value = float(val_str)
                rows.append([date_str, value])
            except ValueError as e:
                print(f"  ⚠ Skipping invalid row: date={date_str}, value={val_str} ({e})")

    if not rows:
        print(f"✗ No valid data rows found in {csv_path}")
        sys.exit(1)

    # Sort by date
    rows.sort(key=lambda x: x[0])

    # Load existing
    if OUTPUT_PATH.exists():
        with open(OUTPUT_PATH) as f:
            data = json.load(f)
    else:
        data = {"updated": "", "metrics": {}}

    existing = data["metrics"].get(metric_id, {})
    history = existing.get("history", [])

    # Merge: build a dict for dedup, CSV values take precedence
    date_map = {h[0]: h[1] for h in history}
    new_count = 0
    replaced_count = 0
    for date_str, value in rows:
        if date_str in date_map:
            replaced_count += 1
        else:
            new_count += 1
        date_map[date_str] = value

    # Rebuild sorted history
    history = sorted([[d, v] for d, v in date_map.items()], key=lambda x: x[0])

    # Current value = latest
    current_value = history[-1][1]

    # Direction from last two points
    direction = "flat"
    if len(history) >= 2:
        prev, curr = history[-2][1], history[-1][1]
        if curr > prev:
            direction = "up"
        elif curr < prev:
            direction = "down"

    data["metrics"][metric_id] = {
        "name": config["name"],
        "name_zh": config.get("name_zh", ""),
        "description": config["description"],
        "value": current_value,
        "direction": direction,
        "unit": config["unit"],
        "history": history,
        "source": "manual",
        "note": config.get("note", ""),
    }
    data["updated"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")

    with open(OUTPUT_PATH, "w") as f:
        json.dump(data, f, indent=2)

    print(f"✓ Backfilled {metric_id} from {csv_path}")
    print(f"  {new_count} new points, {replaced_count} replaced, {len(history)} total")
    print(f"  Range: {history[0][0]} → {history[-1][0]}")
    print(f"  Latest: {current_value} {config['unit']} ({direction})")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pulse data pipeline")
    sub = parser.add_subparsers(dest="command")

    # Default fetch (no subcommand)
    sub.add_parser("fetch", help="Fetch all API-sourced metrics (default)")

    # Backfill from CSV
    bf = sub.add_parser("backfill", help="Load manual metric data from CSV")
    bf.add_argument("metric_id", help="Metric key (e.g. china_pmi)")
    bf.add_argument("csv_path", nargs="?", help="Path to CSV file (default: data/backfill/<metric_id>.csv)")

    args = parser.parse_args()

    if args.command == "backfill":
        csv_path = args.csv_path or f"data/backfill/{args.metric_id}.csv"
        backfill_from_csv(args.metric_id, csv_path)
    else:
        # Default: fetch
        main()
