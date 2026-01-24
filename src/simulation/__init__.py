"""
Simulation module for heterogeneous real-time correlation analysis.

This module provides:
- ScenarioSequencer: State machine for managing scenarios
- UR5eTelemetryGenerator: UR5e simulated data generation
- CorrelationEngine: Axia80 + UR5e correlation calculation
"""

from .scenario_sequencer import ScenarioSequencer, ScenarioType
from .ur5e_generator import UR5eTelemetryGenerator
from .correlation_engine import CorrelationEngine

__all__ = [
    "ScenarioSequencer",
    "ScenarioType",
    "UR5eTelemetryGenerator",
    "CorrelationEngine",
]
