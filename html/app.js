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

async function initDashboard() {
    setupEventListeners();
    try {
        const res = await fetch(`${API_BASE}/metrics`);
        const rawMetrics = await res.json();
        
        // Explicitly hide metrics the user doesn't want to track
        allAvailableMetrics = rawMetrics.filter(m => m !== 'Height');
        
        document.getElementById('loading').style.display = 'none';
        renderCurrentTab();
    } catch (e) {
        document.getElementById('loading').innerHTML = 'Error loading metrics: ' + e.message;
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

    if (metricsToRender.length === 0) {
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

async function fetchDataAndRender(metric, canvasId) {
    try {
        const res = await fetch(`${API_BASE}/data/${metric}?range=${currentTimeRange}`);
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
