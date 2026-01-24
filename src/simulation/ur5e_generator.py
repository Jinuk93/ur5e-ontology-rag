"""
UR5e Telemetry Generator - Generates simulated UR5e robot telemetry.

This module generates realistic UR5e telemetry data based on the current
scenario from the ScenarioSequencer, ensuring physical correlation with
Axia80 force sensor data.
"""

import random
import time
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional

from .scenario_sequencer import ScenarioType, get_scenario_sequencer


class SafetyMode(str, Enum):
    """UR5e safety modes."""
    NORMAL = "normal"
    REDUCED = "reduced"
    PROTECTIVE_STOP = "protective_stop"


class ProgramState(str, Enum):
    """UR5e program states."""
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"


@dataclass
class UR5eTelemetry:
    """UR5e telemetry data structure."""
    tcp_speed: float  # m/s (0 ~ 1.0)
    tcp_acceleration: float  # m/s² (-5 ~ 5)
    joint_torque_sum: float  # Nm (0 ~ 150)
    joint_current_avg: float  # A (0.5 ~ 5.0)
    safety_mode: SafetyMode
    program_state: ProgramState
    protective_stop: bool

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "tcp_speed": round(self.tcp_speed, 3),
            "tcp_acceleration": round(self.tcp_acceleration, 3),
            "joint_torque_sum": round(self.joint_torque_sum, 1),
            "joint_current_avg": round(self.joint_current_avg, 2),
            "safety_mode": self.safety_mode.value,
            "program_state": self.program_state.value,
            "protective_stop": self.protective_stop,
        }


@dataclass
class ScenarioBaseValues:
    """Base values for a scenario (before noise)."""
    tcp_speed: float
    force_magnitude: float
    joint_torque_sum: float
    joint_current_avg: float
    safety_mode: SafetyMode
    program_state: ProgramState


class ProtectiveStopState:
    """Manages protective stop latching and recovery."""

    def __init__(self, recovery_delay: float = 3.0):
        self.is_active = False
        self.activated_at: Optional[float] = None
        self.recovery_delay = recovery_delay

    def trigger(self):
        """Trigger protective stop."""
        if not self.is_active:
            self.is_active = True
            self.activated_at = time.time()

    def can_recover(self, current_risk: float) -> bool:
        """Check if recovery is possible."""
        if not self.is_active or self.activated_at is None:
            return False

        elapsed = time.time() - self.activated_at
        return elapsed >= self.recovery_delay and current_risk < 0.3

    def recover(self):
        """Recover from protective stop."""
        self.is_active = False
        self.activated_at = None


class UR5eTelemetryGenerator:
    """
    Generates simulated UR5e telemetry based on scenario state.

    The generator creates physically plausible data that correlates
    with Axia80 sensor readings based on the current scenario.
    """

    # Noise parameters (as per design doc)
    NOISE_STD = 0.03  # ±3% for UR5e data

    def __init__(self):
        """Initialize the generator."""
        self._protective_stop = ProtectiveStopState()
        self._previous_values: Optional[UR5eTelemetry] = None

    def _apply_noise(self, value: float, std_ratio: float = None) -> float:
        """Apply Gaussian noise to a value."""
        std = std_ratio or self.NOISE_STD
        noise = random.gauss(0, abs(value) * std) if value != 0 else random.gauss(0, 0.01)
        return value + noise

    def _get_normal_base_values(self, phase: float) -> ScenarioBaseValues:
        """Get base values for normal operation scenario."""
        # Slight variation based on work cycle phase
        cycle_phase = (phase * 4) % 1.0  # 4 mini-cycles per scenario

        if cycle_phase < 0.2:  # Idle
            tcp_speed = 0.05
            force = 15
        elif cycle_phase < 0.4:  # Approach
            tcp_speed = 0.25
            force = 20
        elif cycle_phase < 0.6:  # Work
            tcp_speed = 0.15
            force = 35
        else:  # Return
            tcp_speed = 0.20
            force = 25

        return ScenarioBaseValues(
            tcp_speed=tcp_speed,
            force_magnitude=force,
            joint_torque_sum=30 + force * 0.3,
            joint_current_avg=1.5 + force * 0.02,
            safety_mode=SafetyMode.NORMAL,
            program_state=ProgramState.RUNNING,
        )

    def _get_collision_base_values(self, phase: float) -> ScenarioBaseValues:
        """Get base values for collision scenario."""
        if phase < 0.3:  # Approach phase - speeding up
            tcp_speed = 0.4 + 0.2 * (phase / 0.3)
            force = 30 + 20 * (phase / 0.3)
            safety_mode = SafetyMode.NORMAL
            program_state = ProgramState.RUNNING
            protective = False
        elif phase < 0.5:  # Contact moment - spike
            contact_phase = (phase - 0.3) / 0.2
            tcp_speed = 0.6 - 0.5 * contact_phase  # Rapid deceleration
            force = 50 + 100 * contact_phase  # Force spike
            safety_mode = SafetyMode.NORMAL if contact_phase < 0.5 else SafetyMode.PROTECTIVE_STOP
            program_state = ProgramState.RUNNING if contact_phase < 0.5 else ProgramState.PAUSED
            protective = contact_phase > 0.5
        elif phase < 0.7:  # Reaction phase
            tcp_speed = 0.1
            force = 150 - 70 * ((phase - 0.5) / 0.2)
            safety_mode = SafetyMode.PROTECTIVE_STOP
            program_state = ProgramState.PAUSED
            protective = True
        else:  # Recovery phase
            recovery_phase = (phase - 0.7) / 0.3
            tcp_speed = 0.02 + 0.08 * recovery_phase
            force = 80 - 40 * recovery_phase
            safety_mode = SafetyMode.REDUCED if recovery_phase > 0.5 else SafetyMode.PROTECTIVE_STOP
            program_state = ProgramState.PAUSED if recovery_phase < 0.5 else ProgramState.RUNNING
            protective = recovery_phase < 0.3

        if protective:
            self._protective_stop.trigger()

        return ScenarioBaseValues(
            tcp_speed=tcp_speed,
            force_magnitude=force,
            joint_torque_sum=40 + force * 0.5,
            joint_current_avg=2.0 + force * 0.02,
            safety_mode=safety_mode,
            program_state=program_state,
        )

    def _get_overload_base_values(self, phase: float) -> ScenarioBaseValues:
        """Get base values for overload scenario."""
        # Sustained high load
        return ScenarioBaseValues(
            tcp_speed=0.15 + 0.05 * random.random(),
            force_magnitude=65 + 15 * random.random(),
            joint_torque_sum=75 + 15 * random.random(),
            joint_current_avg=4.0 + 0.5 * random.random(),
            safety_mode=SafetyMode.NORMAL,
            program_state=ProgramState.RUNNING,
        )

    def _get_wear_base_values(self, phase: float) -> ScenarioBaseValues:
        """Get base values for wear indication scenario."""
        # Key feature: high torque with normal force (torque/force mismatch)
        return ScenarioBaseValues(
            tcp_speed=0.18 + 0.04 * random.random(),
            force_magnitude=20 + 5 * random.random(),  # Normal force
            joint_torque_sum=60 + 10 * random.random(),  # Abnormally high torque!
            joint_current_avg=3.5 + 0.5 * random.random(),
            safety_mode=SafetyMode.NORMAL,
            program_state=ProgramState.RUNNING,
        )

    def _get_risk_approach_base_values(self, phase: float) -> ScenarioBaseValues:
        """Get base values for risk approach scenario."""
        # Gradual increase toward danger
        return ScenarioBaseValues(
            tcp_speed=0.3 + 0.2 * phase,  # 0.3 → 0.5
            force_magnitude=25 + 30 * phase,  # 25 → 55
            joint_torque_sum=35 + 30 * phase,
            joint_current_avg=2.0 + 1.5 * phase,
            safety_mode=SafetyMode.NORMAL,
            program_state=ProgramState.RUNNING,
        )

    def _interpolate_transition(
        self,
        old_telemetry: UR5eTelemetry,
        new_base: ScenarioBaseValues,
        progress: float
    ) -> ScenarioBaseValues:
        """Interpolate between old and new values during transition."""
        return ScenarioBaseValues(
            tcp_speed=old_telemetry.tcp_speed + (new_base.tcp_speed - old_telemetry.tcp_speed) * progress,
            force_magnitude=new_base.force_magnitude,  # Force comes from Axia80
            joint_torque_sum=old_telemetry.joint_torque_sum + (new_base.joint_torque_sum - old_telemetry.joint_torque_sum) * progress,
            joint_current_avg=old_telemetry.joint_current_avg + (new_base.joint_current_avg - old_telemetry.joint_current_avg) * progress,
            safety_mode=new_base.safety_mode if progress > 0.5 else old_telemetry.safety_mode,
            program_state=new_base.program_state if progress > 0.5 else old_telemetry.program_state,
        )

    def generate(self, scenario_state: Dict) -> UR5eTelemetry:
        """
        Generate UR5e telemetry based on current scenario state.

        Args:
            scenario_state: Dict from ScenarioSequencer.tick()

        Returns:
            UR5eTelemetry data
        """
        scenario = ScenarioType(scenario_state["scenario"])
        phase = scenario_state["phase"]

        # Get base values for current scenario
        if scenario == ScenarioType.NORMAL:
            base = self._get_normal_base_values(phase)
        elif scenario == ScenarioType.COLLISION:
            base = self._get_collision_base_values(phase)
        elif scenario == ScenarioType.OVERLOAD:
            base = self._get_overload_base_values(phase)
        elif scenario == ScenarioType.WEAR:
            base = self._get_wear_base_values(phase)
        elif scenario == ScenarioType.RISK_APPROACH:
            base = self._get_risk_approach_base_values(phase)
        else:
            base = self._get_normal_base_values(phase)

        # Apply transition smoothing if needed
        if scenario_state["is_transitioning"] and self._previous_values:
            progress = scenario_state["transition_progress"]
            base = self._interpolate_transition(self._previous_values, base, progress)

        # Check protective stop state
        if self._protective_stop.is_active:
            base.safety_mode = SafetyMode.PROTECTIVE_STOP
            base.program_state = ProgramState.PAUSED
            base.tcp_speed = 0.0

        # Apply noise
        tcp_speed = max(0, self._apply_noise(base.tcp_speed))
        joint_torque = max(0, self._apply_noise(base.joint_torque_sum))
        joint_current = max(0.5, self._apply_noise(base.joint_current_avg))

        # Calculate acceleration (derivative estimate)
        if self._previous_values:
            tcp_accel = (tcp_speed - self._previous_values.tcp_speed) * 10  # Assuming 0.1s interval
        else:
            tcp_accel = 0.0
        tcp_accel = max(-5, min(5, tcp_accel))

        # Enforce safety mode constraints
        if base.safety_mode == SafetyMode.REDUCED:
            tcp_speed = min(tcp_speed, 0.25)
        elif base.safety_mode == SafetyMode.PROTECTIVE_STOP:
            tcp_speed = 0.0

        telemetry = UR5eTelemetry(
            tcp_speed=tcp_speed,
            tcp_acceleration=tcp_accel,
            joint_torque_sum=joint_torque,
            joint_current_avg=joint_current,
            safety_mode=base.safety_mode,
            program_state=base.program_state,
            protective_stop=self._protective_stop.is_active,
        )

        self._previous_values = telemetry
        return telemetry

    def get_expected_force_magnitude(self, scenario_state: Dict) -> float:
        """
        Get expected force magnitude for current scenario.

        This is used by the Axia80 generator to create correlated data.
        """
        scenario = ScenarioType(scenario_state["scenario"])
        phase = scenario_state["phase"]

        if scenario == ScenarioType.NORMAL:
            base = self._get_normal_base_values(phase)
        elif scenario == ScenarioType.COLLISION:
            base = self._get_collision_base_values(phase)
        elif scenario == ScenarioType.OVERLOAD:
            base = self._get_overload_base_values(phase)
        elif scenario == ScenarioType.WEAR:
            base = self._get_wear_base_values(phase)
        elif scenario == ScenarioType.RISK_APPROACH:
            base = self._get_risk_approach_base_values(phase)
        else:
            base = self._get_normal_base_values(phase)

        return base.force_magnitude


# Singleton instance
_global_generator: Optional[UR5eTelemetryGenerator] = None


def get_ur5e_generator() -> UR5eTelemetryGenerator:
    """Get or create global UR5e telemetry generator."""
    global _global_generator
    if _global_generator is None:
        _global_generator = UR5eTelemetryGenerator()
    return _global_generator
