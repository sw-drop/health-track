let fullData = [];
let charts = {}; // Store chart instances to destroy them on update
let isAuthorized = false;
let pinCode = "";

const API_URL = '/api/data';

async function refreshData() {
    try {
        const response = await fetch(API_URL);
        if (!response.ok) throw new Error('Failed to load data');
        
        const rawData = await response.json();
        const HEIGHT_M = 1.8542; // 6'1"
        fullData = rawData.sort((a, b) => a.timestamp - b.timestamp).map(d => {
            if (!d.bmi && d.weight_kg) {
                d.bmi = parseFloat((d.weight_kg / (HEIGHT_M * HEIGHT_M)).toFixed(1));
            }
            return d;
        });
        
        if (fullData.length === 0) {
            console.warn("No data available");
            return;
        }

        const activeBtn = document.querySelector('.time-filter.active');
        const activeRange = activeBtn ? activeBtn.getAttribute('data-range') : '90';
        renderCharts(activeRange);

        if (isAuthorized) {
            populateTable();
        }
    } catch (error) {
        console.error("Error loading dashboard data:", error);
    }
}

document.addEventListener('DOMContentLoaded', async () => {
    await refreshData();

    // Setup filter buttons
    const buttons = document.querySelectorAll('.time-filter');
    buttons.forEach(btn => {
        btn.addEventListener('click', (e) => {
            // Update active state
            buttons.forEach(b => b.classList.remove('active'));
            e.target.classList.add('active');
            
            // Render charts for range
            const range = e.target.getAttribute('data-range');
            renderCharts(range);
        });
    });
});

function renderCharts(daysStr) {
    let dataToRender = fullData;

    if (daysStr !== 'all') {
        const days = parseInt(daysStr, 10);
        // timestamp is in seconds
        const cutoffTime = Math.floor(Date.now() / 1000) - (days * 24 * 60 * 60);
        dataToRender = fullData.filter(d => d.timestamp >= cutoffTime);
    }

    if (dataToRender.length === 0) {
        // Fallback to latest item if no data in range
        dataToRender = [fullData[fullData.length - 1]];
    }

    // Extract arrays
    const labels = dataToRender.map(d => d.timestamp * 1000);
    const weights = dataToRender.map(d => {
        if (!isAuthorized && d.weight_kg !== undefined && d.weight_kg !== null) {
            return parseFloat((d.weight_kg - 85).toFixed(1));
        }
        return d.weight_kg;
    });
    const bodyFats = dataToRender.map(d => (d.body_fat && d.body_fat > 0) ? d.body_fat : null);
    const bmis = dataToRender.map(d => (d.bmi && d.bmi > 0) ? d.bmi : null);
    const visceralFats = dataToRender.map(d => (d.visceral_fat && d.visceral_fat > 0) ? d.visceral_fat : null);

    // Helper to find most recent valid metric
    const findLatest = (arr, key) => {
        for(let i = arr.length - 1; i >= 0; i--) {
            if(arr[i][key] !== undefined && arr[i][key] !== null) {
                return arr[i][key];
            }
        }
        return '--';
    };

    const curWeight = findLatest(dataToRender, 'weight_kg');
    const curFat = findLatest(dataToRender, 'body_fat');
    const curBmi = findLatest(dataToRender, 'bmi');
    const curVisceral = findLatest(dataToRender, 'visceral_fat');

    let weightText = '-- kg';
    if (curWeight !== '--') {
        if (isAuthorized) {
            weightText = `${curWeight} kg`;
        } else {
            const offsetWeight = (curWeight - 85).toFixed(1);
            weightText = offsetWeight > 0 ? `+${offsetWeight} kg` : `${offsetWeight} kg`;
        }
    }
    document.getElementById('current-weight').textContent = weightText;
    document.getElementById('current-body-fat').textContent = curFat !== '--' ? `${curFat}%` : '--%';
    document.getElementById('current-bmi').textContent = curBmi;
    document.getElementById('current-visceral').textContent = curVisceral !== '--' ? curVisceral : '--';

    // Chart defaults
    Chart.defaults.font.family = "'Inter', sans-serif";
    Chart.defaults.color = "#64748b";

    // Destroy existing charts if any
    Object.keys(charts).forEach(key => {
        if (charts[key]) charts[key].destroy();
    });

    // Helper to create gradient
    const createGradient = (ctx, colorStart, colorEnd) => {
        const gradient = ctx.createLinearGradient(0, 0, 0, 400);
        gradient.addColorStop(0, colorStart);
        gradient.addColorStop(1, colorEnd);
        return gradient;
    };

    // 1. Main Weight Chart
    const ctxWeight = document.getElementById('weightChart').getContext('2d');
    const weightGradient = createGradient(ctxWeight, 'rgba(59, 130, 246, 0.15)', 'rgba(59, 130, 246, 0.0)');
    
    charts['weight'] = new Chart(ctxWeight, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Weight (kg)',
                data: weights,
                borderColor: '#475569', // Slate blue
                backgroundColor: weightGradient,
                borderWidth: 3,
                pointBackgroundColor: '#ffffff',
                pointBorderColor: '#475569',
                pointBorderWidth: 2,
                pointRadius: dataToRender.length > 50 ? 0 : 4, // Hide points if too crowded
                pointHoverRadius: 6,
                fill: true,
                tension: 0.3
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { 
                legend: { display: false },
                tooltip: {
                    intersect: false,
                    mode: 'index',
                    callbacks: {
                        label: function(context) {
                            let val = context.raw;
                            if (!isAuthorized && context.dataset.label === 'Weight (kg)') {
                                return `Weight: ${val > 0 ? '+' : ''}${val} kg`;
                            }
                            return `Weight: ${val} kg`;
                        }
                    }
                }
            },
            interaction: {
                intersect: false,
                mode: 'index',
            },
            scales: {
                x: {
                    type: 'time',
                    time: {
                        tooltipFormat: 'MMM d, yyyy'
                    },
                    grid: { display: false, drawBorder: false },
                    ticks: { maxTicksLimit: 10 } // Prevent label crowding
                },
                y: {
                    grid: { color: 'rgba(0,0,0,0.04)', drawBorder: false },
                    min: (() => {
                        const valid = weights.filter(v => v !== null && v !== undefined && !isNaN(v));
                        return valid.length > 0 ? Math.min(...valid) - 1 : undefined;
                    })(),
                    max: (() => {
                        const valid = weights.filter(v => v !== null && v !== undefined && !isNaN(v));
                        return valid.length > 0 ? Math.max(...valid) + 1 : undefined;
                    })()
                }
            }
        }
    });

    // Mini Charts config template
    const miniChartConfig = (dataArray, color) => ({
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                data: dataArray,
                borderColor: color,
                borderWidth: 2,
                pointRadius: 0,
                pointHoverRadius: 0,
                fill: false,
                tension: 0.3
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false }, tooltip: { enabled: false } },
            scales: {
                x: { type: 'time', display: false },
                y: {
                    display: true,
                    min: (() => {
                        const valid = dataArray.filter(v => v !== null && v !== undefined && !isNaN(v));
                        return valid.length > 0 ? Math.min(...valid) * 0.98 : undefined;
                    })(),
                    max: (() => {
                        const valid = dataArray.filter(v => v !== null && v !== undefined && !isNaN(v));
                        return valid.length > 0 ? Math.max(...valid) * 1.02 : undefined;
                    })()
                }
            },
            layout: { padding: 0 },
            animation: false,
            spanGaps: true
        }
    });

    // 2. Mini Charts
    charts['bodyFat'] = new Chart(document.getElementById('bodyFatChart').getContext('2d'), miniChartConfig(bodyFats, '#94a3b8'));
    charts['bmi'] = new Chart(document.getElementById('bmiChart').getContext('2d'), miniChartConfig(bmis, '#94a3b8'));
    charts['visceral'] = new Chart(document.getElementById('visceralChart').getContext('2d'), miniChartConfig(visceralFats, '#94a3b8'));
}

// Modal Logic
const editBtn = document.getElementById('edit-data-btn');
const modal = document.getElementById('edit-modal');
const closeBtn = document.getElementById('close-modal-btn');
const cancelModalBtn = document.getElementById('cancel-modal-btn');

if (editBtn) {
    editBtn.addEventListener('click', async () => {
        if (!isAuthorized) {
            const inputPin = prompt("Enter PIN code to unlock dashboard:");
            if (inputPin) {
                try {
                    const response = await fetch('/api/verify', {
                        method: 'POST',
                        headers: { 'X-PIN-Code': inputPin }
                    });
                    if (response.ok) {
                        isAuthorized = true;
                        pinCode = inputPin;
                        
                        // Transform the lock button into an edit button
                        editBtn.textContent = 'Edit';
                        
                        // Re-render charts to show true values
                        const activeBtn = document.querySelector('.time-filter.active');
                        const activeRange = activeBtn ? activeBtn.getAttribute('data-range') : '90';
                        renderCharts(activeRange);
                        // Notice: We intentionally do NOT open the modal here.
                    } else {
                        alert("Incorrect PIN");
                    }
                } catch(e) {
                    alert("Error verifying PIN");
                }
            }
        } else {
            // Already unlocked, open the modal to edit records
            populateTable();
            const now = new Date();
            now.setMinutes(now.getMinutes() - now.getTimezoneOffset());
            document.getElementById('new-datetime').value = now.toISOString().slice(0, 16);
            modal.classList.remove('hidden');
        }
    });
}

const closeModal = () => modal.classList.add('hidden');

if (closeBtn) closeBtn.addEventListener('click', closeModal);
if (cancelModalBtn) cancelModalBtn.addEventListener('click', closeModal);

    function populateTable() {
        const tbody = document.getElementById('data-table-body');
        tbody.innerHTML = '';
        
        // Render in reverse chronological order
        [...fullData].reverse().forEach(record => {
            const tr = document.createElement('tr');
            const d = new Date(record.timestamp * 1000);
            
            const w = record.weight_kg !== undefined ? record.weight_kg : '';
            const f = record.body_fat !== undefined ? record.body_fat : '';
            const v = record.visceral_fat !== undefined ? record.visceral_fat : '';
            const b = record.bmi !== undefined ? record.bmi : '';

            tr.innerHTML = `
                <td style="font-size:0.8rem; max-width:140px;">${d.toLocaleString()}</td>
                <td><input type="number" step="0.1" value="${w}" id="w-${record.timestamp}" style="width: 75px; padding: 4px;"></td>
                <td><input type="number" step="0.1" value="${f}" id="f-${record.timestamp}" style="width: 75px; padding: 4px;"></td>
                <td><input type="number" step="0.1" value="${v}" id="v-${record.timestamp}" style="width: 75px; padding: 4px;"></td>
                <td><input type="number" step="0.1" value="${b}" id="b-${record.timestamp}" style="width: 75px; padding: 4px;"></td>
                <td style="white-space:nowrap;">
                    <button class="btn-sm" style="padding: 4px 8px;" onclick="editRecord(${record.timestamp})">Save</button>
                    <button class="btn-sm" style="background: #ef4444; color: white; padding: 4px 8px;" onclick="deleteRecord(${record.timestamp})">Del</button>
                </td>
            `;
            tbody.appendChild(tr);
        });
    }

    window.editRecord = async (timestamp) => {
        const wVal = document.getElementById(`w-${timestamp}`).value;
        const fVal = document.getElementById(`f-${timestamp}`).value;
        const vVal = document.getElementById(`v-${timestamp}`).value;
        const bVal = document.getElementById(`b-${timestamp}`).value;
        
        if (!wVal) {
            alert("Weight is required.");
            return;
        }
        
        const payload = {
            weight_kg: parseFloat(wVal)
        };
        if (fVal) payload.body_fat = parseFloat(fVal);
        if (vVal) payload.visceral_fat = parseFloat(vVal);
        if (bVal) payload.bmi = parseFloat(bVal);

        try {
            const response = await fetch(`${API_URL}/${timestamp}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    'X-PIN-Code': pinCode
                },
                body: JSON.stringify(payload)
            });
            if (!response.ok) throw new Error("Unauthorized or server error.");
            refreshData();
        } catch(e) {
            alert(e.message);
        }
    };

    window.deleteRecord = async (timestamp) => {
        if (!confirm("Are you sure you want to permanently delete this record? A backup will be kept in the server log.")) return;
        
        try {
            const response = await fetch(`${API_URL}/${timestamp}`, {
                method: 'DELETE',
                headers: {
                    'X-PIN-Code': pinCode
                }
            });
            if (!response.ok) throw new Error("Unauthorized or server error.");
            refreshData();
        } catch(e) {
            alert(e.message);
        }
    };

    window.addRecord = async () => {
        const dtVal = document.getElementById('new-datetime').value;
        const wVal = document.getElementById('new-weight').value;
        const fVal = document.getElementById('new-fat').value;
        const vVal = document.getElementById('new-visceral').value;
        const bVal = document.getElementById('new-bmi').value;
        
        if (!wVal) {
            alert("Weight is required to add a new record.");
            return;
        }
        
        const payload = {
            weight_kg: parseFloat(wVal)
        };
        
        if (dtVal) {
            payload.timestamp = Math.floor(new Date(dtVal).getTime() / 1000);
        }
        
        if (fVal) payload.body_fat = parseFloat(fVal);
        if (vVal) payload.visceral_fat = parseFloat(vVal);
        if (bVal) payload.bmi = parseFloat(bVal);

        try {
            const response = await fetch(API_URL, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-PIN-Code': pinCode
                },
                body: JSON.stringify(payload)
            });
            if (!response.ok) throw new Error("Unauthorized or server error.");
            document.getElementById('new-weight').value = '';
            document.getElementById('new-fat').value = '';
            document.getElementById('new-visceral').value = '';
            document.getElementById('new-bmi').value = '';
            refreshData();
        } catch(e) {
            alert(e.message);
        }
    };
