"""
Lane Density & ROI Occupancy Estimator
Calculates spatial vehicle occupancy, queue density, and congestion indices within defined Regions of Interest (ROIs).
"""

from typing import Dict, List, Tuple
import numpy as np


class LaneDensityEstimator:
    def __init__(self, frame_width: int = 640, frame_height: int = 480):
        self.frame_width = frame_width
        self.frame_height = frame_height

        # Predefined 4-lane ROIs as normalized polygons or bounding boxes
        self.lane_rois: Dict[str, Dict] = {
            "lane_1": {"name": "Northbound / Lane 1", "roi": (0.05, 0.2, 0.4, 0.7)}, # (x1_pct, y1_pct, x2_pct, y2_pct)
            "lane_2": {"name": "Southbound / Lane 2", "roi": (0.55, 0.2, 0.95, 0.7)},
        }

    def set_custom_rois(self, rois: Dict[str, Dict]):
        self.lane_rois = rois

    def estimate_lane_density(self, tracked_objects: list) -> Dict[str, dict]:
        """
        Calculates vehicle distribution and queue level across monitored lane ROIs.
        """
        results = {}

        for lane_id, info in self.lane_rois.items():
            x1_p, y1_p, x2_p, y2_p = info["roi"]
            x1 = int(x1_p * self.frame_width)
            y1 = int(y1_p * self.frame_height)
            x2 = int(x2_p * self.frame_width)
            y2 = int(y2_p * self.frame_height)
            roi_area = max(1, (x2 - x1) * (y2 - y1))

            vehs_in_roi = []
            occupied_area = 0

            for obj in tracked_objects:
                cx, cy = obj.centroid
                if x1 <= cx <= x2 and y1 <= cy <= y2:
                    vehs_in_roi.append(obj)
                    bx, by, bw, bh = obj.bbox
                    occupied_area += bw * bh

            occupancy_ratio = min(1.0, occupied_area / roi_area)
            vehicle_count = len(vehs_in_roi)

            # Categorize congestion status
            if vehicle_count == 0:
                congestion_level = "CLEAR"
            elif occupancy_ratio < 0.3:
                congestion_level = "LOW"
            elif occupancy_ratio < 0.65:
                congestion_level = "MODERATE"
            else:
                congestion_level = "HEAVY"

            results[lane_id] = {
                "name": info["name"],
                "vehicle_count": vehicle_count,
                "occupancy_pct": round(occupancy_ratio * 100, 1),
                "congestion_level": congestion_level,
                "has_emergency": any(obj.label.upper() == "AMBULANCE" for obj in vehs_in_roi),
                "roi_coords": [x1, y1, x2, y2]
            }

        return results
