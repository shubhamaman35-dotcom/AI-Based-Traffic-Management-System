/**
 * Live Telemetry & Performance Charts (Chart.js)
 */

class TrafficChartsManager {
  constructor() {
    this.throughputChart = null;
    this.densityChart = null;
    this.comparisonChart = null;

    this.maxPoints = 25;
    this.timestamps = [];
    this.throughputData = [];
    this.waitTimeData = [];
  }

  init() {
    const defaultFont = { family: "'Inter', sans-serif", size: 11 };
    const gridColor = 'rgba(255, 255, 255, 0.06)';
    const tickColor = '#94a3b8';

    // 1. Throughput & Wait Time Trend Chart
    const ctx1 = document.getElementById('throughputChart');
    if (ctx1) {
      this.throughputChart = new Chart(ctx1, {
        type: 'line',
        data: {
          labels: [],
          datasets: [
            {
              label: 'Throughput (veh/min)',
              data: [],
              borderColor: '#38bdf8',
              backgroundColor: 'rgba(56, 189, 248, 0.1)',
              fill: true,
              tension: 0.3,
              yAxisID: 'y'
            },
            {
              label: 'Avg Wait Time (s)',
              data: [],
              borderColor: '#f59e0b',
              backgroundColor: 'rgba(245, 158, 11, 0.05)',
              fill: false,
              tension: 0.3,
              yAxisID: 'y1'
            }
          ]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          animation: false,
          scales: {
            x: { grid: { color: gridColor }, ticks: { color: tickColor, font: defaultFont } },
            y: {
              type: 'linear',
              position: 'left',
              title: { display: true, text: 'Vehicles / min', color: '#38bdf8' },
              grid: { color: gridColor },
              ticks: { color: tickColor, font: defaultFont }
            },
            y1: {
              type: 'linear',
              position: 'right',
              title: { display: true, text: 'Wait Time (sec)', color: '#f59e0b' },
              grid: { drawOnChartArea: false },
              ticks: { color: tickColor, font: defaultFont }
            }
          },
          plugins: {
            legend: { labels: { color: '#f1f5f9', font: defaultFont } }
          }
        }
      });
    }

    // 2. Lane Queue Breakdown Bar Chart
    const ctx2 = document.getElementById('densityChart');
    if (ctx2) {
      this.densityChart = new Chart(ctx2, {
        type: 'bar',
        data: {
          labels: ['North', 'South', 'East', 'West'],
          datasets: [{
            label: 'Queue Count (Stopped Vehicles)',
            data: [0, 0, 0, 0],
            backgroundColor: [
              'rgba(56, 189, 248, 0.7)',
              'rgba(16, 185, 129, 0.7)',
              'rgba(245, 158, 11, 0.7)',
              'rgba(168, 85, 247, 0.7)'
            ],
            borderColor: ['#38bdf8', '#10b981', '#f59e0b', '#a855f7'],
            borderWidth: 1.5,
            borderRadius: 6
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          animation: { duration: 300 },
          scales: {
            x: { grid: { color: gridColor }, ticks: { color: tickColor, font: defaultFont } },
            y: {
              beginAtZero: true,
              suggestedMax: 10,
              grid: { color: gridColor },
              ticks: { color: tickColor, font: defaultFont }
            }
          },
          plugins: {
            legend: { display: false }
          }
        }
      });
    }

    // 3. AI vs Fixed-Timer Benchmark Comparison Chart
    const ctx3 = document.getElementById('comparisonChart');
    if (ctx3) {
      this.comparisonChart = new Chart(ctx3, {
        type: 'radar',
        data: {
          labels: ['Avg Wait Time', 'Throughput', 'Queue Clearing Speed', 'Emergency Response', 'Fuel Efficiency', 'CO2 Reductions'],
          datasets: [
            {
              label: 'AI-Adaptive Control',
              data: [90, 88, 92, 98, 85, 87],
              borderColor: '#38bdf8',
              backgroundColor: 'rgba(56, 189, 248, 0.25)',
              pointBackgroundColor: '#38bdf8'
            },
            {
              label: 'Fixed-Timer (Baseline)',
              data: [50, 58, 48, 20, 52, 54],
              borderColor: '#f43f5e',
              backgroundColor: 'rgba(244, 63, 94, 0.15)',
              pointBackgroundColor: '#f43f5e'
            }
          ]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          scales: {
            r: {
              angleLines: { color: gridColor },
              grid: { color: gridColor },
              pointLabels: { color: '#f1f5f9', font: defaultFont },
              ticks: { display: false, max: 100 }
            }
          },
          plugins: {
            legend: { labels: { color: '#f1f5f9', font: defaultFont } }
          }
        }
      });
    }
  }

  update(metrics, controllerStatus) {
    if (!metrics) return;

    const timeLabel = new Date().toLocaleTimeString([], { hour12: false, minute: '2-digit', second: '2-digit' });

    // Update Throughput chart
    if (this.throughputChart) {
      if (this.throughputChart.data.labels.length > this.maxPoints) {
        this.throughputChart.data.labels.shift();
        this.throughputChart.data.datasets[0].data.shift();
        this.throughputChart.data.datasets[1].data.shift();
      }
      this.throughputChart.data.labels.push(timeLabel);
      this.throughputChart.data.datasets[0].data.push(metrics.throughput_vpm || 0);
      this.throughputChart.data.datasets[1].data.push(metrics.avg_wait_time_sec || 0);
      this.throughputChart.update();
    }

    // Update Queue Density chart
    if (this.densityChart && metrics.lane_queue_lengths) {
      const q = metrics.lane_queue_lengths;
      this.densityChart.data.datasets[0].data = [
        q.north || 0,
        q.south || 0,
        q.east || 0,
        q.west || 0
      ];
      this.densityChart.update();
    }
  }
}
