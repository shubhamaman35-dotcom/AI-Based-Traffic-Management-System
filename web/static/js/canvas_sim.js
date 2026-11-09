/**
 * 2D Canvas Intersection Renderer
 * Draws realistic 4-way intersection, dynamic vehicles, animated traffic signals,
 * emergency corridors, and pedestrian crosswalks.
 */

class IntersectionCanvasRenderer {
  constructor(canvasId) {
    this.canvas = document.getElementById(canvasId);
    this.ctx = this.canvas.getContext('2d');
    
    // Virtual world coordinates (Center is 0,0)
    this.width = this.canvas.width;
    this.height = this.canvas.height;
    this.centerX = this.width / 2;
    this.centerY = this.height / 2;

    this.roadWidth = 140; // Total road width for 2-lane dual direction (70px per approach)
    this.laneWidth = 35;
    this.stopLineOffset = 75; // px from intersection center to stop line

    // Scale factor: 1 meter in simulation = ~2.5 pixels on canvas
    this.scale = 2.5;

    // Animation ticker
    this.tick = 0;
  }

  resize() {
    const rect = this.canvas.parentElement.getBoundingClientRect();
    if (rect.width > 300) {
      this.canvas.width = Math.min(900, rect.width);
      this.canvas.height = 600;
      this.width = this.canvas.width;
      this.height = this.canvas.height;
      this.centerX = this.width / 2;
      this.centerY = this.height / 2;
    }
  }

  render(frameData) {
    if (!frameData) return;
    this.tick++;
    const ctx = this.ctx;
    ctx.clearRect(0, 0, this.width, this.height);

    // 1. Draw Ground / Grass
    ctx.fillStyle = '#0f172a';
    ctx.fillRect(0, 0, this.width, this.height);

    // 2. Draw Roads (Asphalt)
    ctx.fillStyle = '#1e293b';
    // Horizontal Road (East-West)
    ctx.fillRect(0, this.centerY - this.roadWidth / 2, this.width, this.roadWidth);
    // Vertical Road (North-South)
    ctx.fillRect(this.centerX - this.roadWidth / 2, 0, this.roadWidth, this.height);

    // 3. Draw Road Markings
    this._drawRoadMarkings(frameData);

    // 4. Draw Blocked Lane Cones
    if (frameData.blocked_lanes) {
      this._drawBlockedLanes(frameData.blocked_lanes);
    }

    // 5. Draw Emergency Corridor Glow if active
    if (frameData.emergency_status && frameData.emergency_status.is_corridor_active) {
      this._drawEmergencyCorridor(frameData.emergency_status.target_lane);
    }

    // 6. Draw Vehicles
    if (frameData.vehicles) {
      for (const veh of frameData.vehicles) {
        this._drawVehicle(veh);
      }
    }

    // 7. Draw Traffic Light Signal Heads
    this._drawTrafficSignals(frameData.signals, frameData.controller_status);
  }

  _drawRoadMarkings(frameData) {
    const ctx = this.ctx;
    const cx = this.centerX;
    const cy = this.centerY;
    const rw = this.roadWidth;
    const slo = this.stopLineOffset;

    // Crosswalks (Zebra Stripes)
    ctx.fillStyle = 'rgba(255, 255, 255, 0.7)';
    const zebraCount = 8;
    const stripeW = 10;
    const stripeH = 4;

    // North crosswalk
    for (let i = 0; i < zebraCount; i++) {
      ctx.fillRect(cx - rw / 2 + 10 + i * 15, cy - slo - 15, stripeW, stripeH * 3);
    }
    // South crosswalk
    for (let i = 0; i < zebraCount; i++) {
      ctx.fillRect(cx - rw / 2 + 10 + i * 15, cy + slo + 3, stripeW, stripeH * 3);
    }
    // West crosswalk
    for (let i = 0; i < zebraCount; i++) {
      ctx.fillRect(cx - slo - 15, cy - rw / 2 + 10 + i * 15, stripeH * 3, stripeW);
    }
    // East crosswalk
    for (let i = 0; i < zebraCount; i++) {
      ctx.fillRect(cx + slo + 3, cy - rw / 2 + 10 + i * 15, stripeH * 3, stripeW);
    }

    // Solid White Stop Lines
    ctx.strokeStyle = '#ffffff';
    ctx.lineWidth = 4;
    // North stop line (incoming lane: right side of north road)
    ctx.beginPath();
    ctx.moveTo(cx - rw / 2, cy - slo);
    ctx.lineTo(cx, cy - slo);
    ctx.stroke();

    // South stop line (incoming lane: left side of south road)
    ctx.beginPath();
    ctx.moveTo(cx, cy + slo);
    ctx.lineTo(cx + rw / 2, cy + slo);
    ctx.stroke();

    // West stop line
    ctx.beginPath();
    ctx.moveTo(cx - slo, cy);
    ctx.lineTo(cx - slo, cy + rw / 2);
    ctx.stroke();

    // East stop line
    ctx.beginPath();
    ctx.moveTo(cx + slo, cy - rw / 2);
    ctx.lineTo(cx + slo, cy);
    ctx.stroke();

    // Yellow Double Center Lines
    ctx.strokeStyle = '#f59e0b';
    ctx.lineWidth = 2;
    // North-South Center Line
    ctx.beginPath();
    ctx.moveTo(cx - 2, 0);
    ctx.lineTo(cx - 2, cy - slo);
    ctx.moveTo(cx + 2, 0);
    ctx.lineTo(cx + 2, cy - slo);
    ctx.moveTo(cx - 2, cy + slo);
    ctx.lineTo(cx - 2, this.height);
    ctx.moveTo(cx + 2, cy + slo);
    ctx.lineTo(cx + 2, this.height);
    ctx.stroke();

    // East-West Center Line
    ctx.beginPath();
    ctx.moveTo(0, cy - 2);
    ctx.lineTo(cx - slo, cy - 2);
    ctx.moveTo(0, cy + 2);
    ctx.lineTo(cx - slo, cy + 2);
    ctx.moveTo(cx + slo, cy - 2);
    ctx.lineTo(this.width, cy - 2);
    ctx.moveTo(cx + slo, cy + 2);
    ctx.lineTo(this.width, cy + 2);
    ctx.stroke();
  }

  _drawBlockedLanes(blockedLanes) {
    const ctx = this.ctx;
    const cx = this.centerX;
    const cy = this.centerY;

    for (const [lane, isBlocked] of Object.entries(blockedLanes)) {
      if (!isBlocked) continue;
      let bx = cx, by = cy;
      if (lane === 'north') { bx = cx - 35; by = cy - 110; }
      else if (lane === 'south') { bx = cx + 35; by = cy + 110; }
      else if (lane === 'east') { bx = cx + 110; by = cy - 35; }
      else if (lane === 'west') { bx = cx - 110; by = cy + 35; }

      // Draw Danger Warning Symbol
      ctx.fillStyle = '#ef4444';
      ctx.beginPath();
      ctx.arc(bx, by, 16, 0, Math.PI * 2);
      ctx.fill();

      ctx.fillStyle = '#ffffff';
      ctx.font = 'bold 12px monospace';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText('✕', bx, by);

      ctx.fillStyle = '#f87171';
      ctx.font = '10px Inter, sans-serif';
      ctx.fillText('BLOCKED', bx, by + 24);
    }
  }

  _drawEmergencyCorridor(targetLane) {
    if (!targetLane) return;
    const ctx = this.ctx;
    const cx = this.centerX;
    const cy = this.centerY;

    ctx.save();
    ctx.fillStyle = 'rgba(239, 68, 68, 0.15)';
    ctx.strokeStyle = 'rgba(239, 68, 68, 0.6)';
    ctx.lineWidth = 2;
    ctx.setLineDash([8, 8]);

    if (targetLane === 'north') {
      ctx.fillRect(cx - 70, 0, 70, this.height);
      ctx.strokeRect(cx - 70, 0, 70, this.height);
    } else if (targetLane === 'south') {
      ctx.fillRect(cx, 0, 70, this.height);
      ctx.strokeRect(cx, 0, 70, this.height);
    } else if (targetLane === 'east') {
      ctx.fillRect(0, cy - 70, this.width, 70);
      ctx.strokeRect(0, cy - 70, this.width, 70);
    } else if (targetLane === 'west') {
      ctx.fillRect(0, cy, this.width, 70);
      ctx.strokeRect(0, cy, this.width, 70);
    }
    ctx.restore();
  }

  _drawVehicle(veh) {
    const ctx = this.ctx;
    const cx = this.centerX;
    const cy = this.centerY;
    const distPx = veh.distance * this.scale;

    let x = 0, y = 0, angle = 0;
    const laneOffset = 35; // Center of 70px approach half

    if (veh.lane === 'north') {
      x = cx - laneOffset;
      y = (cy - this.stopLineOffset) - distPx;
      angle = Math.PI / 2; // Heading South
    } else if (veh.lane === 'south') {
      x = cx + laneOffset;
      y = (cy + this.stopLineOffset) + distPx;
      angle = -Math.PI / 2; // Heading North
    } else if (veh.lane === 'east') {
      x = (cx + this.stopLineOffset) + distPx;
      y = cy - laneOffset;
      angle = Math.PI; // Heading West
    } else if (veh.lane === 'west') {
      x = (cx - this.stopLineOffset) - distPx;
      y = cy + laneOffset;
      angle = 0; // Heading East
    }

    // Vehicle dimensions
    let len = 20, wid = 12;
    if (veh.type === 'BUS') { len = 38; wid = 14; }
    else if (veh.type === 'TRUCK') { len = 44; wid = 15; }
    else if (veh.type === 'MOTORCYCLE') { len = 12; wid = 7; }
    else if (veh.type === 'AMBULANCE') { len = 28; wid = 13; }

    ctx.save();
    ctx.translate(x, y);
    ctx.rotate(angle);

    // Vehicle Body Shadow & Glow
    ctx.shadowColor = veh.is_emergency ? 'rgba(239, 68, 68, 0.8)' : 'rgba(0, 0, 0, 0.5)';
    ctx.shadowBlur = veh.is_emergency ? 15 : 6;

    // Main Body
    ctx.fillStyle = veh.color || '#38bdf8';
    ctx.fillRect(-len / 2, -wid / 2, len, wid);

    // Windshield
    ctx.fillStyle = '#1e293b';
    ctx.fillRect(len * 0.1, -wid * 0.4, len * 0.25, wid * 0.8);

    // Headlights
    ctx.fillStyle = 'rgba(254, 240, 138, 0.8)';
    ctx.fillRect(len / 2 - 2, -wid / 2 + 1, 2, 3);
    ctx.fillRect(len / 2 - 2, wid / 2 - 4, 2, 3);

    // Emergency Flashing Beacon
    if (veh.is_emergency) {
      const beaconColor = (Math.floor(this.tick / 6) % 2 === 0) ? '#ef4444' : '#38bdf8';
      ctx.fillStyle = beaconColor;
      ctx.beginPath();
      ctx.arc(0, 0, 4.5, 0, Math.PI * 2);
      ctx.fill();
    }

    ctx.restore();

    // Speed / Wait Badge for stopped vehicles
    if (veh.wait_time > 2.0 && !veh.has_crossed) {
      ctx.fillStyle = 'rgba(15, 23, 42, 0.85)';
      ctx.fillRect(x - 16, y - 18, 32, 14);
      ctx.strokeStyle = '#f59e0b';
      ctx.lineWidth = 1;
      ctx.strokeRect(x - 16, y - 18, 32, 14);
      ctx.fillStyle = '#f59e0b';
      ctx.font = 'bold 9px monospace';
      ctx.textAlign = 'center';
      ctx.fillText(`${Math.round(veh.wait_time)}s`, x, y - 8);
    }
  }

  _drawTrafficSignals(signals, ctrlStatus) {
    if (!signals) return;
    const ctx = this.ctx;
    const cx = this.centerX;
    const cy = this.centerY;
    const slo = this.stopLineOffset;

    const signalCoords = {
      north: { x: cx - 85, y: cy - slo - 15, rot: 0 },
      south: { x: cx + 85, y: cy + slo + 15, rot: Math.PI },
      east:  { x: cx + slo + 15, y: cy - 85, rot: -Math.PI / 2 },
      west:  { x: cx - slo - 15, y: cy + 85, rot: Math.PI / 2 },
    };

    for (const [lane, state] of Object.entries(signals)) {
      const pos = signalCoords[lane];
      if (!pos) continue;

      ctx.save();
      ctx.translate(pos.x, pos.y);

      // Traffic Signal Housing
      ctx.fillStyle = '#0a0e17';
      ctx.strokeStyle = 'rgba(255, 255, 255, 0.2)';
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      ctx.roundRect(-12, -26, 24, 52, 6);
      ctx.fill();
      ctx.stroke();

      // Red, Yellow, Green bulbs
      const isRed = (state === 'RED');
      const isYellow = (state === 'YELLOW');
      const isGreen = (state === 'GREEN');

      // Red Light
      ctx.fillStyle = isRed ? '#ef4444' : '#331515';
      if (isRed) { ctx.shadowColor = '#ef4444'; ctx.shadowBlur = 12; }
      ctx.beginPath(); ctx.arc(0, -15, 6, 0, Math.PI * 2); ctx.fill();
      ctx.shadowBlur = 0;

      // Yellow Light
      ctx.fillStyle = isYellow ? '#eab308' : '#2d240d';
      if (isYellow) { ctx.shadowColor = '#eab308'; ctx.shadowBlur = 12; }
      ctx.beginPath(); ctx.arc(0, 0, 6, 0, Math.PI * 2); ctx.fill();
      ctx.shadowBlur = 0;

      // Green Light
      ctx.fillStyle = isGreen ? '#22c55e' : '#0e2b17';
      if (isGreen) { ctx.shadowColor = '#22c55e'; ctx.shadowBlur = 12; }
      ctx.beginPath(); ctx.arc(0, 15, 6, 0, Math.PI * 2); ctx.fill();
      ctx.shadowBlur = 0;

      ctx.restore();
    }
  }
}
