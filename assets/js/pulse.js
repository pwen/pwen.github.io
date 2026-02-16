/* ─── Pulse.js — Interactive thesis tracker ─── */

(function () {
    'use strict';

    const BASE = '/assets/data/pulse';
    let thesesData = null;
    let metricsData = null;
    let activeThesis = 'all'; // 'all' or a thesis id
    let currentYear = 2026;

    const CATEGORY_FILES = [
        'currencies', 'rates', 'liquidity', 'metals',
        'energy', 'equities', 'sentiment', 'em'
    ];

    // ─── Bootstrap ───
    async function init() {
        const yearSelect = document.getElementById('pulse-year');
        if (yearSelect) {
            yearSelect.addEventListener('change', e => {
                currentYear = parseInt(e.target.value);
                loadYear(currentYear);
            });
        }
        await loadYear(currentYear);
    }

    async function loadYear(year) {
        try {
            // Load theses + all category metric files in parallel
            const thesesResp = fetch(`${BASE}/theses-${year}.json`).then(r => r.json());
            const metricFetches = CATEGORY_FILES.map(cat =>
                fetch(`${BASE}/${cat}.json`).then(r => r.json())
            );
            const [thesesResult, ...metricResults] = await Promise.all([thesesResp, ...metricFetches]);

            thesesData = thesesResult;

            // Merge category files into single metricsData
            metricsData = { updated: null, metrics: {} };
            for (const catData of metricResults) {
                if (catData.updated && (!metricsData.updated || catData.updated > metricsData.updated)) {
                    metricsData.updated = catData.updated;
                }
                Object.assign(metricsData.metrics, catData.metrics);
            }

            // Also fetch thesis markdown bodies
            await loadThesisBodies(thesesData.theses);

            renderUpdated();
            renderTheses();
            renderDashboard();
            renderReflection();
            waitForChartsAndInjectDots();
        } catch (err) {
            console.error('Failed to load Pulse data:', err);
        }
    }

    async function loadThesisBodies(theses) {
        const fetches = theses.map(async t => {
            try {
                // Fetch the Jekyll-rendered thesis page
                // The markdown files in _pulse/ won't be rendered as pages by default,
                // so we embed the body directly from the JSON or use inline content.
                // For now, fetch the raw markdown and do a simple conversion.
                const resp = await fetch(`/pulse-content/${currentYear}/${currentYear}-${t.id}.md`);
                if (resp.ok) {
                    const text = await resp.text();
                    // Strip front matter
                    const body = text.replace(/^---[\s\S]*?---\s*/, '');
                    t.body = markdownToHtml(body);
                } else {
                    t.body = null;
                }
            } catch {
                t.body = null;
            }
        });
        await Promise.all(fetches);
    }

    // Simple markdown → HTML (handles ##, **, *, -, em)
    function markdownToHtml(md) {
        return md
            .split('\n\n')
            .map(block => {
                block = block.trim();
                if (!block) return '';

                // Headings
                if (block.startsWith('## ')) {
                    return `<h2>${inline(block.slice(3))}</h2>`;
                }

                // Bullet list
                if (block.match(/^[-*] /m)) {
                    const items = block.split('\n')
                        .filter(l => l.match(/^[-*] /))
                        .map(l => `<li>${inline(l.replace(/^[-*] /, ''))}</li>`)
                        .join('');
                    return `<ul>${items}</ul>`;
                }

                // Paragraph
                return `<p>${inline(block.replace(/\n/g, ' '))}</p>`;
            })
            .join('\n');
    }

    function inline(text) {
        return text
            .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.+?)\*/g, '<em>$1</em>')
            .replace(/`(.+?)`/g, '<code>$1</code>');
    }

    // ─── Render "Updated" timestamp ───
    function renderUpdated() {
        const el = document.getElementById('pulse-updated');
        if (!el || !metricsData?.updated) return;
        const d = new Date(metricsData.updated);
        el.textContent = `Last updated: ${d.toLocaleDateString('en-US', {
            month: 'short', day: 'numeric', year: 'numeric'
        })}`;
    }

    function thesisTitle(id) {
        if (!thesesData) return id;
        const t = thesesData.theses.find(th => th.id === id);
        return t ? t.title : id;
    }

    // ─── Floating tooltip for thesis dots ───
    let dotTooltipEl = null;
    function ensureDotTooltip() {
        if (dotTooltipEl) return dotTooltipEl;
        dotTooltipEl = document.createElement('div');
        dotTooltipEl.className = 'dot-tooltip';
        document.body.appendChild(dotTooltipEl);
        return dotTooltipEl;
    }

    function showDotTooltip(dot) {
        const tip = ensureDotTooltip();
        const thesisId = dot.dataset.thesis;
        tip.textContent = thesisTitle(thesisId);
        const rect = dot.getBoundingClientRect();
        tip.style.left = `${rect.left + rect.width / 2}px`;
        tip.style.top = `${rect.top - 4}px`;
        tip.style.transform = 'translate(-50%, -100%)';
        tip.classList.add('visible');
    }

    function hideDotTooltip() {
        if (dotTooltipEl) dotTooltipEl.classList.remove('visible');
    }

    function setActiveThesis(thesis) {
        // Toggle: clicking the same thesis again goes back to "all"
        if (activeThesis === thesis) thesis = 'all';
        activeThesis = thesis;

        // Update thesis card states
        document.querySelectorAll('.thesis-card').forEach(card => {
            if (thesis === 'all') {
                card.classList.remove('dimmed', 'highlighted', 'selected');
            } else if (card.dataset.thesis === thesis) {
                card.classList.remove('dimmed');
                card.classList.add('highlighted', 'selected');
            } else {
                card.classList.add('dimmed');
                card.classList.remove('highlighted', 'selected');
            }
        });

        // Update charts.js metric row states
        const thesesObj = thesis !== 'all'
            ? thesesData.theses.find(t => t.id === thesis)
            : null;

        document.querySelectorAll('.chart-metric-row').forEach(row => {
            const metricId = row.dataset.metric;
            // Also affect the expand panel below the row
            const expandEl = document.getElementById(`expand-${metricId}`);
            if (thesis === 'all') {
                row.classList.remove('thesis-dimmed', 'thesis-highlighted');
                if (expandEl) expandEl.classList.remove('thesis-dimmed', 'thesis-highlighted');
            } else if (thesesObj && thesesObj.metrics.includes(metricId)) {
                row.classList.remove('thesis-dimmed');
                row.classList.add('thesis-highlighted');
                if (expandEl) { expandEl.classList.remove('thesis-dimmed'); expandEl.classList.add('thesis-highlighted'); }
            } else {
                row.classList.add('thesis-dimmed');
                row.classList.remove('thesis-highlighted');
                if (expandEl) { expandEl.classList.add('thesis-dimmed'); expandEl.classList.remove('thesis-highlighted'); }
            }
        });

        // Also dim/undim category headers if all their metrics are dimmed
        document.querySelectorAll('.chart-category').forEach(cat => {
            const rows = cat.querySelectorAll('.chart-metric-row');
            const allDimmed = Array.from(rows).every(r => r.classList.contains('thesis-dimmed'));
            const header = cat.querySelector('.chart-category-header');
            if (thesis === 'all') {
                if (header) header.classList.remove('thesis-dimmed');
            } else if (allDimmed) {
                if (header) header.classList.add('thesis-dimmed');
            } else {
                if (header) header.classList.remove('thesis-dimmed');
            }
        });
    }

    // ─── Inject thesis dots into charts.js metric rows ───
    function injectThesisDots() {
        const rows = document.querySelectorAll('.chart-metric-row[data-metric]');
        if (rows.length === 0) return false; // charts not rendered yet

        rows.forEach(row => {
            // Skip if dots already injected
            if (row.querySelector('.thesis-dots')) return;

            const metricId = row.dataset.metric;
            const related = thesesData.theses.filter(t => t.metrics.includes(metricId));

            // Always inject a dots container (even if empty) so all rows have consistent column widths
            const dotsWrap = document.createElement('span');
            dotsWrap.className = 'thesis-dots';
            related.forEach(t => {
                const dot = document.createElement('span');
                dot.className = 'thesis-dot';
                dot.style.background = t.color;
                dot.dataset.thesis = t.id;
                dot.addEventListener('mouseenter', () => showDotTooltip(dot));
                dot.addEventListener('mouseleave', hideDotTooltip);
                dot.addEventListener('click', e => {
                    e.stopPropagation();
                    setActiveThesis(t.id);
                });
                dotsWrap.appendChild(dot);
            });

            // Insert dots after the data section
            const dataEl = row.querySelector('.chart-metric-data');
            if (dataEl) {
                dataEl.after(dotsWrap);
            } else {
                row.appendChild(dotsWrap);
            }
        });
        return true;
    }

    function waitForChartsAndInjectDots() {
        if (injectThesisDots()) return;
        // Charts not rendered yet — observe DOM for changes
        const observer = new MutationObserver(() => {
            if (injectThesisDots()) observer.disconnect();
        });
        const container = document.getElementById('charts-categories');
        if (container) {
            observer.observe(container, { childList: true, subtree: true });
        }
        // Safety timeout
        setTimeout(() => observer.disconnect(), 10000);
    }

    // ─── Render Thesis Cards ───
    function renderTheses() {
        const container = document.getElementById('pulse-theses');
        if (!container) return;

        container.innerHTML = thesesData.theses.map(t => `
      <div class="thesis-card" data-thesis="${t.id}" style="border-left-color:${t.color}">
        <div class="thesis-card-header">
          <span class="thesis-icon">${t.icon}</span>
          <div class="thesis-header-text">
            <span class="thesis-title">${t.title}</span>
            <span class="thesis-summary">${t.summary}</span>
          </div>
          <span class="thesis-toggle">▶</span>
        </div>
        <div class="thesis-body">
          ${t.body || `<p>${t.summary}</p>`}
        </div>
      </div>
    `).join('');

        // Click header text → filter dashboard; click toggle arrow → expand/collapse
        container.querySelectorAll('.thesis-card-header').forEach(header => {
            const card = header.closest('.thesis-card');
            const id = card.dataset.thesis;

            // Clicking the toggle arrow expands/collapses
            header.querySelector('.thesis-toggle').addEventListener('click', e => {
                e.stopPropagation();
                card.classList.toggle('expanded');
            });

            // Clicking the header text filters dashboard
            header.querySelector('.thesis-header-text').addEventListener('click', () => {
                setActiveThesis(id);
            });
        });
    }

    // ─── Render Dashboard ───
    let modalChart = null; // track active chart instance for cleanup

    function renderDashboard() {
        const container = document.getElementById('pulse-dashboard');
        if (!container) return;

        // Collect all unique metrics across all theses
        const metricIds = [];
        const seen = new Set();
        thesesData.theses.forEach(t => {
            t.metrics.forEach(m => {
                if (!seen.has(m)) {
                    seen.add(m);
                    metricIds.push(m);
                }
            });
        });

        // Table header
        let html = `<div class="metric-table-head">
            <span class="mt-col mt-name">NAME</span>
            <span class="mt-col mt-value">LATEST</span>
            <span class="mt-col mt-change">YTD</span>
            <span class="mt-col mt-dots"></span>
        </div>`;

        // Table rows
        html += metricIds.map(mId => {
            const m = metricsData.metrics[mId];
            if (!m) return '';

            const relatedTheses = thesesData.theses.filter(t => t.metrics.includes(mId));
            const displayValue = formatValue(m);
            const changeText = formatChangeText(m);
            const changeDir = formatChangeDir(m);

            const dotsHtml = relatedTheses.map(t =>
                `<span class="metric-dot" style="background:${t.color}" data-thesis="${t.id}"></span>`
            ).join('');

            const infoHtml = m.description
                ? `<span class="metric-info" data-description="${m.description.replace(/"/g, '&quot;')}">ⓘ</span>`
                : '';

            return `
            <div class="metric-row" data-metric="${mId}">
                <span class="mt-col mt-name">${m.name}${infoHtml}</span>
                <span class="mt-col mt-value">${displayValue}</span>
                <span class="mt-col mt-change ${changeDir}">${changeText}</span>
                <span class="mt-col mt-dots">${dotsHtml}</span>
            </div>`;
        }).join('');

        container.innerHTML = html;

        // Row click → open chart modal
        container.querySelectorAll('.metric-row').forEach(row => {
            row.addEventListener('click', () => {
                openChartModal(row.dataset.metric);
            });
        });

        // Dot click → filter by thesis (stop propagation so row click doesn't fire)
        container.querySelectorAll('.metric-dot').forEach(dot => {
            dot.addEventListener('click', e => {
                e.stopPropagation();
                setActiveThesis(dot.dataset.thesis);
            });
            dot.addEventListener('mouseenter', () => showDotTooltip(dot));
            dot.addEventListener('mouseleave', hideDotTooltip);
        });

        // Info icon → stop propagation
        container.querySelectorAll('.metric-info').forEach(info => {
            info.addEventListener('click', e => e.stopPropagation());
        });
    }

    // ─── Chart Modal ───
    function openChartModal(metricId) {
        const m = metricsData.metrics[metricId];
        if (!m || !m.spark) return;

        const modal = document.getElementById('chart-modal');
        const title = document.getElementById('chart-modal-title');
        const subtitle = document.getElementById('chart-modal-subtitle');
        const canvas = document.getElementById('chart-modal-canvas');
        if (!modal || !canvas) return;

        title.textContent = m.name;
        const changeText = formatChangeText(m);
        const changeDir = formatChangeDir(m);
        subtitle.innerHTML = `<span class="modal-value">${formatValue(m)}</span> <span class="metric-change ${changeDir}">${changeText}</span>`;

        // Destroy previous chart
        if (modalChart) { modalChart.destroy(); modalChart = null; }

        const color = m.direction === 'up' ? '#2d9a5d' : m.direction === 'down' ? '#d94040' : '#888';

        modalChart = new Chart(canvas, {
            type: 'line',
            data: {
                labels: m.spark.map((_, i) => i),
                datasets: [{
                    data: m.spark,
                    borderColor: color,
                    borderWidth: 2,
                    pointRadius: 0,
                    pointHoverRadius: 4,
                    pointHoverBackgroundColor: color,
                    fill: {
                        target: 'origin',
                        above: color + '18',
                        below: color + '18'
                    },
                    tension: 0.3
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        enabled: true,
                        callbacks: {
                            label: ctx => formatValue({ ...m, value: ctx.parsed.y }),
                            title: () => ''
                        }
                    }
                },
                scales: {
                    x: { display: false },
                    y: {
                        display: true,
                        position: 'right',
                        grid: { color: '#f0f0f0' },
                        ticks: { font: { size: 11 }, color: '#999' }
                    }
                },
                interaction: {
                    intersect: false,
                    mode: 'index'
                },
                animation: { duration: 300 }
            }
        });

        modal.classList.add('active');
        document.body.style.overflow = 'hidden';
    }

    function closeChartModal() {
        const modal = document.getElementById('chart-modal');
        if (modal) modal.classList.remove('active');
        document.body.style.overflow = '';
        if (modalChart) { modalChart.destroy(); modalChart = null; }
    }

    function formatValue(m) {
        const v = m.value;
        if (m.unit === '$/oz' || m.unit === '$') return `$${v.toLocaleString()}`;
        if (m.unit === '$/bbl') return `$${v.toFixed(2)}`;
        if (m.unit === '$/lb') return `$${v.toFixed(2)}`;
        if (m.unit === '$T') return `$${v}T`;
        if (m.unit === '%') return `${v}%`;
        if (m.unit === '% YoY' || m.unit === '% QoQ') return `${v}%`;
        if (m.unit === 'ratio') return v.toFixed(2);
        if (m.unit === 'rate') return v.toFixed(2);
        if (m.unit === 'index') return v.toLocaleString();
        return v.toString();
    }

    function formatChangeText(m) {
        if (m.change_ytd_pct != null) {
            const sign = m.change_ytd_pct > 0 ? '+' : '';
            return `${sign}${m.change_ytd_pct.toFixed(1)}%`;
        }
        if (m.change_ytd_bp != null) {
            const sign = m.change_ytd_bp > 0 ? '+' : '';
            return `${sign}${m.change_ytd_bp}bp`;
        }
        return '—';
    }

    function formatChangeDir(m) {
        let val = m.change_ytd_pct ?? m.change_ytd_bp;
        if (val == null && m.history && m.history.length >= 2) {
            // Fallback: compute from history
            const jan1 = new Date(new Date().getFullYear(), 0, 1);
            let closest = null, closestDiff = Infinity;
            for (const [dateStr, v] of m.history) {
                const diff = Math.abs(new Date(dateStr) - jan1);
                if (diff < closestDiff) { closestDiff = diff; closest = v; }
            }
            if (closest != null && closest !== 0) {
                val = m.value - closest;
            }
        }
        val = val ?? 0;
        return val > 0 ? 'up' : val < 0 ? 'down' : 'flat';
    }

    // Sparkline removed — charts now live in modal popup

    // ─── Reflection (for past years) ───
    function renderReflection() {
        const container = document.getElementById('pulse-reflection');
        const content = document.getElementById('pulse-reflection-content');
        if (!container || !content) return;

        if (thesesData.reflection) {
            container.style.display = 'block';
            content.innerHTML = `<div class="pulse-reflection-content">${markdownToHtml(thesesData.reflection)}</div>`;
        } else {
            container.style.display = 'none';
        }
    }

    // ─── Init on DOM ready ───
    function bindModalClose() {
        const modal = document.getElementById('chart-modal');
        if (!modal) return;
        // Close on backdrop click
        modal.addEventListener('click', e => {
            if (e.target === modal) closeChartModal();
        });
        // Close on × button
        const btn = modal.querySelector('.chart-modal-close');
        if (btn) btn.addEventListener('click', closeChartModal);
        // Close on Escape
        document.addEventListener('keydown', e => {
            if (e.key === 'Escape') closeChartModal();
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => { bindModalClose(); init(); });
    } else {
        bindModalClose();
        init();
    }

})();
