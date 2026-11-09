"""
Emergency Preemption Manager (Green Corridor)
Detects approaching emergency vehicles (Ambulance, Fire Truck, Police)
and immediately preempts active signal cycles to grant uninterrupted right of way.
"""

from typing import Dict, Optional, List
import time
from .adaptive_signal import AdaptiveSignalController, SignalState


class EmergencyVehicleEvent:
    def __init__(self, vehicle_id: str, lane_id: str, vehicle_type: str = "AMBULANCE", distance_m: float = 120.0):
        self.vehicle_id = vehicle_id
        self.lane_id = lane_id
        self.vehicle_type = vehicle_type
        self.distance_m = distance_m
        self.detected_at = time.time()
        self.cleared_at: Optional[float] = None
        self.is_active = True


class EmergencyPreemptionManager:
    """
    Manages green corridors for emergency vehicles.
    Intercepts the AdaptiveSignalController when an emergency vehicle is detected.
    """

    def __init__(self, controller: AdaptiveSignalController):
        self.controller = controller
        self.active_emergencies: Dict[str, EmergencyVehicleEvent] = {}
        self.preemption_state: str = "IDLE"  # IDLE, TRANSITIONING_YELLOW, CORRIDOR_ACTIVE, RECOVERING
        self.target_lane: Optional[str] = None
        self.transition_timer: float = 0.0
        self.emergency_log: List[dict] = []

    @property
    def is_corridor_active(self) -> bool:
        return self.preemption_state in ("TRANSITIONING_YELLOW", "CORRIDOR_ACTIVE")

    def register_emergency(self, vehicle_id: str, lane_id: str, vehicle_type: str = "AMBULANCE", distance_m: float = 120.0):
        """Trigger an emergency green corridor request for a lane."""
        event = EmergencyVehicleEvent(vehicle_id, lane_id, vehicle_type, distance_m)
        self.active_emergencies[vehicle_id] = event
        self.target_lane = lane_id

        # Determine current signal condition
        current_signals = self.controller.get_current_lane_signals()
        if current_signals.get(lane_id) == SignalState.GREEN:
            # Already green, lock into corridor
            self.preemption_state = "CORRIDOR_ACTIVE"
        else:
            # Need safe clearance: turn active green to yellow
            self.preemption_state = "TRANSITIONING_YELLOW"
            self.transition_timer = 0.0

        self.emergency_log.append({
            "event": "DISPATCHED",
            "vehicle_id": vehicle_id,
            "lane_id": lane_id,
            "vehicle_type": vehicle_type,
            "timestamp": time.time()
        })

    def clear_emergency(self, vehicle_id: str):
        """Mark an emergency vehicle as having passed the intersection cordon."""
        if vehicle_id in self.active_emergencies:
            ev = self.active_emergencies.pop(vehicle_id)
            ev.cleared_at = time.time()
            ev.is_active = False
            duration = ev.cleared_at - ev.detected_at

            self.emergency_log.append({
                "event": "CLEARED",
                "vehicle_id": vehicle_id,
                "lane_id": ev.lane_id,
                "time_saved_est_sec": round(max(5.0, 35.0 - duration), 1),
                "timestamp": ev.cleared_at
            })

        if not self.active_emergencies:
            # All emergency vehicles cleared -> recovery transition
            self.preemption_state = "RECOVERING"
            self.transition_timer = 0.0
            self.target_lane = None

    def step(self, dt: float = 1.0) -> Optional[Dict[str, SignalState]]:
        """
        Step the preemption manager.
        If preemption is active, returns the overridden signal dictionary.
        Otherwise returns None (let standard controller run).
        """
        if self.preemption_state == "IDLE":
            return None

        self.transition_timer += dt

        if self.preemption_state == "TRANSITIONING_YELLOW":
            # Give non-emergency lanes 2.0s yellow before clearing
            if self.transition_timer >= 2.0:
                self.preemption_state = "CORRIDOR_ACTIVE"
                self.transition_timer = 0.0
            else:
                # Return yellow on previously green lanes, red on others
                prev_signals = self.controller.get_current_lane_signals()
                override = {}
                for lid, state in prev_signals.items():
                    override[lid] = SignalState.YELLOW if state == SignalState.GREEN else SignalState.RED
                return override

        if self.preemption_state == "CORRIDOR_ACTIVE":
            # Force target lane to GREEN, all other lanes to RED
            signals = {lid: SignalState.RED for lid in self.controller.lane_ids}
            if self.target_lane and self.target_lane in signals:
                signals[self.target_lane] = SignalState.GREEN
            return signals

        if self.preemption_state == "RECOVERING":
            # 2.0s yellow on target lane, then return to normal adaptive controller
            if self.transition_timer >= 2.0:
                self.preemption_state = "IDLE"
                self.transition_timer = 0.0
                return None
            else:
                signals = {lid: SignalState.RED for lid in self.controller.lane_ids}
                if self.target_lane and self.target_lane in signals:
                    signals[self.target_lane] = SignalState.YELLOW
                return signals

        return None

    def get_status(self) -> dict:
        return {
            "preemption_state": self.preemption_state,
            "is_corridor_active": self.is_corridor_active,
            "target_lane": self.target_lane,
            "active_count": len(self.active_emergencies),
            "emergencies": [
                {
                    "id": ev.vehicle_id,
                    "lane": ev.lane_id,
                    "type": ev.vehicle_type,
                    "distance_m": round(ev.distance_m, 1),
                }
                for ev in self.active_emergencies.values()
            ],
            "total_emergencies_served": len([e for e in self.emergency_log if e["event"] == "CLEARED"])
        }
