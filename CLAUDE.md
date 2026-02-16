# CLAUDE.md

## General Preferences

- **Prefer running commands** over describing what to do. Execute scripts, edits, and shell commands directly rather than suggesting them.
- **Edit files directly** instead of running Python/shell scripts to modify them when the tool can do it.
- **No em-dashes** (—): use colons (:) instead.
- **No emoji** unless explicitly requested.
- **Concise responses**: skip unnecessary framing, introductions, and conclusions.
- **Chinese content**: the user reads and writes Chinese fluently. Metric names include `name_zh` fields.
- **Terminal**: use `python3 -c` to write temp files (auto-approved), never `cat > file << 'EOF'` (requires manual approval). Never start the Jekyll server: the user always has it running.

## Workspace Structure

This is a multi-project workspace:

- **pwen.github.io**: Jekyll 3.10 personal site on GitHub Pages. Includes a "Pulse" macro dashboard.
- **kexian**: Flask app with PostgreSQL (Alembic migrations). Dockerized, deployed on Railway.
- **rebalancer**: Flask portfolio rebalancer with CSV parsers (Fidelity, Schwab). Dockerized, deployed on Railway.

## pwen.github.io — Pulse Dashboard

### Tech Stack
- Jekyll 3.10, Chart.js 4, Vanilla JS (two IIFEs: `pulse.js` and `charts.js`)
- Python data pipeline: `uv` + PEP 723 inline deps, `yfinance`, `fredapi`, `pandas`
- GitHub Actions daily cron at 7AM UTC

### Data Architecture
- 56 metrics across 9 categories, LOOKBACK_YEARS=11 (~11 years of weekly data)
- Metrics split into **per-category JSON files**: `currencies.json`, `rates.json`, `liquidity.json`, `china.json`, `metals.json`, `energy.json`, `equities.json`, `sentiment.json`, `row.json`
- Lightweight `metrics.json` index (metadata only, no history arrays)
- All files in `assets/data/pulse/`
- `fetch_pulse_data.py` writes per-category files (with history) + metrics.json (slim index)
- `charts.js` and `pulse.js` load per-category files in parallel via `Promise.all`
- Chart periods: 1M, 3M, 6M, YTD, 1Y, 5Y, 10Y
- Theses defined in `theses-2026.json`
- Manual CSVs in `data/backfill/` extended back to 2015
- AI-assisted backfill prompt template in `prompts/BACKFILL_MANUAL_METRICS.md`

### Metric Source Types
- `yfinance`: daily close via yfinance
- `fred`: FRED API series
- `derived`: computed from other data at fetch time (e.g., ratio of two tickers like GSG/SPY, normalized basket ratio like atoms_bits, or arithmetic on fetched metrics like cn_us_spread = cn_10y - us_10y)
- `manual`: backfilled from CSV in `data/backfill/` (11 metrics, data back to 2015)

### Backfill Command
```bash
uv run scripts/fetch_pulse_data.py backfill <metric_id> <csv_path>
```
CSV format: `date,value` (header row, one per line).

### Manual Metrics Maintenance
When the user asks to "update manual metrics" or similar:
1. Look up the latest values from public sources (NBS, PBOC, ISM, etc.)
2. Add new rows to the corresponding CSV in `data/backfill/`
3. Run `make backfill-metric ID=<metric_id>` for each updated metric
4. Run `make fetch-data` to regenerate all category JSON files

Manual metrics and their sources/frequencies:
- `china_pmi` (Monthly, NBS)
- `china_retail_sales` (Monthly, NBS)
- `china_cpi` (Monthly, NBS)
- `china_gdp` (Quarterly, NBS)
- `china_m2` (Monthly, PBOC)
- `cn_10y` (Monthly, PBOC/CEIC)
- `cb_gold_buying` (Quarterly, World Gold Council)
- `usd_reserves_share` (Quarterly, IMF COFER)
- `move` (Daily, ICE BofA)
- `us_ism_pmi` (Monthly, ISM)
- `bigtech_capex` (Quarterly, earnings reports)

### Description Style
- What it measures + directional meaning only
- No thesis explanations, no 🔗 links
- No "Forward Guidance" mentions
- Use colons (:) not em-dashes (—)
- Example: "VUG/VTV ratio. Rising = growth stocks outperforming value, falling = value winning."

## kexian & rebalancer

- Both use Flask + PostgreSQL + Alembic
- Both Dockerized with docker-compose.yml
- Both deployed on Railway (railway.toml)
- Use `make` for common dev commands
