"""
Vehicle Model and Physics
Defines vehicle types, kinematic parameters, and state tracking.
"""

from enum import Enum
import uuid
import math
from typing import Optional


class VehicleType(str, Enum):
    CAR = "CAR"
    BUS = "BUS"
    TRUCK = "TRUCK"
    MOTORCYCLE = "MOTORCYCLE"
    AMBULANCE = "AMBULANCE"


VEHICLE_CONFIGS = {
    VehicleType.CAR: {
        "length": 4.5,
        "width": 1.9,
        "max_speed": 13.8,  # ~50 km/h (m/s)
        "accel": 2.5,       # m/s^2
        "decel": 4.5,       # m/s^2
        "pcu": 1.0,
        "color": "#38bdf8", # Sky blue
    },
    VehicleType.BUS: {
        "length": 11.0,
        "width": 2.6,
        "max_speed": 10.0,  # ~36 km/h
        "accel": 1.5,
        "decel": 3.5,
        "pcu": 2.5,
        "color": "#fbbf24", # Amber
    },
    VehicleType.TRUCK: {
        "length": 13.0,
        "width": 2.6,
        "max_speed": 9.0,   # ~32 km/h
        "accel": 1.2,
        "decel": 3.0,
        "pcu": 3.0,
        "color": "#a855f7", # Purple
    },
    VehicleType.MOTORCYCLE: {
        "length": 2.2,
        "width": 0.9,
        "max_speed": 14.5,  # ~52 km/h
        "accel": 3.2,
        "decel": 5.0,
        "pcu": 0.5,
        "color": "#34d399", # Emerald green
    },
    VehicleType.AMBULANCE: {
        "length": 6.5,
        "width": 2.2,
        "max_speed": 16.5,  # ~60 km/h
        "accel": 3.5,
        "decel": 5.5,
        "pcu": 50.0,
        "color": "#ef4444", # High-vis Red
    }
}


class Vehicle:
    """
    Simulated vehicle navigating a single approach lane toward the intersection.
    Distance represents meters remaining until the intersection stop line (0m).
    """

    def __init__(
        self,
        vehicle_id: Optional[str] = None,
        vehicle_type: VehicleType = VehicleType.CAR,
        origin_lane: str = "north",
        initial_distance: float = 150.0,
        initial_speed: float = 10.0,
        destination_turn: str = "straight", # left, straight, right
    ):
        self.vehicle_id = vehicle_id or f"veh_{uuid.uuid4().hex[:6]}"
        self.vehicle_type = vehicle_type
        self.origin_lane = origin_lane
        self.destination_turn = destination_turn

        config = VEHICLE_CONFIGS[vehicle_type]
        self.length = config["length"]
        self.width = config["width"]
        self.max_speed = config["max_speed"]
        self.max_accel = config["accel"]
        self.max_decel = config["decel"]
        self.pcu = config["pcu"]
        self.color = config["color"]
        self.is_emergency = (vehicle_type == VehicleType.AMBULANCE)

        # Kinematics
        self.distance = initial_distance  # meters to stop line (0 = stop line, negative = crossed)
        self.speed = min(initial_speed, self.max_speed)
        self.acceleration = 0.0

        # State tracking
        self.wait_time = 0.0
        self.total_trip_time = 0.0
        self.has_crossed = False
        self.is_stopped = False
        self.spawn_timestamp = 0.0

    def update_kinematics(
        self,
        dt: float,
        lead_vehicle: Optional["Vehicle"],
        is_green: bool,
        is_yellow: bool,
        stop_line_dist: float = 0.0,
    ):
        """
        Intelligent Driver Model (IDM) inspired longitudinal car-following update.
        """
        self.total_trip_time += dt

        # Target desired distance & speed
        desired_speed = self.max_speed
        min_gap = 2.5 # safe minimum distance in meters
        desired_time_headway = 1.2 # seconds

        # Determine virtual obstacle: lead vehicle or red/yellow traffic light
        obstacle_dist = float("inf")
        obstacle_speed = 0.0

        # 1. Lead vehicle in same lane ahead of us
        if lead_vehicle is not None:
            gap_to_lead = (self.distance - lead_vehicle.distance) - lead_vehicle.length
            if gap_to_lead < obstacle_dist:
                obstacle_dist = max(0.1, gap_to_lead)
                obstacle_speed = lead_vehicle.speed

        # 2. Traffic Light at stop line (distance = 0)
        # If signal is RED or YELLOW and we haven't crossed the stop line yet
        if not self.has_crossed and self.distance > 0:
            if not is_green:
                # If yellow, aggressive or emergency vehicles might proceed if too close to stop safely
                stopping_distance = (self.speed ** 2) / (2 * self.max_decel + 1e-5)
                should_stop = not (is_yellow and (self.distance < stopping_distance or self.is_emergency))
                if should_stop:
                    gap_to_light = self.distance
                    if gap_to_light < obstacle_dist:
                        obstacle_dist = gap_to_light
                        obstacle_speed = 0.0

        # Acceleration calculation (IDM logic)
        delta_v = self.speed - obstacle_speed
        s_star = min_gap + max(0.0, self.speed * desired_time_headway + (self.speed * delta_v) / (2 * math.sqrt(self.max_accel * self.max_decel) + 1e-5))

        accel_free = self.max_accel * (1.0 - (self.speed / (desired_speed + 1e-5)) ** 4)
        accel_interaction = -self.max_accel * ((s_star / obstacle_dist) ** 2) if obstacle_dist > 0 else -self.max_decel

        target_accel = accel_free + accel_interaction
        self.acceleration = max(-self.max_decel, min(self.max_accel, target_accel))

        # Update speed & position
        self.speed = max(0.0, min(self.max_speed, self.speed + self.acceleration * dt))
        self.distance -= self.speed * dt

        # Stopped check for wait time accumulation
        if self.speed < 0.5:
            self.is_stopped = True
            self.wait_time += dt
        else:
            self.is_stopped = False

        if self.distance <= 0 and not self.has_crossed:
            self.has_crossed = True

    def to_dict(self) -> dict:
        return {
            "id": self.vehicle_id,
            "type": self.vehicle_type.value,
            "lane": self.origin_lane,
            "distance": round(self.distance, 1),
            "speed": round(self.speed * 3.6, 1), # km/h
            "wait_time": round(self.wait_time, 1),
            "pcu": self.pcu,
            "color": self.color,
            "is_emergency": self.is_emergency,
            "has_crossed": self.has_crossed
        }
