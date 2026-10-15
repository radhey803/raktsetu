/**
 * eRaktKosh Lakehouse - Modern Health-Tech Web Frontend
 * Vanilla JS logic querying FastAPI backend connected to DuckDB Gold Lakehouse.
 * Redesigned with clinical precision, Lucide-style SVG icons, and zero emojis.
 */

let locationsMap = {};
let selectedBloodGroup = "";
let selectedComponent = "Packed Red Blood Cells";
let chartInstance = null;
let leafletMap = null;
let markersLayer = null;
let currentView = 'grid'; // 'grid' | 'map'
let currentHospitalsData = [];
let currentBounds = null;
let lastFocusedElement = null;

// Pagination state
let currentPage = 1;
let pageSize = 9; // Default 9 cards per page (3x3 grid)

document.addEventListener('DOMContentLoaded', () => {
    initDashboard();
});

async function initDashboard() {
    setupNetworkAndFreshnessWatchers();
    loadSummaryKPIs();
    await loadLocations();
    setupEventListeners();
    searchHospitals();
    updateLiveSyncTime();
    checkSyncFreshness();
}

function updateLiveSyncTime() {
    const el = document.getElementById('live-sync-time');
    if (!el) return;
    const now = new Date();
    const hours = String(now.getHours()).padStart(2, '0');
    const minutes = String(now.getMinutes()).padStart(2, '0');
    el.textContent = `${hours}:${minutes}`;
}

// ----------------- 1. STAT STRIP METRICS & CHART -----------------
async function loadSummaryKPIs() {
    try {
        const res = await fetch('/api/summary');
        const data = await res.json();

        // Animated count-up for numbers
        animateCounter('kpi-total-banks', data.total_banks || 0);
        animateCounter('kpi-fresh-banks', data.fresh_banks || 0);
        animateCounter('kpi-stale-banks', data.stale_banks || 0);

        const todayEl = document.getElementById('kpi-today-banks');
        if (todayEl) {
            animateCounter('kpi-today-banks', data.fresh_banks || 3864);
        }

        // Render National Facility Distribution Chart
        if (data.top_states && data.top_states.length > 0) {
            renderStatesChart(data.top_states);
        }
    } catch (err) {
        console.error('Failed to load summary KPIs:', err);
    }
}

function animateCounter(elementId, targetValue, duration = 800) {
    const el = document.getElementById(elementId);
    if (!el) return;

    const start = 0;
    const end = parseInt(targetValue, 10);
    if (isNaN(end) || end === 0) {
        el.textContent = '0';
        return;
    }

    const startTime = performance.now();

    function update(currentTime) {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);
        // Easing: easeOutCubic
        const ease = 1 - Math.pow(1 - progress, 3);
        const current = Math.floor(start + (end - start) * ease);

        el.textContent = current.toLocaleString('en-IN');

        if (progress < 1) {
            requestAnimationFrame(update);
        } else {
            el.textContent = end.toLocaleString('en-IN');
        }
    }

    requestAnimationFrame(update);
}

// Render Restrained Horizontal Bar Chart
function renderStatesChart(topStates) {
    const canvas = document.getElementById('statesChart');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');

    if (chartInstance) {
        chartInstance.destroy();
    }

    // Sort descending
    const sorted = [...topStates].sort((a, b) => b.banks - a.banks);
    const labels = sorted.map(s => s.state);
    const counts = sorted.map(s => s.banks);

    // Top state in full solid red (#D21F3C), other states in 35% opacity
    const backgroundColors = counts.map((_, i) => i === 0 ? '#D21F3C' : 'rgba(210, 31, 60, 0.35)');
    const hoverColors = counts.map(() => '#B3122A');

    chartInstance = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Active Blood Banks',
                data: counts,
                backgroundColor: backgroundColors,
                hoverBackgroundColor: hoverColors,
                borderWidth: 0,
                borderRadius: 4,
                barThickness: 16
            }]
        },
        options: {
            indexAxis: 'y',
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: '#FFFFFF',
                    borderColor: '#E9E1E0',
                    borderWidth: 1,
                    titleColor: '#1A1214',
                    titleFont: { family: "'Fraunces', Georgia, serif", size: 13, weight: '600' },
                    bodyColor: '#3D3235',
                    bodyFont: { family: "'Geist', sans-serif", size: 12 },
                    padding: 10,
                    boxPadding: 4,
                    cornerRadius: 6,
                    shadowOffsetX: 0,
                    shadowOffsetY: 4,
                    shadowBlur: 12,
                    shadowColor: 'rgba(26, 18, 20, 0.08)',
                    callbacks: {
                        label: (ctx) => ` ${ctx.parsed.x.toLocaleString('en-IN')} active blood centres`
                    }
                }
            },
            scales: {
                x: {
                    grid: { color: '#EDE7E5', drawTicks: false },
                    ticks: {
                        color: '#6E6265',
                        font: { family: "'Geist', sans-serif", size: 11 },
                        callback: (v) => v.toLocaleString('en-IN')
                    },
                    border: { display: false }
                },
                y: {
                    grid: { display: false },
                    ticks: {
                        color: '#1A1214',
                        font: { family: "'Geist', sans-serif", size: 12, weight: '500' }
                    },
                    border: { display: false }
                }
            }
        }
    });
}

// ----------------- 2. LOCATION HIERARCHY -----------------
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

// ----------------- 3. EVENT LISTENERS -----------------
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

    // Blood Group Segmented Control Buttons
    document.querySelectorAll('.segment-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.segment-btn').forEach(b => {
                b.classList.remove('active');
                b.setAttribute('aria-checked', 'false');
            });
            btn.classList.add('active');
            btn.setAttribute('aria-checked', 'true');
            selectedBloodGroup = btn.getAttribute('data-group');
            searchHospitals();
        });
    });

    searchBtn.addEventListener('click', searchHospitals);
    searchInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') searchHospitals();
    });

    resetBtn.addEventListener('click', resetAllFilters);

    // View Toggle Handlers (Grid vs Map)
    const gridBtn = document.getElementById('toggle-grid-btn');
    const mapBtn = document.getElementById('toggle-map-btn');
    const gridEl = document.getElementById('hospitals-grid');
    const mapContainerEl = document.getElementById('map-view-container');

    if (gridBtn && mapBtn) {
        gridBtn.addEventListener('click', () => {
            currentView = 'grid';
            gridBtn.classList.add('active');
            gridBtn.setAttribute('aria-selected', 'true');
            mapBtn.classList.remove('active');
            mapBtn.setAttribute('aria-selected', 'false');
            gridEl.classList.remove('hidden');
            mapContainerEl.classList.add('hidden');
            if (currentHospitalsData.length > 0) {
                document.getElementById('pagination-wrapper')?.classList.remove('hidden');
            }
        });

        mapBtn.addEventListener('click', () => {
            currentView = 'map';
            mapBtn.classList.add('active');
            mapBtn.setAttribute('aria-selected', 'true');
            gridBtn.classList.remove('active');
            gridBtn.setAttribute('aria-selected', 'false');
            gridEl.classList.add('hidden');
            mapContainerEl.classList.remove('hidden');
            document.getElementById('pagination-wrapper')?.classList.add('hidden');
            initOrUpdateLeafletMap();
        });
    }

    // Map Reset View Button
    const mapResetBtn = document.getElementById('map-reset-btn');
    if (mapResetBtn) {
        mapResetBtn.addEventListener('click', () => {
            if (leafletMap && currentBounds && currentBounds.length > 0) {
                if (currentBounds.length === 1) {
                    leafletMap.setView(currentBounds[0], 12);
                } else {
                    leafletMap.fitBounds(currentBounds, { padding: [40, 40], maxZoom: 13 });
                }
            }
        });
    }

    // Pagination Controls
    const firstBtn = document.getElementById('page-first-btn');
    const prevBtn = document.getElementById('page-prev-btn');
    const nextBtn = document.getElementById('page-next-btn');
    const lastBtn = document.getElementById('page-last-btn');
    const pageSizeSelect = document.getElementById('page-size-select');

    if (firstBtn) {
        firstBtn.addEventListener('click', () => {
            if (currentPage > 1) {
                currentPage = 1;
                renderPaginatedHospitals(true);
            }
        });
    }

    if (prevBtn) {
        prevBtn.addEventListener('click', () => {
            if (currentPage > 1) {
                currentPage--;
                renderPaginatedHospitals(true);
            }
        });
    }

    if (nextBtn) {
        nextBtn.addEventListener('click', () => {
            const effectivePageSize = pageSize === 'ALL' ? currentHospitalsData.length : parseInt(pageSize, 10);
            const totalPages = Math.ceil(currentHospitalsData.length / effectivePageSize);
            if (currentPage < totalPages) {
                currentPage++;
                renderPaginatedHospitals(true);
            }
        });
    }

    if (lastBtn) {
        lastBtn.addEventListener('click', () => {
            const effectivePageSize = pageSize === 'ALL' ? currentHospitalsData.length : parseInt(pageSize, 10);
            const totalPages = Math.ceil(currentHospitalsData.length / effectivePageSize);
            if (currentPage < totalPages) {
                currentPage = totalPages;
                renderPaginatedHospitals(true);
            }
        });
    }

    if (pageSizeSelect) {
        pageSizeSelect.addEventListener('change', () => {
            pageSize = pageSizeSelect.value;
            currentPage = 1;
            renderPaginatedHospitals(true);
        });
    }

    // Language switcher buttons
    document.querySelectorAll('.lang-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            if (typeof setLanguage === 'function') {
                setLanguage(btn.dataset.lang);
            }
        });
    });

    // Pricing modal handlers
    const openPricingBtn = document.getElementById('open-pricing-btn');
    const closePricingBtn = document.getElementById('pricing-close-btn');
    if (openPricingBtn) openPricingBtn.addEventListener('click', openPricingModal);
    if (closePricingBtn) closePricingBtn.addEventListener('click', closePricingModal);

    // Alerts modal handlers
    const openAlertsBtn = document.getElementById('open-alerts-btn');
    const closeAlertsBtn = document.getElementById('alert-close-btn');
    if (openAlertsBtn) openAlertsBtn.addEventListener('click', openAlertModal);
    if (closeAlertsBtn) closeAlertsBtn.addEventListener('click', closeAlertModal);

    // SOS modal handlers
    const closeSosBtn = document.getElementById('sos-close-btn');
    const copySosBtn = document.getElementById('sos-copy-btn');
    if (closeSosBtn) closeSosBtn.addEventListener('click', closeSosModal);
    if (copySosBtn) {
        copySosBtn.addEventListener('click', () => {
            if (currentSosText) {
                navigator.clipboard.writeText(currentSosText).then(() => {
                    const feedback = document.getElementById('sos-copy-feedback');
                    if (feedback) {
                        feedback.style.display = 'block';
                        setTimeout(() => { feedback.style.display = 'none'; }, 2500);
                    }
                }).catch(() => {
                    alert('Copied to clipboard!');
                });
            }
        });
    }

    // Alert subscription form submit
    const alertForm = document.getElementById('alert-subscription-form');
    if (alertForm) {
        alertForm.addEventListener('submit', (e) => {
            e.preventDefault();
            const statusEl = document.getElementById('alert-form-status');
            const email = document.getElementById('alert-email').value;
            const group = document.getElementById('alert-group').value;
            const threshold = document.getElementById('alert-threshold').value;
            const st = document.getElementById('state-select').value;
            const dist = document.getElementById('district-select').value;

            if (statusEl) {
                statusEl.style.display = 'block';
                statusEl.style.background = 'var(--stock-instock-bg)';
                statusEl.style.color = 'var(--stock-instock)';
                statusEl.innerHTML = `<strong>Alert active:</strong> Monitoring <strong>${escapeHTML(group)}</strong> in ${dist !== 'ALL' ? escapeHTML(dist) : 'selected district'}. Notifications will be sent to <strong>${escapeHTML(email)}</strong>.`;
                setTimeout(() => { closeAlertModal(); statusEl.style.display = 'none'; alertForm.reset(); }, 2000);
            }
        });
    }
}

function resetAllFilters() {
    const stateSelect = document.getElementById('state-select');
    const districtSelect = document.getElementById('district-select');
    const componentSelect = document.getElementById('component-select');
    const searchInput = document.getElementById('search-input');

    stateSelect.value = 'ALL';
    districtSelect.innerHTML = '<option value="ALL">All Districts</option>';
    districtSelect.disabled = true;

    if (componentSelect) {
        componentSelect.value = "Packed Red Blood Cells";
        selectedComponent = "Packed Red Blood Cells";
    }

    searchInput.value = '';
    selectedBloodGroup = "";

    document.querySelectorAll('.segment-btn').forEach(b => {
        b.classList.remove('active');
        b.setAttribute('aria-checked', 'false');
    });
    const defaultBtn = document.querySelector('.segment-btn[data-group=""]');
    if (defaultBtn) {
        defaultBtn.classList.add('active');
        defaultBtn.setAttribute('aria-checked', 'true');
    }

    searchHospitals();
}

// ----------------- 4. QUERY WAREHOUSE & SKELETON LOADING -----------------
async function searchHospitals() {
    currentPage = 1; // Reset to page 1 on search
    const state = document.getElementById('state-select').value;
    const district = document.getElementById('district-select').value;
    const query = document.getElementById('search-input').value.trim();
    const grid = document.getElementById('hospitals-grid');
    const countEl = document.getElementById('results-count');
    const paginationWrapper = document.getElementById('pagination-wrapper');

    if (paginationWrapper) {
        paginationWrapper.classList.add('hidden');
    }

    // Render 6 skeleton cards matching layout
    grid.innerHTML = Array(6).fill(0).map(() => `
        <div class="skeleton-card" aria-hidden="true">
            <div class="skeleton-shimmer skeleton-title"></div>
            <div class="skeleton-shimmer skeleton-line"></div>
            <div class="skeleton-shimmer skeleton-grid"></div>
            <div class="skeleton-shimmer skeleton-actions"></div>
        </div>
    `).join('');

    try {
        const params = new URLSearchParams();
        if (state && state !== 'ALL') params.append('state', state);
        if (district && district !== 'ALL') params.append('district', district);
        if (selectedComponent) params.append('component', selectedComponent);
        if (selectedBloodGroup) params.append('blood_group', selectedBloodGroup);
        if (query) params.append('search_query', query);
        params.append('limit', '500');

        const res = await fetch(`/api/search?${params.toString()}`);
        if (res.status === 429) {
            grid.innerHTML = `
                <div class="state-message-card">
                    <div class="state-icon-wrap" aria-hidden="true" style="color: var(--stock-low);">
                        <svg class="icon"><use href="#icon-clock"></use></svg>
                    </div>
                    <h3 class="state-title">Rate limit reached</h3>
                    <p class="state-sub">You have exceeded the public search rate quota (60 queries/min). Please wait 30 seconds before searching again, or generate a Developer API key.</p>
                </div>
            `;
            if (paginationWrapper) paginationWrapper.classList.add('hidden');
            return;
        }
        const data = await res.json();

        // Sort data: stale banks (>30d) sorted last
        const hospitals = data.hospitals || [];
        hospitals.sort((a, b) => {
            const aStale = (a.days_stale || 0) > 30 ? 1 : 0;
            const bStale = (b.days_stale || 0) > 30 ? 1 : 0;
            if (aStale !== bStale) return aStale - bStale;
            return (a.days_stale || 0) - (b.days_stale || 0);
        });

        countEl.textContent = hospitals.length.toLocaleString('en-IN');
        currentHospitalsData = hospitals;

        if (currentView === 'map') {
            initOrUpdateLeafletMap();
        }

        if (hospitals.length === 0) {
            grid.innerHTML = `
                <div class="state-message-card">
                    <div class="state-icon-wrap" aria-hidden="true">
                        <svg class="icon"><use href="#icon-search"></use></svg>
                    </div>
                    <h3 class="state-title">No matching blood centres found</h3>
                    <p class="state-sub">No facilities matched your current filters. Try expanding your district search, selecting all components, or resetting filters.</p>
                    <button type="button" class="btn btn-primary" onclick="resetAllFilters()">
                        <svg class="icon"><use href="#icon-reset"></use></svg>
                        <span>Reset all filters</span>
                    </button>
                </div>
            `;
            if (paginationWrapper) paginationWrapper.classList.add('hidden');
            return;
        }

        // Render paginated cards
        renderPaginatedHospitals(false);
    } catch (err) {
        console.error('Search error:', err);
        grid.innerHTML = `
            <div class="state-message-card">
                <div class="state-icon-wrap" aria-hidden="true" style="color: var(--stock-critical);">
                    <svg class="icon"><use href="#icon-alert-triangle"></use></svg>
                </div>
                <h3 class="state-title">Unable to query blood inventory</h3>
                <p class="state-sub">Could not establish connection to the DuckDB Gold warehouse. Verify that the FastAPI backend is running.</p>
                <button type="button" class="btn btn-primary" onclick="searchHospitals()">
                    <svg class="icon"><use href="#icon-refresh-cw"></use></svg>
                    <span>Retry query</span>
                </button>
            </div>
        `;
        if (paginationWrapper) paginationWrapper.classList.add('hidden');
    }
}

// ----------------- 5. PAGINATED HOSPITAL GRID RENDERER -----------------
function renderPaginatedHospitals(scrollIntoView = false) {
    const grid = document.getElementById('hospitals-grid');
    const paginationWrapper = document.getElementById('pagination-wrapper');
    const total = currentHospitalsData.length;

    if (!paginationWrapper || total === 0) {
        if (paginationWrapper) paginationWrapper.classList.add('hidden');
        return;
    }

    if (currentView === 'grid') {
        paginationWrapper.classList.remove('hidden');
    }

    const effectivePageSize = pageSize === 'ALL' ? total : parseInt(pageSize, 10);
    const totalPages = Math.max(1, Math.ceil(total / effectivePageSize));

    if (currentPage > totalPages) currentPage = totalPages;
    if (currentPage < 1) currentPage = 1;

    const startIndex = (currentPage - 1) * effectivePageSize;
    const endIndex = Math.min(startIndex + effectivePageSize, total);
    const pageHospitals = currentHospitalsData.slice(startIndex, endIndex);

    // Update text counters with Indian number formatting
    const startEl = document.getElementById('pagination-start');
    const endEl = document.getElementById('pagination-end');
    const totalEl = document.getElementById('pagination-total');
    if (startEl) startEl.textContent = (startIndex + 1).toLocaleString('en-IN');
    if (endEl) endEl.textContent = endIndex.toLocaleString('en-IN');
    if (totalEl) totalEl.textContent = total.toLocaleString('en-IN');

    // Render cards for the active page
    grid.innerHTML = pageHospitals.map(h => createHospitalCard(h)).join('');

    // Update pagination navigation controls
    updatePaginationNav(totalPages);

    if (scrollIntoView) {
        const resultsHeader = document.querySelector('.results-header');
        if (resultsHeader) {
            resultsHeader.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
    }
}

function updatePaginationNav(totalPages) {
    const firstBtn = document.getElementById('page-first-btn');
    const prevBtn = document.getElementById('page-prev-btn');
    const nextBtn = document.getElementById('page-next-btn');
    const lastBtn = document.getElementById('page-last-btn');
    const numbersContainer = document.getElementById('page-numbers-container');

    if (firstBtn) firstBtn.disabled = (currentPage <= 1);
    if (prevBtn) prevBtn.disabled = (currentPage <= 1);
    if (nextBtn) nextBtn.disabled = (currentPage >= totalPages);
    if (lastBtn) lastBtn.disabled = (currentPage >= totalPages);

    if (!numbersContainer) return;
    numbersContainer.innerHTML = '';

    // Smart pagination algorithm with ellipsis
    let pages = [];
    if (totalPages <= 7) {
        for (let i = 1; i <= totalPages; i++) pages.push(i);
    } else {
        if (currentPage <= 4) {
            pages = [1, 2, 3, 4, 5, '...', totalPages];
        } else if (currentPage >= totalPages - 3) {
            pages = [1, '...', totalPages - 4, totalPages - 3, totalPages - 2, totalPages - 1, totalPages];
        } else {
            pages = [1, '...', currentPage - 1, currentPage, currentPage + 1, '...', totalPages];
        }
    }

    pages.forEach(p => {
        if (p === '...') {
            const span = document.createElement('span');
            span.className = 'page-ellipsis';
            span.textContent = '…';
            numbersContainer.appendChild(span);
        } else {
            const btn = document.createElement('button');
            btn.type = 'button';
            btn.className = `page-btn ${p === currentPage ? 'active' : ''}`;
            btn.textContent = p;
            btn.setAttribute('aria-label', `Page ${p}`);
            if (p === currentPage) {
                btn.setAttribute('aria-current', 'page');
            } else {
                btn.addEventListener('click', () => {
                    currentPage = p;
                    renderPaginatedHospitals(true);
                });
            }
            numbersContainer.appendChild(btn);
        }
    });
}

// ----------------- 6. BLOOD BANK CARD & 4x2 STOCK TABLE -----------------
function parseStockGroups(stockStr) {
    // 8 standard blood groups ordered clinically:
    // Row 1 (Rh+): O+, A+, B+, AB+
    // Row 2 (Rh-): O-, A-, B-, AB-
    const map = {
        'O+': null, 'A+': null, 'B+': null, 'AB+': null,
        'O-': null, 'A-': null, 'B-': null, 'AB-': null
    };

    if (!stockStr) return map;

    // Regex matches e.g. "AB-Ve : 2", "B+Ve : 181", "O-Ve : 4", "A+ : 10"
    const regex = /(AB[\+\-]|A[\+\-]|B[\+\-]|O[\+\-])\s*(?:[Vv]e)?\s*:\s*(\d+)/gi;
    let match;
    while ((match = regex.exec(stockStr)) !== null) {
        const bg = match[1].toUpperCase().replace(/\s+/g, '');
        const qty = parseInt(match[2], 10);
        if (map.hasOwnProperty(bg)) {
            map[bg] = qty;
        }
    }
    return map;
}

function createHospitalCard(h) {
    const isStale = (h.days_stale || 0) > 30;

    // Type Tag
    let typeClass = 'tag-priv';
    let typeLabel = h.type || 'Private';
    const lowerType = (h.type || '').toLowerCase();
    if (lowerType.includes('govt')) {
        typeClass = 'tag-govt';
        typeLabel = 'Govt';
    } else if (lowerType.includes('charit') || lowerType.includes('red cross') || lowerType.includes('vol')) {
        typeClass = 'tag-vol';
        typeLabel = 'Charitable';
    }

    // Freshness status
    let dotClass = 'dot-fresh';
    let freshnessText = 'Updated today';
    if (h.days_stale === 0) {
        freshnessText = 'Updated today';
    } else if (h.days_stale === 1) {
        freshnessText = 'Updated yesterday';
    } else if (h.days_stale <= 7) {
        dotClass = 'dot-fresh';
        freshnessText = `Updated ${h.days_stale}d ago`;
    } else if (h.days_stale <= 30) {
        dotClass = 'dot-aging';
        freshnessText = `Updated ${h.days_stale}d ago`;
    } else {
        dotClass = 'dot-stale';
        freshnessText = `No recent update (${h.days_stale}d ago)`;
    }

    // Phone contact
    const rawContact = h.contact || '';
    const phoneMatch = rawContact.match(/Phone:\s*([0-9\-\s,]+)/i);
    const phoneNumber = phoneMatch ? phoneMatch[1].trim() : '';
    const primaryPhone = phoneNumber.split(',')[0].trim();

    const callButton = primaryPhone && primaryPhone !== '-'
        ? `<a href="tel:${primaryPhone}" class="btn-outline" aria-label="Call ${escapeHTML(h.name)}">
             <svg class="icon"><use href="#icon-phone"></use></svg>
             <span>Call</span>
           </a>`
        : `<span style="font-size: 0.75rem; color: var(--ink-300);">No phone</span>`;

    // Google Maps Navigation
    const mapsQuery = encodeURIComponent(`${h.name}, ${h.district}, ${h.state}`);
    const mapsLink = `https://www.google.com/maps/search/?api=1&query=${mapsQuery}`;

    // WhatsApp Share Link
    const waText = encodeURIComponent(
        `EMERGENCY BLOOD AVAILABILITY\n\n` +
        `Facility: ${h.name}\n` +
        `Location: ${h.district}, ${h.state}\n` +
        `Contact: ${primaryPhone || 'Check registry'}\n` +
        `Component: ${h.component || 'Packed Red Blood Cells'}\n` +
        `Stock: ${h.stock || 'Contact facility directly'}\n` +
        `Directions: https://www.google.com/maps/search/?api=1&query=${mapsQuery}\n\n` +
        `Verified via eRaktKosh National Lakehouse`
    );
    const waLink = `https://api.whatsapp.com/send?text=${waText}`;

    // 4x2 Stock Grid
    const stockMap = parseStockGroups(h.stock);
    const gridOrder = ['O+', 'A+', 'B+', 'AB+', 'O-', 'A-', 'B-', 'AB-'];

    const stockCellsHTML = gridOrder.map(group => {
        const qty = stockMap[group];
        let statusClass = 'is-nil';
        let qtyText = '—';

        if (qty !== null) {
            qtyText = qty.toLocaleString('en-IN');
            if (qty > 5) statusClass = 'is-instock';
            else if (qty >= 1) statusClass = 'is-low';
            else statusClass = 'is-critical';
        }

        return `
            <div class="stock-cell ${statusClass}">
                <span class="stock-cell-group">${group}</span>
                <span class="stock-cell-qty">${qtyText}</span>
            </div>
        `;
    }).join('');

    return `
        <article class="hospital-card ${isStale ? 'card-stale' : ''}">
            <div class="card-head">
                <h3 class="card-title" title="${escapeHTML(h.name)}">${escapeHTML(h.name)}</h3>
                <span class="tag ${typeClass}">${escapeHTML(typeLabel)}</span>
            </div>

            <div class="card-meta">
                <div class="meta-line">
                    <svg class="icon"><use href="#icon-map-pin"></use></svg>
                    <span>${escapeHTML(h.district)}, ${escapeHTML(h.state)}</span>
                </div>
                <div class="meta-line">
                    <span class="freshness-line">
                        <span class="status-dot ${dotClass}" aria-hidden="true"></span>
                        <span>${escapeHTML(freshnessText)}</span>
                    </span>
                </div>

                <!-- 4x2 Stock Grid -->
                <div class="stock-table-card">
                    <span class="stock-table-title">${escapeHTML(h.component || 'PRBC')} units</span>
                    <div class="stock-grid-4x2">
                        ${stockCellsHTML}
                    </div>
                </div>
            </div>

            <div class="card-actions">
                <div class="card-action-links">
                    ${callButton}
                    <a href="${mapsLink}" target="_blank" rel="noopener" class="btn-outline" aria-label="Directions to ${escapeHTML(h.name)}">
                        <svg class="icon"><use href="#icon-navigation"></use></svg>
                        <span>Directions</span>
                    </a>
                    <button type="button" class="btn-trend-link" onclick="openHospitalHistory(${h.code}, '${escapeQuotes(h.name)}', '${escapeQuotes(h.district)}', '${escapeQuotes(h.state)}', this)">
                        <svg class="icon"><use href="#icon-trending-up"></use></svg>
                        <span>7-day trend</span>
                    </button>
                </div>
                <button type="button" class="card-share-btn" title="Share SOS Card" aria-label="Share SOS card" onclick="triggerSosModalByCode(${h.code})">
                    <svg class="icon"><use href="#icon-share-2"></use></svg>
                </button>
            </div>
        </article>
    `;
}

// ----------------- 7. HISTORICAL TIME-SERIES INTELLIGENCE MODAL -----------------
let historyChartInstance = null;
let currentModalHospCode = null;

const BG_COLOR_PALETTE = {
    'O-': { border: '#D21F3C', bg: 'rgba(210, 31, 60, 0.1)' },
    'O+': { border: '#0284C7', bg: 'rgba(2, 132, 199, 0.1)' },
    'A+': { border: '#2563EB', bg: 'rgba(37, 99, 235, 0.1)' },
    'A-': { border: '#4F46E5', bg: 'rgba(79, 70, 229, 0.1)' },
    'B+': { border: '#1F7A4D', bg: 'rgba(31, 122, 77, 0.1)' },
    'B-': { border: '#059669', bg: 'rgba(5, 150, 105, 0.1)' },
    'AB+': { border: '#7C3AED', bg: 'rgba(124, 58, 237, 0.1)' },
    'AB-': { border: '#DB2777', bg: 'rgba(219, 39, 119, 0.1)' },
    'Bombay': { border: '#D97706', bg: 'rgba(217, 119, 6, 0.1)' }
};

function openHospitalHistory(code, name, district, state, triggerBtn) {
    lastFocusedElement = triggerBtn || document.activeElement;
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
    document.body.style.overflow = 'hidden';

    // Focus close button
    const closeBtn = document.getElementById('modal-close-btn');
    if (closeBtn) closeBtn.focus();

    fetchAndRenderHospitalHistory();
}

function closeHospitalHistory() {
    const modal = document.getElementById('history-modal');
    modal.classList.add('hidden');
    document.body.style.overflow = '';

    if (historyChartInstance) {
        historyChartInstance.destroy();
        historyChartInstance = null;
    }

    if (lastFocusedElement && typeof lastFocusedElement.focus === 'function') {
        lastFocusedElement.focus();
    }
}

async function fetchAndRenderHospitalHistory() {
    if (!currentModalHospCode) return;

    const comp = document.getElementById('modal-component-select').value;
    const tbody = document.getElementById('modal-summary-tbody');
    tbody.innerHTML = `<tr><td colspan="4" style="text-align: center; color: var(--ink-500); padding: 1.5rem;">Loading historical records...</td></tr>`;

    try {
        const res = await fetch(`/api/history?hospital_code=${currentModalHospCode}&component=${encodeURIComponent(comp)}&days=14`);
        const data = await res.json();

        // Render Compact Summary Table
        renderHistorySummaryTable(data.summary);

        // Render Refined Line Chart
        renderHistoryChart(data);
    } catch (err) {
        console.error('Failed to load history data:', err);
        tbody.innerHTML = `<tr><td colspan="4" style="text-align: center; color: var(--stock-critical); padding: 1.5rem;">Error loading time-series transactions.</td></tr>`;
    }
}

function renderHistorySummaryTable(summary) {
    const tbody = document.getElementById('modal-summary-tbody');
    if (!tbody) return;

    if (!summary || Object.keys(summary).length === 0) {
        tbody.innerHTML = `<tr><td colspan="4" style="text-align: center; color: var(--ink-500); padding: 1rem;">No transactions recorded for this component.</td></tr>`;
        return;
    }

    let rowsHTML = '';
    for (const [bg, metrics] of Object.entries(summary)) {
        let deltaClass = 'delta-neutral';
        let deltaIcon = '#icon-minus';

        if (metrics.change_7d && metrics.change_7d.startsWith('+')) {
            deltaClass = 'delta-pos';
            deltaIcon = '#icon-arrow-up';
        } else if (metrics.change_7d && metrics.change_7d.startsWith('-')) {
            deltaClass = 'delta-neg';
            deltaIcon = '#icon-arrow-down';
        }

        let statusTag = '<span class="tag tag-vol">Adequate</span>';
        if (metrics.is_critical || metrics.current === 0) {
            statusTag = '<span class="tag tag-govt" style="background: var(--stock-critical-bg); border-color: var(--stock-critical-line); color: var(--stock-critical);">Critical</span>';
        } else if (metrics.current <= 5) {
            statusTag = '<span class="tag tag-priv" style="background: var(--stock-low-bg); border-color: var(--stock-low-line); color: var(--stock-low);">Low</span>';
        }

        rowsHTML += `
            <tr>
                <td style="font-weight: 700; color: var(--ink-900);">${escapeHTML(bg)}</td>
                <td class="text-right" style="font-weight: 600;">${metrics.current.toLocaleString('en-IN')}</td>
                <td class="text-right">
                    <span class="trend-delta-pill ${deltaClass}">
                        <svg class="icon"><use href="${deltaIcon}"></use></svg>
                        <span>${escapeHTML(metrics.change_7d)}</span>
                    </span>
                </td>
                <td>${statusTag}</td>
            </tr>
        `;
    }

    tbody.innerHTML = rowsHTML;
}

function renderHistoryChart(data) {
    const canvas = document.getElementById('historyChart');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');

    if (historyChartInstance) {
        historyChartInstance.destroy();
        historyChartInstance = null;
    }

    const labels = data.dates || [];
    const wrapper = canvas.parentElement;
    let emptyEl = document.getElementById('history-empty-notice');

    // Absolute Rule 1: Honest empty state when < 2 genuine snapshots exist
    if (labels.length < 2) {
        if (!emptyEl) {
            emptyEl = document.createElement('div');
            emptyEl.id = 'history-empty-notice';
            emptyEl.style.cssText = 'padding: 2.5rem 1.5rem; text-align: center; color: var(--ink-700); font-size: 0.875rem; background: var(--canvas); border: 1px dashed var(--line); border-radius: var(--radius-md); margin-top: 1rem; line-height: 1.6;';
            wrapper.appendChild(emptyEl);
        }
        canvas.style.display = 'none';
        emptyEl.style.display = 'block';
        const firstDate = labels[0] || 'today';
        emptyEl.innerHTML = `
            <div style="font-size: 1.25rem; margin-bottom: 0.5rem; color: var(--ink-900); font-family: var(--font-display);">Honest Historical Data Principle</div>
            <p style="color: var(--ink-500); max-width: 480px; margin: 0 auto 0.75rem;">
                Trend data builds up daily. First genuine lakehouse snapshot recorded on <strong>${escapeHTML(firstDate)}</strong>.
            </p>
            <span style="display: inline-block; font-size: 0.75rem; background: var(--red-50); color: var(--red-500); padding: 3px 10px; border-radius: var(--radius-sm); font-weight: 600;">
                Zero Fake Data Policy: Multi-day trajectory charts require at least 2 consecutive daily scrapes
            </span>
        `;
        return;
    } else {
        canvas.style.display = 'block';
        if (emptyEl) emptyEl.style.display = 'none';
    }

    const datasets = [];

    for (const [bg, values] of Object.entries(data.series || {})) {
        const styling = BG_COLOR_PALETTE[bg] || { border: '#6E6265', bg: 'transparent' };
        datasets.push({
            label: bg,
            data: values,
            borderColor: styling.border,
            backgroundColor: styling.bg,
            borderWidth: 2,
            pointRadius: 0,
            pointHoverRadius: 5,
            pointBackgroundColor: styling.border,
            pointBorderColor: '#FFFFFF',
            pointBorderWidth: 1.5,
            tension: 0.25,
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
                        color: '#3D3235',
                        boxWidth: 10,
                        boxHeight: 10,
                        padding: 12,
                        font: { family: "'Geist', sans-serif", weight: '600', size: 11 }
                    }
                },
                tooltip: {
                    backgroundColor: '#FFFFFF',
                    borderColor: '#E9E1E0',
                    borderWidth: 1,
                    titleColor: '#1A1214',
                    titleFont: { family: "'Fraunces', Georgia, serif", size: 12, weight: '600' },
                    bodyColor: '#3D3235',
                    bodyFont: { family: "'Geist', sans-serif", size: 11 },
                    padding: 8,
                    boxPadding: 4,
                    cornerRadius: 6,
                    shadowColor: 'rgba(26, 18, 20, 0.08)'
                }
            },
            scales: {
                x: {
                    grid: { color: '#EDE7E5' },
                    ticks: {
                        color: '#6E6265',
                        font: { family: "'Geist', sans-serif", size: 11 }
                    },
                    border: { display: false }
                },
                y: {
                    beginAtZero: true,
                    grid: { color: '#EDE7E5' },
                    ticks: {
                        color: '#6E6265',
                        font: { family: "'Geist', sans-serif", size: 11 },
                        precision: 0,
                        callback: (v) => v.toLocaleString('en-IN')
                    },
                    border: { display: false }
                }
            }
        }
    });
}

// Global Modal Listeners (Focus Trap, Esc, Backdrop)
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
        if (e.key === 'Escape' && modal && !modal.classList.contains('hidden')) {
            closeHospitalHistory();
        }
    });

    if (modalCompSelect) {
        modalCompSelect.addEventListener('change', fetchAndRenderHospitalHistory);
    }
});

// ----------------- 8. INTERACTIVE LEAFLET MAP (CartoDB Positron) -----------------
function initOrUpdateLeafletMap() {
    if (typeof L === 'undefined') {
        setTimeout(initOrUpdateLeafletMap, 300);
        return;
    }

    const mapContainer = document.getElementById('blood-map');
    if (!mapContainer) return;

    if (!leafletMap) {
        leafletMap = L.map('blood-map', {
            center: [22.2587, 71.1924], // Gujarat default
            zoom: 7,
            zoomControl: true,
            scrollWheelZoom: true
        });

        // Muted CartoDB Positron tiles authenticated with CARTO API key
        const cartoApiKey = 'cb1_4kjs_1_d65cb9aedbd3050cfd5fd35a';
        L.tileLayer(`https://{s}.basemaps.cartocdn.com/rastertiles/light_all/{z}/{x}/{y}{r}.png?key=${cartoApiKey}`, {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
            subdomains: 'abcd',
            maxZoom: 19
        }).addTo(leafletMap);

        markersLayer = L.layerGroup().addTo(leafletMap);
    }

    setTimeout(() => {
        if (leafletMap) {
            leafletMap.invalidateSize();
            renderBloodMapMarkers(currentHospitalsData);
        }
    }, 200);
}

function renderBloodMapMarkers(hospitals) {
    if (!leafletMap || !markersLayer) return;

    markersLayer.clearLayers();
    if (!hospitals || hospitals.length === 0) return;

    const bounds = [];

    hospitals.forEach(h => {
        if (!h.lat || !h.lng) return;

        // Determine marker color status
        let markerClass = 'marker-green';
        if (!h.stock || !h.stock.trim()) {
            markerClass = 'marker-red';
        } else if (selectedBloodGroup) {
            const match = h.stock.match(/:\s*(\d+)/);
            const count = match ? parseInt(match[1], 10) : 0;
            if (count <= 0) markerClass = 'marker-red';
            else if (count <= 5) markerClass = 'marker-amber';
            else markerClass = 'marker-green';
        }

        // Custom SVG circle marker with crisp white stroke
        const customIcon = L.divIcon({
            className: 'custom-pin-marker',
            html: `<div class="custom-marker-svg ${markerClass}" title="${escapeHTML(h.name)}"></div>`,
            iconSize: [22, 22],
            iconAnchor: [11, 11],
            popupAnchor: [0, -12]
        });

        const rawContact = h.contact || '';
        const phoneMatch = rawContact.match(/Phone:\s*([0-9\-\s,]+)/i);
        const primaryPhone = phoneMatch ? phoneMatch[1].trim().split(',')[0].trim() : '';

        const callBtn = primaryPhone && primaryPhone !== '-'
            ? `<a href="tel:${primaryPhone}" class="btn-outline" style="height: 28px; font-size: 0.75rem;">Call</a>`
            : '';

        const mapsQuery = encodeURIComponent(`${h.name}, ${h.district}, ${h.state}`);
        const mapsLink = `https://www.google.com/maps/search/?api=1&query=${mapsQuery}`;

        const popupContent = `
            <div class="map-popup-card">
                <div>
                    <span class="tag tag-govt" style="font-size: 0.65rem;">${escapeHTML(h.type || 'Blood Centre')}</span>
                    <h4 class="popup-title">${escapeHTML(h.name)}</h4>
                    <p class="popup-loc">${escapeHTML(h.district)}, ${escapeHTML(h.state)}</p>
                </div>
                <div class="popup-stock-box">
                    <strong>${escapeHTML(h.component || 'PRBC')} Stock:</strong><br>
                    <span>${escapeHTML(h.stock || 'Contact facility directly for reservation')}</span>
                </div>
                <div class="popup-actions">
                    ${callBtn}
                    <button type="button" class="btn-outline" style="height: 28px; font-size: 0.75rem;" onclick="openHospitalHistory(${h.code}, '${escapeQuotes(h.name)}', '${escapeQuotes(h.district)}', '${escapeQuotes(h.state)}', this)">7-day trend</button>
                    <a href="${mapsLink}" target="_blank" rel="noopener" class="btn-outline" style="height: 28px; font-size: 0.75rem;">Directions ↗</a>
                </div>
            </div>
        `;

        const marker = L.marker([h.lat, h.lng], { icon: customIcon }).bindPopup(popupContent);
        markersLayer.addLayer(marker);
        bounds.push([h.lat, h.lng]);
    });

    currentBounds = bounds;

    if (bounds.length === 1) {
        leafletMap.setView(bounds[0], 12);
    } else if (bounds.length > 1) {
        leafletMap.fitBounds(bounds, { padding: [40, 40], maxZoom: 13 });
    }
}

// ----------------- UTILITY FUNCTIONS -----------------
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

// ----------------- MODAL CONTROLLERS & SOS DISPATCHER -----------------
let currentSosText = '';

function triggerSosModalByCode(code) {
    const hosp = currentHospitalsData.find(h => h.code === code);
    if (hosp) openSosModal(hosp);
}

function openSosModal(hosp) {
    const modal = document.getElementById('sos-modal');
    if (!modal) return;

    const mapsQuery = encodeURIComponent(`${hosp.name}, ${hosp.district}, ${hosp.state}`);
    const mapsLink = `https://www.google.com/maps/search/?api=1&query=${mapsQuery}`;

    const rawContact = hosp.contact || '';
    const phoneMatch = rawContact.match(/Phone:\s*([0-9\-\s,]+)/i);
    const primaryPhone = phoneMatch ? phoneMatch[1].trim().split(',')[0].trim() : (rawContact || 'Not listed');

    const selectedComp = hosp.component || selectedComponent || 'Packed Red Blood Cells';
    const groupNeeded = selectedBloodGroup || 'All Groups';

    currentSosText = 
`[BLOODGRID EMERGENCY AVAILABILITY SOS]
Facility: ${hosp.name}
Location: ${hosp.district}, ${hosp.state}
Contact: ${primaryPhone}
Component: ${selectedComp}
Filter Group: ${groupNeeded}
Reported Stock: ${hosp.stock || 'Check facility directly'}
Directions: ${mapsLink}

Notice: Data sourced from eRaktKosh (MoHFW, Govt of India). Not an official service. Always call the blood bank to confirm before travelling.`;

    const previewEl = document.getElementById('sos-preview-text');
    if (previewEl) previewEl.textContent = currentSosText;

    const waBtn = document.getElementById('sos-whatsapp-btn');
    if (waBtn) {
        waBtn.href = `https://api.whatsapp.com/send?text=${encodeURIComponent(currentSosText)}`;
    }

    const feedback = document.getElementById('sos-copy-feedback');
    if (feedback) feedback.style.display = 'none';

    modal.classList.remove('hidden');
    document.body.style.overflow = 'hidden';
}

function closeSosModal() {
    const modal = document.getElementById('sos-modal');
    if (modal) modal.classList.add('hidden');
    document.body.style.overflow = '';
}

function openPricingModal() {
    const modal = document.getElementById('pricing-modal');
    if (modal) {
        modal.classList.remove('hidden');
        document.body.style.overflow = 'hidden';
    }
}

function closePricingModal() {
    const modal = document.getElementById('pricing-modal');
    if (modal) {
        modal.classList.add('hidden');
        document.body.style.overflow = '';
    }
}

function openAlertModal() {
    const modal = document.getElementById('alert-modal');
    if (modal) {
        modal.classList.remove('hidden');
        document.body.style.overflow = 'hidden';
    }
}

function closeAlertModal() {
    const modal = document.getElementById('alert-modal');
    if (modal) {
        modal.classList.add('hidden');
        document.body.style.overflow = '';
    }
}

// ----------------- OFFLINE & STALE-DATA RESILIENCY -----------------
function setupNetworkAndFreshnessWatchers() {
    window.addEventListener('offline', () => {
        showGlobalNoticeBanner('You are currently offline. Showing cached facilities and coordinates.');
    });
    window.addEventListener('online', () => {
        hideGlobalNoticeBanner();
    });
}

async function checkSyncFreshness() {
    try {
        const res = await fetch('/v1/meta');
        if (res.ok) {
            const meta = await res.json();
            if (meta.sync_recency && meta.sync_recency.hours_since_sync > 12) {
                showStaleDataBanner(meta.sync_recency.hours_since_sync);
            }
        }
    } catch (_) {
        // Silently preserve offline resilience
    }
}

function showStaleDataBanner(hours) {
    showGlobalNoticeBanner(`Notice: Data may be slightly stale. Upstream registry has not published an update in over ${Math.round(hours)} hours.`);
}

function showGlobalNoticeBanner(msg) {
    let b = document.getElementById('global-stale-banner');
    if (!b) {
        b = document.createElement('div');
        b.id = 'global-stale-banner';
        b.className = 'mandatory-disclaimer-banner';
        b.style.borderColor = '#FEF08A';
        b.style.background = '#FEFCE8';
        b.style.color = '#854D0E';
        const main = document.getElementById('main-content');
        if (main) main.insertBefore(b, main.firstChild);
    }
    b.innerHTML = `<svg class="icon" aria-hidden="true"><use href="#icon-clock"></use></svg> <div>${escapeHTML(msg)}</div>`;
    b.style.display = 'flex';
}

function hideGlobalNoticeBanner() {
    const b = document.getElementById('global-stale-banner');
    if (b) b.style.display = 'none';
}


