import numpy as np
import pytest
from core.vision.detector import TrafficVisionDetector
from core.vision.tracker import CentroidTracker
from core.vision.density import LaneDensityEstimator


def test_centroid_tracker_lifecycle():
    tracker = CentroidTracker(max_disappeared=5, max_distance=50.0)
    
    # Frame 1: 1 detection
    detections = [(100, 100, 40, 20, "CAR", 0.9)]
    objects = tracker.update(detections, dt=0.033)
    assert len(objects) == 1
    assert objects[0].object_id == 1
    
    # Frame 2: Vehicle moved slightly
    detections = [(105, 105, 40, 20, "CAR", 0.9)]
    objects = tracker.update(detections, dt=0.033)
    assert len(objects) == 1
    assert objects[0].object_id == 1
    assert len(objects[0].trajectory) == 2


def test_lane_density_estimator():
    estimator = LaneDensityEstimator(frame_width=640, frame_height=480)
    
    class MockObj:
        def __init__(self, cx, cy, label="CAR"):
            self.centroid = (cx, cy)
            self.bbox = (cx - 15, cy - 10, 30, 20)
            self.label = label
            
    # Mock vehicles in Lane 1 ROI (x: 0.05 to 0.4 -> 32 to 256, y: 0.2 to 0.7 -> 96 to 336)
    objs = [MockObj(100, 150), MockObj(120, 200)]
    densities = estimator.estimate_lane_density(objs)
    
    assert "lane_1" in densities
    assert densities["lane_1"]["vehicle_count"] == 2
    assert densities["lane_1"]["congestion_level"] in ("LOW", "CLEAR", "MODERATE", "HEAVY")


def test_vision_detector_frame_processing():
    detector = TrafficVisionDetector()
    synthetic_frame = np.full((480, 640, 3), 50, dtype=np.uint8)
    
    annotated, stats = detector.process_frame(synthetic_frame)
    assert annotated.shape == (480, 640, 3)
    assert "fps" in stats
    assert "lane_densities" in stats
    
    jpeg_bytes = detector.encode_jpeg(annotated)
    assert len(jpeg_bytes) > 0
