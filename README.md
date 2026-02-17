🚀 A blog built with Jekyll and hosted on Github Pages

### Development

```
bundle install
bundle exec jekyll serve
```

Content should be served locally at `http://localhost:4000`

### 📝 Writing a New Post

1. Create a new file in the `_posts` directory
2. Name it with the format: `YYYY-MM-DD-title.md` (for English) or `YYYY-MM-DD-title-zh.md` (for Mandarin)
3. Add the front matter at the top of the file:

**To add images**:

1. Place your images in the `assets/images/` directory
2. Reference them in your post:
   ```markdown
   ![Image description](/assets/images/your-image.jpg)
   ```
3. Or set as the post's featured image in the front matter:
   ```yaml
   image: /assets/images/your-image.jpg
   ```

### 📚 Resources

- [Jekyll Documentation](https://jekyllrb.com/docs/)
- [GitHub Pages Documentation](https://docs.github.com/en/pages)
- [Markdown Guide](https://www.markdownguide.org/)
- [Liquid Template Language](https://shopify.github.io/liquid/)

---

## 📊 Pulse Data Pipeline

The Pulse macro dashboard tracks 61 metrics across 9 categories, organized around 5 macro theses. Most are fetched automatically from yfinance and FRED; some require manual CSV backfill.

### Metric Source Types

| Type | How it works |
|------|-------------|
| `yfinance` | Daily close via yfinance |
| `fred` | FRED API series |
| `computed` | Ratio of two tickers (e.g., GSG/SPY) |
| `basket_ratio` | Normalized basket A / basket B (e.g., atoms_bits) |
| `manual` | Backfilled from CSV in `data/backfill/` |
| `derived` | Computed from other metrics at fetch time (e.g., cn_us_spread) |

### Automatic Fetch

```bash
make fetch-data
```

Runs daily via GitHub Actions (7AM UTC). Pulls 11 years of weekly data from yfinance and FRED, writes per-category files + lightweight metrics.json index. Chart supports periods: 1M, 3M, 6M, YTD, 1Y, 5Y, 10Y.

### Manual Metric Updates

These metrics have no free API. Their data lives in CSV files under `data/backfill/` (extended back to 2015). To update, add a new row to the CSV and re-run backfill:

| Metric ID | Name | Source | Frequency | Where to Find |
|-----------|------|--------|-----------|---------------|
| `china_pmi` | China Mfg PMI (中国制造业PMI) | NBS | Monthly | [data.stats.gov.cn](https://data.stats.gov.cn) |
| `china_retail_sales` | China Retail Sales YoY (中国社零同比) | NBS | Monthly | [data.stats.gov.cn](https://data.stats.gov.cn) |
| `china_cpi` | China CPI YoY (中国CPI同比) | NBS | Monthly | [data.stats.gov.cn](https://data.stats.gov.cn) |
| `china_gdp` | China GDP YoY (中国GDP同比) | NBS | Quarterly | [data.stats.gov.cn](https://data.stats.gov.cn) |
| `china_m2` | China M2 YoY (中国M2同比) | PBOC | Monthly | [pbc.gov.cn](http://www.pbc.gov.cn/diaochatongjisi/116219/116319/index.html) |
| `cn_10y` | China 10Y Yield (中国10年期国债) | PBOC/CEIC | Monthly | [ceicdata.com](https://www.ceicdata.com) or PBOC |
| `cb_gold_buying` | Central Bank Gold Buying (央行购金量) | World Gold Council | Quarterly | [gold.org/goldhub](https://www.gold.org/goldhub/data/gold-demand-by-country) |
| `usd_reserves_share` | USD Share of Reserves (美元储备占比) | IMF COFER | Quarterly | [data.imf.org](https://data.imf.org/regular.aspx?key=41175) |
| `move` | MOVE Index (国债波动率指数) | ICE BofA | Daily | [ice.com](https://www.ice.com/marketdata/reports/258) |
| `us_ism_pmi` | US Manufacturing PMI (美国制造业PMI) | ISM | Monthly | [ismworld.org](https://www.ismworld.org/supply-management-news-and-reports/reports/ism-report-on-business/) |
| `bigtech_capex` | Big Tech CapEx (大型科技公司资本开支) | Earnings reports | Quarterly | big tech quarterly filings |

**Workflow:**

1. Open the CSV (e.g. `data/backfill/china_pmi.csv`)
2. Add a new row: `2026-02-28,50.5`
3. Run: `make backfill-metric ID=china_pmi`

```bash
# Load one metric
make backfill-metric ID=china_pmi

# Load all manual metrics at once
make backfill-all
```

CSV format: columns `date,value`, one row per period:
```csv
date,value
2021-01-31,51.3
2021-02-28,50.6
...
```

Backfill merges with existing history (new dates added, existing dates replaced). Safe to re-run.
