# Copilot Instructions

## General Preferences

- **Prefer running commands** over describing what to do. Execute scripts, edits, and shell commands directly rather than suggesting them.
- **Edit files directly** instead of running Python/shell scripts to modify them when the tool can do it.
- **No em-dashes** (—): use colons (:) instead.
- **No emoji** unless explicitly requested.
- **Concise responses**: skip unnecessary framing, introductions, and conclusions.
- **Chinese content**: the user reads and writes Chinese fluently. Metric names include `name_zh` fields.

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
- Metrics split into **per-category JSON files**: `currencies.json`, `rates.json`, `liquidity.json`, `metals.json`, `energy.json`, `equities.json`, `sentiment.json`, `em.json`
- Combined `metrics.json` kept for backfill compatibility
- All files in `assets/data/pulse/`
- `fetch_pulse_data.py` writes both per-category files and combined file
- `charts.js` and `pulse.js` load per-category files in parallel via `Promise.all`
- Theses defined in `theses-2026.json`

### Metric Source Types
- `yfinance`: daily close via yfinance
- `fred`: FRED API series
- `computed`: ratio of two tickers (e.g., GSG/SPY)
- `basket_ratio`: normalized basket A / basket B (e.g., atoms_bits = XLB+XLI+XLE+XME / IGV+WCLD)
- `manual`: backfilled from CSV in `data/backfill/`

### Backfill Command
```bash
uv run scripts/fetch_pulse_data.py backfill <metric_id> <csv_path>
```
CSV format: `date,value` (header row, one per line).

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
