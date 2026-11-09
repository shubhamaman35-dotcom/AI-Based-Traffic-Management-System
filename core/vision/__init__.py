"""
Computer Vision & Video Analysis Package
Vehicle detection, lane-based counting, tracking, and emergency vehicle recognition.
"""

from .detector import TrafficVisionDetector, DetectionResult
from .tracker import CentroidTracker
from .density import LaneDensityEstimator

__all__ = ["TrafficVisionDetector", "DetectionResult", "CentroidTracker", "LaneDensityEstimator"]
