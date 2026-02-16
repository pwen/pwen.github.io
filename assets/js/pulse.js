/* ─── Pulse.js — Interactive thesis tracker ─── */

(function () {
    'use strict';

    const BASE = '/assets/data/pulse';
    let thesesData = null;
    let metricsData = null;
    let activeThesis = 'all'; // 'all' or a thesis id
    let currentYear = 2026;

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
            const [thesesResp, metricsResp] = await Promise.all([
                fetch(`${BASE}/theses-${year}.json`),
                fetch(`${BASE}/metrics.json`)
            ]);
            thesesData = await thesesResp.json();
            metricsData = await metricsResp.json();

            // Also fetch thesis markdown bodies
            await loadThesisBodies(thesesData.theses);

            renderUpdated();
            renderTheses();
            renderDashboard();
            renderReflection();
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

    function shortTitle(id) {
        const map = {
            'dollar': 'Weak Dollar',
            'china': 'China Ascending',
            'fragmentation': '战国时期',
            'ai': 'AI Boom',
            'hard-assets': 'Hard Assets'
        };
        return map[id] || id;
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

        // Update metric card states
        const thesesObj = thesis !== 'all'
            ? thesesData.theses.find(t => t.id === thesis)
            : null;

        document.querySelectorAll('.metric-card').forEach(card => {
            if (thesis === 'all') {
                card.classList.remove('dimmed', 'highlighted');
            } else if (thesesObj && thesesObj.metrics.includes(card.dataset.metric)) {
                card.classList.remove('dimmed');
                card.classList.add('highlighted');
            } else {
                card.classList.add('dimmed');
                card.classList.remove('highlighted');
            }
        });
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

        container.innerHTML = metricIds.map(mId => {
            const m = metricsData.metrics[mId];
            if (!m) return '';

            // Which theses use this metric?
            const relatedTheses = thesesData.theses.filter(t => t.metrics.includes(mId));

            // Format value
            const displayValue = formatValue(m);

            // Format change
            const changeHtml = formatChange(m);

            // Thesis dots
            const dotsHtml = relatedTheses.map(t =>
                `<span class="metric-dot" style="background:${t.color}" data-tooltip="${shortTitle(t.id)}" data-thesis="${t.id}"></span>`
            ).join('');

            // Info icon (only if description exists)
            const infoHtml = m.description
                ? `<span class="metric-info" data-description="${m.description.replace(/"/g, '&quot;')}">ⓘ</span>`
                : '';

            return `
        <div class="metric-card" data-metric="${mId}">
          <div class="metric-name">${m.name}${infoHtml}</div>
          <div class="metric-value-row">
            <span class="metric-value">${displayValue}</span>
            ${changeHtml}
          </div>
          <canvas class="metric-spark" id="spark-${mId}"></canvas>
          <div class="metric-dots">${dotsHtml}</div>
        </div>`;
        }).join('');

        // Render sparklines
        metricIds.forEach(mId => {
            const m = metricsData.metrics[mId];
            if (m?.spark) renderSparkline(`spark-${mId}`, m.spark, m.direction);
        });

        // Dot click → filter by thesis
        container.querySelectorAll('.metric-dot').forEach(dot => {
            dot.addEventListener('click', e => {
                e.stopPropagation();
                setActiveThesis(dot.dataset.thesis);
            });
        });
    }

    function formatValue(m) {
        const v = m.value;
        if (m.unit === '$/oz' || m.unit === '$') return `$${v.toLocaleString()}`;
        if (m.unit === '$/bbl') return `$${v.toFixed(2)}`;
        if (m.unit === '$/lb') return `$${v.toFixed(2)}`;
        if (m.unit === '$T') return `$${v}T`;
        if (m.unit === '%') return `${v}%`;
        if (m.unit === '% YoY') return `${v}%`;
        if (m.unit === 'ratio') return v.toFixed(2);
        if (m.unit === 'rate') return v.toFixed(2);
        if (m.unit === 'index') return v.toLocaleString();
        return v.toString();
    }

    function formatChange(m) {
        if (m.change_ytd_pct != null) {
            const sign = m.change_ytd_pct > 0 ? '+' : '';
            const dir = m.change_ytd_pct > 0 ? 'up' : m.change_ytd_pct < 0 ? 'down' : 'flat';
            const arrow = m.change_ytd_pct > 0 ? '▲' : m.change_ytd_pct < 0 ? '▼' : '—';
            return `<span class="metric-change ${dir}">${arrow} ${sign}${m.change_ytd_pct.toFixed(1)}% ytd</span>`;
        }
        if (m.change_ytd_bp != null) {
            const sign = m.change_ytd_bp > 0 ? '+' : '';
            const dir = m.change_ytd_bp > 0 ? 'up' : m.change_ytd_bp < 0 ? 'down' : 'flat';
            const arrow = m.change_ytd_bp > 0 ? '▲' : m.change_ytd_bp < 0 ? '▼' : '—';
            return `<span class="metric-change ${dir}">${arrow} ${sign}${m.change_ytd_bp}bp ytd</span>`;
        }
        return '';
    }

    // ─── Sparkline (tiny Chart.js line) ───
    function renderSparkline(canvasId, data, direction) {
        const canvas = document.getElementById(canvasId);
        if (!canvas) return;

        const color = direction === 'up' ? '#2d9a5d' : direction === 'down' ? '#d94040' : '#888';

        new Chart(canvas, {
            type: 'line',
            data: {
                labels: data.map((_, i) => i),
                datasets: [{
                    data: data,
                    borderColor: color,
                    borderWidth: 1.5,
                    pointRadius: 0,
                    fill: {
                        target: 'origin',
                        above: color + '15',
                        below: color + '15'
                    },
                    tension: 0.3
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false }, tooltip: { enabled: false } },
                scales: {
                    x: { display: false },
                    y: { display: false }
                },
                animation: false
            }
        });
    }

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
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();
