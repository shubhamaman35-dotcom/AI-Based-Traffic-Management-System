"""
FastAPI Server & Real-Time Telemetry Backend
Provides WebSocket telemetry feed, MJPEG video streaming, and REST control endpoints.
"""

import asyncio
import os
import cv2
import time
from typing import Set, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, Form
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.requests import Request

from core.simulation.intersection import IntersectionSimulation
from core.vision.detector import TrafficVisionDetector

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: launch background simulation loop
    sim_task = asyncio.create_task(simulation_loop())
    yield
    # Shutdown
    sim_task.cancel()

app = FastAPI(title="AI Smart Traffic Management System", version="1.0.0", lifespan=lifespan)

# Setup directories
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_DIR = os.path.join(BASE_DIR, "web", "static")
TEMPLATES_DIR = os.path.join(BASE_DIR, "web", "templates")
UPLOADS_DIR = os.path.join(BASE_DIR, "data", "uploads")
SAMPLE_VID_DIR = os.path.join(BASE_DIR, "data", "sample_videos")
os.makedirs(UPLOADS_DIR, exist_ok=True)
os.makedirs(SAMPLE_VID_DIR, exist_ok=True)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# Global Simulation & Vision Instances
sim = IntersectionSimulation(mode="ADAPTIVE")
vision_detector = TrafficVisionDetector()

# WebSocket active client pool
active_connections: Set[WebSocket] = set()

# Video stream state
current_video_source = os.path.join(SAMPLE_VID_DIR, "traffic_sample.mp4")
is_video_running = True


async def simulation_loop():
    """Background task advancing the 4-way intersection simulation and broadcasting to clients."""
    dt = 0.05 # 20 ticks per second
    while True:
        try:
            frame_data = sim.step(dt)
            if active_connections:
                # Broadcast JSON frame to all active WebSocket clients
                disconnected = set()
                for ws in active_connections:
                    try:
                        await ws.send_json(frame_data)
                    except Exception:
                        disconnected.add(ws)
                for ws in disconnected:
                    active_connections.remove(ws)
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"Error in simulation loop: {e}")

        await asyncio.sleep(dt)


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Serve main control center operations dashboard."""
    return templates.TemplateResponse(request=request, name="index.html")



@app.websocket("/ws/traffic-stream")
async def websocket_traffic_stream(websocket: WebSocket):
    """Real-time high-speed telemetry feed for 2D intersection visualizer."""
    await websocket.accept()
    active_connections.add(websocket)
    try:
        while True:
            # Keep connection alive and accept client commands if sent
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        active_connections.remove(websocket)
    except Exception:
        if websocket in active_connections:
            active_connections.remove(websocket)


def generate_video_frames():
    """MJPEG frame generator reading video and applying AI computer vision detector."""
    global current_video_source
    while True:
        if not os.path.exists(current_video_source):
            time.sleep(0.5)
            continue

        cap = cv2.VideoCapture(current_video_source)
        if not cap.isOpened():
            time.sleep(0.5)
            continue

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                # Loop video seamlessly
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                continue

            # Process with AI Detector (HUD, Bounding boxes, count lines, density)
            annotated_frame, _ = vision_detector.process_frame(frame)
            jpeg_bytes = vision_detector.encode_jpeg(annotated_frame, quality=75)

            yield (b"--frame\r\n"
                   b"Content-Type: image/jpeg\r\n\r\n" + jpeg_bytes + b"\r\n")

            time.sleep(0.033) # ~30 FPS

        cap.release()


@app.get("/video_feed")
async def video_feed():
    """Stream live annotated computer vision feed as MJPEG."""
    return StreamingResponse(
        generate_video_frames(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


# --- REST API Endpoints ---

@app.post("/api/control/mode")
async def set_controller_mode(mode: str = Form(...)):
    """Switch controller mode (ADAPTIVE, FIXED_TIME, ACTUATED)."""
    sim.set_mode(mode.upper())
    return {"status": "success", "mode": sim.mode}


@app.post("/api/control/scenario")
async def set_scenario(scenario: str = Form(...)):
    """Set simulation scenario (NORMAL, RUSH_HOUR, RAINY, BLOCKAGE)."""
    sim.set_scenario(scenario.upper())
    return {"status": "success", "scenario": sim.current_scenario}


@app.post("/api/control/emergency")
async def trigger_emergency(lane: str = Form("north")):
    """Trigger emergency vehicle dispatch on specified approach lane."""
    vehicle_id = sim.trigger_emergency_vehicle(lane.lower())
    return {"status": "dispatched", "vehicle_id": vehicle_id, "lane": lane}


@app.post("/api/control/toggle-blockage")
async def toggle_blockage(lane: str = Form(...)):
    """Toggle accident or road blockage on a lane."""
    is_blocked = sim.toggle_lane_blockage(lane.lower())
    return {"status": "success", "lane": lane, "is_blocked": is_blocked}


@app.post("/api/control/speed")
async def set_simulation_speed(speed: float = Form(...)):
    """Adjust simulation multiplier (e.g. 1.0x, 2.0x, 4.0x)."""
    sim.simulation_speed = max(0.2, min(5.0, speed))
    return {"status": "success", "speed": sim.simulation_speed}


@app.post("/api/video/upload")
async def upload_traffic_video(file: UploadFile = File(...)):
    """Upload custom traffic video file for real-time computer vision analysis."""
    global current_video_source
    file_path = os.path.join(UPLOADS_DIR, file.filename)
    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)

    current_video_source = file_path
    return {"status": "success", "filename": file.filename, "path": file_path}


@app.post("/api/video/reset-sample")
async def reset_sample_video():
    """Reset vision feed back to bundled sample video."""
    global current_video_source
    sample_path = os.path.join(SAMPLE_VID_DIR, "traffic_sample.mp4")
    if os.path.exists(sample_path):
        current_video_source = sample_path
        return {"status": "success", "source": "sample"}
    return {"status": "error", "message": "Sample video not found"}


@app.get("/api/metrics/export")
async def export_metrics(format: str = "json"):
    """Export current traffic telemetry and audit log."""
    summary = sim.metrics.get_summary(0, 0, {})
    preempt = sim.emergency_manager.get_status()

    report_data = {
        "timestamp": time.time(),
        "mode": sim.mode,
        "scenario": sim.current_scenario,
        "metrics": summary,
        "emergency_events": sim.emergency_manager.emergency_log,
        "adaptive_cycles": sim.adaptive_controller.phase_history[-20:]
    }

    if format.lower() == "csv":
        # Generate clean CSV format
        lines = [
            "Metric,Value",
            f"Mode,{sim.mode}",
            f"Total Vehicles Passed,{summary['total_vehicles_passed']}",
            f"Average Wait Time (s),{summary['avg_wait_time_sec']}",
            f"Max Wait Time (s),{summary['max_wait_time_sec']}",
            f"Throughput (veh/min),{summary['throughput_vpm']}",
            f"Idle CO2 Generated (kg),{summary['emissions']['idle_co2_kg']}",
            f"CO2 Saved by AI (kg),{summary['emissions']['co2_saved_kg']}",
            f"Fuel Saved (Liters),{summary['emissions']['fuel_saved_liters']}",
            f"Efficiency Gain (%),{summary['emissions']['efficiency_gain_pct']}",
            f"Total Emergencies Served,{preempt['total_emergencies_served']}"
        ]
        csv_content = "\n".join(lines)
        return Response(content=csv_content, media_type="text/csv", headers={"Content-Disposition": "attachment; filename=traffic_audit_report.csv"})

    return JSONResponse(content=report_data)
