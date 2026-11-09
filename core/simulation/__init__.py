"""
Simulation Engine
Handles micro-simulation of 4-way multi-lane intersections, vehicle physics,
scenario triggers (rush hour, lane blockages, emergency dispatches), and telemetry collection.
"""

from .vehicle import Vehicle, VehicleType
from .intersection import IntersectionSimulation
from .metrics import TrafficMetricsTracker

__all__ = ["Vehicle", "VehicleType", "IntersectionSimulation", "TrafficMetricsTracker"]
