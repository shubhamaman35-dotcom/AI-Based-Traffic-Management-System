import pytest
from core.controller.adaptive_signal import AdaptiveSignalController, LaneTrafficState, SignalState
from core.controller.emergency import EmergencyPreemptionManager
from core.controller.baseline_signals import FixedTimeController, ActuatedController


def test_lane_traffic_state_pcu():
    state = LaneTrafficState(
        lane_id="north",
        cars=4,        # 4 * 1.0 = 4.0
        buses=2,       # 2 * 2.5 = 5.0
        trucks=1,      # 1 * 3.0 = 3.0
        motorcycles=2, # 2 * 0.5 = 1.0
        emergency_vehicles=0
    )
    assert state.total_vehicles == 9
    assert state.pcu_density == 13.0
    assert state.urgency_score == 13.0


def test_adaptive_controller_green_time_bounds():
    ctrl = AdaptiveSignalController(min_green=8.0, max_green=60.0)
    
    # When empty
    empty_phase = ctrl.phases[0]
    green = ctrl.compute_dynamic_green_time(empty_phase)
    assert green == 8.0

    # High load on north
    ctrl.update_lane_state("north", LaneTrafficState("north", cars=15, buses=4, trucks=3))
    ctrl.update_lane_state("south", LaneTrafficState("south", cars=2))
    
    high_green = ctrl.compute_dynamic_green_time(empty_phase)
    assert high_green > 8.0
    assert high_green <= 60.0


def test_emergency_preemption_lifecycle():
    ctrl = AdaptiveSignalController()
    mgr = EmergencyPreemptionManager(ctrl)
    
    assert not mgr.is_corridor_active
    assert mgr.preemption_state == "IDLE"
    
    # Register emergency on north lane
    mgr.register_emergency("amb_001", "north", "AMBULANCE", distance_m=100.0)
    assert mgr.preemption_state in ("TRANSITIONING_YELLOW", "CORRIDOR_ACTIVE")
    
    # Advance transition timer
    mgr.step(3.0)
    assert mgr.is_corridor_active
    
    override = mgr.step(1.0)
    assert override is not None
    assert override["north"] == SignalState.GREEN
    assert override["south"] == SignalState.RED
    assert override["east"] == SignalState.RED
    assert override["west"] == SignalState.RED
    
    # Clear emergency
    mgr.clear_emergency("amb_001")
    assert mgr.preemption_state == "RECOVERING"
    
    mgr.step(3.0)
    assert mgr.preemption_state == "IDLE"


def test_fixed_controller_cycling():
    fixed = FixedTimeController(fixed_green=20.0, yellow_time=3.0, all_red_time=1.0)
    assert fixed.current_state == SignalState.GREEN
    
    # Advance 21 seconds -> should turn yellow
    fixed.step(21.0)
    assert fixed.current_state == SignalState.YELLOW
    
    # Advance 3.5 seconds -> should turn red (yellow is 3s)
    fixed.step(3.5)
    assert fixed.current_state == SignalState.RED
    
    # Advance 1.5 seconds -> should turn green (all-red is 1s) and advance phase
    fixed.step(1.5)
    assert fixed.current_state == SignalState.GREEN
    assert fixed.current_phase_index == 1
