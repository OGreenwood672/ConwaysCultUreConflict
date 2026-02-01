import './style.css'
import Chart from 'chart.js/auto'

const ATTRIBUTES = ['Aggression', 'Resources', 'Commerce', 'Resilience', 'Adaptability']
const POLL_INTERVAL = 2000  // Poll every 2 seconds

let chart = null
let currentCulture = null
let historyData = []  // Array of {timestamp, attributes}
let isLiveMode = true
let currentHistoryIndex = 0

document.querySelector('#app').innerHTML = `
  <div class="container">
    <h1>Culture Attributes</h1>
    <div class="culture-selector">
      <label for="culture-select">Select Culture:</label>
      <select id="culture-select">
        <option value="">Loading...</option>
      </select>
    </div>
    <div class="chart-container">
      <canvas id="radar-chart"></canvas>
    </div>
    <div class="time-controls">
      <div class="time-header">
        <span class="time-label">Timeline</span>
        <button id="live-btn" class="live-btn active">LIVE</button>
      </div>
      <div class="slider-container">
        <input type="range" id="time-slider" min="0" max="0" value="0" disabled>
        <div class="slider-labels">
          <span id="slider-min">--</span>
          <span id="slider-current">No history</span>
          <span id="slider-max">--</span>
        </div>
      </div>
    </div>
    <div class="attributes-list" id="attributes-list"></div>
    <div class="timestamp" id="timestamp"></div>
  </div>
`

function createRadarChart(canvasId) {
  const ctx = document.getElementById(canvasId).getContext('2d')

  return new Chart(ctx, {
    type: 'radar',
    data: {
      labels: ATTRIBUTES,
      datasets: [{
        label: 'Attributes',
        data: [50, 50, 50, 50, 50],
        fill: true,
        backgroundColor: 'rgba(91, 155, 213, 0.18)',
        borderColor: '#5B9BD5',
        borderWidth: 2.2,
        pointBackgroundColor: 'white',
        pointBorderColor: '#5B9BD5',
        pointBorderWidth: 2,
        pointRadius: 5,
        pointHoverRadius: 7
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      scales: {
        r: {
          beginAtZero: true,
          max: 100,
          min: 0,
          ticks: {
            stepSize: 25,
            color: '#b0b0b0',
            backdropColor: 'transparent',
            font: { size: 10 }
          },
          grid: {
            color: '#e0e0e0',
            lineWidth: 0.8
          },
          angleLines: {
            color: '#e8e8e8',
            lineWidth: 0.6
          },
          pointLabels: {
            color: '#333333',
            font: {
              size: 12,
              weight: 'bold'
            }
          }
        }
      },
      plugins: {
        legend: {
          display: false
        },
        tooltip: {
          callbacks: {
            label: (context) => `${context.label}: ${context.raw}%`
          }
        }
      }
    }
  })
}

function updateChart(attributes) {
  if (!chart) return

  const values = ATTRIBUTES.map(attr => attributes[attr] || 50)
  chart.data.datasets[0].data = values
  chart.update('none')  // No animation for smoother updates
}

function updateAttributesList(attributes) {
  const container = document.getElementById('attributes-list')
  container.innerHTML = ATTRIBUTES.map(attr => `
    <div class="attribute-item">
      <span class="attr-name">${attr}</span>
      <div class="attr-bar-container">
        <div class="attr-bar" style="width: ${attributes[attr] || 0}%"></div>
      </div>
      <span class="attr-value">${attributes[attr] || 0}%</span>
    </div>
  `).join('')
}

function updateTimestamp(timestamp) {
  const el = document.getElementById('timestamp')
  if (timestamp) {
    const date = new Date(timestamp * 1000)
    el.textContent = `Last updated: ${date.toLocaleTimeString()}`
  } else {
    el.textContent = ''
  }
}

async function fetchCultures() {
  try {
    const response = await fetch('/culture_data/all_cultures.json')
    if (!response.ok) throw new Error('No data yet')
    return await response.json()
  } catch (e) {
    return null
  }
}

async function fetchHistory(cultureName) {
  try {
    const response = await fetch(`/culture_data/history/${cultureName}.csv`)
    if (!response.ok) return []

    const text = await response.text()
    const lines = text.trim().split('\n')
    if (lines.length < 2) return []  // Need header + at least one row

    const data = []
    for (let i = 1; i < lines.length; i++) {
      const values = lines[i].split(',')
      if (values.length >= 6) {
        data.push({
          timestamp: parseFloat(values[0]),
          attributes: {
            Aggression: parseInt(values[1]),
            Resources: parseInt(values[2]),
            Commerce: parseInt(values[3]),
            Resilience: parseInt(values[4]),
            Adaptability: parseInt(values[5])
          }
        })
      }
    }
    return data
  } catch (e) {
    return []
  }
}

function formatTime(timestamp) {
  const date = new Date(timestamp * 1000)
  return date.toLocaleTimeString()
}

function updateSlider() {
  const slider = document.getElementById('time-slider')
  const minLabel = document.getElementById('slider-min')
  const maxLabel = document.getElementById('slider-max')
  const currentLabel = document.getElementById('slider-current')
  const liveBtn = document.getElementById('live-btn')

  if (historyData.length === 0) {
    slider.disabled = true
    slider.max = 0
    slider.value = 0
    minLabel.textContent = '--'
    maxLabel.textContent = '--'
    currentLabel.textContent = 'No history'
    return
  }

  slider.disabled = false
  slider.max = historyData.length - 1
  minLabel.textContent = formatTime(historyData[0].timestamp)
  maxLabel.textContent = formatTime(historyData[historyData.length - 1].timestamp)

  if (isLiveMode) {
    slider.value = historyData.length - 1
    currentLabel.textContent = 'LIVE'
    liveBtn.classList.add('active')
  } else {
    slider.value = currentHistoryIndex
    currentLabel.textContent = formatTime(historyData[currentHistoryIndex].timestamp)
    liveBtn.classList.remove('active')
  }
}

function displayHistoryPoint(index) {
  if (index < 0 || index >= historyData.length) return

  const point = historyData[index]
  updateChart(point.attributes)
  updateAttributesList(point.attributes)
  updateTimestamp(point.timestamp)
}

function populateCultureSelect(cultures) {
  const select = document.getElementById('culture-select')
  const cultureNames = Object.keys(cultures)

  if (cultureNames.length === 0) {
    select.innerHTML = '<option value="">No cultures found</option>'
    return
  }

  select.innerHTML = cultureNames.map(name =>
    `<option value="${name}" ${name === currentCulture ? 'selected' : ''}>${name}</option>`
  ).join('')

  // Select first culture if none selected
  if (!currentCulture && cultureNames.length > 0) {
    currentCulture = cultureNames[0]
    select.value = currentCulture
  }
}

function displayCulture(cultures, cultureName) {
  if (!cultures || !cultureName || !cultures[cultureName]) {
    updateChart({})
    updateAttributesList({})
    updateTimestamp(null)
    return
  }

  const data = cultures[cultureName]
  updateChart(data.attributes)
  updateAttributesList(data.attributes)
  updateTimestamp(data.timestamp)
}

async function pollData() {
  const cultures = await fetchCultures()

  if (cultures) {
    populateCultureSelect(cultures)

    // Fetch history for current culture
    if (currentCulture) {
      historyData = await fetchHistory(currentCulture)
      updateSlider()
    }

    // Only update display if in live mode
    if (isLiveMode) {
      displayCulture(cultures, currentCulture)
    }
  }
}

function init() {
  chart = createRadarChart('radar-chart')

  // Culture selector change handler
  document.getElementById('culture-select').addEventListener('change', async (e) => {
    currentCulture = e.target.value
    isLiveMode = true
    currentHistoryIndex = 0
    await pollData()
  })

  // Time slider change handler
  document.getElementById('time-slider').addEventListener('input', (e) => {
    isLiveMode = false
    currentHistoryIndex = parseInt(e.target.value)
    displayHistoryPoint(currentHistoryIndex)
    updateSlider()
  })

  // Live button click handler
  document.getElementById('live-btn').addEventListener('click', () => {
    isLiveMode = true
    currentHistoryIndex = historyData.length - 1
    updateSlider()
    pollData()
  })

  // Initial poll and start interval
  pollData()
  setInterval(pollData, POLL_INTERVAL)
}

init()
