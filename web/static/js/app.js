/**
 * Main Application Controller
 * Handles WebSocket communication, UI event bindings, and live dashboard state updates.
 */

document.addEventListener('DOMContentLoaded', () => {
  const canvasRenderer = new IntersectionCanvasRenderer('simCanvas');
  const chartsManager = new TrafficChartsManager();

  // Initialize Canvas & Charts
  window.addEventListener('resize', () => canvasRenderer.resize());
  canvasRenderer.resize();
  chartsManager.init();

  // Navigation Tabs
  const tabBtns = document.querySelectorAll('.tab-btn');
  const tabContents = document.querySelectorAll('.tab-content');

  tabBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      const targetTab = btn.getAttribute('data-tab');
      tabBtns.forEach(b => b.classList.remove('active'));
      tabContents.forEach(c => c.classList.remove('active'));

      btn.classList.add('active');
      const content = document.getElementById(targetTab);
      if (content) content.classList.add('active');

      if (targetTab === 'tab-sim') {
        canvasRenderer.resize();
      }
    });
  });

  // Scenario Buttons
  const scenarioBtns = document.querySelectorAll('.btn-scenario');
  scenarioBtns.forEach(btn => {
    btn.addEventListener('click', async () => {
      const scenario = btn.getAttribute('data-scenario');
      scenarioBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');

      const formData = new FormData();
      formData.append('scenario', scenario);
      await fetch('/api/control/scenario', { method: 'POST', body: formData });
      logTerminal(`Scenario set to: ${scenario}`);
    });
  });

  // Mode Buttons (ADAPTIVE, FIXED_TIME, ACTUATED)
  const modeBtns = document.querySelectorAll('.btn-mode');
  modeBtns.forEach(btn => {
    btn.addEventListener('click', async () => {
      const mode = btn.getAttribute('data-mode');
      modeBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');

      const formData = new FormData();
      formData.append('mode', mode);
      await fetch('/api/control/mode', { method: 'POST', body: formData });
      logTerminal(`Controller switched to mode: ${mode}`);
    });
  });

  // Emergency Dispatch Button
  const btnEmergency = document.getElementById('btnDispatchEmergency');
  const emergencyLaneSelect = document.getElementById('emergencyLaneSelect');
  if (btnEmergency) {
    btnEmergency.addEventListener('click', async () => {
      const lane = emergencyLaneSelect ? emergencyLaneSelect.value : 'north';
      const formData = new FormData();
      formData.append('lane', lane);
      const res = await fetch('/api/control/emergency', { method: 'POST', body: formData });
      const data = await res.json();
      logTerminal(`[EMERGENCY] Ambulance dispatched on ${lane.toUpperCase()} lane! Green corridor requested.`);
    });
  }

  // Toggle Blockage Buttons
  const blockageBtns = document.querySelectorAll('.btn-blockage');
  blockageBtns.forEach(btn => {
    btn.addEventListener('click', async () => {
      const lane = btn.getAttribute('data-lane');
      const formData = new FormData();
      formData.append('lane', lane);
      const res = await fetch('/api/control/toggle-blockage', { method: 'POST', body: formData });
      const data = await res.json();
      btn.classList.toggle('active', data.is_blocked);
      logTerminal(`Lane ${lane.toUpperCase()} blockage toggled: ${data.is_blocked ? 'BLOCKED' : 'CLEAR'}`);
    });
  });

  // Video Upload Handler
  const videoUploadInput = document.getElementById('videoUploadInput');
  if (videoUploadInput) {
    videoUploadInput.addEventListener('change', async (e) => {
      const file = e.target.files[0];
      if (!file) return;

      const formData = new FormData();
      formData.append('file', file);
      logTerminal(`Uploading video: ${file.name}...`);

      const res = await fetch('/api/video/upload', { method: 'POST', body: formData });
      const data = await res.json();
      if (data.status === 'success') {
        logTerminal(`Video loaded successfully! AI Vision Stream updated.`);
        // Reload video feed image
        const img = document.getElementById('liveVideoFeed');
        if (img) img.src = `/video_feed?t=${Date.now()}`;
      }
    });
  }

  // Reset Sample Video
  const btnResetVideo = document.getElementById('btnResetVideo');
  if (btnResetVideo) {
    btnResetVideo.addEventListener('click', async () => {
      await fetch('/api/video/reset-sample', { method: 'POST' });
      logTerminal(`Reset to bundled sample traffic footage.`);
      const img = document.getElementById('liveVideoFeed');
      if (img) img.src = `/video_feed?t=${Date.now()}`;
    });
  }

  // Export Audit CSV
  const btnExportCsv = document.getElementById('btnExportCsv');
  if (btnExportCsv) {
    btnExportCsv.addEventListener('click', () => {
      window.location.href = '/api/metrics/export?format=csv';
    });
  }

  // WebSocket Telemetry Connection
  let ws = null;
  function connectWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/traffic-stream`;

    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      document.getElementById('wsStatus').textContent = 'LIVE 60 FPS';
      document.getElementById('wsStatusDot').style.backgroundColor = '#10b981';
      logTerminal('WebSocket telemetry stream connected.');
    };

    ws.onmessage = (event) => {
      try {
        const frameData = JSON.parse(event.data);
        updateDashboard(frameData);
      } catch (err) {
        console.error('Error parsing frame:', err);
      }
    };

    ws.onclose = () => {
      document.getElementById('wsStatus').textContent = 'RECONNECTING...';
      document.getElementById('wsStatusDot').style.backgroundColor = '#ef4444';
      setTimeout(connectWebSocket, 2000);
    };
  }

  // Update UI Elements with incoming frame telemetry
  function updateDashboard(data) {
    // 1. Render 2D Canvas
    canvasRenderer.render(data);

    // 2. Metrics & KPI cards
    const m = data.metrics || {};
    const e = m.emissions || {};
    const ctrl = data.controller_status || {};
    const emerg = data.emergency_status || {};

    setElemText('valVehiclesPassed', m.total_vehicles_passed ?? '--');
    setElemText('valAvgWait', `${m.avg_wait_time_sec ?? '--'}s`);
    setElemText('valThroughput', `${m.throughput_vpm ?? '--'} vpm`);
    setElemText('valActiveQueue', m.active_vehicles_in_queue ?? '0');
    setElemText('valCo2Saved', `${e.co2_saved_kg ?? '--'} kg`);
    setElemText('valEfficiency', `+${e.efficiency_gain_pct ?? '34.5'}%`);

    // 3. Controller Signal Card
    setElemText('hudActivePhase', ctrl.active_phase ?? '--');
    setElemText('hudState', ctrl.state ?? '--');
    setElemText('hudRemaining', `${ctrl.remaining_time ?? '0'}s`);

    // 4. Update Signal Light Bulbs in HUD
    if (data.signals) {
      updateSignalBulbs(data.signals);
    }

    // 5. Emergency Corridor Alert Banner
    const emergBanner = document.getElementById('emergencyAlertBanner');
    if (emergBanner) {
      if (emerg.is_corridor_active) {
        emergBanner.classList.add('active');
        setElemText('emergencyBannerText', `🚨 GREEN CORRIDOR ACTIVE: PRIORITY CLEARANCE FOR ${emerg.target_lane.toUpperCase()} APPROACH`);
      } else {
        emergBanner.classList.remove('active');
      }
    }

    // 6. Update Charts
    chartsManager.update(m, ctrl);
  }

  function updateSignalBulbs(signals) {
    for (const [lane, state] of Object.entries(signals)) {
      const redDot = document.getElementById(`sig_${lane}_red`);
      const yellowDot = document.getElementById(`sig_${lane}_yellow`);
      const greenDot = document.getElementById(`sig_${lane}_green`);

      if (redDot && yellowDot && greenDot) {
        redDot.classList.toggle('active', state === 'RED');
        yellowDot.classList.toggle('active', state === 'YELLOW');
        greenDot.classList.toggle('active', state === 'GREEN');
      }
    }
  }

  function setElemText(id, text) {
    const el = document.getElementById(id);
    if (el) el.textContent = text;
  }

  function logTerminal(msg) {
    const term = document.getElementById('logTerminal');
    if (!term) return;
    const time = new Date().toLocaleTimeString();
    const entry = document.createElement('div');
    entry.className = 'log-entry';
    entry.textContent = `[${time}] ${msg}`;
    term.appendChild(entry);
    term.scrollTop = term.scrollHeight;
  }

  // Start WebSocket
  connectWebSocket();
});
