/**
 * eRaktKosh Live Web Application
 * Vanilla JS logic querying FastAPI backend connected to DuckDB Gold Lakehouse.
 */

let locationsMap = {};
let selectedBloodGroup = "";
let selectedComponent = "Packed Red Blood Cells";
let chartInstance = null;

document.addEventListener('DOMContentLoaded', () => {
    initDashboard();
});

async function initDashboard() {
    loadSummaryKPIs();
    await loadLocations();
    setupEventListeners();
    searchHospitals();
}

// 1. Fetch & Populate KPI Metrics and Chart
async function loadSummaryKPIs() {
    try {
        const res = await fetch('/api/summary');
        const data = await res.json();

        document.getElementById('kpi-total-banks').textContent = data.total_banks.toLocaleString();
        document.getElementById('kpi-fresh-banks').textContent = data.fresh_banks.toLocaleString();
        document.getElementById('kpi-stale-banks').textContent = data.stale_banks.toLocaleString();

        // Render Chart.js
        if (data.top_states && data.top_states.length > 0) {
            renderStatesChart(data.top_states);
        }
    } catch (err) {
        console.error('Failed to load summary KPIs:', err);
    }
}

// Render Modern Horizontal Bar Chart
function renderStatesChart(topStates) {
    const ctx = document.getElementById('statesChart').getContext('2d');

    if (chartInstance) {
        chartInstance.destroy();
    }

    const labels = topStates.map(s => s.state);
    const counts = topStates.map(s => s.banks);

    chartInstance = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Active Blood Banks',
                data: counts,
                backgroundColor: 'rgba(239, 68, 68, 0.75)',
                borderColor: '#ef4444',
                borderWidth: 1,
                borderRadius: 6,
                hoverBackgroundColor: 'rgba(239, 68, 68, 0.95)'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: '#0f172a',
                    borderColor: 'rgba(255,255,255,0.1)',
                    borderWidth: 1,
                    titleColor: '#fff',
                    bodyColor: '#cbd5e1'
                }
            },
            scales: {
                x: {
                    grid: { color: 'rgba(255, 255, 255, 0.05)' },
                    ticks: { color: '#94a3b8', font: { family: 'Inter' } }
                },
                y: {
                    grid: { display: false },
                    ticks: { color: '#f8fafc', font: { family: 'Outfit', weight: '600' } }
                }
            }
        }
    });
}

// 2. Fetch Location Hierarchy
async function loadLocations() {
    try {
        const res = await fetch('/api/locations');
        locationsMap = await res.json();

        const stateSelect = document.getElementById('state-select');
        const sortedStates = Object.keys(locationsMap).sort();

        sortedStates.forEach(state => {
            const opt = document.createElement('option');
            opt.value = state;
            opt.textContent = state;
            stateSelect.appendChild(opt);
        });
    } catch (err) {
        console.error('Failed to load locations:', err);
    }
}

// 3. Event Listeners
function setupEventListeners() {
    const stateSelect = document.getElementById('state-select');
    const districtSelect = document.getElementById('district-select');
    const componentSelect = document.getElementById('component-select');
    const searchBtn = document.getElementById('search-btn');
    const resetBtn = document.getElementById('reset-btn');
    const searchInput = document.getElementById('search-input');

    // State Select
    stateSelect.addEventListener('change', () => {
        const selectedState = stateSelect.value;
        districtSelect.innerHTML = '<option value="ALL">All Districts</option>';

        if (selectedState === 'ALL' || !locationsMap[selectedState]) {
            districtSelect.disabled = true;
        } else {
            districtSelect.disabled = false;
            const districts = locationsMap[selectedState].sort();
            districts.forEach(d => {
                const opt = document.createElement('option');
                opt.value = d;
                opt.textContent = d;
                districtSelect.appendChild(opt);
            });
        }
    });

    // Component Dropdown Change
    if (componentSelect) {
        componentSelect.addEventListener('change', () => {
            selectedComponent = componentSelect.value;
            searchHospitals();
        });
    }

    // Blood Group Pills
    document.querySelectorAll('.pill-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.pill-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            selectedBloodGroup = btn.getAttribute('data-group');
            searchHospitals();
        });
    });

    searchBtn.addEventListener('click', searchHospitals);
    searchInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') searchHospitals();
    });

    resetBtn.addEventListener('click', () => {
        stateSelect.value = 'ALL';
        districtSelect.innerHTML = '<option value="ALL">All Districts</option>';
        districtSelect.disabled = true;
        if (componentSelect) {
            componentSelect.value = "Packed Red Blood Cells";
            selectedComponent = "Packed Red Blood Cells";
        }
        searchInput.value = '';
        selectedBloodGroup = "";
        document.querySelectorAll('.pill-btn').forEach(b => b.classList.remove('active'));
        document.querySelector('.pill-btn[data-group=""]').classList.add('active');
        searchHospitals();
    });
}

// 4. Query Facilities & Render Cards
async function searchHospitals() {
    const state = document.getElementById('state-select').value;
    const district = document.getElementById('district-select').value;
    const query = document.getElementById('search-input').value.trim();
    const grid = document.getElementById('hospitals-grid');
    const countEl = document.getElementById('results-count');

    grid.innerHTML = `
        <div class="loading-state">
            <div class="spinner"></div>
            <p>Scanning DuckDB Gold & Silver Lakehouse...</p>
        </div>
    `;

    try {
        const params = new URLSearchParams();
        if (state && state !== 'ALL') params.append('state', state);
        if (district && district !== 'ALL') params.append('district', district);
        if (selectedComponent) params.append('component', selectedComponent);
        if (selectedBloodGroup) params.append('blood_group', selectedBloodGroup);
        if (query) params.append('search_query', query);
        params.append('limit', '60');

        const res = await fetch(`/api/search?${params.toString()}`);
        const data = await res.json();

        countEl.textContent = data.count;

        if (data.count === 0) {
            grid.innerHTML = `
                <div class="empty-state">
                    <h3>No blood banks matched your stock criteria.</h3>
                    <p>Try clearing the blood group filter or expanding your district search.</p>
                </div>
            `;
            return;
        }

        grid.innerHTML = data.hospitals.map(h => createHospitalCard(h)).join('');
    } catch (err) {
        grid.innerHTML = `<div class="empty-state"><p style="color: #ef4444;">Error connecting to API. Ensure FastAPI server is running.</p></div>`;
        console.error('Search error:', err);
    }
}

// 5. Render Individual Hospital Card HTML with Live Stock & WhatsApp Button
function createHospitalCard(h) {
    const isGovt = (h.type || '').toLowerCase().includes('govt');
    const typeBadge = isGovt
        ? `<span class="badge badge-govt">🏛️ ${h.type}</span>`
        : `<span class="badge badge-priv">🏥 ${h.type || 'Private'}</span>`;

    // Freshness Badge
    let freshnessBadge = `<span class="badge badge-fresh">🟢 Fresh (&lt;24h)</span>`;
    if (h.days_stale > 30) {
        freshnessBadge = `<span class="badge badge-stale">🔴 Stale (${h.days_stale}d)</span>`;
    } else if (h.days_stale > 7) {
        freshnessBadge = `<span class="badge badge-aging">🟡 Aging (${h.days_stale}d)</span>`;
    }

    // Clean Phone Contact
    const rawContact = h.contact || '';
    const phoneMatch = rawContact.match(/Phone:\s*([0-9\-\s,]+)/i);
    const phoneNumber = phoneMatch ? phoneMatch[1].trim() : '';

    const callButton = phoneNumber && phoneNumber !== '-'
        ? `<a href="tel:${phoneNumber.split(',')[0].trim()}" class="call-btn">📞 Call: ${phoneNumber.split(',')[0].trim()}</a>`
        : `<span style="font-size: 0.8rem; color: #64748b;">No Phone Listed</span>`;

    // Google Maps Search Link
    const mapsQuery = encodeURIComponent(`${h.name}, ${h.district}, ${h.state}`);
    const mapsLink = `https://www.google.com/maps/search/?api=1&query=${mapsQuery}`;

    // Available Stock Chips
    let stockHTML = '';
    if (h.stock && h.stock.trim()) {
        const stockItems = h.stock.split(',').slice(0, 6).map(item => item.trim()).filter(Boolean);
        if (stockItems.length > 0) {
            stockHTML = `
                <div class="stock-section">
                    <span class="stock-title">📦 ${escapeHTML(h.component || 'Packed Red Blood Cells')} Stock:</span>
                    <div class="stock-pills-list">
                        ${stockItems.map(item => `<span class="stock-chip">🩸 ${escapeHTML(item)}</span>`).join('')}
                    </div>
                </div>
            `;
        }
    }

    // WhatsApp SOS Share Link
    const waText = encodeURIComponent(
        `🚨 EMERGENCY BLOOD AVAILABILITY ALERT 🚨\n\n` +
        `🏥 Facility: ${h.name}\n` +
        `📍 Location: ${h.district}, ${h.state}\n` +
        `📞 Contact: ${phoneNumber || 'Check portal'}\n` +
        `💉 Component: ${h.component || 'Packed Red Blood Cells'}\n` +
        `🩸 Stock: ${h.stock || 'Contact facility directly'}\n` +
        `🗺️ Maps: https://www.google.com/maps/search/?api=1&query=${mapsQuery}\n\n` +
        `Verified via eRaktKosh National Lakehouse`
    );
    const waLink = `https://api.whatsapp.com/send?text=${waText}`;

    return `
        <div class="hospital-card">
            <div>
                <div class="card-top">
                    <h4 class="hosp-title">${escapeHTML(h.name)}</h4>
                    ${typeBadge}
                </div>

                <div class="hosp-meta" style="margin-top: 0.75rem;">
                    <div class="meta-row">
                        <span class="meta-icon">📍</span>
                        <span>${escapeHTML(h.district)}, ${escapeHTML(h.state)}</span>
                    </div>
                    <div class="meta-row">
                        <span class="meta-icon">🏢</span>
                        <span style="font-size: 0.8rem;">${escapeHTML(h.address || 'Address not provided')}</span>
                    </div>
                    <div class="meta-row" style="margin-top: 0.25rem;">
                        <span class="meta-icon">🕒</span>
                        <span style="font-size: 0.75rem;">Status: ${freshnessBadge}</span>
                    </div>
                </div>

                ${stockHTML}
            </div>

            <div class="card-bottom">
                <div style="display: flex; gap: 0.5rem; align-items: center; flex-wrap: wrap;">
                    ${callButton}
                    <button class="trend-btn" onclick="openHospitalHistory(${h.code}, '${escapeQuotes(h.name)}', '${escapeQuotes(h.district)}', '${escapeQuotes(h.state)}')">📈 7-Day Trend</button>
                    <a href="${waLink}" target="_blank" rel="noopener" class="whatsapp-btn" title="Share on WhatsApp">💬 Share</a>
                </div>
                <a href="${mapsLink}" target="_blank" rel="noopener" class="maps-link">📍 Maps ↗</a>
            </div>
        </div>
    `;
}

// ----------------- 6. HISTORICAL TIME-SERIES INTELLIGENCE MODAL -----------------

let historyChartInstance = null;
let currentModalHospCode = null;

const BG_COLOR_PALETTE = {
    'O-': { border: '#ef4444', bg: 'rgba(239, 68, 68, 0.2)' },     // Red (Universal Donor)
    'O+': { border: '#06b6d4', bg: 'rgba(6, 182, 212, 0.2)' },     // Cyan
    'A+': { border: '#3b82f6', bg: 'rgba(59, 130, 246, 0.2)' },    // Blue
    'A-': { border: '#818cf8', bg: 'rgba(129, 140, 248, 0.2)' },   // Indigo
    'B+': { border: '#10b981', bg: 'rgba(16, 185, 129, 0.2)' },    // Emerald
    'B-': { border: '#34d399', bg: 'rgba(52, 211, 153, 0.2)' },    // Mint
    'AB+': { border: '#a855f7', bg: 'rgba(168, 85, 247, 0.2)' },   // Purple
    'AB-': { border: '#ec4899', bg: 'rgba(236, 72, 153, 0.2)' },   // Pink
    'Bombay': { border: '#f59e0b', bg: 'rgba(245, 158, 11, 0.2)' } // Amber (Rare)
};

function openHospitalHistory(code, name, district, state) {
    currentModalHospCode = code;
    const modal = document.getElementById('history-modal');
    document.getElementById('modal-hosp-name').textContent = name;
    document.getElementById('modal-hosp-loc').textContent = `${district}, ${state}`;

    const modalCompSelect = document.getElementById('modal-component-select');
    if (selectedComponent && selectedComponent !== 'ALL') {
        modalCompSelect.value = selectedComponent;
    } else {
        modalCompSelect.value = 'Packed Red Blood Cells';
    }

    modal.classList.remove('hidden');
    fetchAndRenderHospitalHistory();
}

function closeHospitalHistory() {
    const modal = document.getElementById('history-modal');
    modal.classList.add('hidden');
    if (historyChartInstance) {
        historyChartInstance.destroy();
        historyChartInstance = null;
    }
}

async function fetchAndRenderHospitalHistory() {
    if (!currentModalHospCode) return;

    const comp = document.getElementById('modal-component-select').value;
    const summaryContainer = document.getElementById('modal-summary-pills');
    summaryContainer.innerHTML = '<span class="trend-summary-chip chip-neutral">⏳ Loading time-series data...</span>';

    try {
        const res = await fetch(`/api/history?hospital_code=${currentModalHospCode}&component=${encodeURIComponent(comp)}&days=14`);
        const data = await res.json();

        // Render summary pills
        renderHistorySummaryPills(data.summary);

        // Render Line Chart
        renderHistoryChart(data);
    } catch (err) {
        console.error('Failed to load history data:', err);
        summaryContainer.innerHTML = '<span class="trend-summary-chip chip-negative">⚠️ Error loading history records.</span>';
    }
}

function renderHistorySummaryPills(summary) {
    const container = document.getElementById('modal-summary-pills');
    if (!summary || Object.keys(summary).length === 0) {
        container.innerHTML = '<span class="trend-summary-chip chip-neutral">No recorded transactions for this component.</span>';
        return;
    }

    let html = '';
    for (const [bg, metrics] of Object.entries(summary)) {
        let chipClass = 'chip-neutral';
        let icon = '🔹';

        if (metrics.is_critical) {
            chipClass = 'chip-critical';
            icon = '⚠️';
        } else if (metrics.change_7d.startsWith('+')) {
            chipClass = 'chip-positive';
            icon = '📈';
        } else if (metrics.change_7d.startsWith('-')) {
            chipClass = 'chip-negative';
            icon = '📉';
        }

        html += `
            <div class="trend-summary-chip ${chipClass}">
                <span>${icon} <strong>${bg}:</strong> ${metrics.current} units (${metrics.change_7d})</span>
            </div>
        `;
    }
    container.innerHTML = html;
}

function renderHistoryChart(data) {
    const ctx = document.getElementById('historyChart').getContext('2d');
    if (historyChartInstance) {
        historyChartInstance.destroy();
    }

    const labels = data.dates || [];
    const datasets = [];

    for (const [bg, values] of Object.entries(data.series || {})) {
        const styling = BG_COLOR_PALETTE[bg] || { border: '#cbd5e1', bg: 'rgba(203, 213, 225, 0.2)' };
        datasets.push({
            label: `${bg}`,
            data: values,
            borderColor: styling.border,
            backgroundColor: styling.bg,
            borderWidth: 2.5,
            pointRadius: 4,
            pointHoverRadius: 6,
            pointBackgroundColor: styling.border,
            tension: 0.3,
            fill: false
        });
    }

    historyChartInstance = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: datasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: 'index',
                intersect: false
            },
            plugins: {
                legend: {
                    position: 'top',
                    labels: {
                        color: '#94a3b8',
                        boxWidth: 12,
                        padding: 12,
                        font: { family: 'Outfit', weight: '600', size: 11 }
                    }
                },
                tooltip: {
                    backgroundColor: '#0f172a',
                    borderColor: 'rgba(255,255,255,0.15)',
                    borderWidth: 1,
                    titleColor: '#fff',
                    bodyColor: '#cbd5e1',
                    padding: 10,
                    boxPadding: 4
                }
            },
            scales: {
                x: {
                    grid: { color: 'rgba(255, 255, 255, 0.05)' },
                    ticks: { color: '#94a3b8', font: { family: 'Inter' } }
                },
                y: {
                    beginAtZero: true,
                    grid: { color: 'rgba(255, 255, 255, 0.05)' },
                    ticks: {
                        color: '#94a3b8',
                        font: { family: 'Inter' },
                        precision: 0
                    },
                    title: {
                        display: true,
                        text: 'Units Available',
                        color: '#64748b',
                        font: { size: 11 }
                    }
                }
            }
        }
    });
}

// Modal Global Listeners
document.addEventListener('DOMContentLoaded', () => {
    const modal = document.getElementById('history-modal');
    const closeBtn = document.getElementById('modal-close-btn');
    const modalCompSelect = document.getElementById('modal-component-select');

    if (closeBtn) closeBtn.addEventListener('click', closeHospitalHistory);
    if (modal) {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) closeHospitalHistory();
        });
    }
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') closeHospitalHistory();
    });
    if (modalCompSelect) {
        modalCompSelect.addEventListener('change', fetchAndRenderHospitalHistory);
    }
});

function escapeHTML(str) {
    if (!str) return '';
    return str.replace(/[&<>'"]/g,
        tag => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[tag] || tag)
    );
}

function escapeQuotes(str) {
    if (!str) return '';
    return str.replace(/'/g, "\\'").replace(/"/g, '&quot;');
}

