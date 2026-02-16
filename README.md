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

The Pulse macro dashboard tracks 33 metrics. Most are fetched automatically from yfinance and FRED, but **4 metrics** require manual updates because they come from sources without free APIs.

### Automatic Fetch

```bash
make fetch-data
```

Runs daily via GitHub Actions. Pulls 5 years of weekly data from yfinance (market) and FRED (economic indicators).

### Manual Metric Updates

These 4 metrics have no free API. Their data lives in CSV files under `data/backfill/`. To update, just add a new row to the CSV and re-run backfill:

| Metric ID | Name | Source | Frequency | Where to Find |
|-----------|------|--------|-----------|---------------|
| `china_pmi` | China Mfg PMI (中国制造业PMI) | NBS | Monthly | [data.stats.gov.cn](https://data.stats.gov.cn) |
| `china_retail_sales` | China Retail Sales YoY (中国社零同比) | NBS | Monthly | [data.stats.gov.cn](https://data.stats.gov.cn) |
| `cb_gold_buying` | Central Bank Gold Buying (央行购金量) | World Gold Council | Quarterly | [gold.org/goldhub](https://www.gold.org/goldhub/data/gold-demand-by-country) |
| `usd_reserves_share` | USD Share of Reserves (美元储备占比) | IMF COFER | Quarterly | [data.imf.org](https://data.imf.org/regular.aspx?key=41175) |

**Workflow:**

1. Open the CSV (e.g. `data/backfill/china_pmi.csv`)
2. Add a new row: `2026-02-28,50.5`
3. Run: `make backfill-metric ID=china_pmi`

```bash
# Load one metric
make backfill-metric ID=china_pmi

# Load all 4
make backfill-metric ID=china_pmi && \
make backfill-metric ID=china_retail_sales && \
make backfill-metric ID=cb_gold_buying && \
make backfill-metric ID=usd_reserves_share
```

CSV format — columns `date,value`, one row per period:
```csv
date,value
2021-01-31,51.3
2021-02-28,50.6
...
```

Backfill merges with existing history (new dates added, existing dates replaced). Safe to re-run.
