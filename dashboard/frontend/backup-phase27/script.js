// AquaGuard Dashboard JavaScript

// Backend API configuration.
// The dashboard is served from a static server during development;
// the FastAPI backend runs on the port listed here.
const API_BASE_URL = "http://localhost:8000";

// Demonstration readings used only when the backend is reachable and
// returns a valid response. These are clearly labeled as simulated
// measurements, NOT real sensor data.
const SIMULATED_READINGS = {
    ph: 7.2,
    dissolved_oxygen: 6.5,
    ammonia: 0.1,
    temperature: 26.0
};

// Tab switching functionality
function switchTab(tabName) {
    // Hide all tab sections
    document.querySelectorAll('.tab').forEach(function(tab) {
        tab.classList.remove('active');
    });
    // Show selected section
    const target = document.getElementById(tabName);
    if (target) target.classList.add('active');
    // Update bottom tab buttons
    document.querySelectorAll('#tabs button').forEach(function(btn) {
        btn.classList.remove('active');
    });
    const btn = document.querySelector('#tabs button[onclick*="\'' + tabName + '\'"]');
    if (btn) btn.classList.add('active');
}

// Marketplace functionality
function openMarketplace() {
    switchTab('marketplace');
    loadMarketplaceData();
}

// Dashboard functionality
function openDashboard() {
    switchTab('monitoring');
    loadDashboardData();
}

// Alerts functionality
function openAlerts() {
    switchTab('alerts');
    loadAlertsData();
}

function setErrorMessage(message) {
    const el = document.getElementById('connection-error');
    if (el) {
        el.textContent = message;
        el.style.display = 'block';
    }
}

function clearErrorMessage() {
    const el = document.getElementById('connection-error');
    if (el) {
        el.textContent = '';
        el.style.display = 'none';
    }
}

function setLoading(isLoading) {
    const el = document.getElementById('loading-indicator');
    if (el) {
        el.style.display = isLoading ? 'block' : 'none';
    }
}

// Load dashboard data from the FastAPI backend.
// Uses POST /water-quality with clearly labeled demonstration readings.
async function loadDashboardData() {
    clearErrorMessage();
    setLoading(true);

    try {
        const url = new URL(API_BASE_URL + "/water-quality");
        url.searchParams.append("ph", SIMULATED_READINGS.ph);
        url.searchParams.append("dissolved_oxygen", SIMULATED_READINGS.dissolved_oxygen);
        url.searchParams.append("ammonia", SIMULATED_READINGS.ammonia);
        url.searchParams.append("temperature", SIMULATED_READINGS.temperature);
        url.searchParams.append("farm_id", "demo-farm-001");

        const response = await fetch(url.toString(), {
            method: "POST",
            headers: { "Content-Type": "application/json" },
        });

        if (!response.ok) {
            throw new Error("HTTP " + response.status + " - " + response.statusText);
        }

        const data = await response.json();
        const analysis = data.analysis || {};
        const readings = data.readings || SIMULATED_READINGS;

        // Update metric cards with backend-submitted values.
        // These remain demonstration values (not real sensor measurements).
        const phEl = document.getElementById('ph-value');
        if (phEl) phEl.textContent = readings.ph + " (Normal)";

        const doeEl = document.getElementById('doe-value');
        if (doeEl) doeEl.textContent = readings.dissolved_oxygen + " mg/L (Good)";

        const ammoniaEl = document.getElementById('ammonia-value');
        if (ammoniaEl) ammoniaEl.textContent = readings.ammonia + " mg/L (Safe)";

        const tempEl = document.getElementById('temp-value');
        if (tempEl) tempEl.textContent = readings.temperature + "°C (Optimal)";

        // Update risk badge with backend-calculated assessment.
        const riskBadge = document.getElementById('risk-level');
        if (riskBadge) {
            const level = analysis.risk_level ? analysis.risk_level.toUpperCase() : "LOW";
            riskBadge.textContent = level;
            riskBadge.className = 'badge ' + (analysis.risk_level || 'low');
        }

        // Render recommendations if the element exists.
        const recEl = document.getElementById('recommendations');
        if (recEl && Array.isArray(analysis.recommendations)) {
            recEl.innerHTML = analysis.recommendations.map(function(r) {
                return '<li>' + r + '</li>';
            }).join('');
        }

        // Show risk score if present.
        const scoreEl = document.getElementById('risk-score');
        if (scoreEl && typeof analysis.risk_score !== 'undefined') {
            scoreEl.textContent = analysis.risk_score + "/8";
        }

    } catch (err) {
        console.error("Failed to load dashboard data:", err);
        setErrorMessage("Connection error: backend unavailable (" + err.message + "). " +
            "Displaying last known demonstration readings only.");
    } finally {
        setLoading(false);
    }
}

// Load alerts data
function loadAlertsData() {
    const listEl = document.getElementById('alerts-list');
    const loadingEl = document.getElementById('alerts-loading');
    const errorEl = document.getElementById('alerts-error');
    if (listEl) listEl.innerHTML = '';
    if (loadingEl) loadingEl.style.display = 'block';
    if (errorEl) { errorEl.style.display = 'none'; errorEl.textContent = ''; }

    const apiUrl = API_BASE_URL + "/alerts/demo-farm-001";
    fetch(apiUrl, { method: 'GET' })
        .then(function(res) {
            if (!res.ok) throw new Error('HTTP ' + res.status);
            return res.json();
        })
        .then(function(data) {
            if (loadingEl) loadingEl.style.display = 'none';
            if (!Array.isArray(data) || data.length === 0) {
                if (listEl) listEl.innerHTML = '<li style="color:#aaa;">No alerts recorded for this farm.</li>';
                return;
            }
            if (listEl) {
                listEl.innerHTML = data.map(function(a) {
                    return '<li><strong>' + (a.severity || 'Unknown') + '</strong> — ' + (a.disease || 'N/A') +
                        ': ' + (a.message || '') + '</li>';
                }).join('');
            }
        })
        .catch(function(err) {
            if (loadingEl) loadingEl.style.display = 'none';
            if (errorEl) { errorEl.textContent = 'Backend unavailable: ' + err.message; errorEl.style.display = 'block'; }
            if (listEl) listEl.innerHTML = '<li style="color:#aaa;">Unable to load alerts.</li>';
        });
}

// Load marketplace data
function loadMarketplaceData() {
    // Simulate marketplace data
    const marketplace = {
        price: '₹45/kg',
        demand: 'High',
        nearbyBuyers: 3
    };

    const marketplaceContainer = document.getElementById('marketplace');
    if (marketplaceContainer) {
        marketplaceContainer.innerHTML = `
            <h3>Market Prices</h3>
            <p>Current price: ${marketplace.price}</p>
            <p>Demand: ${marketplace.demand}</p>
            <p>Nearby buyers: ${marketplace.nearbyBuyers}</p>
        `;
    }
}

// Initialize dashboard
// If the backend is reachable we fetch real analysis; otherwise we rely
// on clearly labeled demonstration values and show an error message.
document.addEventListener('DOMContentLoaded', () => {
    loadDashboardData();
});