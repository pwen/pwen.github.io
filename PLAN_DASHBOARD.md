# 看戏的地儿 (Pulse) — pwen.github.io/pulse

## Status

### ✅ Phase 1 DONE — Frontend + Content

**Frontend (Sruth-style redesign):**
- `pulse.html` — thesis tracker with chart modal overlay
- `pulse.css` — table-row layout, modal styles, responsive
- `pulse.js` — table rendering, click-to-chart modal (Chart.js), markdown-to-HTML converter
- `charts.html` — category-grouped metrics page (sruth.app/charts style)
- `charts.css` — collapsible category sections, inline chart expand styles
- `charts.js` — category rendering, click-to-expand inline Chart.js, accordion logic
- `theses-2026.json` — 5 theses with Chinese titles/summaries, colors, icons, metric mappings
- `metrics.json` — 33 metrics across 8 categories with sample data + descriptions (placeholder values, will be replaced by GitHub Action)
- Year selector for future year-over-year support
- Reflection section (currently `null`)

**Metrics (33 total, 8 categories):**
- 💵 Currencies (4): DXY, EUR/USD, USD/CNY, USD Share of Reserves
- 🏛️ Rates & Yields (5): US 10Y, 10Y-2Y Spread, 5Y TIPS, 10Y Breakeven, HY Credit Spread
- 🏦 Liquidity & Fiscal (3): Fed Balance Sheet, Debt/GDP, TGA
- ⛏️ Metals (4): Gold, Silver, Copper, Uranium
- ⛽ Energy (3): WTI Oil, Natural Gas, Energy CPI
- 📈 US Equities & Sectors (5): S&P 500, QQQ, SMH, XLU, GSCI/SPY Ratio
- 🌡️ Sentiment & Alternatives (3): VIX, Bitcoin, Central Bank Gold Buying
- 🌏 EM & China (6): CSI 300, Hang Seng, KWEB, China PMI, China Retail Sales, EEM

**Thesis write-ups (all Mandarin, 口语化又专业性):**
- ✅ `2026-dollar.md` — 美元结构性走弱 (债务螺旋, 美联储接盘, 美元信用)
- ✅ `2026-china.md` — 中国资产重估 (消费转型, 制度改革, A股长牛起点)
- ✅ `2026-fragmentation.md` — 旧秩序瓦解 (战国时代, 战略资源溢价, 结构性通胀)
- ✅ `2026-ai.md` — AI革命 (码农亲历, 张笑宇《技术与文明》, 受益者轮动, 中美AI路线分化)
- ✅ `2026-hard-assets.md` — 实物资产牛市 (四大驱动力: 投资不足/货币贬值/能源转型/地缘溢价)

**JSON titles & summaries (all Chinese):**
- 💵 美元正在结构性走弱
- 🇨🇳 中国资产正在被重估
- ⚔️ 旧秩序正在瓦解，地缘竞争加剧
- 🤖 AI正在改变一切，而我们还没有做好准备
- ⛏️ 实物资产正在进入结构性牛市

**Dashboard layout:** Sruth-style table rows (not cards). Metrics shown as rows with columns: name, value, change, direction dot. Click any row → Chart.js modal popup with historical chart. No inline sparklines.

**Next: Phase 2** — Build GitHub Action data pipeline to auto-update metrics.json daily.

## Concept

A thesis-driven dashboard. I define 5 convictions about where the world is
heading, then curate specific data/charts to track whether reality is
confirming or challenging each thesis. The AI summary is framed around
how today's data moves relate to my theses — not a generic market wrap.

```
┌─────────────────────────────────────────────────┐
│  GitHub Action (daily ~4:30 PM ET)              │
│  ┌──────────────┐  ┌──────────────┐             │
│  │ FRED API     │  │ yfinance     │             │
│  │ (macro data) │  │ (markets)    │             │
│  └──────┬───────┘  └──────┬───────┘             │
│         └────────┬────────┘                     │
│                  ▼                              │
│        Python fetch script                      │
│                  │                              │
│                  ▼                              │
│        Claude/OpenAI API → AI summary           │
│                  │                              │
│                  ▼                              │
│    assets/data/dashboard.json (committed)       │
│                  │                              │
│         GitHub Pages rebuild                    │
└─────────────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────┐
│  /dashboard page                                │
│  ┌──────────────────────────────────┐           │
│  │ AI Market Wrap (daily summary)   │           │
│  └──────────────────────────────────┘           │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐        │
│  │ Card     │ │ Card     │ │ Card     │ ...     │
│  │ S&P 500  │ │ 10Y Yld  │ │ VIX      │        │
│  │ 6,821    │ │ 4.09%    │ │ 21.66    │        │
│  │ -1.45%   │ │ -9bp     │ │ +4.16    │        │
│  └──────────┘ └──────────┘ └──────────┘        │
│  ┌──────────────────────────────────┐           │
│  │ Historical charts (1Y / 3Y)     │           │
│  │ (Chart.js line charts)          │           │
│  └──────────────────────────────────┘           │
└─────────────────────────────────────────────────┘
```

---

## Phase 1 — Data Pipeline (GitHub Action + Python)

### 1a. API Keys & Secrets

| Secret              | Source                              | Cost |
|----------------------|-------------------------------------|------|
| `FRED_API_KEY`       | https://fred.stlouisfed.org/docs/api/api_key.html | Free |
| `ANTHROPIC_API_KEY`  | Anthropic console (for AI summary)  | ~$0.01/day |

- yfinance needs no API key
- Store both as GitHub repo secrets

### 1b. Python fetch script

**File**: `.github/scripts/fetch_dashboard.py`

```
Input: FRED API key (env var)
Output: assets/data/dashboard.json
```

**Data to fetch:**

FRED (macro — includes historical series for charts):
- DFF       — Fed funds effective rate
- DGS2      — US 2Y Treasury yield
- DGS10     — US 10Y Treasury yield
- DGS30     — US 30Y Treasury yield
- T10Y2Y    — 10Y-2Y spread (yield curve)
- CPIAUCSL  — CPI headline
- UNRATE    — Unemployment rate
- GDP       — GDP level
- VIXCLS    — VIX (FRED mirror)

Yahoo Finance via yfinance (current + trailing history):
- ^GSPC     — S&P 500
- ^DJI      — Dow Jones
- ^IXIC     — Nasdaq
- ^VIX      — VIX
- GC=F      — Gold
- CL=F      — WTI Crude Oil
- BTC-USD   — Bitcoin
- DX-Y.NYB  — US Dollar Index

For each metric, fetch:
- **Latest value** + 1D change (for the cards)
- **3-year daily history** (for the line charts, downsampled to weekly)

### 1c. JSON schema

```json
{
  "updated_at": "2026-02-15T21:30:00Z",
  "ai_summary": "Markets fell on mixed CPI data...",
  "metrics": [
    {
      "id": "SP500",
      "label": "S&P 500",
      "section": "markets",
      "source": "yahoo",
      "ticker": "^GSPC",
      "latest": 6821.92,
      "change_1d": -100.51,
      "change_1d_pct": -1.45,
      "history": [
        {"date": "2023-02-15", "value": 4136.48},
        {"date": "2023-02-22", "value": 4079.09},
        ...
      ]
    },
    ...
  ]
}
```

### 1d. GitHub Action workflow

**File**: `.github/workflows/dashboard.yml`

```yaml
name: Update Dashboard
on:
  schedule:
    - cron: '30 21 * * 1-5'   # 4:30 PM ET (21:30 UTC), weekdays only
  workflow_dispatch:            # manual trigger for testing

jobs:
  update:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: pip install fredapi yfinance anthropic
      - run: python .github/scripts/fetch_dashboard.py
        env:
          FRED_API_KEY: ${{ secrets.FRED_API_KEY }}
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
      - uses: stefanzweifel/git-auto-commit-action@v5
        with:
          commit_message: 'chore: update dashboard data'
          file_pattern: 'assets/data/dashboard.json'
```

---

## Phase 2 — Dashboard Page (Jekyll + Chart.js) ✅ DONE

Completed as Sruth-style redesign:
- Table rows instead of card grid
- Click-to-chart modal instead of inline sparklines
- Responsive (table head hidden on mobile, modal adapts)
- Chart.js 4 for on-demand chart rendering in modal

### 2b. Implemented layout (Sruth-style)

1. **Thesis tabs** — 5 colored tabs across top, click to filter metrics
2. **Metric table** — Header row + metric rows with columns: name, value, change, direction dot
3. **Chart modal** — Click any row → overlay with Chart.js line chart, close via ×/backdrop/Escape
4. **Thesis write-up** — Markdown content loaded from `pulse-content/2026/` files, rendered inline below metrics
5. **Year selector** — Dropdown for future year-over-year support

### 2c. Row design (implemented)

Each metric row shows:
```
│ Gold          │ $2,935  │ +8.2%  │ 🟢 │
```

- Green/red dot for positive/negative change
- Click → full chart modal with historical data
- No inline sparklines (removed for performance)

### 2d. Tech choices

- **Chart.js** — Already used in kexian, stays consistent
- **No build step** — Vanilla JS, ES modules, same approach as kexian
- **Dark theme** — Matches the blog aesthetic
- **Responsive** — Card grid adapts to mobile

---

## Phase 3 — AI Market Summary

### 3a. Generation

In the Python fetch script, after fetching all data:

1. Build a prompt with the day's data snapshot (all latest values + 1D changes)
2. Call Claude API (claude-3-5-haiku, cheap + fast)
3. Ask for a 2-3 paragraph market wrap focusing on:
   - Key movers and why
   - What's notable / unusual
   - Outlook / what to watch
4. Write the response into `dashboard.json` as `ai_summary`

### 3b. Display

- Rendered at the top of the dashboard in a styled card
- Date-stamped (e.g., "Market Wrap — February 15, 2026")
- Collapsible — shows first paragraph, "Read more" to expand
- Subtle badge: "Generated by AI"

---

## Phase 4 — Polish & Extras (optional, later)

- **Metric selection**: Let user choose which cards to show (localStorage)
- **More metrics**: Add sectors, credit spreads, forex, etc.
- **Signal badges**: Like sruth.app's "NORMAL" / "ELEVATED" / "EXTREME"
  (compute z-score from historical data in the Python script)
- **Comparison mode**: Overlay two metrics on the same chart
- **RSS/email**: Weekly digest from the AI summaries

---

## Implementation Order

1. ~~Register FRED API key, add to GitHub secrets~~
2. ~~Write Python fetch script (FRED + yfinance + Claude)~~ → not yet started
3. ~~Create GitHub Action workflow~~ → not yet started
4. ~~Test with `workflow_dispatch` (manual run)~~ → not yet started
5. ✅ Create `pulse.html` page + layout (Sruth-style redesign)
6. ✅ Build `pulse.js` — table rendering + chart modal from JSON
7. ✅ Build `pulse.css` — dark table rows, modal, responsive
8. ✅ Chart.js historical charts (click-to-expand modal)
9. ~~Add AI summary display~~ → Phase 3
10. ~~Add sparklines to cards~~ → removed (modal chart only)
11. ~~Wire into site nav~~ → not yet
12. ✅ Write all 5 thesis write-ups in Mandarin
13. ✅ Translate all JSON titles/summaries to Chinese
14. ✅ Add metric descriptions/tooltips (18 metrics)

---

## Dependencies / Prereqs

- [ ] FRED API key (register at fred.stlouisfed.org)
- [ ] Anthropic API key (for AI summaries)
- [ ] Both keys added as GitHub repo secrets
- [ ] Confirm GitHub Actions are enabled for the repo
