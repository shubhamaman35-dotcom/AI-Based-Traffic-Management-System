"""
AI Computer Vision Traffic Detector & Video Processor
Performs real-time vehicle detection, emergency vehicle identification,
lane density estimation, and visual HUD overlays.
"""

from dataclasses import dataclass
from typing import List, Tuple, Dict, Optional
import cv2
import numpy as np
import time
from .tracker import CentroidTracker, TrackedVehicle
from .density import LaneDensityEstimator


@dataclass
class DetectionResult:
    bbox: Tuple[int, int, int, int] # x, y, w, h
    label: str
    confidence: float
    is_emergency: bool


class TrafficVisionDetector:
    def __init__(self, min_area: int = 1200, max_area: int = 40000):
        self.min_area = min_area
        self.max_area = max_area

        # Background subtractor for robust motion-based vehicle detection
        self.bg_subtractor = cv2.createBackgroundSubtractorMOG2(
            history=200, varThreshold=25, detectShadows=True
        )

        # Multi-object tracker
        self.tracker = CentroidTracker(max_disappeared=15, max_distance=50.0)

        # Density estimator
        self.density_estimator = LaneDensityEstimator()

        # Cumulative Counters
        self.total_counted_in = 0
        self.total_counted_out = 0
        self.vehicle_counts_by_type = {"CAR": 0, "BUS": 0, "TRUCK": 0, "MOTORCYCLE": 0, "AMBULANCE": 0}

        # Counting Line Y-position (normalized ratio of frame height)
        self.count_line_y_ratio = 0.55

        # Performance stats
        self.fps = 0.0
        self.last_frame_time = time.time()

    def _classify_vehicle_contour(self, w: int, h: int, area: float, roi_crop: Optional[np.ndarray]) -> Tuple[str, bool]:
        """
        Classifies detected object based on geometry, aspect ratio, and emergency color cues.
        """
        aspect_ratio = float(w) / max(1, h)
        is_emergency = False

        # Emergency vehicle color check (high saturation red/white or siren patterns)
        if roi_crop is not None and roi_crop.size > 0:
            hsv = cv2.cvtColor(roi_crop, cv2.COLOR_BGR2HSV)
            # Red color mask in HSV
            mask1 = cv2.inRange(hsv, np.array([0, 70, 50]), np.array([10, 255, 255]))
            mask2 = cv2.inRange(hsv, np.array([170, 70, 50]), np.array([180, 255, 255]))
            red_mask = mask1 | mask2
            red_ratio = np.sum(red_mask > 0) / float(roi_crop.shape[0] * roi_crop.shape[1])
            if red_ratio > 0.18 and area > 2000:
                is_emergency = True
                return "AMBULANCE", True

        if area > 14000 or (h > 90 and w > 120):
            return "TRUCK", False
        elif area > 7500 or h > 80:
            return "BUS", False
        elif area < 2500 or (aspect_ratio < 0.6 and area < 3500):
            return "MOTORCYCLE", False
        else:
            return "CAR", False

    def process_frame(self, frame: np.ndarray) -> Tuple[np.ndarray, dict]:
        """
        Processes a single BGR video frame:
        1. Runs background subtraction & morphological cleaning
        2. Detects bounding boxes and classifies vehicle types
        3. Updates centroid tracker and speed vectors
        4. Calculates lane density & line-crossing counts
        5. Renders futuristic cyber-styled visual HUD overlay
        """
        current_time = time.time()
        dt = max(0.001, current_time - self.last_frame_time)
        self.fps = 0.9 * self.fps + 0.1 * (1.0 / dt)
        self.last_frame_time = current_time

        h, w = frame.shape[:2]
        self.density_estimator.frame_width = w
        self.density_estimator.frame_height = h

        # Preprocessing: Blur & Background Subtraction
        blurred = cv2.GaussianBlur(frame, (5, 5), 0)
        fg_mask = self.bg_subtractor.apply(blurred)

        # Remove shadows (gray value 127 in MOG2) and apply morphology
        _, thresh = cv2.threshold(fg_mask, 200, 255, cv2.THRESH_BINARY)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        cleaned = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel, iterations=2)
        cleaned = cv2.dilate(cleaned, kernel, iterations=1)

        # Find Contours
        contours, _ = cv2.findContours(cleaned, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        detections = []

        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < self.min_area or area > self.max_area:
                continue

            x, y, bw, bh = cv2.boundingRect(cnt)
            roi_crop = frame[max(0, y):min(h, y + bh), max(0, x):min(w, x + bw)]
            label, is_emerg = self._classify_vehicle_contour(bw, bh, area, roi_crop)
            confidence = min(0.98, 0.70 + (area / self.max_area) * 0.28)
            detections.append((x, y, bw, bh, label, confidence))

        # Update Centroid Tracker
        tracked_objects = self.tracker.update(detections, dt)

        # Counting Line
        count_line_y = int(h * self.count_line_y_ratio)

        for obj in tracked_objects:
            if not obj.has_counted and len(obj.trajectory) >= 2:
                prev_y = obj.trajectory[-2][1]
                curr_y = obj.centroid[1]

                if prev_y < count_line_y <= curr_y: # Moving downwards
                    self.total_counted_in += 1
                    self.vehicle_counts_by_type[obj.label] = self.vehicle_counts_by_type.get(obj.label, 0) + 1
                    obj.has_counted = True
                elif prev_y > count_line_y >= curr_y: # Moving upwards
                    self.total_counted_out += 1
                    self.vehicle_counts_by_type[obj.label] = self.vehicle_counts_by_type.get(obj.label, 0) + 1
                    obj.has_counted = True

        # Estimate Lane Density
        lane_densities = self.density_estimator.estimate_lane_density(tracked_objects)

        # --- Visual Annotations ---
        annotated = frame.copy()

        # Draw Lane ROI boxes
        for lane_id, ldata in lane_densities.items():
            rx1, ry1, rx2, ry2 = ldata["roi_coords"]
            color = (0, 255, 0) if ldata["congestion_level"] in ("CLEAR", "LOW") else (0, 165, 255) if ldata["congestion_level"] == "MODERATE" else (0, 0, 255)
            cv2.rectangle(annotated, (rx1, ry1), (rx2, ry2), color, 1)
            cv2.putText(
                annotated,
                f"{ldata['name']}: {ldata['vehicle_count']} veh ({ldata['congestion_level']})",
                (rx1 + 5, ry1 + 20),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                color,
                1,
                cv2.LINE_AA,
            )

        # Draw Counting Line
        cv2.line(annotated, (0, count_line_y), (w, count_line_y), (0, 255, 255), 2)
        cv2.putText(annotated, "VIRTUAL CORDON / COUNT LINE", (10, count_line_y - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 1, cv2.LINE_AA)

        # Draw Bounding Boxes and IDs
        for obj in tracked_objects:
            bx, by, bw, bh = obj.bbox
            is_amb = (obj.label == "AMBULANCE")

            box_color = (0, 0, 255) if is_amb else (255, 191, 0) if obj.label == "BUS" else (255, 105, 180) if obj.label == "TRUCK" else (0, 255, 127) if obj.label == "MOTORCYCLE" else (255, 200, 50)

            # Box corners
            cv2.rectangle(annotated, (bx, by), (bx + bw, by + bh), box_color, 2)

            # Trajectory Trail
            for pt_idx in range(1, len(obj.trajectory)):
                cv2.line(annotated, obj.trajectory[pt_idx - 1], obj.trajectory[pt_idx], box_color, 1)

            # Label badge
            speed_kmh = int(obj.speed_px_per_sec * 0.15) # simulated conversion
            badge_text = f"#{obj.object_id} {obj.label} [{speed_kmh} km/h]"
            if is_amb:
                badge_text = f"EMERGENCY #{obj.object_id} {obj.label}"

            # Badge background
            (tw, th), _ = cv2.getTextSize(badge_text, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
            cv2.rectangle(annotated, (bx, max(0, by - 18)), (bx + tw + 6, max(0, by)), box_color, -1)
            cv2.putText(annotated, badge_text, (bx + 3, max(0, by - 4)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0) if not is_amb else (255, 255, 255), 1, cv2.LINE_AA)

        # HUD Top Banner
        overlay = annotated.copy()
        cv2.rectangle(overlay, (0, 0), (w, 42), (20, 24, 33), -1)
        cv2.addWeighted(overlay, 0.85, annotated, 0.15, 0, annotated)

        cv2.putText(annotated, f"AI VISION STREAM | FPS: {self.fps:.1f}", (15, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (56, 189, 248), 2, cv2.LINE_AA)
        cv2.putText(annotated, f"COUNT IN: {self.total_counted_in}  OUT: {self.total_counted_out}  ACTIVE: {len(tracked_objects)}", (w - 380, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (255, 255, 255), 1, cv2.LINE_AA)

        stats = {
            "fps": round(self.fps, 1),
            "active_vehicles": len(tracked_objects),
            "total_in": self.total_counted_in,
            "total_out": self.total_counted_out,
            "vehicle_type_counts": self.vehicle_counts_by_type,
            "lane_densities": lane_densities,
            "emergency_detected": any(obj.label == "AMBULANCE" for obj in tracked_objects)
        }

        return annotated, stats

    def encode_jpeg(self, frame: np.ndarray, quality: int = 80) -> bytes:
        """Encode OpenCV image to JPEG bytes for MJPEG streaming."""
        encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), quality]
        _, buffer = cv2.imencode(".jpg", frame, encode_param)
        return buffer.tobytes()
