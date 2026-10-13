/**
 * eRaktKosh Live Web Application
 * Vanilla JS logic querying FastAPI backend connected to DuckDB Gold Lakehouse.
 */

let locationsMap = {};
let selectedBloodGroup = "";
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
    let query = document.getElementById('search-input').value.trim();
    const grid = document.getElementById('hospitals-grid');
    const countEl = document.getElementById('results-count');

    // If blood group pill selected, append to search query
    if (selectedBloodGroup) {
        query = query ? `${query} ${selectedBloodGroup}` : selectedBloodGroup;
    }

    grid.innerHTML = `
        <div class="loading-state">
            <div class="spinner"></div>
            <p>Scanning DuckDB Gold Tables...</p>
        </div>
    `;

    try {
        const params = new URLSearchParams();
        if (state && state !== 'ALL') params.append('state', state);
        if (district && district !== 'ALL') params.append('district', district);
        if (query) params.append('search_query', query);
        params.append('limit', '60');

        const res = await fetch(`/api/search?${params.toString()}`);
        const data = await res.json();

        countEl.textContent = data.count;

        if (data.count === 0) {
            grid.innerHTML = `
                <div class="empty-state">
                    <h3>No blood banks matched your search criteria.</h3>
                    <p>Try selecting a broader district or clearing the text search.</p>
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

// 5. Render Individual Hospital Card HTML
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
            </div>

            <div class="card-bottom">
                ${callButton}
                <a href="${mapsLink}" target="_blank" rel="noopener" class="maps-link">📍 View on Maps ↗</a>
            </div>
        </div>
    `;
}

function escapeHTML(str) {
    if (!str) return '';
    return str.replace(/[&<>'"]/g,
        tag => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[tag] || tag)
    );
}
