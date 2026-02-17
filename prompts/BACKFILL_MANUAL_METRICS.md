
## For AI:

```
I need to update the manual metrics for my Pulse macro dashboard.
Today is [DATE]. Please help me find the latest values and append them to the CSVs.

Here are the metrics that need updating. For each one, look up the latest available value, then append a new row to the CSV. The CSV format is `date,value` with date as `YYYY-MM-DD` (last day of the period).

### Monthly metrics (update every month):

1. **China Mfg PMI** — `data/backfill/china_pmi.csv`
   - NBS Manufacturing PMI. Source: https://tradingeconomics.com/china/manufacturing-pmi
   - Unit: index (50 = expansion/contraction line)

2. **China Retail Sales YoY** — `data/backfill/china_retail_sales.csv`
   - Source: https://tradingeconomics.com/china/retail-sales-annual
   - Unit: % YoY

3. **China CPI YoY** — `data/backfill/china_cpi.csv`
   - Source: https://tradingeconomics.com/china/consumer-price-index-cpi
   - Unit: % YoY

4. **China M2 YoY** — `data/backfill/china_m2.csv`
   - Source: https://tradingeconomics.com/china/money-supply-m2
   - Unit: % YoY

5. **China 10Y Yield** — `data/backfill/cn_10y.csv`
   - Source: https://tradingeconomics.com/china/government-bond-yield or https://www.investing.com/rates-bonds/china-10-year-bond-yield
   - Unit: % (last trading day of month)

6. **US ISM Manufacturing PMI** — `data/backfill/us_ism_pmi.csv`
   - Source: https://www.ismworld.org/supply-management-news-and-reports/reports/ism-report-on-business/ or https://tradingeconomics.com/united-states/business-conditions
   - Unit: index

7. **MOVE Index** — `data/backfill/move.csv`
   - ICE BofA Treasury implied volatility. Source: https://tradingeconomics.com/united-states/ice-bofa-move-index
   - Unit: index (weekly — use last trading day of the week)

### Quarterly metrics (update every quarter):

8. **China GDP YoY** — `data/backfill/china_gdp.csv`
   - Source: https://tradingeconomics.com/china/gdp-growth-annual
   - Unit: % YoY. Date = last day of quarter (03-31, 06-30, 09-30, 12-31)

9. **China Market Cap/GDP** — `data/backfill/china_mktcap_gdp.csv`
   - Source: https://tradingeconomics.com/china/market-capitalization-of-listed-domestic-companies-percent-of-gdp-wb-data.html or https://www.ceicdata.com
   - Unit: % (market cap as percentage of GDP). Date = last day of quarter

10. **USD Share of FX Reserves** — `data/backfill/usd_reserves_share.csv`
   - IMF COFER data. Source: https://data.imf.org/regular.aspx?key=41175
   - Unit: %. ~1 quarter lag. Date = last day of quarter

11. **Central Bank Gold Buying** — `data/backfill/cb_gold_buying.csv`
    - World Gold Council. Source: https://www.gold.org/goldhub/data/gold-demand-by-country
    - Unit: tonnes/yr. Date = last day of quarter
    - **IMPORTANT**: The CSV stores **trailing 4-quarter (12-month) totals**, NOT cumulative YTD.
      WGC reports cumulative YTD figures (e.g. Q1=244, Q2=500, Q3=750, Q4=1000).
      You must first convert to per-quarter values (Q1=244, Q2=256, Q3=250, Q4=250),
      then compute the rolling 4Q sum for each quarter. This avoids a zig-zag chart pattern.

12. **Big Tech CapEx** — `data/backfill/bigtech_capex.csv`
    - Sum of quarterly capex: MSFT + GOOGL + AMZN + META + ORCL
    - Unit: $B (annualized). Date = last day of quarter. Compiled from earnings reports.

After appending new rows to the CSVs, run the backfill for each updated metric:

  make backfill-all

Or individually:

  uv run scripts/fetch_pulse_data.py backfill <metric_id>

```

## For Human

### Monthly (around the 15th–20th of each month, after China NBS releases)

- [ ] china_pmi
- [ ] china_retail_sales
- [ ] china_cpi
- [ ] china_m2
- [ ] cn_10y
- [ ] us_ism_pmi
- [ ] move (weekly data — add all weeks since last update)

### Quarterly (after quarter-end, ~1 month lag for official data)

- [ ] china_gdp
- [ ] china_mktcap_gdp
- [ ] usd_reserves_share (~1 quarter lag from IMF)
- [ ] cb_gold_buying (~1 quarter lag from WGC)
- [ ] bigtech_capex (after earnings season, ~6 weeks after quarter-end)


## Tips:

- **China NBS data** is typically released around the 15th of the following month
- **ISM PMI** is released on the first business day of each month
- **MOVE** can be updated weekly or monthly; weekly gives richer chart data
- **IMF COFER** data has ~1 quarter lag (e.g., Q3 data available in Q1 next year)
- **Big Tech CapEx** requires summing 5 companies' quarterly earnings — typically available ~6 weeks after quarter-end
- The `make backfill-all` command will re-import ALL manual CSVs at once — safe to run anytime since existing data is preserved and only new rows are added
