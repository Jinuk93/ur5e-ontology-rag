"""
Correlation Engine - Generates correlated Axia80 + UR5e data and calculates risk metrics.

This module:
1. Generates Axia80 force sensor data based on scenario (with delay/noise)
2. Calculates correlation metrics between UR5e and Axia80
3. Computes risk scores and recommendations
"""

import math
import random
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Deque, Dict, List, Optional

from .scenario_sequencer import ScenarioType, get_scenario_sequencer
from .ur5e_generator import UR5eTelemetry, get_ur5e_generator


@dataclass
class Axia80Data:
    """Axia80 force sensor data."""
    Fx: float
    Fy: float
    Fz: float
    Tx: float
    Ty: float
    Tz: float
    force_magnitude: float
    force_rate: float
    force_spike: bool
    peak_axis: str

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "Fx": round(self.Fx, 2),
            "Fy": round(self.Fy, 2),
            "Fz": round(self.Fz, 2),
            "Tx": round(self.Tx, 3),
            "Ty": round(self.Ty, 3),
            "Tz": round(self.Tz, 3),
            "force_magnitude": round(self.force_magnitude, 2),
            "force_rate": round(self.force_rate, 2),
            "force_spike": self.force_spike,
            "peak_axis": self.peak_axis,
        }


@dataclass
class CorrelationMetrics:
    """Correlation metrics between UR5e and Axia80."""
    torque_force_ratio: float
    speed_force_correlation: float
    anomaly_detected: bool

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "torque_force_ratio": round(self.torque_force_ratio, 2),
            "speed_force_correlation": round(self.speed_force_correlation, 2),
            "anomaly_detected": self.anomaly_detected,
        }


@dataclass
class RiskAssessment:
    """Risk assessment results."""
    contact_risk_score: float
    collision_risk_score: float
    risk_level: str  # low, medium, high, critical
    recommended_action: str
    prediction_horizon_sec: int = 3

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "contact_risk_score": round(self.contact_risk_score, 2),
            "collision_risk_score": round(self.collision_risk_score, 2),
            "risk_level": self.risk_level,
            "recommended_action": self.recommended_action,
            "prediction_horizon_sec": self.prediction_horizon_sec,
        }


@dataclass
class IntegratedReading:
    """Complete integrated sensor reading."""
    timestamp: str
    scenario: Dict
    axia80: Axia80Data
    ur5e: UR5eTelemetry
    correlation: CorrelationMetrics
    risk: RiskAssessment

    def to_dict(self) -> Dict:
        """Convert to dictionary for API response."""
        return {
            "timestamp": self.timestamp,
            "scenario": self.scenario,
            "axia80": self.axia80.to_dict(),
            "ur5e": self.ur5e.to_dict(),
            "correlation": self.correlation.to_dict(),
            "risk": self.risk.to_dict(),
        }


class CorrelationEngine:
    """
    Generates correlated sensor data and calculates risk metrics.

    This engine coordinates data generation from both UR5e and Axia80,
    ensuring physical correlation while maintaining realistic noise patterns.
    """

    # Axia80 noise and delay parameters
    AXIA80_NOISE_STD = 0.05  # ±5%
    AXIA80_DELAY_MS = (100, 200)  # Response delay range

    # Risk calculation thresholds
    FORCE_SPIKE_THRESHOLD = 100  # N
    TORQUE_FORCE_RATIO_THRESHOLD = 2.0
    HIGH_SPEED_THRESHOLD = 0.5  # m/s

    def __init__(self, history_size: int = 60):
        """Initialize correlation engine."""
        self._sequencer = get_scenario_sequencer()
        self._ur5e_generator = get_ur5e_generator()
        self._history: Deque[IntegratedReading] = deque(maxlen=history_size)
        self._previous_force_magnitude: Optional[float] = None
        self._last_tick_time: Optional[float] = None

    def _generate_axia80_data(self, scenario_state: Dict, ur5e: UR5eTelemetry) -> Axia80Data:
        """
        Generate Axia80 data correlated with UR5e and scenario.

        Force is primarily determined by scenario, with noise and correlation to UR5e.
        """
        # Get expected force from UR5e generator
        expected_force = self._ur5e_generator.get_expected_force_magnitude(scenario_state)

        # Apply noise (±5%)
        force_magnitude = expected_force * (1 + random.gauss(0, self.AXIA80_NOISE_STD))

        # Fz is primary (vertical force, typically negative for downward)
        # Distribute force among axes with Fz dominant
        fz_ratio = 0.9 + random.gauss(0, 0.05)
        Fz = -force_magnitude * fz_ratio  # Negative for downward

        # Small lateral forces (Fx, Fy)
        Fx = random.gauss(0, force_magnitude * 0.05)
        Fy = random.gauss(0, force_magnitude * 0.05)

        # Torques (small, correlated with force)
        Tx = random.gauss(0, 0.5) + Fy * 0.01
        Ty = random.gauss(0, 0.5) - Fx * 0.01
        Tz = random.gauss(0, 0.2)

        # Calculate force rate (derivative)
        if self._previous_force_magnitude is not None:
            force_rate = (force_magnitude - self._previous_force_magnitude)
        else:
            force_rate = 0.0
        self._previous_force_magnitude = force_magnitude

        # Determine peak axis
        forces = {"Fx": abs(Fx), "Fy": abs(Fy), "Fz": abs(Fz)}
        peak_axis = max(forces, key=forces.get)

        # Force spike detection
        force_spike = force_magnitude > self.FORCE_SPIKE_THRESHOLD

        return Axia80Data(
            Fx=Fx,
            Fy=Fy,
            Fz=Fz,
            Tx=Tx,
            Ty=Ty,
            Tz=Tz,
            force_magnitude=force_magnitude,
            force_rate=force_rate,
            force_spike=force_spike,
            peak_axis=peak_axis,
        )

    def _calculate_correlation(
        self,
        axia80: Axia80Data,
        ur5e: UR5eTelemetry
    ) -> CorrelationMetrics:
        """Calculate correlation metrics between UR5e and Axia80."""
        # Torque/Force ratio (anomaly indicator)
        force_denom = max(axia80.force_magnitude, 1.0)
        torque_force_ratio = ur5e.joint_torque_sum / force_denom

        # Speed-Force correlation (simplified)
        # In normal operation: higher speed often means lower sustained force
        # This is a simplified correlation coefficient
        if len(self._history) >= 5:
            recent = list(self._history)[-5:]
            speeds = [r.ur5e.tcp_speed for r in recent]
            forces = [r.axia80.force_magnitude for r in recent]

            # Simple correlation calculation
            mean_speed = sum(speeds) / len(speeds)
            mean_force = sum(forces) / len(forces)

            numerator = sum((s - mean_speed) * (f - mean_force) for s, f in zip(speeds, forces))
            denom_speed = math.sqrt(sum((s - mean_speed) ** 2 for s in speeds))
            denom_force = math.sqrt(sum((f - mean_force) ** 2 for f in forces))

            if denom_speed > 0 and denom_force > 0:
                speed_force_correlation = numerator / (denom_speed * denom_force)
            else:
                speed_force_correlation = 0.0
        else:
            speed_force_correlation = 0.0

        # Anomaly detection: high torque with normal/low force
        anomaly_detected = torque_force_ratio > self.TORQUE_FORCE_RATIO_THRESHOLD * 1.25

        return CorrelationMetrics(
            torque_force_ratio=torque_force_ratio,
            speed_force_correlation=speed_force_correlation,
            anomaly_detected=anomaly_detected,
        )

    def _calculate_contact_risk_score(
        self,
        axia80: Axia80Data,
        ur5e: UR5eTelemetry,
        correlation: CorrelationMetrics
    ) -> float:
        """
        Calculate contact risk score (0-1).

        Based on: force magnitude, speed, force rate, torque/force ratio
        """
        score = 0.0

        # 1. Force magnitude contribution (40%)
        force_norm = min(axia80.force_magnitude / 150, 1.0)
        score += 0.4 * force_norm

        # 2. Speed contribution (30%)
        speed_norm = min(ur5e.tcp_speed / 0.8, 1.0)
        score += 0.3 * speed_norm

        # 3. Force rate contribution (20%)
        rate_norm = min(abs(axia80.force_rate) / 50, 1.0)
        score += 0.2 * rate_norm

        # 4. Torque/Force anomaly contribution (10%)
        if correlation.torque_force_ratio > self.TORQUE_FORCE_RATIO_THRESHOLD:
            score += 0.1

        return min(score, 1.0)

    def _calculate_collision_risk_score(self) -> float:
        """
        Calculate collision risk score based on recent history.

        This is a risk score, NOT a probability.
        """
        if len(self._history) < 3:
            return 0.0

        recent = list(self._history)[-5:]

        # 1. Force trend analysis
        forces = [r.axia80.force_magnitude for r in recent]
        if len(forces) >= 2:
            force_trend = (forces[-1] - forces[0]) / len(forces)
        else:
            force_trend = 0.0

        # 2. Speed trend analysis
        speeds = [r.ur5e.tcp_speed for r in recent]
        if len(speeds) >= 2:
            speed_trend = (speeds[-1] - speeds[0]) / len(speeds)
        else:
            speed_trend = 0.0

        # 3. Current contact risk
        current_risk = recent[-1].risk.contact_risk_score if recent else 0.0

        # Combined score calculation
        score = (
            0.3 * min(force_trend / 20, 1.0) +
            0.2 * min(speed_trend / 0.1, 1.0) +
            0.3 * current_risk +
            0.2 * (1 if forces[-1] > 50 else 0)
        )

        return min(max(score, 0.0), 1.0)

    def _determine_risk_level(
        self,
        contact_risk: float,
        collision_risk: float
    ) -> str:
        """Determine risk level string."""
        max_risk = max(contact_risk, collision_risk)

        if max_risk >= 0.8:
            return "critical"
        elif max_risk >= 0.5:
            return "high"
        elif max_risk >= 0.3:
            return "medium"
        else:
            return "low"

    def _determine_recommended_action(
        self,
        contact_risk: float,
        collision_risk: float,
        anomaly: bool
    ) -> str:
        """Determine recommended action."""
        if anomaly:
            return "inspect_joints"

        max_risk = max(contact_risk, collision_risk)

        if max_risk >= 0.8:
            return "emergency_stop"
        elif max_risk >= 0.5:
            return "slow_down"
        elif max_risk >= 0.3:
            return "caution"
        else:
            return "maintain"

    def _assess_risk(
        self,
        axia80: Axia80Data,
        ur5e: UR5eTelemetry,
        correlation: CorrelationMetrics
    ) -> RiskAssessment:
        """Perform complete risk assessment."""
        contact_risk = self._calculate_contact_risk_score(axia80, ur5e, correlation)

        # Need to add to history first to calculate collision risk
        # This will be updated after adding to history
        collision_risk = self._calculate_collision_risk_score()

        risk_level = self._determine_risk_level(contact_risk, collision_risk)
        recommended_action = self._determine_recommended_action(
            contact_risk, collision_risk, correlation.anomaly_detected
        )

        return RiskAssessment(
            contact_risk_score=contact_risk,
            collision_risk_score=collision_risk,
            risk_level=risk_level,
            recommended_action=recommended_action,
        )

    def tick(self) -> IntegratedReading:
        """
        Generate one tick of integrated sensor data.

        Returns:
            IntegratedReading with all sensor data and risk assessment
        """
        # Get scenario state
        scenario_state = self._sequencer.tick()

        # Generate UR5e telemetry
        ur5e = self._ur5e_generator.generate(scenario_state)

        # Generate Axia80 data (with correlation to UR5e/scenario)
        axia80 = self._generate_axia80_data(scenario_state, ur5e)

        # Calculate correlation metrics
        correlation = self._calculate_correlation(axia80, ur5e)

        # Assess risk
        risk = self._assess_risk(axia80, ur5e, correlation)

        # Create integrated reading
        reading = IntegratedReading(
            timestamp=datetime.utcnow().isoformat() + "Z",
            scenario={
                "current": scenario_state["scenario"],
                "elapsed_sec": scenario_state["elapsed_sec"],
                "remaining_sec": scenario_state["remaining_sec"],
            },
            axia80=axia80,
            ur5e=ur5e,
            correlation=correlation,
            risk=risk,
        )

        # Add to history
        self._history.append(reading)

        # Recalculate collision risk with updated history
        reading.risk.collision_risk_score = self._calculate_collision_risk_score()
        reading.risk.risk_level = self._determine_risk_level(
            reading.risk.contact_risk_score,
            reading.risk.collision_risk_score
        )
        reading.risk.recommended_action = self._determine_recommended_action(
            reading.risk.contact_risk_score,
            reading.risk.collision_risk_score,
            reading.correlation.anomaly_detected
        )

        return reading

    def get_history(self, count: int = 60) -> List[IntegratedReading]:
        """Get recent history."""
        return list(self._history)[-count:]

    def get_statistics(self) -> Dict:
        """Get statistics from recent history."""
        if not self._history:
            return {}

        readings = list(self._history)

        forces = [r.axia80.force_magnitude for r in readings]
        speeds = [r.ur5e.tcp_speed for r in readings]
        risks = [r.risk.contact_risk_score for r in readings]

        return {
            "count": len(readings),
            "force": {
                "min": round(min(forces), 1),
                "max": round(max(forces), 1),
                "avg": round(sum(forces) / len(forces), 1),
            },
            "speed": {
                "min": round(min(speeds), 3),
                "max": round(max(speeds), 3),
                "avg": round(sum(speeds) / len(speeds), 3),
            },
            "risk": {
                "min": round(min(risks), 2),
                "max": round(max(risks), 2),
                "avg": round(sum(risks) / len(risks), 2),
            },
        }


# Singleton instance
_global_engine: Optional[CorrelationEngine] = None


def get_correlation_engine() -> CorrelationEngine:
    """Get or create global correlation engine."""
    global _global_engine
    if _global_engine is None:
        _global_engine = CorrelationEngine()
    return _global_engine


def reset_correlation_engine():
    """Reset the global correlation engine."""
    global _global_engine
    _global_engine = None
