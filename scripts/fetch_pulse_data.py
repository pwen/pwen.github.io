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
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "assets" / "data" / "pulse"
OUTPUT_PATH = OUTPUT_DIR / "metrics.json"  # lightweight index (metadata only, no history)
LOOKBACK_YEARS = 5

# Category → metric IDs  (mirrors charts.js CATEGORIES)
CATEGORY_MAP = [
    ("currencies", ["dxy", "eurusd", "usdcny", "usd_reserves_share"]),
    ("rates", ["us_10y", "cn_10y", "cn_us_spread", "yield_curve", "tips_5y", "breakeven_10y", "hy_spread", "move"]),
    ("liquidity", ["fed_balance_sheet", "debt_to_gdp", "tga"]),
    ("china", ["csi300", "hsi", "kweb", "china_pmi", "china_retail_sales", "china_cpi", "china_gdp", "china_m2"]),
    ("metals", ["gold", "silver", "copper", "uranium"]),
    ("energy", ["oil", "natgas", "energy_cpi"]),
    ("equities", ["sp500", "qqq", "smh", "xlu", "gsci_spy_ratio", "bigtech_capex", "growth_value", "cap_equal", "atoms_bits"]),
    ("sentiment", ["vix", "btc", "cb_gold_buying", "us_ism_pmi", "us_gdp", "us_cpi", "umich_sentiment"]),
    ("row", ["eem", "inda", "ilf"]),
]

# ─── Metric definitions ─────────────────────────────────────────────────────

# Each metric: key → config dict
# source_type: "yfinance", "fred", "derived", "manual"
METRICS = {
    # ── Currencies ──
    "dxy": {
        "name": "US Dollar Index (DXY)",
        "name_zh": "美元指数",
        "description": "Dollar vs a basket of major fiat currencies (euro-heavy). Rising = dollar strengthening, falling = dollar weakening. A relative measure: if all currencies debase together, DXY stays flat.",
        "source_type": "yfinance",
        "ticker": "DX-Y.NYB",
        "unit": "index",
    },
    "eurusd": {
        "name": "EUR/USD",
        "name_zh": "欧元/美元",
        "description": "Euro vs dollar. DXY's largest component (~58%). Rising = dollar weakening, falling = dollar strengthening.",
        "source_type": "yfinance",
        "ticker": "EURUSD=X",
        "unit": "rate",
    },
    "usdcny": {
        "name": "USD/CNY",
        "name_zh": "美元/人民币",
        "description": "Dollar-yuan exchange rate. Rising = yuan weakening, falling = yuan strengthening. Below 7.00 signals meaningful capital flow shift toward China.",
        "source_type": "yfinance",
        "ticker": "CNY=X",
        "unit": "rate",
    },
    "usd_reserves_share": {
        "name": "USD Share of FX Reserves",
        "name_zh": "美元外汇储备占比",
        "description": "USD share of global foreign-exchange reserves held by central banks (IMF COFER, quarterly, ~1 Q lag). Falling = structural de-dollarization. Down from 72 % in 2000 to ~57 %: slow-moving but largely irreversible.",
        "source_type": "manual",
        "frequency": "quarterly",
        "unit": "%",
        "note": "Quarterly, lagged — IMF COFER",
    },

    # ── Rates & Yields ──
    "us_10y": {
        "name": "US 10Y Yield",
        "name_zh": "美国十年期国债收益率",
        "description": "Benchmark Treasury yield. Rising = market demanding more compensation to hold US debt. Above 5% is a yellow flag, above 6% likely forces Fed intervention.",
        "source_type": "yfinance",
        "ticker": "^TNX",
        "unit": "%",
        "change_mode": "bp",
    },
    "yield_curve": {
        "name": "10Y-2Y Spread",
        "name_zh": "收益率曲线（10Y-2Y利差）",
        "description": "10Y minus 2Y Treasury yield: measures yield curve steepness. Positive and rising = curve steepening (long-end yields rising faster, often signaling inflation expectations or fiscal stress). Inverted (negative) = market pricing rate cuts. Re-steepening after inversion historically precedes recessions within 6-18 months.",
        "source_type": "fred",
        "series": "T10Y2Y",
        "unit": "% spread",
        "change_mode": "bp",
    },
    "tips_5y": {
        "name": "US 5Y TIPS (Real Yield)",
        "name_zh": "五年期实际利率（TIPS）",
        "description": "Real cost of money after inflation. Rising = tighter real conditions, falling = looser. Negative real yields push capital toward gold and hard assets.",
        "source_type": "fred",
        "series": "DFII5",
        "unit": "%",
        "change_mode": "bp",
    },
    "breakeven_10y": {
        "name": "10Y Breakeven Inflation",
        "name_zh": "十年期盈亏平衡通胀率",
        "description": "Market-implied inflation expectation for the next 10 years. Rising = market pricing higher inflation, falling = disinflation expectations.",
        "source_type": "fred",
        "series": "T10YIE",
        "unit": "%",
        "change_mode": "bp",
    },
    "cn_10y": {
        "name": "China 10Y Yield",
        "name_zh": "中国10年期国债收益率",
        "description": "China 10-year government bond yield. Falling = PBOC easing, deflation risk. Rising = growth expectations improving. The US-China spread drives capital flows.",
        "source_type": "manual",
        "frequency": "monthly",
        "unit": "%",
        "change_mode": "bp",
        "note": "Monthly — PBOC / CEIC (no free API)",
    },
    "cn_us_spread": {
        "name": "China–US 10Y Spread",
        "name_zh": "中美10年期利差",
        "description": "China 10Y minus US 10Y yield (in bp). Currently deeply negative: US must offer far higher yields to fund its debt. Becoming more negative = US fiscal pressure worsening, dollar weakness signal. Narrowing (less negative) = pressure easing. Also a CNY stability indicator: wide gap = capital outflow pressure on yuan.",
        "source_type": "derived",
        "derive_from": ["cn_10y", "us_10y"],
        "derive_op": "subtract_bp",
        "unit": "bp",
        "change_mode": "bp",
        "note": "Derived: (cn_10y − us_10y) × 100",
    },
    "hy_spread": {
        "name": "HY Credit Spread (OAS)",
        "name_zh": "高收益债利差",
        "description": "High-yield bond spread over Treasuries. Widening = credit stress / risk-off. Tight = complacency. Above 5% historically signals recession risk.",
        "source_type": "fred",
        "series": "BAMLH0A0HYM2",
        "unit": "%",
        "change_mode": "bp",
    },

    # ── Liquidity & Fiscal ──
    "fed_balance_sheet": {
        "name": "Fed Balance Sheet",
        "name_zh": "美联储资产负债表",
        "description": "Total assets held by the Federal Reserve. Rising = QE / liquidity injection, falling = QT / tightening. Treasury market stress forces re-expansion.",
        "source_type": "fred",
        "series": "WALCL",
        "unit": "$T",
        "transform": lambda v: round(v / 1_000_000, 2),  # millions → trillions
    },
    "debt_to_gdp": {
        "name": "US Debt/GDP",
        "name_zh": "美国债务/GDP",
        "description": "Federal debt as a share of GDP. Rising = fiscal trajectory worsening. If GDP grows faster than debt, the ratio stabilizes; otherwise compounding takes over.",
        "source_type": "fred",
        "series": "GFDEGDQ188S",
        "unit": "%",
        "note": "Quarterly, interpolated",
    },
    "tga": {
        "name": "Treasury General Account",
        "name_zh": "财政部一般账户（TGA）",
        "description": "US government's checking account at the Fed. Drawdowns inject liquidity into markets (bullish for risk assets). Refills drain liquidity.",
        "source_type": "fred",
        "series": "WTREGEN",
        "unit": "$B",
        "transform": lambda v: round(v / 1_000, 1),  # millions → billions
    },

    # ── Metals ──
    "gold": {
        "name": "Gold",
        "name_zh": "黄金",
        "description": "Spot gold price. Rising = inflation hedge demand / loss of confidence in fiat. Central banks buying gold = voting to diversify away from dollars.",
        "source_type": "yfinance",
        "ticker": "GC=F",
        "unit": "$/oz",
    },
    "silver": {
        "name": "Silver",
        "name_zh": "白银",
        "description": "Both monetary and industrial metal (solar, electronics). Market in structural deficit. Outperforms gold in bull runs, more volatile.",
        "source_type": "yfinance",
        "ticker": "SI=F",
        "unit": "$/oz",
    },
    "copper": {
        "name": "Copper",
        "name_zh": "铜",
        "description": "Electrification bellwether: EVs, data centers, wind turbines, grid upgrades. Supply structurally constrained (mines take 7-15 years). Rising = industrial and green demand outpacing supply.",
        "source_type": "yfinance",
        "ticker": "HG=F",
        "unit": "$/lb",
    },
    "uranium": {
        "name": "Uranium (URA ETF)",
        "name_zh": "铀",
        "description": "Global X Uranium ETF. Proxy for nuclear renaissance: 30+ countries committed to tripling capacity. Supply constrained, Russia controls 40% of enrichment.",
        "source_type": "yfinance",
        "ticker": "URA",
        "unit": "$",
    },

    # ── Energy ──
    "oil": {
        "name": "WTI Crude",
        "name_zh": "原油",
        "description": "WTI crude futures. Rising = supply tightening or demand growth. Politically suppressed via Saudi deals and SPR releases, but geological supply constraints persist.",
        "source_type": "yfinance",
        "ticker": "CL=F",
        "unit": "$/bbl",
    },
    "natgas": {
        "name": "Natural Gas",
        "name_zh": "天然气",
        "description": "Henry Hub natural gas futures. Rising = tightening supply or seasonal/structural demand. AI data centers driving new electricity demand. Also a geopolitical commodity (Russia/Europe, LNG).",
        "source_type": "yfinance",
        "ticker": "NG=F",
        "unit": "$/MMBtu",
    },
    "energy_cpi": {
        "name": "Energy Services CPI YoY",
        "name_zh": "能源服务CPI（同比）",
        "description": "Year-over-year change in energy services prices (BLS). Rising = energy inflation accelerating. Directly tied to AI data center power demand. Above 7% creates political backlash.",
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
        "description": "Broad US equity benchmark. Rising = risk-on, falling = risk-off. Compare with QQQ/SMH to gauge whether tech is leading or lagging.",
        "source_type": "yfinance",
        "ticker": "^GSPC",
        "unit": "index",
    },
    "qqq": {
        "name": "Nasdaq 100 ETF (QQQ)",
        "name_zh": "纳斯达克100",
        "description": "100 largest Nasdaq non-financial companies. AI/tech-heavy (Mag7 dominant). QQQ vs SMH divergence signals whether AI leadership is rotating.",
        "source_type": "yfinance",
        "ticker": "QQQ",
        "unit": "$",
    },
    "smh": {
        "name": "Semiconductor ETF (SMH)",
        "name_zh": "半导体",
        "description": "VanEck Semiconductor ETF: Nvidia, TSMC, ASML. The AI picks-and-shovels trade. SMH underperforming QQQ = leadership rotating from chip builders to enablers/adopters.",
        "source_type": "yfinance",
        "ticker": "SMH",
        "unit": "$",
    },
    "xlu": {
        "name": "Utilities ETF (XLU)",
        "name_zh": "公用事业",
        "description": "Utilities sector ETF. Data centers need massive electricity: XLU outperforming tech = market rotating into AI infrastructure over AI hype.",
        "source_type": "yfinance",
        "ticker": "XLU",
        "unit": "$",
    },
    "gsci_spy_ratio": {
        "name": "Commodities / S&P 500",
        "name_zh": "大宗商品/标普500比率",
        "description": "GSG/SPY ratio: real assets vs financial assets. Rising = commodities outperforming equities. Turning up from decades-long lows.",
        "source_type": "derived",
        "components": ["GSG", "SPY"],
        "unit": "ratio",
    },

    # ── Sentiment & Alternatives ──
    "vix": {
        "name": "VIX",
        "name_zh": "恐慌指数",
        "description": "S&P 500 implied volatility. Below 15 = complacency, above 25 = fear, above 35 = panic. Spikes tend to be short-lived but can signal regime shifts.",
        "source_type": "yfinance",
        "ticker": "^VIX",
        "unit": "index",
    },
    "btc": {
        "name": "Bitcoin",
        "name_zh": "比特币",
        "description": "Digital debasement hedge. Correlates with global liquidity: central bank balance sheet expansion = BTC tailwind. Also a barometer of risk appetite.",
        "source_type": "yfinance",
        "ticker": "BTC-USD",
        "unit": "$",
    },
    "cb_gold_buying": {
        "name": "Central Bank Gold Buying",
        "name_zh": "央行购金量",
        "description": "Quarterly net purchases by central banks (World Gold Council). Net buyers since 2010, accelerating post-2022. Rising = structural de-dollarization demand.",
        "source_type": "manual",
        "frequency": "quarterly",
        "unit": "tonnes/yr",
        "note": "Quarterly, lagged — World Gold Council",
    },

    # ── EM & China ──
    "csi300": {
        "name": "CSI 300",
        "name_zh": "沪深300",
        "description": "China's benchmark equity index (top 300 A-shares). Rising = domestic and foreign capital returning to Chinese markets.",
        "source_type": "yfinance",
        "ticker": "000300.SS",
        "unit": "index",
    },
    "hsi": {
        "name": "Hang Seng Index",
        "name_zh": "恒生指数",
        "description": "Hong Kong's benchmark: the offshore window into Chinese equities. More sensitive to global capital flows and foreign sentiment than onshore CSI 300.",
        "source_type": "yfinance",
        "ticker": "^HSI",
        "unit": "index",
    },
    "kweb": {
        "name": "China Internet ETF (KWEB)",
        "name_zh": "中概互联网ETF",
        "description": "KraneShares China Internet ETF: Alibaba, Tencent, PDD, etc. Rising = foreign confidence in Chinese tech improving.",
        "source_type": "yfinance",
        "ticker": "KWEB",
        "unit": "$",
    },
    "china_pmi": {
        "name": "China Mfg PMI",
        "name_zh": "中国制造业PMI",
        "description": "NBS Manufacturing PMI. Above 50 = expansion, below 50 = contraction. Sustained above 51 confirms recovery; below 49 signals deepening weakness.",
        "source_type": "manual",
        "frequency": "monthly",
        "unit": "index",
        "note": "NBS monthly",
    },
    "china_retail_sales": {
        "name": "China Retail Sales YoY",
        "name_zh": "中国社零同比",
        "description": "Monthly YoY growth in Chinese retail sales (NBS). Rising = consumer recovery gaining traction. Needs to sustain 4%+ to confirm consumption pivot.",
        "source_type": "manual",
        "frequency": "monthly",
        "unit": "% YoY",
        "note": "NBS monthly",
    },
    "eem": {
        "name": "MSCI Emerging Markets ETF (EEM)",
        "name_zh": "新兴市场ETF",
        "description": "Broad EM equity benchmark. Rising = capital flowing into developing markets. EM outperforming DM = dollar weakness + fragmentation trade working.",
        "source_type": "yfinance",
        "ticker": "EEM",
        "unit": "$",
    },
    "inda": {
        "name": "India ETF (INDA)",
        "name_zh": "印度ETF",
        "description": "iShares MSCI India ETF. Tracks large and mid-cap Indian equities. India is the fastest-growing major economy with strong demographics and manufacturing push (Make in India).",
        "source_type": "yfinance",
        "ticker": "INDA",
        "unit": "$",
    },
    "ilf": {
        "name": "Latin America ETF (ILF)",
        "name_zh": "拉美ETF",
        "description": "iShares Latin America 40 ETF. Tracks Brazil, Mexico, Chile, Colombia. Commodity-rich region benefiting from nearshoring (Mexico) and resource nationalism.",
        "source_type": "yfinance",
        "ticker": "ILF",
        "unit": "$",
    },
    "china_cpi": {
        "name": "China CPI YoY",
        "name_zh": "中国CPI（同比）",
        "description": "Year-over-year change in China consumer prices. Negative = deflation risk, the #1 macro worry for China bulls. Sustained positive CPI needed to confirm reflation thesis.",
        "source_type": "manual",
        "frequency": "monthly",
        "unit": "% YoY",
        "note": "Monthly — NBS",
    },
    "china_gdp": {
        "name": "China GDP YoY",
        "name_zh": "中国GDP（同比）",
        "description": "China real GDP year-over-year growth rate. Headline execution metric for the 15-year plan. Target ~5%. Sustained above-target growth validates the re-rating thesis.",
        "source_type": "manual",
        "frequency": "quarterly",
        "unit": "% YoY",
        "note": "Quarterly — NBS",
    },
    "china_m2": {
        "name": "China M2 YoY",
        "name_zh": "中国M2（同比）",
        "description": "China broad money supply year-over-year growth. M2 > 10% = PBOC actively stimulating. Rising M2 is a leading indicator for credit impulse and asset reflation.",
        "source_type": "manual",
        "frequency": "monthly",
        "unit": "% YoY",
        "note": "Monthly — PBOC",
    },

    # ── Volatility & Macro Signals ──
    "move": {
        "name": "MOVE Index",
        "name_zh": "国债波动率指数",
        "description": "ICE BofA MOVE Index: Treasury market implied volatility across 2Y-30Y maturities. The bond market's VIX. Above 120 = elevated stress, above 150 = potential basis trade unwinds and forced Fed intervention.",
        "source_type": "manual",
        "frequency": "daily",
        "unit": "index",
        "note": "ICE BofA — backfill required",
    },
    "us_ism_pmi": {
        "name": "US Manufacturing PMI (ISM)",
        "name_zh": "美国制造业PMI",
        "description": "ISM Manufacturing PMI: the oldest US manufacturing indicator. Above 50 = expansion, below 50 = contraction. Sustained expansion signals onshoring and supply chain diversification.",
        "source_type": "manual",
        "frequency": "monthly",
        "unit": "index",
        "note": "Monthly — ISM (no free API, backfill from CSV)",
    },

    # ── US Macro ──
    "us_gdp": {
        "name": "US Real GDP Growth",
        "name_zh": "美国实际GDP增速",
        "description": "Real GDP growth rate (SAAR). The headline US growth number. Above 2% = solid, above 3% = strong, below 0% for 2 consecutive quarters = recession.",
        "source_type": "fred",
        "series": "A191RL1Q225SBEA",
        "unit": "% QoQ",
        "note": "Quarterly, annualized — BEA",
    },
    "us_cpi": {
        "name": "US CPI YoY",
        "name_zh": "美国CPI（同比）",
        "description": "Headline consumer price inflation, year-over-year. The Fed's dual mandate target is 2%. Above 3% = hawkish pressure, below 2% = rate cut runway. Drives gold, bonds, and dollar.",
        "source_type": "fred",
        "series": "CPIAUCSL",
        "unit": "% YoY",
        "transform_yoy": True,
        "note": "Monthly, lagged ~2 weeks — BLS",
    },
    "umich_sentiment": {
        "name": "UMich Consumer Sentiment",
        "name_zh": "密歇根消费者信心指数",
        "description": "University of Michigan consumer sentiment index. Below 60 = deep pessimism (recession risk), above 80 = confidence. A leading indicator: consumers cut spending before GDP falls.",
        "source_type": "fred",
        "series": "UMCSENT",
        "unit": "index",
        "note": "Monthly — UMich",
    },

    # ── AI & Rotation ──
    "bigtech_capex": {
        "name": "Big Tech CapEx",
        "name_zh": "大型科技公司资本开支",
        "description": "Combined capex of MSFT, GOOGL, AMZN, META, ORCL (quarterly). Rising = AI infrastructure buildout accelerating. Follow the capex, not the capex spenders.",
        "source_type": "manual",
        "frequency": "quarterly",
        "unit": "$B",
        "note": "Quarterly, compiled from earnings — MSFT+GOOGL+AMZN+META+ORCL",
    },
    "growth_value": {
        "name": "Growth / Value",
        "name_zh": "成长/价值比率",
        "description": "VUG/VTV ratio. Rising = growth stocks outperforming value, falling = value winning. A declining ratio signals rotation from tech/financial assets into real-economy sectors.",
        "source_type": "derived",
        "components": ["VUG", "VTV"],
        "unit": "ratio",
    },
    "cap_equal": {
        "name": "Cap-Weight / Equal-Weight",
        "name_zh": "市值加权/等权比率",
        "description": "SPY/RSP ratio. Rising = mega-cap concentration winning, falling = market breadth broadening. A declining ratio means the average stock is outperforming the index.",
        "source_type": "derived",
        "components": ["SPY", "RSP"],
        "unit": "ratio",
    },
    "atoms_bits": {
        "name": "Atoms vs Bits",
        "name_zh": "实物/数字比率",
        "description": "Physical-economy ETFs (XLB+XLI+XLE+XME) vs digital-economy ETFs (IGV+WCLD). Rising = hard assets outperforming software/cloud. A sustained rise signals regime change from bits to atoms.",
        "source_type": "derived",
        "basket_a": ["XLB", "XLI", "XLE", "XME"],
        "basket_b": ["IGV", "WCLD"],
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

def compute_basket_ratio(basket_a: list[str], basket_b: list[str], start: str, end: str) -> list[tuple[str, float]]:
    """Compute ratio of equal-weight basket A to equal-weight basket B.

    Each basket's daily value = equal-weight average of normalized prices
    (each ticker normalized to 1.0 on first common date).
    Result = basket_a_value / basket_b_value.
    """
    import pandas as pd
    try:
        all_tickers = basket_a + basket_b
        series = {}
        for ticker in all_tickers:
            df = yf.Ticker(ticker).history(start=start, end=end, auto_adjust=True)
            if df.empty:
                print(f"  \u26a0 basket: no data for {ticker}")
                return []
            series[ticker] = df["Close"]

        # Find common dates across ALL tickers
        common = series[all_tickers[0]].index
        for ticker in all_tickers[1:]:
            common = common.intersection(series[ticker].index)
        if len(common) == 0:
            print(f"  \u26a0 basket: no common dates")
            return []

        # Normalize each to 1.0 on first date, then equal-weight average per basket
        first_date = common[0]
        norm = {}
        for ticker in all_tickers:
            s = series[ticker][common]
            norm[ticker] = s / s.iloc[0]

        basket_a_val = sum(norm[t] for t in basket_a) / len(basket_a)
        basket_b_val = sum(norm[t] for t in basket_b) / len(basket_b)
        ratio = (basket_a_val / basket_b_val).dropna()

        result = []
        for idx, val in ratio.items():
            result.append((idx.strftime("%Y-%m-%d"), round(float(val), 4)))
        return result
    except Exception as e:
        print(f"  \u2717 basket ratio error: {e}")
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


def compute_zscore(history: list) -> dict:
    """Compute z-score and signal label from history data.

    Uses full history to compute mean/std, then z = (latest - mean) / std.
    Signal thresholds (matching sruth.app convention):
        |z| < 1.5  → NORMAL
        1.5 ≤ |z| < 2.5 → ELEVATED
        |z| ≥ 2.5  → EXTREME
    """
    if not history or len(history) < 4:
        return {}

    values = [h[1] if isinstance(h, list) else h for h in history]
    n = len(values)
    mean = sum(values) / n
    variance = sum((v - mean) ** 2 for v in values) / n
    std = variance ** 0.5

    if std == 0:
        return {"zscore": 0.0, "signal": "NORMAL"}

    z = round((values[-1] - mean) / std, 1)
    az = abs(z)

    if az >= 2.5:
        signal = "EXTREME"
    elif az >= 1.5:
        signal = "ELEVATED"
    else:
        signal = "NORMAL"

    return {"zscore": z, "signal": signal}


def compute_trend(history: list, lookback: int = 8) -> dict:
    """Compute trend direction over the last `lookback` data points.

    Compares latest value to the value `lookback` points ago.
    Returns 'up', 'down', or 'flat' (change < 0.5%).
    """
    if not history or len(history) < lookback + 1:
        return {}

    values = [h[1] if isinstance(h, list) else h for h in history]
    latest = values[-1]
    past = values[-(lookback + 1)]

    if past == 0:
        return {"trend": "flat"}

    pct_change = (latest - past) / abs(past) * 100

    if pct_change > 0.5:
        return {"trend": "up"}
    elif pct_change < -0.5:
        return {"trend": "down"}
    else:
        return {"trend": "flat"}


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

        elif source == "derived":
            # Check what kind of derived metric this is
            if "components" in config:
                components = config["components"]
                history = compute_ratio(components[0], components[1], start_date, end_date)
            elif "basket_a" in config:
                history = compute_basket_ratio(
                    config["basket_a"], config["basket_b"], start_date, end_date
                )
            elif "derive_from" in config:
                # Defer: computed in second pass after all other metrics are fetched
                print("deferred (derived)")
                continue

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
            "source": f"{source}:{config.get('ticker') or config.get('series') or config.get('components', [''])[0] or '+'.join(config.get('basket_a', ['']))}",
        }
        m.update(ytd)

        if "note" in config:
            m["note"] = config["note"]

        result_metrics[metric_id] = m
        count = len(history_weekly)
        print(f"✓ {count} points, value={current_value}")

    # ── Second pass: derived metrics that depend on other fetched metrics ──
    for metric_id, config in METRICS.items():
        if config["source_type"] != "derived" or "derive_from" not in config:
            continue
        print(f"  [{metric_id}] (derived) ...", end=" ", flush=True)

        sources = config["derive_from"]  # e.g. ["cn_10y", "us_10y"]
        op = config["derive_op"]         # e.g. "subtract_bp"

        # Collect history from already-fetched metrics
        src_histories = []
        ok = True
        for src_id in sources:
            src_m = result_metrics.get(src_id)
            if not src_m or not src_m.get("history"):
                print(f"✗ missing source metric {src_id}")
                errors.append(metric_id)
                ok = False
                break
            src_histories.append({h[0]: h[1] for h in src_m["history"]})
        if not ok:
            if metric_id in existing:
                result_metrics[metric_id] = existing[metric_id]
            continue

        # Align on dates: use the sparser series as the base, find closest dates in the denser one
        hist_a, hist_b = src_histories[0], src_histories[1]
        base, other = (hist_a, hist_b) if len(hist_a) <= len(hist_b) else (hist_b, hist_a)
        base_is_a = len(hist_a) <= len(hist_b)
        other_dates = sorted(other.keys())

        history = []
        for d in sorted(base.keys()):
            # Find closest date in the other series (within 7 days)
            d_dt = datetime.strptime(d, "%Y-%m-%d")
            closest = min(other_dates, key=lambda dd: abs((datetime.strptime(dd, "%Y-%m-%d") - d_dt).days))
            if abs((datetime.strptime(closest, "%Y-%m-%d") - d_dt).days) > 7:
                continue
            a_val = hist_a[d] if base_is_a else hist_a.get(closest, hist_a.get(d))
            b_val = hist_b.get(closest, hist_b.get(d)) if base_is_a else hist_b[d]
            if op == "subtract_bp":
                val = round((a_val - b_val) * 100, 1)
            elif op == "subtract":
                val = round(a_val - b_val, 4)
            else:
                val = round(a_val / b_val, 4) if b_val != 0 else 0
            history.append((d, val))

        if not history:
            print("✗ no data after derivation")
            errors.append(metric_id)
            if metric_id in existing:
                result_metrics[metric_id] = existing[metric_id]
            continue

        history_weekly = downsample_weekly(history)
        current_value = history[-1][1]
        direction = "up" if len(history) >= 2 and history[-1][1] >= history[-2][1] else "down" if len(history) >= 2 else "flat"
        change_mode = config.get("change_mode", "pct")
        ytd = compute_ytd_change(history, change_mode)

        m = {
            "name": config["name"],
            "name_zh": config.get("name_zh", ""),
            "description": config["description"],
            "value": current_value,
            "direction": direction,
            "unit": config["unit"],
            "history": history_weekly,
            "source": f"derived:{'+'.join(sources)}",
        }
        m.update(ytd)
        if "note" in config:
            m["note"] = config["note"]
        result_metrics[metric_id] = m
        print(f"✓ {len(history_weekly)} points, value={current_value}")

    # Compute z-scores and trends for all metrics
    for mid, mdata in result_metrics.items():
        hist = mdata.get("history", [])
        zinfo = compute_zscore(hist)
        if zinfo:
            mdata.update(zinfo)
        tinfo = compute_trend(hist)
        if tinfo:
            mdata.update(tinfo)

    # Write per-category files
    updated_str = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    total_written = 0
    for cat_id, metric_ids in CATEGORY_MAP:
        cat_metrics = {mid: result_metrics[mid] for mid in metric_ids if mid in result_metrics}
        cat_output = {"updated": updated_str, "metrics": cat_metrics}
        cat_path = OUTPUT_DIR / f"{cat_id}.json"
        with open(cat_path, "w") as f:
            json.dump(cat_output, f, indent=2)
        total_written += len(cat_metrics)
        print(f"  → {cat_path.name}: {len(cat_metrics)} metrics ({cat_path.stat().st_size / 1024:.0f} KB)")

    # Write lightweight metrics.json index (metadata only — no history arrays)
    slim_metrics = {}
    for mid, mdata in result_metrics.items():
        slim = {k: v for k, v in mdata.items() if k != "history"}
        slim_metrics[mid] = slim
    combined = {"updated": updated_str, "metrics": slim_metrics}
    with open(OUTPUT_PATH, "w") as f:
        json.dump(combined, f, indent=2)

    print(f"\n✓ Wrote {total_written} metrics across {len(CATEGORY_MAP)} category files")
    print(f"  metrics.json index: {OUTPUT_PATH.stat().st_size / 1024:.0f} KB (metadata only)")
    if errors:
        print(f"⚠ Failed metrics: {', '.join(errors)}")


def _category_for_metric(metric_id: str) -> str | None:
    """Return the category ID that contains the given metric, or None."""
    for cat_id, metric_ids in CATEGORY_MAP:
        if metric_id in metric_ids:
            return cat_id
    return None


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

    cat_id = _category_for_metric(metric_id)
    if not cat_id:
        print(f"✗ '{metric_id}' is not assigned to any category in CATEGORY_MAP")
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

    # Load existing data from the category file (not the combined metrics.json)
    cat_path = OUTPUT_DIR / f"{cat_id}.json"
    if cat_path.exists():
        with open(cat_path) as f:
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

    # Compute YTD change
    change_mode = config.get("change_mode", "pct")
    ytd = compute_ytd_change([(h[0], h[1]) for h in history], change_mode)

    metric_obj = {
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
    metric_obj.update(ytd)
    zinfo = compute_zscore(history)
    if zinfo:
        metric_obj.update(zinfo)
    tinfo = compute_trend(history)
    if tinfo:
        metric_obj.update(tinfo)

    updated_str = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
    data["metrics"][metric_id] = metric_obj
    data["updated"] = updated_str

    # Write back to category file
    with open(cat_path, "w") as f:
        json.dump(data, f, indent=2)

    # Update lightweight metrics.json index (metadata only — no history)
    if OUTPUT_PATH.exists():
        with open(OUTPUT_PATH) as f:
            index_data = json.load(f)
    else:
        index_data = {"updated": "", "metrics": {}}
    slim = {k: v for k, v in metric_obj.items() if k != "history"}
    index_data["metrics"][metric_id] = slim
    index_data["updated"] = updated_str
    with open(OUTPUT_PATH, "w") as f:
        json.dump(index_data, f, indent=2)

    print(f"✓ Backfilled {metric_id} → {cat_path.name}")
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
