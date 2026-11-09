import pytest
from core.simulation.vehicle import Vehicle, VehicleType
from core.simulation.intersection import IntersectionSimulation
from core.simulation.metrics import TrafficMetricsTracker


def test_vehicle_kinematics_stop_at_red():
    veh = Vehicle(
        vehicle_type=VehicleType.CAR,
        origin_lane="north",
        initial_distance=25.0,
        initial_speed=8.0
    )
    
    # Red light: vehicle should decelerate and come to a stop before the stop line (distance > 0)
    for _ in range(80):
        veh.update_kinematics(dt=0.1, lead_vehicle=None, is_green=False, is_yellow=False)
    
    assert veh.distance >= 0.0
    assert veh.speed < 1.0
    assert veh.is_stopped


def test_vehicle_kinematics_proceed_at_green():
    veh = Vehicle(
        vehicle_type=VehicleType.CAR,
        origin_lane="north",
        initial_distance=10.0,
        initial_speed=8.0
    )
    
    # Green light: vehicle should cross stop line
    for _ in range(30):
        veh.update_kinematics(dt=0.1, lead_vehicle=None, is_green=True, is_yellow=False)
    
    assert veh.has_crossed
    assert veh.distance < 0.0


def test_intersection_simulation_step():
    sim = IntersectionSimulation(mode="ADAPTIVE")
    
    # Step simulation 50 iterations
    for _ in range(50):
        frame = sim.step(dt=0.1)
    
    assert "signals" in frame
    assert "controller_status" in frame
    assert "metrics" in frame
    assert "vehicles" in frame
    assert frame["mode"] == "ADAPTIVE"


def test_metrics_tracker():
    tracker = TrafficMetricsTracker()
    tracker.record_vehicle_departure(wait_time=12.0, pcu=1.0)
    tracker.record_vehicle_departure(wait_time=18.0, pcu=2.5)
    
    summary = tracker.get_summary(active_vehicles_wait=0.0, active_vehicle_count=0, lane_queues={"north": 0})
    assert summary["total_vehicles_passed"] == 2
    assert summary["avg_wait_time_sec"] == 15.0
    assert summary["max_wait_time_sec"] == 18.0
    assert summary["emissions"]["idle_co2_kg"] > 0
