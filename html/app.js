const API_BASE = '/api';

const formatMetricName = (type) => {
    return type.replace(/([A-Z])/g, ' $1').trim();
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
            ticks: { color: '#999' }
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
    try {
        const res = await fetch(`${API_BASE}/metrics`);
        const metrics = await res.json();
        
        document.getElementById('loading').style.display = 'none';
        const grid = document.getElementById('dashboard-grid');

        for (const metric of metrics) {
            const panelId = `chart-${metric}`;
            const title = formatMetricName(metric);
            
            const panelHtml = `
                <div class="panel">
                    <div class="panel-header">
                        <h2 class="panel-title">${title}</h2>
                        <div class="panel-value" id="val-${metric}">--</div>
                    </div>
                    <div class="chart-container">
                        <canvas id="${panelId}"></canvas>
                    </div>
                </div>
            `;
            grid.insertAdjacentHTML('beforeend', panelHtml);
            fetchDataAndRender(metric, panelId);
        }
    } catch (e) {
        document.getElementById('loading').innerHTML = 'Error loading metrics: ' + e.message;
    }
}

async function fetchDataAndRender(metric, canvasId) {
    try {
        const res = await fetch(`${API_BASE}/data/${metric}`);
        const result = await res.json();
        const dataPoints = result.data;
        const unit = result.unit || '';

        if (!dataPoints || dataPoints.length === 0) {
            document.getElementById(`val-${metric}`).textContent = 'No Data';
            return;
        }

        const latestVal = dataPoints[dataPoints.length - 1].value;
        const isBar = ['StepCount', 'ActiveEnergyBurned', 'FlightsClimbed'].includes(metric);
        
        let displayVal = latestVal;
        let displayUnit = unit;

        if (unit === 'min' && latestVal > 60) {
            displayVal = latestVal / 60.0;
            displayUnit = 'hr';
        }

        if (displayVal % 1 !== 0) displayVal = displayVal.toFixed(1);
        document.getElementById(`val-${metric}`).textContent = `${displayVal} ${displayUnit}`;

        const chartData = dataPoints.map(p => ({ x: new Date(p.time), y: p.value }));

        new Chart(document.getElementById(canvasId), {
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
