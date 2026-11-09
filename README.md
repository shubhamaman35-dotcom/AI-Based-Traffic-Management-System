# 🚦 AI-Based Smart Traffic Management System (AI-STMS)

An intelligent, multi-lane adaptive traffic signal control and real-time computer vision monitoring system designed to eliminate urban congestion, prioritize emergency vehicles (Green Corridors), and optimize vehicular throughput.

---

## 🌟 Key Features

1. **AI-Driven Dynamic Signal Allocation**:
   - Computes real-time green light duration based on vehicle classifications and **Passenger Car Unit (PCU)** density.
   - Eliminates rigid fixed-time cycles (e.g. 30s per lane) by dynamically adapting phase lengths between $8\text{s}$ and $60\text{s}$.
   - Anti-starvation fair queueing logic ensures low-density lanes are never starved indefinitely.

2. **Emergency Vehicle Priority (Green Corridor)**:
   - Instant computer vision & sensor identification of emergency vehicles (Ambulances, Fire Trucks, Police).
   - Preemption system initiates a safe clearance transition and locks conflicting signals to RED while granting an uninterrupted GREEN corridor.
   - Seamlessly restores normal adaptive scheduling once the emergency vehicle departs the intersection.

3. **Computer Vision & Video Analysis Engine**:
   - Integrated OpenCV & AI detection pipeline with background subtraction, morphological filtering, and contour classification.
   - Classifies vehicles into **Cars, Buses, Trucks, Motorcycles, and Ambulances**.
   - Line-crossing counting, speed vector estimation, and lane Region of Interest (ROI) congestion analysis.
   - Live Cyberpunk HUD overlay on video streams (bounding boxes, speed badges, density heatmap).

4. **Multi-Lane 4-Way Intersection Micro-Simulator**:
   - High-performance 2D Canvas micro-simulation with Intelligent Driver Model (IDM) car-following physics.
   - Live comparison benchmark: **AI-Adaptive** vs **Fixed-Timer** vs **Actuated Controller**.
   - Scenario controls: Morning/Evening Rush Hours ($2.5\times$ spawn density), Rainy Weather, Lane Blockages/Accidents.

5. **Modern Glassmorphic Operations Dashboard**:
   - 60 FPS real-time WebSocket telemetry feed.
   - Interactive 2D simulation canvas.
   - Live performance graphs with Chart.js (Throughput, Wait Times, Queue Depths, Efficiency Radar).
   - Downloadable Traffic Performance Audit reports in CSV / JSON format.

---

## 📐 Mathematical Formulation

### 1. Passenger Car Unit (PCU) Weighting
$$\text{Density}_i = (N_{\text{car}} \times 1.0) + (N_{\text{bus}} \times 2.5) + (N_{\text{truck}} \times 3.0) + (N_{\text{bike}} \times 0.5) + (N_{\text{emergency}} \times 50.0)$$

### 2. Urgency & Starvation Factor
$$\text{Urgency}_i = \text{Density}_i + (T_{\text{max\_wait}, i} \times k_{\text{starvation}})$$

### 3. Dynamic Green Time Allocation
$$T_{\text{green}, i} = \text{clamp}\left(T_{\min}, \left(\frac{\text{Urgency}_i}{\sum \text{Urgency}}\right) \times T_{\text{cycle}}, T_{\max}\right)$$

---

## 📁 Directory Structure

```
AI BASED TRAFFIC MANAGEMENT SYSTEM/
├── core/
│   ├── controller/
│   │   ├── adaptive_signal.py     # AI Adaptive Signal Controller & PCU Math
│   │   ├── emergency.py           # Emergency Vehicle Green Corridor Preemption
│   │   └── baseline_signals.py    # Fixed-Time & Actuated Baseline Controllers
│   ├── simulation/
│   │   ├── intersection.py        # 4-way Intersection Simulation Physics
│   │   ├── vehicle.py             # Vehicle Kinematics & IDM Car-Following Model
│   │   └── metrics.py             # KPIs, Throughput & Carbon (CO2) Emissions Tracker
│   └── vision/
│       ├── detector.py            # AI Computer Vision Vehicle & Emergency Detector
│       ├── tracker.py             # Multi-Object Centroid & Trajectory Tracker
│       └── density.py             # Lane ROI Density & Congestion Estimator
├── server/
│   └── app.py                     # FastAPI Web Application & WebSocket Server
├── web/
│   ├── static/
│   │   ├── css/style.css          # Glassmorphic Dark-Mode UI Stylesheet
│   │   ├── js/app.js              # Application Logic & WebSocket Listener
│   │   ├── js/canvas_sim.js       # 2D Intersection Simulation Canvas Renderer
│   │   └── js/charts.js           # Live Performance Charts (Chart.js)
│   └── templates/
│       └── index.html             # Operations Dashboard Web Page
├── data/
│   ├── sample_videos/             # Bundled Realistic Traffic Footage
│   └── generate_sample_video.py   # Synthetic Traffic Video Generator
├── tests/
│   ├── test_api.py                # REST API Endpoint Tests
│   ├── test_controller.py         # Adaptive Controller & Preemption Tests
│   ├── test_detector.py           # Computer Vision & Tracker Tests
│   └── test_simulation.py         # Physics & Kinematics Tests
├── requirements.txt               # Dependencies
├── run.py                         # Application Entrypoint
└── README.md                      # Documentation
```

---

## 🚀 Quick Start & Installation

### 1. Install Dependencies
```bash
python -m pip install -r requirements.txt
```

### 2. Launch the Operations Dashboard
```bash
python run.py
```
The server will start at `http://127.0.0.1:8000` and automatically launch your default browser.

---

## 🧪 Running Automated Tests

Run the test suite covering all controller, simulation, computer vision, and API modules:
```bash
python -m pytest tests/
```

---

## 📊 Operations Guide

1. **4-Way Intersection Simulator**:
   - View real-time vehicles moving across North, South, East, and West approaches.
   - Switch between **AI-Adaptive**, **Fixed-Timer**, and **Actuated** modes in the control room sidebar to observe differences in queue buildup.
   - Click **"Dispatch Ambulance"** to test instantaneous emergency green corridor preemption.
   - Toggle **"Lane Blockage"** to simulate accidents or road construction.

2. **AI Computer Vision Stream**:
   - View live detection with bounding boxes, speed tags, virtual count line, and lane congestion ROIs.
   - Upload any MP4/AVI traffic video using the file dropzone to process custom traffic feeds.

3. **Analytics & Benchmarking**:
   - Monitor real-time throughput ($vpm$) and wait times.
   - Inspect radar performance metrics comparing AI-Adaptive control against legacy fixed timers.
   - Click **"Download Audit Report (.CSV)"** to export traffic performance data.
