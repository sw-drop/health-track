const API_BASE = '/api';

// State
let currentTimeRange = '1M';
let currentTab = 'Overview';
let allAvailableMetrics = [];
let chartInstances = {};

// Categories
const OVERVIEW_METRICS = ['BodyMass', 'StepCount', 'HeartRate', 'SleepAnalysis_AsleepCore', 'ActiveEnergyBurned'];

const CATEGORY_MAP = {
    'Activity': ['StepCount', 'ActiveEnergyBurned', 'BasalEnergyBurned', 'AppleExerciseTime', 'DistanceWalkingRunning', 'FlightsClimbed', 'PhysicalEffort'],
    'Sleep': ['SleepAnalysis_AsleepCore', 'SleepAnalysis_AsleepDeep', 'SleepAnalysis_AsleepREM', 'SleepAnalysis_Awake', 'SleepAnalysis_InBed', 'SleepAnalysis_AsleepUnspecified', 'AppleSleepingBreathingDisturbances', 'TimeInDaylight'],
    'Vitals': ['HeartRate', 'RestingHeartRate', 'HeartRateVariabilitySDNN', 'OxygenSaturation', 'RespiratoryRate', 'VO2Max'],
    'Mobility': ['WalkingSpeed', 'WalkingStepLength', 'WalkingAsymmetryPercentage', 'WalkingDoubleSupportPercentage', 'AppleWalkingSteadiness', 'StairAscentSpeed', 'StairDescentSpeed', 'WalkingHeartRateAverage'],
    'Body': ['BodyMass', 'BodyMassIndex', 'BodyFatPercentage', 'LeanBodyMass', 'Height'],
    'Stand': ['AppleStandTime', 'AppleStandHour_Stood', 'AppleStandHour_Idle'],
    'Environment': ['EnvironmentalAudioExposure', 'HeadphoneAudioExposure', 'EnvironmentalSoundReduction']
};

const getCategoryForMetric = (metric) => {
    for (const [cat, metrics] of Object.entries(CATEGORY_MAP)) {
        if (metrics.includes(metric)) return cat;
    }
    return 'Other';
};

const formatMetricName = (type) => {
    return type.replace(/_/g, ' ').replace(/([A-Z])/g, ' $1').trim();
};

const commonOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { display: false } },
    scales: {
        x: {
            type: 'time',
            time: { tooltipFormat: 'PP' },
            grid: { display: false, drawBorder: false },
            ticks: { color: '#999', maxRotation: 0 }
        },
        y: {
            grid: { color: '#f0f0f0', drawBorder: false },
            ticks: { color: '#999' },
            beginAtZero: false
        }
    },
    elements: {
        point: { radius: 0, hitRadius: 10, hoverRadius: 4 },
        line: { tension: 0.4 }
    },
    spanGaps: true
};

const sageGreen = '#8da399';
const sageGreenLight = 'rgba(141, 163, 153, 0.2)';

// Authentication
function showPinScreen() {
    document.getElementById('pin-overlay').style.display = 'flex';
    document.getElementById('main-content').style.display = 'none';
}

function hidePinScreen() {
    document.getElementById('pin-overlay').style.display = 'none';
    document.getElementById('main-content').style.display = 'block';
}

async function fetchWithPin(url) {
    const pin = localStorage.getItem('health_pin') || '';
    const res = await fetch(url, {
        headers: { 'X-PIN': pin }
    });
    if (res.status === 401) {
        showPinScreen();
        throw new Error('Unauthorized');
    }
    return res;
}

document.getElementById('pin-submit').addEventListener('click', async () => {
    const pin = document.getElementById('pin-input').value;
    localStorage.setItem('health_pin', pin);
    document.getElementById('pin-error').textContent = '';
    
    try {
        await initDashboard();
    } catch (e) {
        document.getElementById('pin-error').textContent = 'Incorrect PIN';
        localStorage.removeItem('health_pin');
    }
});

// Auto-submit PIN on Enter
document.getElementById('pin-input').addEventListener('keypress', (e) => {
    if (e.key === 'Enter') document.getElementById('pin-submit').click();
});

async function initDashboard() {
    setupEventListeners();
    try {
        const res = await fetchWithPin(`${API_BASE}/metrics`);
        const rawMetrics = await res.json();
        
        // Explicitly hide metrics the user doesn't want to track
        allAvailableMetrics = rawMetrics.filter(m => m !== 'Height');
        
        hidePinScreen(); // Success
        document.getElementById('loading').style.display = 'none';
        renderCurrentTab();
    } catch (e) {
        if (e.message !== 'Unauthorized') {
            document.getElementById('loading').innerHTML = 'Error loading metrics: ' + e.message;
        }
        throw e; // RE-THROW so the caller knows it failed!
    }
}

function setupEventListeners() {
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            e.target.classList.add('active');
            currentTab = e.target.dataset.tab;
            renderCurrentTab();
        });
    });

    document.querySelectorAll('.time-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            document.querySelectorAll('.time-btn').forEach(b => b.classList.remove('active'));
            e.target.classList.add('active');
            currentTimeRange = e.target.dataset.range;
            renderCurrentTab();
        });
    });
}

function renderCurrentTab() {
    const grid = document.getElementById('dashboard-grid');
    grid.innerHTML = ''; // Clear grid

    // Destroy old charts to save memory
    for (const id in chartInstances) {
        chartInstances[id].destroy();
        delete chartInstances[id];
    }

    let metricsToRender = [];
    if (currentTab === 'Overview') {
        metricsToRender = OVERVIEW_METRICS.filter(m => allAvailableMetrics.includes(m));
    } else {
        metricsToRender = allAvailableMetrics.filter(m => getCategoryForMetric(m) === currentTab);
    }

    if (currentTab === 'Sleep') {
        grid.insertAdjacentHTML('beforeend', `
            <div class="panel" style="grid-column: 1 / -1; display: flex; justify-content: space-around; align-items: center; padding: 2rem; background: linear-gradient(135deg, #2f4b7c, #003f5c); color: white; border-radius: 12px;">
                <div style="text-align: center;">
                    <div style="font-size: 1rem; opacity: 0.8; margin-bottom: 0.5rem; text-transform: uppercase; letter-spacing: 1px;">Total Sleep Time</div>
                    <div id="sleep-summary-total" style="font-size: 2.5rem; font-weight: 600;">--</div>
                </div>
                <div style="text-align: center;">
                    <div style="font-size: 1rem; opacity: 0.8; margin-bottom: 0.5rem; text-transform: uppercase; letter-spacing: 1px;">Sleep Score</div>
                    <div id="sleep-summary-score" style="font-size: 2.5rem; font-weight: 600;">--/100</div>
                </div>
            </div>
            <div class="panel" style="grid-column: 1 / -1;">
                <div class="panel-title">Chronological Sleep Phases</div>
                <div class="chart-container" style="height: 400px;">
                    <canvas id="sleep-segments-chart"></canvas>
                </div>
            </div>
        `);
        renderSleepSegmentsChart('sleep-segments-chart');
        fetchAndRenderSleepSummary();
    }

    if (metricsToRender.length === 0 && currentTab !== 'Sleep') {
        grid.innerHTML = '<div style="color:#999; padding:2rem;">No metrics found for this category.</div>';
        return;
    }

    for (const metric of metricsToRender) {
        const panelId = `chart-${metric}`;
        const title = formatMetricName(metric);
        
        const panelHtml = `
            <div class="panel">
                <div class="panel-title">${title}</div>
                <div class="panel-value-container">
                    <div class="panel-value" id="val-${metric}">--</div>
                    <div class="trend-indicator trend-neutral" id="trend-${metric}">--</div>
                </div>
                <div class="chart-container">
                    <canvas id="${panelId}"></canvas>
                </div>
            </div>
        `;
        grid.insertAdjacentHTML('beforeend', panelHtml);
        fetchDataAndRender(metric, panelId);
    }
}

async function fetchAndRenderSleepSummary() {
    try {
        const res = await fetchWithPin(`${API_BASE}/sleep/summary`);
        const result = await res.json();
        
        if (result.total_sleep_mins) {
            const hrs = Math.floor(result.total_sleep_mins / 60);
            const mins = result.total_sleep_mins % 60;
            document.getElementById('sleep-summary-total').textContent = `${hrs}h ${mins}m`;
        } else {
            document.getElementById('sleep-summary-total').textContent = 'No Data';
        }
        
        if (result.score) {
            document.getElementById('sleep-summary-score').textContent = `${result.score}/100`;
            
            // Add a subtitle showing the date of the score
            if (result.date) {
                const dateEl = document.createElement('div');
                dateEl.style.fontSize = '0.8rem';
                dateEl.style.opacity = '0.7';
                dateEl.style.marginTop = '0.5rem';
                dateEl.textContent = `for ${result.date}`;
                document.getElementById('sleep-summary-score').appendChild(dateEl);
            }
        } else {
            document.getElementById('sleep-summary-score').textContent = 'No Data';
        }
    } catch (e) {
        console.error('Failed to load sleep summary', e);
        document.getElementById('sleep-summary-total').textContent = 'Error';
        document.getElementById('sleep-summary-score').textContent = 'Error';
    }
}

async function renderSleepSegmentsChart(canvasId) {
    try {
        const res = await fetchWithPin(`${API_BASE}/sleep/segments?range=${currentTimeRange}`);
        const result = await res.json();
        const segments = result.data;

        if (!segments || segments.length === 0) {
            return;
        }

        const colors = {
            'Deep': '#003f5c',
            'Core': '#2f4b7c',
            'REM': '#665191',
            'Awake': '#ff7c43',
            'Unspecified': '#a05195'
        };

        const datasets = {};
        for (const key of Object.keys(colors)) {
            datasets[key] = {
                label: key,
                data: [],
                backgroundColor: colors[key],
                borderSkipped: false,
                barPercentage: 1.0,
                categoryPercentage: 0.8
            };
        }

        segments.forEach(seg => {
            // Filter out the large overarching Apple Health blocks that hide the detailed phases
            if (seg.state === 'Unspecified' || seg.state === 'Asleep') {
                return;
            }

            // X-axis: the "Sleep Session Date"
            const dStart = new Date(seg.start * 1000);
            if (dStart.getHours() < 12) {
                dStart.setDate(dStart.getDate() - 1); // Attribute post-midnight sleep to previous night
            }
            dStart.setHours(0,0,0,0);
            const xDate = dStart.getTime();

            // Y-axis: time of day relative to a dummy date (e.g. year 2000)
            // We want 8PM to be at the bottom, 12PM to be at the top
            const yMin = new Date(seg.start * 1000);
            const yMax = new Date(seg.stop * 1000);

            const mapTimeToDummyDate = (dateObj) => {
                const dummy = new Date(2000, 0, 1, dateObj.getHours(), dateObj.getMinutes(), dateObj.getSeconds());
                if (dateObj.getHours() < 12) {
                    dummy.setDate(2); // Next morning belongs to the next day sequentially
                }
                return dummy.getTime();
            };

            const state = datasets[seg.state] ? seg.state : 'Unspecified';
            if (datasets[state]) {
                datasets[state].data.push({
                    x: xDate,
                    y: [mapTimeToDummyDate(yMin), mapTimeToDummyDate(yMax)]
                });
            }
        });

        // Filter out empty datasets
        const activeDatasets = Object.values(datasets).filter(ds => ds.data.length > 0);

        chartInstances[canvasId] = new Chart(document.getElementById(canvasId), {
            type: 'bar',
            data: { datasets: activeDatasets },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: true, position: 'top' },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const y = context.raw.y;
                                const min = new Date(y[0]).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
                                const max = new Date(y[1]).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
                                return `${context.dataset.label}: ${min} - ${max}`;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        type: 'time',
                        time: { unit: 'day', tooltipFormat: 'PP' },
                        offset: true,
                        grid: { display: false },
                        ticks: { color: '#999' },
                        stacked: true // Force datasets into the exact same column footprint
                    },
                    y: {
                        type: 'time',
                        time: {
                            unit: 'hour',
                            displayFormats: { hour: 'h a' },
                            tooltipFormat: 'h:mm a'
                        },
                        grid: { color: '#f0f0f0' },
                        ticks: { color: '#999' },
                        min: new Date(2000, 0, 1, 20, 0, 0).getTime(), // 8 PM
                        max: new Date(2000, 0, 2, 12, 0, 0).getTime(), // 12 PM
                        reverse: false // 8 PM at bottom, 12 PM at top
                    }
                }
            }
        });
    } catch (e) {
        console.error('Failed to load sleep segments', e);
    }
}

async function fetchDataAndRender(metric, canvasId) {
    try {
        const res = await fetchWithPin(`${API_BASE}/data/${metric}?range=${currentTimeRange}`);
        const result = await res.json();
        const dataPoints = result.data;
        const unit = result.unit || '';

        const trendEl = document.getElementById(`trend-${metric}`);

        if (!dataPoints || dataPoints.length === 0) {
            document.getElementById(`val-${metric}`).textContent = 'No Data';
            trendEl.style.display = 'none';
            return;
        }

        const latestVal = dataPoints[dataPoints.length - 1].value;
        const isBar = ['StepCount', 'ActiveEnergyBurned', 'FlightsClimbed', 'AppleStandTime'].includes(metric);
        
        // Formatting Display Value
        let displayVal = latestVal;
        let displayUnit = unit;
        if (unit === 'min' && latestVal > 60) {
            displayVal = latestVal / 60.0;
            displayUnit = 'hr';
        }
        if (displayVal % 1 !== 0) displayVal = displayVal.toFixed(1);
        document.getElementById(`val-${metric}`).textContent = `${displayVal} ${displayUnit}`;

        // Trend Calculation
        if (dataPoints.length > 1) {
            const previousData = dataPoints.slice(0, -1);
            const prevAvg = previousData.reduce((sum, p) => sum + p.value, 0) / previousData.length;
            const diff = latestVal - prevAvg;
            
            let diffDisplay = diff;
            let diffUnit = unit;
            if (unit === 'min' && Math.abs(diff) > 60) {
                diffDisplay = diff / 60.0;
                diffUnit = 'hr';
            }
            if (diffDisplay % 1 !== 0) diffDisplay = diffDisplay.toFixed(1);

            // Inverse logic for metrics where lower is better (Heart Rate, BMI, Fat %)
            const lowerIsBetter = ['HeartRate', 'RestingHeartRate', 'BodyMass', 'BodyFatPercentage'].some(m => metric.includes(m));

            if (diff > 0) {
                trendEl.textContent = `↑ ${Math.abs(diffDisplay)} ${diffUnit} avg`;
                trendEl.className = lowerIsBetter ? 'trend-indicator trend-down' : 'trend-indicator trend-up';
            } else if (diff < 0) {
                trendEl.textContent = `↓ ${Math.abs(diffDisplay)} ${diffUnit} avg`;
                trendEl.className = lowerIsBetter ? 'trend-indicator trend-up' : 'trend-indicator trend-down';
            } else {
                trendEl.textContent = `→ Flat`;
                trendEl.className = 'trend-indicator trend-neutral';
            }
        } else {
            trendEl.style.display = 'none';
        }

        const chartData = dataPoints.map(p => ({ x: new Date(p.time), y: p.value }));

        chartInstances[canvasId] = new Chart(document.getElementById(canvasId), {
            type: isBar ? 'bar' : 'line',
            data: {
                datasets: [{
                    data: chartData,
                    borderColor: sageGreen,
                    backgroundColor: isBar ? sageGreen : sageGreenLight,
                    fill: !isBar,
                    borderWidth: isBar ? 0 : 2,
                    borderRadius: isBar ? 4 : 0
                }]
            },
            options: commonOptions
        });
    } catch (e) {
        console.error(`Failed to load data for ${metric}`, e);
    }
}

document.addEventListener('DOMContentLoaded', initDashboard);
