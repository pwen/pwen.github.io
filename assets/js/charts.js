/* ─── Charts.js — Category-grouped metrics with inline charts ─── */

(function () {
    'use strict';

    const BASE = '/assets/data/pulse';
    let metricsData = null;
    let activeChart = null; // currently rendered Chart.js instance
    let expandedMetric = null; // currently expanded metric id

    // ─── Category definitions ───
    const CATEGORIES = [
        {
            id: 'currencies',
            name: 'CURRENCIES',
            icon: '💵',
            metrics: ['dxy', 'eurusd', 'usdcny', 'usd_reserves_share']
        },
        {
            id: 'rates',
            name: 'RATES & YIELDS',
            icon: '🏛️',
            metrics: ['us_10y', 'yield_curve', 'tips_5y', 'breakeven_10y', 'hy_spread']
        },
        {
            id: 'liquidity',
            name: 'LIQUIDITY & FISCAL',
            icon: '🏦',
            metrics: ['fed_balance_sheet', 'debt_to_gdp', 'tga']
        },
        {
            id: 'metals',
            name: 'METALS',
            icon: '⛏️',
            metrics: ['gold', 'silver', 'copper', 'uranium']
        },
        {
            id: 'energy',
            name: 'ENERGY',
            icon: '⛽',
            metrics: ['oil', 'natgas', 'energy_cpi']
        },
        {
            id: 'equities',
            name: 'US EQUITIES & SECTORS',
            icon: '📈',
            metrics: ['sp500', 'qqq', 'smh', 'xlu', 'gsci_spy_ratio']
        },
        {
            id: 'sentiment',
            name: 'SENTIMENT & ALTERNATIVES',
            icon: '🌡️',
            metrics: ['vix', 'btc', 'cb_gold_buying']
        },
        {
            id: 'em',
            name: 'EM & CHINA',
            icon: '🌏',
            metrics: ['csi300', 'hsi', 'kweb', 'china_pmi', 'china_retail_sales', 'eem']
        }
    ];

    // ─── Bootstrap ───
    async function init() {
        try {
            const resp = await fetch(`${BASE}/metrics.json`);
            metricsData = await resp.json();
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
                        ${metricRows}
                    </div>
                </div>
            `;
        }).join('');

        // Bind category collapse/expand
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

        // Bind metric row clicks
        container.querySelectorAll('.chart-metric-row').forEach(row => {
            row.addEventListener('click', () => toggleMetricChart(row.dataset.metric));
        });
    }

    // ─── Single metric row ───
    function renderMetricRow(id, m) {
        const changeText = formatChangeText(m);
        const dir = m.direction === 'up' ? 'up' : 'down';

        return `
            <div class="chart-metric-row" data-metric="${id}">
                <div class="chart-metric-info">
                    <span class="chart-metric-arrow">▸</span>
                    <span class="chart-metric-name">${m.name}</span>
                </div>
                <div class="chart-metric-data">
                    <span class="chart-metric-value">${formatValue(m)}</span>
                    <span class="chart-metric-change ${dir}">${changeText}</span>
                    <span class="chart-metric-icon" title="View chart">📊</span>
                </div>
            </div>
            <div class="chart-metric-expand" id="expand-${id}">
                <div class="chart-metric-desc" id="desc-${id}"></div>
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

        // If already expanded, collapse
        if (expandedMetric === metricId) {
            expandEl.classList.remove('expanded');
            row.classList.remove('active');
            row.querySelector('.chart-metric-arrow').textContent = '▸';
            if (activeChart) { activeChart.destroy(); activeChart = null; }
            expandedMetric = null;
            return;
        }

        // Collapse previous
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

        // Expand new
        expandEl.classList.add('expanded');
        row.classList.add('active');
        row.querySelector('.chart-metric-arrow').textContent = '▾';
        expandedMetric = metricId;

        // Show description
        const m = metricsData.metrics[metricId];
        const descEl = document.getElementById(`desc-${metricId}`);
        if (descEl && m.description) {
            descEl.textContent = m.description;
        }

        // Render chart
        const canvas = document.getElementById(`canvas-${metricId}`);
        if (canvas && m.spark && m.spark.length > 0) {
            renderInlineChart(canvas, m);
        }
    }

    // ─── Render Chart.js inline chart ───
    function renderInlineChart(canvas, m) {
        const ctx = canvas.getContext('2d');
        const data = m.spark;
        const labels = data.map((_, i) => {
            const weeksAgo = data.length - 1 - i;
            if (weeksAgo === 0) return 'Now';
            return `-${weeksAgo}w`;
        });

        const color = m.direction === 'up' ? '#4caf87' : '#e05555';

        activeChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels,
                datasets: [{
                    data,
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
                        backgroundColor: '#1a1a2e',
                        titleColor: '#ccc',
                        bodyColor: '#fff',
                        borderColor: '#333',
                        borderWidth: 1,
                        callbacks: {
                            label: ctx => formatRawValue(ctx.raw, m)
                        }
                    }
                },
                scales: {
                    x: {
                        ticks: { color: '#666', maxTicksLimit: 6, font: { size: 11 } },
                        grid: { color: 'rgba(255,255,255,0.05)' }
                    },
                    y: {
                        ticks: { color: '#666', font: { size: 11 } },
                        grid: { color: 'rgba(255,255,255,0.05)' }
                    }
                },
                interaction: {
                    intersect: false,
                    mode: 'index'
                }
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
        if (m.unit === '$/MMBtu') return `$${v.toFixed(2)}`;
        if (m.unit === '%') return `${v.toFixed(2)}%`;
        if (m.unit === '% spread') return `${v.toFixed(2)}%`;
        if (m.unit === 'rate') return v.toFixed(4);
        if (m.unit === 'ratio') return v.toFixed(2);
        if (m.unit === '%YoY') return `${v.toFixed(1)}%`;
        if (m.unit === 'tonnes/yr') return `${v.toLocaleString()}t`;
        if (typeof v === 'number' && v > 1000) return v.toLocaleString(undefined, { maximumFractionDigits: 2 });
        if (typeof v === 'number') return v.toFixed(2);
        return String(v);
    }

    function formatChangeText(m) {
        if (m.change_ytd_bp != null) return `${m.change_ytd_bp > 0 ? '+' : ''}${m.change_ytd_bp}bp YTD`;
        if (m.change_ytd_pct != null) return `${m.change_ytd_pct > 0 ? '+' : ''}${m.change_ytd_pct}% YTD`;
        if (m.change_1d != null) return `${m.change_1d > 0 ? '+' : ''}${m.change_1d.toFixed(2)} 1D`;
        return '';
    }

    function formatRawValue(raw, m) {
        if (m.unit === '%' || m.unit === '% spread' || m.unit === '%YoY') return raw.toFixed(2) + '%';
        if (m.unit === '$/oz' || m.unit === '$') return '$' + raw.toLocaleString();
        if (m.unit === '$T') return '$' + raw + 'T';
        if (m.unit === '$B') return '$' + raw + 'B';
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
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
