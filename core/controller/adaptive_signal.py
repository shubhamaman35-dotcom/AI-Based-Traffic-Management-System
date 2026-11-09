"""
AI-Based Adaptive Signal Controller
Calculates dynamic green light times based on real-time vehicle classification,
Passenger Car Units (PCU), queue length, and starvation wait times.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional
import time


class SignalState(str, Enum):
    RED = "RED"
    YELLOW = "YELLOW"
    GREEN = "GREEN"


@dataclass
class LaneTrafficState:
    lane_id: str
    cars: int = 0
    buses: int = 0
    trucks: int = 0
    motorcycles: int = 0
    emergency_vehicles: int = 0
    avg_speed_kmh: float = 30.0
    accumulated_wait_time: float = 0.0
    max_wait_time: float = 0.0
    is_blocked: bool = False

    @property
    def total_vehicles(self) -> int:
        return self.cars + self.buses + self.trucks + self.motorcycles + self.emergency_vehicles

    @property
    def pcu_density(self) -> float:
        """
        Calculate Passenger Car Unit (PCU) equivalent density:
        - Car: 1.0
        - Bus: 2.5
        - Truck: 3.0
        - Motorcycle: 0.5
        - Emergency: 50.0 (high priority)
        """
        if self.is_blocked:
            return 0.0
        return (
            self.cars * 1.0
            + self.buses * 2.5
            + self.trucks * 3.0
            + self.motorcycles * 0.5
            + self.emergency_vehicles * 50.0
        )

    @property
    def urgency_score(self) -> float:
        """
        Urgency combines vehicle load density + starvation penalty.
        Ensures low-traffic lanes don't wait indefinitely.
        """
        # Starvation weight: each second of max wait time adds 0.2 PCU equivalent
        starvation_bonus = self.max_wait_time * 0.2
        return self.pcu_density + starvation_bonus


@dataclass
class SignalPhase:
    phase_id: str
    name: str
    active_lanes: List[str]
    green_duration: float = 15.0
    yellow_duration: float = 3.0
    all_red_duration: float = 1.0


class AdaptiveSignalController:
    """
    Intelligent dynamic signal controller using real-time PCU density,
    traffic saturation estimation, and anti-starvation fair scheduling.
    """

    def __init__(
        self,
        lane_ids: Optional[List[str]] = None,
        min_green: float = 8.0,
        max_green: float = 60.0,
        yellow_time: float = 3.0,
        all_red_time: float = 1.0,
        cycle_base_time: float = 10.0,
    ):
        self.lane_ids = lane_ids or ["north", "south", "east", "west"]
        self.min_green = min_green
        self.max_green = max_green
        self.yellow_time = yellow_time
        self.all_red_time = all_red_time
        self.cycle_base_time = cycle_base_time

        # Define 4-phase or paired phases (North, South, East, West)
        self.phases: List[SignalPhase] = [
            SignalPhase("P_NORTH", "North Approach", ["north"]),
            SignalPhase("P_SOUTH", "South Approach", ["south"]),
            SignalPhase("P_EAST", "East Approach", ["east"]),
            SignalPhase("P_WEST", "West Approach", ["west"]),
        ]

        self.current_phase_index: int = 0
        self.current_state: SignalState = SignalState.GREEN
        self.time_in_current_state: float = 0.0
        self.current_allocated_green: float = min_green

        # Lane state tracking
        self.lane_states: Dict[str, LaneTrafficState] = {
            lid: LaneTrafficState(lane_id=lid) for lid in self.lane_ids
        }

        # History and Analytics
        self.cycle_count: int = 0
        self.phase_history: List[dict] = []

    @property
    def active_phase(self) -> SignalPhase:
        return self.phases[self.current_phase_index]

    def update_lane_state(self, lane_id: str, state: LaneTrafficState):
        """Update sensor / vision data for a given lane."""
        if lane_id in self.lane_states:
            self.lane_states[lane_id] = state

    def compute_dynamic_green_time(self, phase: SignalPhase) -> float:
        """
        Dynamic Green Time Algorithm:
        Computes optimal green time based on current PCU density in active lanes
        relative to the total intersection load.
        """
        active_pcu = sum(self.lane_states[lid].pcu_density for lid in phase.active_lanes if lid in self.lane_states)
        total_pcu = sum(s.pcu_density for s in self.lane_states.values())

        if total_pcu <= 0 or active_pcu <= 0:
            return self.min_green

        # Linear + Saturation Scaling:
        # Base green + (active_pcu / total_pcu) * proportional band + queue discharge factor (approx 1.8s per PCU)
        discharge_time = active_pcu * 1.8
        proportional_time = (active_pcu / total_pcu) * 45.0
        calculated_green = max(discharge_time, proportional_time, self.min_green)

        # Clamping within min/max bounds
        clamped_green = min(max(calculated_green, self.min_green), self.max_green)
        return round(clamped_green, 1)

    def select_next_phase(self) -> int:
        """
        AI Selection: Choose next phase with the highest urgency score
        (Density + Starvation prevention). If tie, cycles round-robin.
        """
        scores = []
        for idx, phase in enumerate(self.phases):
            # Don't pick the same phase immediately unless it's the only one with traffic
            is_current = (idx == self.current_phase_index)
            score = sum(self.lane_states[lid].urgency_score for lid in phase.active_lanes if lid in self.lane_states)
            if is_current:
                score *= 0.1  # heavily penalize staying on same phase immediately to ensure fair rotation
            scores.append((score, idx))

        # Sort descending by score
        scores.sort(key=lambda x: x[0], reverse=True)
        best_score, best_idx = scores[0]

        # If all scores are very low, fallback to sequential round-robin
        if best_score <= 0.1:
            return (self.current_phase_index + 1) % len(self.phases)

        return best_idx

    def step(self, dt: float = 1.0) -> dict:
        """
        Advance controller state by dt seconds.
        Returns the current signal states for all lanes.
        """
        self.time_in_current_state += dt

        # State transition logic
        if self.current_state == SignalState.GREEN:
            if self.time_in_current_state >= self.current_allocated_green:
                self.current_state = SignalState.YELLOW
                self.time_in_current_state = 0.0

        elif self.current_state == SignalState.YELLOW:
            if self.time_in_current_state >= self.yellow_time:
                self.current_state = SignalState.RED
                self.time_in_current_state = 0.0

        elif self.current_state == SignalState.RED:
            if self.time_in_current_state >= self.all_red_time:
                # Switch to next phase
                next_phase_idx = self.select_next_phase()
                self.current_phase_index = next_phase_idx
                self.current_allocated_green = self.compute_dynamic_green_time(self.active_phase)
                self.current_state = SignalState.GREEN
                self.time_in_current_state = 0.0
                self.cycle_count += 1

                self.phase_history.append({
                    "phase": self.active_phase.name,
                    "allocated_green": self.current_allocated_green,
                    "cycle": self.cycle_count,
                    "timestamp": time.time()
                })
                if len(self.phase_history) > 100:
                    self.phase_history.pop(0)

        return self.get_current_lane_signals()

    def get_current_lane_signals(self) -> Dict[str, SignalState]:
        """Returns the signal state (GREEN, YELLOW, RED) for each lane."""
        signals = {lid: SignalState.RED for lid in self.lane_ids}
        active_lanes = self.active_phase.active_lanes

        for lid in active_lanes:
            if lid in signals:
                signals[lid] = self.current_state

        return signals

    def get_status_summary(self) -> dict:
        """Provides status for dashboard telemetry."""
        lane_signals = self.get_current_lane_signals()
        remaining_time = 0.0
        if self.current_state == SignalState.GREEN:
            remaining_time = max(0.0, self.current_allocated_green - self.time_in_current_state)
        elif self.current_state == SignalState.YELLOW:
            remaining_time = max(0.0, self.yellow_time - self.time_in_current_state)
        elif self.current_state == SignalState.RED:
            remaining_time = max(0.0, self.all_red_time - self.time_in_current_state)

        return {
            "active_phase": self.active_phase.name,
            "phase_id": self.active_phase.phase_id,
            "state": self.current_state.value,
            "time_in_state": round(self.time_in_current_state, 1),
            "allocated_green": round(self.current_allocated_green, 1),
            "remaining_time": round(remaining_time, 1),
            "lane_signals": {k: v.value for k, v in lane_signals.items()},
            "cycle_count": self.cycle_count,
            "lane_densities": {k: round(v.pcu_density, 1) for k, v in self.lane_states.items()}
        }
