"""
4-Way Multi-Lane Intersection Simulation Environment
Coordinates vehicle generation, motion dynamics, signal synchronization,
scenario triggers, and telemetry extraction.
"""

from typing import Dict, List, Optional
import random
import time
from .vehicle import Vehicle, VehicleType
from .metrics import TrafficMetricsTracker
from ..controller.adaptive_signal import AdaptiveSignalController, LaneTrafficState, SignalState
from ..controller.emergency import EmergencyPreemptionManager
from ..controller.baseline_signals import FixedTimeController, ActuatedController


class IntersectionSimulation:
    def __init__(
        self,
        mode: str = "ADAPTIVE", # ADAPTIVE, FIXED_TIME, ACTUATED
        spawn_rate_scale: float = 1.0,
    ):
        self.lane_ids = ["north", "south", "east", "west"]
        self.mode = mode
        self.spawn_rate_scale = spawn_rate_scale

        # Signal Controllers
        self.adaptive_controller = AdaptiveSignalController(self.lane_ids)
        self.emergency_manager = EmergencyPreemptionManager(self.adaptive_controller)
        self.fixed_controller = FixedTimeController(self.lane_ids, fixed_green=25.0)
        self.actuated_controller = ActuatedController(self.lane_ids)

        # Vehicles mapped by lane
        self.vehicles_by_lane: Dict[str, List[Vehicle]] = {lid: [] for lid in self.lane_ids}
        self.completed_vehicles: List[Vehicle] = []

        # Lane conditions (e.g. blockage/accident)
        self.blocked_lanes: Dict[str, bool] = {lid: False for lid in self.lane_ids}

        # Metrics Tracker
        self.metrics = TrafficMetricsTracker()

        # Spawn timers (seconds until next vehicle spawn per lane)
        self.spawn_timers: Dict[str, float] = {lid: random.uniform(1.0, 3.0) for lid in self.lane_ids}

        # Scenario settings
        self.current_scenario: str = "NORMAL" # NORMAL, RUSH_HOUR, EMERGENCY_TEST, RAINY, BLOCKAGE
        self.simulation_speed: float = 1.0 # 1.0x, 2.0x, etc.

    def set_mode(self, mode: str):
        """Switch controller mode: ADAPTIVE, FIXED_TIME, ACTUATED."""
        if mode in ("ADAPTIVE", "FIXED_TIME", "ACTUATED"):
            self.mode = mode

    def set_scenario(self, scenario: str):
        """Configure scenario preset."""
        self.current_scenario = scenario
        if scenario == "RUSH_HOUR":
            self.spawn_rate_scale = 2.5
        elif scenario == "RAINY":
            self.spawn_rate_scale = 1.2
        elif scenario == "NORMAL":
            self.spawn_rate_scale = 1.0
            self.blocked_lanes = {lid: False for lid in self.lane_ids}
        elif scenario == "BLOCKAGE":
            self.blocked_lanes["east"] = True

    def trigger_emergency_vehicle(self, lane_id: str = "north") -> str:
        """Manually or dynamically dispatch an emergency ambulance on a specific lane."""
        if lane_id not in self.lane_ids:
            lane_id = "north"

        amb = Vehicle(
            vehicle_type=VehicleType.AMBULANCE,
            origin_lane=lane_id,
            initial_distance=140.0,
            initial_speed=12.0,
        )
        self.vehicles_by_lane[lane_id].append(amb)
        self.emergency_manager.register_emergency(amb.vehicle_id, lane_id, "AMBULANCE", amb.distance)
        return amb.vehicle_id

    def toggle_lane_blockage(self, lane_id: str) -> bool:
        if lane_id in self.blocked_lanes:
            self.blocked_lanes[lane_id] = not self.blocked_lanes[lane_id]
            return self.blocked_lanes[lane_id]
        return False

    def _spawn_vehicle_if_due(self, lane_id: str, dt: float):
        if self.blocked_lanes.get(lane_id, False):
            return

        self.spawn_timers[lane_id] -= dt
        if self.spawn_timers[lane_id] <= 0:
            # Base interval modified by scenario scale
            base_interval = random.uniform(2.5, 6.0) / max(0.2, self.spawn_rate_scale)
            self.spawn_timers[lane_id] = base_interval

            # Check if entrance is clear (distance > 130m)
            lane_vehs = self.vehicles_by_lane[lane_id]
            if not lane_vehs or lane_vehs[-1].distance < 135.0:
                # Random vehicle type selection with realistic urban distribution
                r = random.random()
                if r < 0.65:
                    v_type = VehicleType.CAR
                elif r < 0.80:
                    v_type = VehicleType.MOTORCYCLE
                elif r < 0.92:
                    v_type = VehicleType.BUS
                else:
                    v_type = VehicleType.TRUCK

                veh = Vehicle(
                    vehicle_type=v_type,
                    origin_lane=lane_id,
                    initial_distance=150.0,
                    initial_speed=random.uniform(7.0, 11.0),
                )
                self.vehicles_by_lane[lane_id].append(veh)

    def _sync_lane_states_to_adaptive(self):
        """Synthesizes computer vision sensor counts into the adaptive controller."""
        for lid in self.lane_ids:
            vehs = [v for v in self.vehicles_by_lane[lid] if v.distance >= -5.0]
            cars = sum(1 for v in vehs if v.vehicle_type == VehicleType.CAR)
            buses = sum(1 for v in vehs if v.vehicle_type == VehicleType.BUS)
            trucks = sum(1 for v in vehs if v.vehicle_type == VehicleType.TRUCK)
            bikes = sum(1 for v in vehs if v.vehicle_type == VehicleType.MOTORCYCLE)
            emergencies = sum(1 for v in vehs if v.is_emergency)

            total_wait = sum(v.wait_time for v in vehs)
            max_wait = max((v.wait_time for v in vehs), default=0.0)
            avg_spd = (sum(v.speed * 3.6 for v in vehs) / len(vehs)) if vehs else 40.0

            state = LaneTrafficState(
                lane_id=lid,
                cars=cars,
                buses=buses,
                trucks=trucks,
                motorcycles=bikes,
                emergency_vehicles=emergencies,
                avg_speed_kmh=round(avg_spd, 1),
                accumulated_wait_time=round(total_wait, 1),
                max_wait_time=round(max_wait, 1),
                is_blocked=self.blocked_lanes.get(lid, False)
            )
            self.adaptive_controller.update_lane_state(lid, state)

    def step(self, dt: float = 0.1) -> dict:
        """
        Advance the simulation by dt seconds.
        Updates signals, moves vehicles, handles departures, and aggregates metrics.
        """
        dt_eff = dt * self.simulation_speed

        # 1. Spawn new vehicles
        for lid in self.lane_ids:
            self._spawn_vehicle_if_due(lid, dt_eff)

        # 2. Update and evaluate Signal Controller
        signals: Dict[str, SignalState] = {}

        if self.mode == "ADAPTIVE":
            self._sync_lane_states_to_adaptive()
            # Check for active emergency preemption override
            preempt_signals = self.emergency_manager.step(dt_eff)
            if preempt_signals is not None:
                signals = preempt_signals
            else:
                signals = self.adaptive_controller.step(dt_eff)

        elif self.mode == "FIXED_TIME":
            signals = self.fixed_controller.step(dt_eff)

        elif self.mode == "ACTUATED":
            # If vehicle is waiting at stop line, extend green
            active_phase_lanes = self.actuated_controller.active_phase.active_lanes
            for lid in active_phase_lanes:
                if any(v.distance < 20.0 and not v.has_crossed for v in self.vehicles_by_lane[lid]):
                    self.actuated_controller.extend_green_on_detection()
            signals = self.actuated_controller.step(dt_eff)

        # 3. Update Vehicle Kinematics
        for lid in self.lane_ids:
            lane_vehs = self.vehicles_by_lane[lid]
            is_green = (signals.get(lid) == SignalState.GREEN)
            is_yellow = (signals.get(lid) == SignalState.YELLOW)

            # Sort vehicles by distance ascending (closest to stop line first)
            lane_vehs.sort(key=lambda v: v.distance)

            to_remove = []
            for i, veh in enumerate(lane_vehs):
                lead = lane_vehs[i - 1] if i > 0 else None
                veh.update_kinematics(dt_eff, lead, is_green, is_yellow)

                # Check if emergency vehicle just crossed stop line
                if veh.is_emergency and veh.has_crossed:
                    self.emergency_manager.clear_emergency(veh.vehicle_id)

                # If vehicle has passed far past the intersection (-40m), remove it
                if veh.distance <= -40.0:
                    self.metrics.record_vehicle_departure(veh.wait_time, veh.pcu)
                    to_remove.append(veh)

            for rem in to_remove:
                lane_vehs.remove(rem)

        # 4. Compile Frame Data
        return self.get_frame_state(signals)

    def get_frame_state(self, current_signals: Optional[Dict[str, SignalState]] = None) -> dict:
        """Returns snapshot of current intersection frame for UI streaming."""
        if current_signals is None:
            if self.mode == "ADAPTIVE":
                preempt = self.emergency_manager.get_status()
                if preempt["is_corridor_active"] or preempt["preemption_state"] != "IDLE":
                    current_signals = self.emergency_manager.step(0.0) or self.adaptive_controller.get_current_lane_signals()
                else:
                    current_signals = self.adaptive_controller.get_current_lane_signals()
            elif self.mode == "FIXED_TIME":
                current_signals = self.fixed_controller.get_current_lane_signals()
            else:
                current_signals = self.actuated_controller.get_current_lane_signals()

        # Serialize active vehicles
        all_vehicles = []
        total_active_wait = 0.0
        active_count = 0
        lane_queues = {}

        for lid, vlist in self.vehicles_by_lane.items():
            queue_len = sum(1 for v in vlist if v.is_stopped and not v.has_crossed)
            lane_queues[lid] = queue_len
            for v in vlist:
                all_vehicles.append(v.to_dict())
                if not v.has_crossed:
                    total_active_wait += v.wait_time
                    active_count += 1

        # Controller status info
        if self.mode == "ADAPTIVE":
            ctrl_summary = self.adaptive_controller.get_status_summary()
        elif self.mode == "FIXED_TIME":
            ctrl_summary = self.fixed_controller.get_status_summary()
        else:
            ctrl_summary = self.actuated_controller.get_status_summary()

        metrics_summary = self.metrics.get_summary(total_active_wait, active_count, lane_queues)
        emergency_status = self.emergency_manager.get_status()

        return {
            "mode": self.mode,
            "scenario": self.current_scenario,
            "signals": {k: v.value if isinstance(v, SignalState) else v for k, v in current_signals.items()},
            "controller_status": ctrl_summary,
            "emergency_status": emergency_status,
            "blocked_lanes": self.blocked_lanes,
            "vehicles": all_vehicles,
            "metrics": metrics_summary,
            "timestamp": time.time()
        }
