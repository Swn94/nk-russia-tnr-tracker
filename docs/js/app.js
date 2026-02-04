/**
 * NK-Russia Human Rights Tracker - Dashboard Application
 */

// Configuration
const CONFIG = {
    apiBaseUrl: 'http://localhost:8000',
    refreshInterval: 60000, // 1 minute
};

// State
let state = {
    cases: [],
    actors: [],
    candidates: [],
    currentSection: 'overview',
};

// Utility Functions
function formatDate(dateString) {
    if (!dateString) return '--';
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
    });
}

function getSeverityClass(score) {
    if (score <= 3) return 'low';
    if (score <= 6) return 'medium';
    return 'high';
}

function truncate(str, length = 50) {
    if (!str) return '';
    return str.length > length ? str.substring(0, length) + '...' : str;
}

// API Functions
async function fetchData(endpoint, params = {}) {
    try {
        const url = new URL(`${CONFIG.apiBaseUrl}${endpoint}`);
        Object.keys(params).forEach(key => {
            if (params[key]) url.searchParams.append(key, params[key]);
        });

        const response = await fetch(url);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        return await response.json();
    } catch (error) {
        console.error(`Error fetching ${endpoint}:`, error);
        return null;
    }
}

// Dashboard Functions
async function loadOverviewStats() {
    // In production, these would be real API calls
    // For demo, using placeholder data
    document.getElementById('total-cases').textContent = '127';
    document.getElementById('total-actors').textContent = '453';
    document.getElementById('sanctions-candidates').textContent = '28';
    document.getElementById('total-evidence').textContent = '1,847';

    // Initialize charts
    initTNRTypeChart();
    initCountryChart();
}

function initTNRTypeChart() {
    const ctx = document.getElementById('tnr-type-chart').getContext('2d');
    new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Direct Attack', 'Co-opting', 'Mobility Controls', 'Threats from Distance'],
            datasets: [{
                data: [35, 28, 22, 42],
                backgroundColor: [
                    '#f56565',
                    '#ed8936',
                    '#ecc94b',
                    '#48bb78',
                ],
                borderWidth: 2,
                borderColor: '#fff',
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    position: 'bottom',
                }
            }
        }
    });
}

function initCountryChart() {
    const ctx = document.getElementById('country-chart').getContext('2d');
    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: ['North Korea', 'Russia', 'China', 'Iran', 'Belarus'],
            datasets: [{
                label: 'Cases',
                data: [45, 38, 22, 15, 7],
                backgroundColor: '#2c5282',
                borderRadius: 4,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    display: false,
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                }
            }
        }
    });
}

async function loadCases() {
    const status = document.getElementById('case-status-filter').value;
    const tnrType = document.getElementById('case-tnr-filter').value;
    const search = document.getElementById('case-search').value;

    // Demo data - replace with actual API call
    const cases = [
        {
            id: '1',
            title: 'Assassination of Kim Jong-nam',
            title_korean: '김정남 암살 사건',
            tnr_type: 'direct_attack',
            country: 'Malaysia',
            date_occurred: '2017-02-13',
            severity_score: 10,
            status: 'documented',
        },
        {
            id: '2',
            title: 'Forced labor in Russia',
            title_korean: '러시아 강제 노동',
            tnr_type: 'mobility_controls',
            country: 'Russia',
            date_occurred: '2023-06-15',
            severity_score: 8,
            status: 'under_investigation',
        },
        {
            id: '3',
            title: 'Defector family threats',
            title_korean: '탈북자 가족 협박',
            tnr_type: 'threats_from_distance',
            country: 'South Korea',
            date_occurred: '2024-01-20',
            severity_score: 7,
            status: 'open',
        },
    ];

    renderCasesTable(cases);
}

function renderCasesTable(cases) {
    const tbody = document.getElementById('cases-tbody');
    tbody.innerHTML = '';

    cases.forEach(c => {
        const severityClass = getSeverityClass(c.severity_score);
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>
                <strong>${truncate(c.title, 40)}</strong>
                ${c.title_korean ? `<br><small style="color: var(--text-muted);">${truncate(c.title_korean, 40)}</small>` : ''}
            </td>
            <td>${formatTNRType(c.tnr_type)}</td>
            <td>${c.country || '--'}</td>
            <td>${formatDate(c.date_occurred)}</td>
            <td>
                <span class="severity">
                    <span class="severity-bar">
                        <span class="severity-fill ${severityClass}" style="width: ${c.severity_score * 10}%"></span>
                    </span>
                    ${c.severity_score}/10
                </span>
            </td>
            <td><span class="status-badge ${c.status}">${formatStatus(c.status)}</span></td>
            <td>
                <button class="btn btn-small" onclick="viewCase('${c.id}')">View</button>
            </td>
        `;
        tbody.appendChild(row);
    });
}

function formatTNRType(type) {
    const types = {
        direct_attack: 'Direct Attack',
        co_opting: 'Co-opting',
        mobility_controls: 'Mobility Controls',
        threats_from_distance: 'Threats from Distance',
    };
    return types[type] || type || '--';
}

function formatStatus(status) {
    const statuses = {
        open: 'Open',
        under_investigation: 'Under Investigation',
        documented: 'Documented',
        closed: 'Closed',
        candidate: 'Candidate',
        proposed: 'Proposed',
        under_review: 'Under Review',
        sanctioned: 'Sanctioned',
    };
    return statuses[status] || status || '--';
}

async function loadActors() {
    const type = document.getElementById('actor-type-filter').value;
    const search = document.getElementById('actor-search').value;

    // Demo data
    const actors = [
        {
            id: '1',
            name: 'Kim Jong Un',
            name_korean: '김정은',
            actor_type: 'perpetrator',
            position: 'Supreme Leader',
            organization: 'Workers Party of Korea',
            nationality: 'North Korea',
        },
        {
            id: '2',
            name: 'Choe Ryong Hae',
            name_korean: '최룡해',
            actor_type: 'perpetrator',
            position: 'President of the Presidium',
            organization: 'Supreme People Assembly',
            nationality: 'North Korea',
        },
        {
            id: '3',
            name: 'Anonymous Defector A',
            name_korean: '탈북자 A',
            actor_type: 'victim',
            position: 'Former factory worker',
            organization: null,
            nationality: 'North Korea',
        },
    ];

    renderActorsGrid(actors);
}

function renderActorsGrid(actors) {
    const grid = document.getElementById('actors-grid');
    grid.innerHTML = '';

    actors.forEach(actor => {
        const card = document.createElement('div');
        card.className = 'actor-card';
        card.innerHTML = `
            <span class="actor-type ${actor.actor_type}">${actor.actor_type}</span>
            <h4>${actor.name}</h4>
            ${actor.name_korean ? `<p style="color: var(--text-muted); font-style: italic;">${actor.name_korean}</p>` : ''}
            ${actor.position ? `<p><strong>Position:</strong> ${actor.position}</p>` : ''}
            ${actor.organization ? `<p><strong>Organization:</strong> ${actor.organization}</p>` : ''}
            <p><strong>Nationality:</strong> ${actor.nationality || 'Unknown'}</p>
            <button class="btn btn-small" onclick="viewActor('${actor.id}')" style="margin-top: 0.5rem;">View Details</button>
        `;
        grid.appendChild(card);
    });
}

async function loadSanctions() {
    const status = document.getElementById('sanction-status-filter').value;
    const priority = document.getElementById('sanction-priority-filter').value;

    // Demo data
    const candidates = [
        {
            id: '1',
            actor_name: 'Kim Jong Un',
            status: 'candidate',
            priority_level: 1,
            evidence_strength_score: 0.95,
            legal_basis: 'Crimes against humanity',
        },
        {
            id: '2',
            actor_name: 'Ministry of State Security',
            status: 'proposed',
            priority_level: 2,
            evidence_strength_score: 0.88,
            legal_basis: 'Systematic torture',
        },
    ];

    renderSanctionsTable(candidates);
}

function renderSanctionsTable(candidates) {
    const tbody = document.getElementById('sanctions-tbody');
    tbody.innerHTML = '';

    candidates.forEach(c => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td><strong>${c.actor_name}</strong></td>
            <td><span class="status-badge ${c.status}">${formatStatus(c.status)}</span></td>
            <td>Priority ${c.priority_level}</td>
            <td>
                <span class="severity">
                    <span class="severity-bar">
                        <span class="severity-fill ${c.evidence_strength_score > 0.7 ? 'high' : c.evidence_strength_score > 0.4 ? 'medium' : 'low'}" style="width: ${c.evidence_strength_score * 100}%"></span>
                    </span>
                    ${(c.evidence_strength_score * 100).toFixed(0)}%
                </span>
            </td>
            <td>${truncate(c.legal_basis, 30)}</td>
            <td>
                <button class="btn btn-small" onclick="viewCandidate('${c.id}')">View</button>
            </td>
        `;
        tbody.appendChild(row);
    });
}

function analyzeChain() {
    const input = document.getElementById('chain-actor-input').value;
    if (!input) return;

    const vizContainer = document.getElementById('chain-viz');
    vizContainer.innerHTML = `
        <div style="text-align: center; width: 100%;">
            <div class="chain-node root">
                <strong>Kim Jong Un</strong><br>
                <small>Supreme Leader</small>
            </div>
            <div style="color: var(--text-muted); margin: 0.5rem 0;">↓</div>
            <div style="display: flex; justify-content: center; gap: 1rem; flex-wrap: wrap;">
                <div class="chain-node">
                    <strong>Choe Ryong Hae</strong><br>
                    <small>President of Presidium</small>
                </div>
                <div class="chain-node">
                    <strong>Kim Tok Hun</strong><br>
                    <small>Premier</small>
                </div>
            </div>
            <div style="color: var(--text-muted); margin: 0.5rem 0;">↓</div>
            <div style="display: flex; justify-content: center; gap: 1rem; flex-wrap: wrap;">
                <div class="chain-node">
                    <strong>Ministry of State Security</strong><br>
                    <small>Entity</small>
                </div>
                <div class="chain-node">
                    <strong>Ministry of People's Security</strong><br>
                    <small>Entity</small>
                </div>
            </div>
        </div>
    `;
}

// View functions (would open modals or navigate to detail pages)
function viewCase(id) {
    console.log('View case:', id);
    alert(`Viewing case ${id} - In production, this would open a detail modal or page`);
}

function viewActor(id) {
    console.log('View actor:', id);
    alert(`Viewing actor ${id} - In production, this would open a detail modal or page`);
}

function viewCandidate(id) {
    console.log('View candidate:', id);
    alert(`Viewing candidate ${id} - In production, this would open a detail modal or page`);
}

// Navigation
function initNavigation() {
    const navLinks = document.querySelectorAll('.nav-link');
    const sections = document.querySelectorAll('.section');

    navLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const targetId = link.getAttribute('href').substring(1);

            // Update active nav
            navLinks.forEach(l => l.classList.remove('active'));
            link.classList.add('active');

            // Show target section
            sections.forEach(s => {
                s.classList.toggle('hidden', s.id !== targetId);
            });

            state.currentSection = targetId;

            // Load section data
            switch (targetId) {
                case 'overview':
                    loadOverviewStats();
                    break;
                case 'cases':
                    loadCases();
                    break;
                case 'actors':
                    loadActors();
                    break;
                case 'sanctions':
                    loadSanctions();
                    break;
            }
        });
    });
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    initNavigation();
    loadOverviewStats();

    // Set last updated time
    document.getElementById('last-updated').textContent = new Date().toLocaleString();

    // Event listeners for filters
    document.getElementById('case-search-btn')?.addEventListener('click', loadCases);
    document.getElementById('case-status-filter')?.addEventListener('change', loadCases);
    document.getElementById('case-tnr-filter')?.addEventListener('change', loadCases);

    document.getElementById('actor-search-btn')?.addEventListener('click', loadActors);
    document.getElementById('actor-type-filter')?.addEventListener('change', loadActors);

    document.getElementById('sanction-status-filter')?.addEventListener('change', loadSanctions);
    document.getElementById('sanction-priority-filter')?.addEventListener('change', loadSanctions);

    document.getElementById('chain-search-btn')?.addEventListener('click', analyzeChain);

    // Refresh data periodically
    setInterval(() => {
        document.getElementById('last-updated').textContent = new Date().toLocaleString();
    }, CONFIG.refreshInterval);
});
