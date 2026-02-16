/* ─── Charts.js — Category-grouped metrics with inline charts ─── */

(function () {
    'use strict';

    const BASE = '/assets/data/pulse';
    let metricsData = null;
    let activeChart = null;
    let expandedMetric = null;
    let activePeriod = 'YTD';
    let changeMode = 'auto'; // 'auto' | 'bp' | 'pct'

    const CATEGORIES = [
        { id: 'china', name: 'CHINA', metrics: ['csi300', 'hsi', 'kweb', 'china_pmi', 'china_retail_sales', 'china_cpi', 'china_gdp', 'china_m2'] },
        { id: 'currencies', name: 'CURRENCIES', metrics: ['dxy', 'eurusd', 'usdcny', 'usd_reserves_share'] },
        { id: 'rates', name: 'RATES & YIELDS', metrics: ['us_10y', 'cn_10y', 'cn_us_spread', 'yield_curve', 'tips_5y', 'breakeven_10y', 'hy_spread', 'move'] },
        { id: 'liquidity', name: 'LIQUIDITY & FISCAL', metrics: ['fed_balance_sheet', 'debt_to_gdp', 'tga'] },
        { id: 'metals', name: 'METALS', metrics: ['gold', 'silver', 'copper', 'uranium'] },
        { id: 'energy', name: 'ENERGY', metrics: ['oil', 'natgas', 'energy_cpi'] },
        { id: 'equities', name: 'US EQUITIES & SECTORS', metrics: ['sp500', 'qqq', 'smh', 'xlu', 'gsci_spy_ratio', 'bigtech_capex', 'growth_value', 'cap_equal', 'atoms_bits'] },
        { id: 'sentiment', name: 'SENTIMENT & ALTERNATIVES', metrics: ['vix', 'btc', 'cb_gold_buying', 'us_ism_pmi', 'us_gdp', 'us_cpi', 'umich_sentiment'] },
        { id: 'row', name: 'REST OF WORLD', metrics: ['eem', 'inda', 'ilf'] }
    ];

    const PERIODS = ['1M', '3M', '6M', 'YTD', '1Y', '5Y'];

    // ─── Bootstrap ───
    async function init() {
        try {
            // Load per-category JSON files in parallel
            const fetches = CATEGORIES.map(cat =>
                fetch(`${BASE}/${cat.id}.json`).then(r => r.json())
            );
            const results = await Promise.all(fetches);

            // Merge into single metricsData object
            metricsData = { updated: null, metrics: {} };
            for (const catData of results) {
                if (catData.updated && (!metricsData.updated || catData.updated > metricsData.updated)) {
                    metricsData.updated = catData.updated;
                }
                Object.assign(metricsData.metrics, catData.metrics);
            }
            renderUpdated();
            renderCategories();
        } catch (err) {
            console.error('Failed to load metrics data:', err);
        }
    }

    function renderUpdated() {
        const el = document.getElementById('charts-updated');
        if (!el || !metricsData?.updated) return;
        const d = new Date(metricsData.updated);
        el.textContent = `Last updated: ${d.toLocaleDateString('en-US', {
            month: 'short', day: 'numeric', year: 'numeric'
        })}`;
    }

    // ─── Render all categories ───
    function renderCategories() {
        const container = document.getElementById('charts-categories');
        if (!container) return;

        container.innerHTML = CATEGORIES.map(cat => {
            const metricRows = cat.metrics
                .filter(id => metricsData.metrics[id])
                .map(id => renderMetricRow(id, metricsData.metrics[id]))
                .join('');

            return `
                <div class="chart-category" data-category="${cat.id}">
                    <div class="chart-category-header" data-cat="${cat.id}">
                        <span class="chart-category-name">${cat.name}</span>
                        <span class="chart-category-toggle">−</span>
                    </div>
                    <div class="chart-category-body" id="cat-body-${cat.id}">
                        <div class="chart-col-headers">
                            <span class="ch-name">NAME</span>
                            <span class="ch-val">LATEST</span>
                            <span class="ch-chg">1W</span>
                            <span class="ch-chg">1M</span>
                            <span class="ch-chg">YTD</span>
                            <span class="ch-chg">1Y</span>
                            <span class="ch-source">SOURCE</span>
                            <span class="ch-dots"></span>
                        </div>
                        ${metricRows}
                    </div>
                </div>
            `;
        }).join('');

        container.querySelectorAll('.chart-category-header').forEach(header => {
            header.addEventListener('click', () => {
                const catId = header.dataset.cat;
                const body = document.getElementById(`cat-body-${catId}`);
                const toggle = header.querySelector('.chart-category-toggle');
                if (body.classList.contains('collapsed')) {
                    body.classList.remove('collapsed');
                    toggle.textContent = '−';
                } else {
                    body.classList.add('collapsed');
                    toggle.textContent = '+';
                }
            });
        });

        container.querySelectorAll('.chart-metric-row').forEach(row => {
            row.addEventListener('click', () => toggleMetricChart(row.dataset.metric));
        });
    }

    // ─── Single metric row ───
    function renderMetricRow(id, m) {
        const changeText = formatChangeText(m);
        const dirYtd = formatChangeDir(m);
        const periodButtons = PERIODS.map(p =>
            `<button class="chart-period-btn${p === activePeriod ? ' active' : ''}" data-period="${p}">${p}</button>`
        ).join('');

        const zhName = m.name_zh ? `<span class="chart-metric-name-zh">${m.name_zh}</span>` : '';

        const chg1w = formatPeriodChange(m, 7);
        const dir1w = periodChangeDir(m, 7);
        const chg1m = formatPeriodChange(m, 30);
        const dir1m = periodChangeDir(m, 30);
        const chg1y = formatPeriodChange(m, 365);
        const dir1y = periodChangeDir(m, 365);

        const sourceLabel = (m.source || '').split(':')[0].toUpperCase() || '—';

        return `
            <div class="chart-metric-row" data-metric="${id}">
                <div class="chart-metric-info">
                    <span class="chart-metric-arrow">▸</span>
                    <span class="chart-metric-name">${m.name}</span>
                    ${zhName}
                </div>
                <div class="chart-metric-data">
                    <span class="chart-metric-value">${formatValue(m)}</span>
                    <span class="chart-metric-change ${dir1w}">${chg1w}</span>
                    <span class="chart-metric-change ${dir1m}">${chg1m}</span>
                    <span class="chart-metric-change ytd ${dirYtd}">${changeText}</span>
                    <span class="chart-metric-change ${dir1y}">${chg1y}</span>
                    <span class="chart-metric-source">${sourceLabel}</span>
                </div>
            </div>
            <div class="chart-metric-expand" id="expand-${id}">
                <div class="chart-expand-header">
                    <div class="chart-metric-desc" id="desc-${id}"></div>
                    <div class="chart-period-bar" id="periods-${id}">
                        ${periodButtons}
                    </div>
                </div>
                <div class="chart-metric-canvas-wrap">
                    <canvas id="canvas-${id}"></canvas>
                </div>
            </div>
        `;
    }

    // ─── Toggle inline chart ───
    function toggleMetricChart(metricId) {
        const expandEl = document.getElementById(`expand-${metricId}`);
        const row = document.querySelector(`.chart-metric-row[data-metric="${metricId}"]`);
        if (!expandEl || !row) return;

        if (expandedMetric === metricId) {
            expandEl.classList.remove('expanded');
            row.classList.remove('active');
            row.querySelector('.chart-metric-arrow').textContent = '▸';
            if (activeChart) { activeChart.destroy(); activeChart = null; }
            expandedMetric = null;
            return;
        }

        if (expandedMetric) {
            const prevExpand = document.getElementById(`expand-${expandedMetric}`);
            const prevRow = document.querySelector(`.chart-metric-row[data-metric="${expandedMetric}"]`);
            if (prevExpand) prevExpand.classList.remove('expanded');
            if (prevRow) {
                prevRow.classList.remove('active');
                prevRow.querySelector('.chart-metric-arrow').textContent = '▸';
            }
            if (activeChart) { activeChart.destroy(); activeChart = null; }
        }

        expandEl.classList.add('expanded');
        row.classList.add('active');
        row.querySelector('.chart-metric-arrow').textContent = '▾';
        expandedMetric = metricId;

        const m = metricsData.metrics[metricId];
        const descEl = document.getElementById(`desc-${metricId}`);
        if (descEl && m.description) descEl.textContent = m.description;

        // Bind period buttons
        const periodBar = document.getElementById(`periods-${metricId}`);
        if (periodBar) {
            periodBar.querySelectorAll('.chart-period-btn').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    activePeriod = btn.dataset.period;
                    periodBar.querySelectorAll('.chart-period-btn').forEach(b => b.classList.remove('active'));
                    btn.classList.add('active');
                    renderChart(metricId);
                });
            });
        }

        renderChart(metricId);
    }

    // ─── Render chart for current period ───
    function renderChart(metricId) {
        const m = metricsData.metrics[metricId];
        const canvas = document.getElementById(`canvas-${metricId}`);
        if (!canvas) return;

        if (activeChart) { activeChart.destroy(); activeChart = null; }

        const chartData = getSlicedHistory(m, activePeriod);
        if (!chartData || chartData.length === 0) return;

        renderInlineChart(canvas, m, chartData);
    }

    // ─── Slice history by time period ───
    function getSlicedHistory(m, period) {
        // New format: history is array of [date_str, value] pairs
        if (m.history && Array.isArray(m.history) && m.history.length > 0) {
            const now = new Date();
            let cutoff;

            switch (period) {
                case '1M': cutoff = new Date(now); cutoff.setMonth(cutoff.getMonth() - 1); break;
                case '3M': cutoff = new Date(now); cutoff.setMonth(cutoff.getMonth() - 3); break;
                case '6M': cutoff = new Date(now); cutoff.setMonth(cutoff.getMonth() - 6); break;
                case 'YTD': cutoff = new Date(now.getFullYear(), 0, 1); break;
                case '1Y': cutoff = new Date(now); cutoff.setFullYear(cutoff.getFullYear() - 1); break;
                case '5Y': cutoff = new Date(now); cutoff.setFullYear(cutoff.getFullYear() - 5); break;
                default: cutoff = new Date(now.getFullYear(), 0, 1);
            }

            const cutoffStr = cutoff.toISOString().slice(0, 10);
            return m.history
                .filter(point => point[0] >= cutoffStr)
                .map(point => ({ date: point[0], value: point[1] }));
        }

        // Legacy: spark array (no dates)
        if (m.spark && m.spark.length > 0) {
            return m.spark.map((v, i) => ({
                date: i === m.spark.length - 1 ? 'Now' : `-${m.spark.length - 1 - i}w`,
                value: v,
            }));
        }

        return null;
    }

    // ─── Render Chart.js inline chart ───
    function renderInlineChart(canvas, m, chartData) {
        const ctx = canvas.getContext('2d');
        const values = chartData.map(d => d.value);
        const labels = chartData.map(d => d.date);

        // Color based on period performance
        const isUp = values[values.length - 1] >= values[0];
        const color = isUp ? '#4caf87' : '#e05555';

        activeChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels,
                datasets: [{
                    data: values,
                    borderColor: color,
                    backgroundColor: hexToRgba(color, 0.08),
                    fill: true,
                    tension: 0.3,
                    pointRadius: 0,
                    pointHoverRadius: 5,
                    pointHoverBackgroundColor: color,
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        backgroundColor: '#fff',
                        titleColor: '#666',
                        bodyColor: '#333',
                        borderColor: '#e1e4e8',
                        borderWidth: 1,
                        callbacks: {
                            label: ctx => formatRawValue(ctx.raw, m)
                        }
                    }
                },
                scales: {
                    x: {
                        ticks: {
                            color: '#888',
                            maxTicksLimit: 6,
                            font: { size: 11 },
                            callback: function (val) {
                                const label = this.getLabelForValue(val);
                                if (label && label.match(/^\d{4}-\d{2}-\d{2}$/)) {
                                    const d = new Date(label + 'T00:00:00');
                                    if (activePeriod === '5Y') {
                                        return d.toLocaleDateString('en-US', { month: 'short', year: 'numeric' });
                                    }
                                    if (activePeriod === '1Y') {
                                        return d.toLocaleDateString('en-US', { month: 'short', year: 'numeric' });
                                    }
                                    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
                                }
                                return label;
                            }
                        },
                        grid: { color: 'rgba(0,0,0,0.06)' }
                    },
                    y: {
                        ticks: { color: '#888', font: { size: 11 } },
                        grid: { color: 'rgba(0,0,0,0.06)' }
                    }
                },
                interaction: { intersect: false, mode: 'index' }
            }
        });
    }

    // ─── Formatting helpers ───
    function formatValue(m) {
        const v = m.value;
        if (v == null) return '—';
        if (m.unit === '$T') return `$${v}T`;
        if (m.unit === '$B') return `$${v}B`;
        if (m.unit === '$/oz') return `$${v.toLocaleString()}`;
        if (m.unit === '$') return `$${v.toLocaleString()}`;
        if (m.unit === '$/bbl') return `$${v.toFixed(2)}`;
        if (m.unit === '$/lb') return `$${v.toFixed(2)}`;
        if (m.unit === '$/MMBtu') return `$${v.toFixed(2)}`;
        if (m.unit === '%') return `${v.toFixed(2)}%`;
        if (m.unit === '% spread') return `${v.toFixed(2)}%`;
        if (m.unit === 'rate') return v.toFixed(4);
        if (m.unit === 'ratio') return v.toFixed(2);
        if (m.unit === '% YoY' || m.unit === '% QoQ') return `${v.toFixed(1)}%`;
        if (m.unit === 'tonnes/yr') return `${v.toLocaleString()}t`;
        if (typeof v === 'number' && v > 1000) return v.toLocaleString(undefined, { maximumFractionDigits: 2 });
        if (typeof v === 'number') return v.toFixed(2);
        return String(v);
    }

    function formatChangeText(m) {
        const useBp = shouldUseBp(m);
        if (useBp) {
            const bp = m.change_ytd_bp != null ? m.change_ytd_bp : computeChangeBp(m, 'ytd');
            if (bp == null) return '—';
            return `${bp > 0 ? '+' : ''}${bp}bp`;
        } else {
            const pct = m.change_ytd_pct != null ? m.change_ytd_pct : computeChangePct(m, 'ytd');
            if (pct == null) return '—';
            return `${pct > 0 ? '+' : ''}${pct.toFixed(1)}%`;
        }
    }

    function formatChangeDir(m) {
        let val = m.change_ytd_pct ?? m.change_ytd_bp;
        if (val == null) {
            // Fallback: compute from history (same as formatChangeText)
            if (shouldUseBp(m)) {
                val = computeChangeBp(m, 'ytd');
            } else {
                val = computeChangePct(m, 'ytd');
            }
        }
        val = val ?? 0;
        return val > 0 ? 'up' : val < 0 ? 'down' : 'flat';
    }

    // Determine whether to show bp or % for a given metric
    function shouldUseBp(m) {
        if (changeMode === 'bp') return true;
        if (changeMode === 'pct') return false;
        // auto: use bp for rate/yield metrics
        return m.change_ytd_bp != null;
    }

    // Find value at a given lookback from history
    function findHistoricalValue(m, daysAgo) {
        if (!m.history || m.history.length < 2) return null;
        const now = new Date();
        const cutoff = new Date(now);
        cutoff.setDate(cutoff.getDate() - daysAgo);
        let closest = null;
        let closestDiff = Infinity;
        for (const [dateStr, val] of m.history) {
            const d = new Date(dateStr);
            const diff = Math.abs(d - cutoff);
            if (diff < closestDiff) {
                closestDiff = diff;
                closest = val;
            }
        }
        return closest;
    }

    function computeChangeBp(m, period) {
        const daysMap = { '1w': 7, '1m': 30, 'ytd': null, '1y': 365 };
        let oldVal;
        if (period === 'ytd') {
            // Find value closest to Jan 1 of current year
            const jan1 = new Date(new Date().getFullYear(), 0, 1);
            let closest = null, closestDiff = Infinity;
            for (const [dateStr, val] of (m.history || [])) {
                const diff = Math.abs(new Date(dateStr) - jan1);
                if (diff < closestDiff) { closestDiff = diff; closest = val; }
            }
            oldVal = closest;
        } else {
            oldVal = findHistoricalValue(m, daysMap[period]);
        }
        if (oldVal == null) return null;
        return Math.round((m.value - oldVal) * 100);
    }

    function computeChangePct(m, period) {
        const daysMap = { '1w': 7, '1m': 30, 'ytd': null, '1y': 365 };
        let oldVal;
        if (period === 'ytd') {
            const jan1 = new Date(new Date().getFullYear(), 0, 1);
            let closest = null, closestDiff = Infinity;
            for (const [dateStr, val] of (m.history || [])) {
                const diff = Math.abs(new Date(dateStr) - jan1);
                if (diff < closestDiff) { closestDiff = diff; closest = val; }
            }
            oldVal = closest;
        } else {
            oldVal = findHistoricalValue(m, daysMap[period]);
        }
        if (oldVal == null || oldVal === 0) return null;
        return ((m.value - oldVal) / Math.abs(oldVal)) * 100;
    }

    // Compute change for a lookback period respecting current changeMode
    function computeChange(m, daysAgo) {
        const oldVal = findHistoricalValue(m, daysAgo);
        if (oldVal == null || oldVal === 0) return null;
        if (shouldUseBp(m)) {
            return Math.round((m.value - oldVal) * 100);
        } else {
            return ((m.value - oldVal) / Math.abs(oldVal)) * 100;
        }
    }

    function formatPeriodChange(m, daysAgo) {
        const change = computeChange(m, daysAgo);
        if (change == null) return '—';
        if (shouldUseBp(m)) {
            const sign = change > 0 ? '+' : '';
            return `${sign}${change}bp`;
        } else {
            const sign = change > 0 ? '+' : '';
            return `${sign}${change.toFixed(1)}%`;
        }
    }

    function periodChangeDir(m, daysAgo) {
        const change = computeChange(m, daysAgo);
        if (change == null) return 'flat';
        return change > 0 ? 'up' : change < 0 ? 'down' : 'flat';
    }

    // Update all change cells in-place when toggle changes
    function updateChangeDisplay() {
        document.querySelectorAll('.chart-metric-row[data-metric]').forEach(row => {
            const id = row.dataset.metric;
            const m = metricsData.metrics[id];
            if (!m) return;

            const spans = row.querySelectorAll('.chart-metric-change');
            if (spans.length < 4) return;

            const periods = [
                { el: spans[0], days: 7 },
                { el: spans[1], days: 30 },
                { el: spans[2], days: null }, // YTD
                { el: spans[3], days: 365 }
            ];

            periods.forEach(({ el, days }) => {
                let text, dir;
                if (days === null) {
                    text = formatChangeText(m);
                    dir = formatChangeDir(m);
                } else {
                    text = formatPeriodChange(m, days);
                    dir = periodChangeDir(m, days);
                }
                el.textContent = text;
                el.className = `chart-metric-change ${days === null ? 'ytd ' : ''}${dir}`;
            });
        });
    }

    // Bind the toggle buttons
    function bindChangeToggle() {
        const toggle = document.getElementById('change-mode-toggle');
        if (!toggle) return;
        toggle.querySelectorAll('.change-mode-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                changeMode = btn.dataset.mode;
                toggle.querySelectorAll('.change-mode-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                updateChangeDisplay();
            });
        });
    }

    function formatRawValue(raw, m) {
        if (m.unit === '%' || m.unit === '% spread' || m.unit === '% YoY' || m.unit === '% QoQ') return raw.toFixed(2) + '%';
        if (m.unit === '$/oz' || m.unit === '$') return '$' + raw.toLocaleString();
        if (m.unit === '$T') return '$' + raw + 'T';
        if (m.unit === '$B') return '$' + raw + 'B';
        if (m.unit === '$/bbl') return '$' + raw.toFixed(2);
        if (m.unit === '$/lb') return '$' + raw.toFixed(2);
        if (m.unit === '$/MMBtu') return '$' + raw.toFixed(2);
        if (m.unit === 'rate') return raw.toFixed(4);
        if (m.unit === 'ratio') return raw.toFixed(4);
        return String(raw);
    }

    function hexToRgba(hex, alpha) {
        const r = parseInt(hex.slice(1, 3), 16);
        const g = parseInt(hex.slice(3, 5), 16);
        const b = parseInt(hex.slice(5, 7), 16);
        return `rgba(${r},${g},${b},${alpha})`;
    }

    // ─── Init on DOM ready ───
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => { bindChangeToggle(); init(); });
    } else {
        bindChangeToggle();
        init();
    }
})();
