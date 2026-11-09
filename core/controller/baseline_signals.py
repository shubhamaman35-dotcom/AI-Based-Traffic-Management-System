"""
Baseline Traffic Signal Controllers
Provides Fixed-Time and Actuated controllers for live comparison benchmarking against the AI Adaptive Controller.
"""

from typing import Dict, List, Optional
from .adaptive_signal import SignalState, SignalPhase


class FixedTimeController:
    """
    Traditional Fixed-Time Traffic Light Controller.
    Cycles through all phases sequentially with a constant green time (e.g. 30 seconds).
    Ignores vehicle queue lengths and congestion density.
    """

    def __init__(
        self,
        lane_ids: Optional[List[str]] = None,
        fixed_green: float = 30.0,
        yellow_time: float = 3.0,
        all_red_time: float = 1.0,
    ):
        self.lane_ids = lane_ids or ["north", "south", "east", "west"]
        self.fixed_green = fixed_green
        self.yellow_time = yellow_time
        self.all_red_time = all_red_time

        self.phases = [
            SignalPhase("P_NORTH", "North Approach", ["north"], green_duration=fixed_green),
            SignalPhase("P_SOUTH", "South Approach", ["south"], green_duration=fixed_green),
            SignalPhase("P_EAST", "East Approach", ["east"], green_duration=fixed_green),
            SignalPhase("P_WEST", "West Approach", ["west"], green_duration=fixed_green),
        ]

        self.current_phase_index: int = 0
        self.current_state: SignalState = SignalState.GREEN
        self.time_in_current_state: float = 0.0
        self.cycle_count: int = 0

    @property
    def active_phase(self) -> SignalPhase:
        return self.phases[self.current_phase_index]

    def step(self, dt: float = 1.0) -> Dict[str, SignalState]:
        self.time_in_current_state += dt

        if self.current_state == SignalState.GREEN:
            if self.time_in_current_state >= self.fixed_green:
                self.current_state = SignalState.YELLOW
                self.time_in_current_state = 0.0

        elif self.current_state == SignalState.YELLOW:
            if self.time_in_current_state >= self.yellow_time:
                self.current_state = SignalState.RED
                self.time_in_current_state = 0.0

        elif self.current_state == SignalState.RED:
            if self.time_in_current_state >= self.all_red_time:
                # Cycle to next phase
                self.current_phase_index = (self.current_phase_index + 1) % len(self.phases)
                self.current_state = SignalState.GREEN
                self.time_in_current_state = 0.0
                self.cycle_count += 1

        return self.get_current_lane_signals()

    def get_current_lane_signals(self) -> Dict[str, SignalState]:
        signals = {lid: SignalState.RED for lid in self.lane_ids}
        for lid in self.active_phase.active_lanes:
            if lid in signals:
                signals[lid] = self.current_state
        return signals

    def get_status_summary(self) -> dict:
        lane_signals = self.get_current_lane_signals()
        remaining_time = 0.0
        if self.current_state == SignalState.GREEN:
            remaining_time = max(0.0, self.fixed_green - self.time_in_current_state)
        elif self.current_state == SignalState.YELLOW:
            remaining_time = max(0.0, self.yellow_time - self.time_in_current_state)
        elif self.current_state == SignalState.RED:
            remaining_time = max(0.0, self.all_red_time - self.time_in_current_state)

        return {
            "controller_type": "FIXED_TIME",
            "active_phase": self.active_phase.name,
            "state": self.current_state.value,
            "time_in_state": round(self.time_in_current_state, 1),
            "allocated_green": round(self.fixed_green, 1),
            "remaining_time": round(remaining_time, 1),
            "lane_signals": {k: v.value for k, v in lane_signals.items()},
            "cycle_count": self.cycle_count,
        }


class ActuatedController:
    """
    Semi-Actuated Controller with loop-detectors.
    Extends green in increments if vehicles are arriving up to a maximum cap.
    """

    def __init__(
        self,
        lane_ids: Optional[List[str]] = None,
        min_green: float = 10.0,
        max_green: float = 40.0,
        vehicle_extension: float = 2.5,
        yellow_time: float = 3.0,
        all_red_time: float = 1.0,
    ):
        self.lane_ids = lane_ids or ["north", "south", "east", "west"]
        self.min_green = min_green
        self.max_green = max_green
        self.vehicle_extension = vehicle_extension
        self.yellow_time = yellow_time
        self.all_red_time = all_red_time

        self.phases = [
            SignalPhase("P_NORTH", "North Approach", ["north"]),
            SignalPhase("P_SOUTH", "South Approach", ["south"]),
            SignalPhase("P_EAST", "East Approach", ["east"]),
            SignalPhase("P_WEST", "West Approach", ["west"]),
        ]

        self.current_phase_index: int = 0
        self.current_state: SignalState = SignalState.GREEN
        self.time_in_current_state: float = 0.0
        self.current_allocated_green: float = min_green
        self.cycle_count: int = 0

    @property
    def active_phase(self) -> SignalPhase:
        return self.phases[self.current_phase_index]

    def extend_green_on_detection(self):
        """Extend current green if vehicle detected, capped at max_green."""
        if self.current_state == SignalState.GREEN:
            new_green = min(self.current_allocated_green + self.vehicle_extension, self.max_green)
            self.current_allocated_green = new_green

    def step(self, dt: float = 1.0) -> Dict[str, SignalState]:
        self.time_in_current_state += dt

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
                self.current_phase_index = (self.current_phase_index + 1) % len(self.phases)
                self.current_allocated_green = self.min_green
                self.current_state = SignalState.GREEN
                self.time_in_current_state = 0.0
                self.cycle_count += 1

        return self.get_current_lane_signals()

    def get_current_lane_signals(self) -> Dict[str, SignalState]:
        signals = {lid: SignalState.RED for lid in self.lane_ids}
        for lid in self.active_phase.active_lanes:
            if lid in signals:
                signals[lid] = self.current_state
        return signals

    def get_status_summary(self) -> dict:
        lane_signals = self.get_current_lane_signals()
        remaining_time = 0.0
        if self.current_state == SignalState.GREEN:
            remaining_time = max(0.0, self.current_allocated_green - self.time_in_current_state)
        elif self.current_state == SignalState.YELLOW:
            remaining_time = max(0.0, self.yellow_time - self.time_in_current_state)
        elif self.current_state == SignalState.RED:
            remaining_time = max(0.0, self.all_red_time - self.time_in_current_state)

        return {
            "controller_type": "ACTUATED",
            "active_phase": self.active_phase.name,
            "state": self.current_state.value,
            "time_in_state": round(self.time_in_current_state, 1),
            "allocated_green": round(self.current_allocated_green, 1),
            "remaining_time": round(remaining_time, 1),
            "lane_signals": {k: v.value for k, v in lane_signals.items()},
            "cycle_count": self.cycle_count,
        }
