# 看戏的地儿 (Pulse) — pwen.github.io/pulse

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

## Phase 2 — Dashboard Page (Jekyll + Chart.js)

### 2a. Files to create

| File                      | Purpose                              |
|---------------------------|--------------------------------------|
| `dashboard.html`          | Jekyll page (layout: default)        |
| `assets/js/dashboard.js`  | Fetch JSON, render cards + charts    |
| `assets/css/dashboard.css`| Dashboard-specific styles            |

### 2b. Page layout (top → bottom)

1. **Header** — "DASHBOARD" + last updated timestamp
2. **AI Summary** — Collapsible card with the daily market wrap
3. **Metric Cards** — Grid of cards grouped by section:
   - **Rates** — Fed funds, 2Y, 10Y, 30Y, yield curve
   - **Markets** — S&P, Dow, Nasdaq, VIX
   - **Economy** — CPI, unemployment, GDP
   - **Commodities & Crypto** — Gold, oil, BTC, DXY
4. **Historical Charts** — Click any card to expand a Chart.js line chart
   showing 1Y/3Y history

### 2c. Card design

Each card shows:
```
┌────────────────────┐
│ S&P 500            │
│ 6,821.92     ▼1.45%│
│ ▁▂▃▄▅▅▆▇▇█        │  ← sparkline (tiny inline chart)
└────────────────────┘
```

- Green/red for positive/negative 1D change
- Optional sparkline using Chart.js (small 60-day line)
- Click → expands to a full-width 1Y/3Y chart below

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

1. Register FRED API key, add to GitHub secrets
2. Write Python fetch script (FRED + yfinance + Claude)
3. Create GitHub Action workflow
4. Test with `workflow_dispatch` (manual run)
5. Create `dashboard.html` page + layout
6. Build `dashboard.js` — card rendering from JSON
7. Build `dashboard.css` — dark cards, grid, responsive
8. Add Chart.js historical charts (click-to-expand)
9. Add AI summary display
10. Add sparklines to cards
11. Wire into site nav

---

## Dependencies / Prereqs

- [ ] FRED API key (register at fred.stlouisfed.org)
- [ ] Anthropic API key (for AI summaries)
- [ ] Both keys added as GitHub repo secrets
- [ ] Confirm GitHub Actions are enabled for the repo
