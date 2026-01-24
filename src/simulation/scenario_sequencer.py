"""
Scenario Sequencer - State machine for managing simulation scenarios.

This module manages scenario transitions with proper duration and smoothing
to create realistic-looking data patterns.
"""

import random
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Optional, Tuple


class ScenarioType(str, Enum):
    """Simulation scenario types."""
    NORMAL = "normal"
    COLLISION = "collision"
    OVERLOAD = "overload"
    WEAR = "wear"
    RISK_APPROACH = "risk_approach"


@dataclass
class ScenarioConfig:
    """Configuration for a scenario."""
    weight: float  # Selection probability weight
    duration_range: Tuple[int, int]  # (min_seconds, max_seconds)
    description: str


# Scenario configurations based on design document
SCENARIO_CONFIGS: Dict[ScenarioType, ScenarioConfig] = {
    ScenarioType.NORMAL: ScenarioConfig(
        weight=0.70,
        duration_range=(10, 20),
        description="Normal operation - stable work cycle"
    ),
    ScenarioType.COLLISION: ScenarioConfig(
        weight=0.10,
        duration_range=(5, 10),
        description="Collision sequence - approach → contact → spike → stop"
    ),
    ScenarioType.OVERLOAD: ScenarioConfig(
        weight=0.10,
        duration_range=(8, 15),
        description="Overload condition - sustained high force/torque"
    ),
    ScenarioType.WEAR: ScenarioConfig(
        weight=0.05,
        duration_range=(10, 20),
        description="Wear indication - torque/force mismatch"
    ),
    ScenarioType.RISK_APPROACH: ScenarioConfig(
        weight=0.05,
        duration_range=(5, 12),
        description="Risk approach - gradual increase toward danger"
    ),
}


@dataclass
class ScenarioState:
    """Current state of the scenario sequencer."""
    current_scenario: ScenarioType
    start_time: float
    duration: int
    previous_scenario: Optional[ScenarioType] = None
    transition_start_time: Optional[float] = None
    transition_duration: float = 2.0  # seconds for smoothing


class ScenarioSequencer:
    """
    State machine for managing simulation scenarios.

    Ensures scenarios are maintained for a realistic duration (5-20 seconds)
    and transitions are smoothed to prevent jarring data changes.
    """

    TRANSITION_DURATION = 2.0  # seconds

    def __init__(self, initial_scenario: ScenarioType = ScenarioType.NORMAL):
        """Initialize the sequencer."""
        self._configs = SCENARIO_CONFIGS
        self._state = ScenarioState(
            current_scenario=initial_scenario,
            start_time=time.time(),
            duration=self._random_duration(initial_scenario)
        )

    def _random_duration(self, scenario: ScenarioType) -> int:
        """Get random duration for a scenario."""
        config = self._configs[scenario]
        return random.randint(*config.duration_range)

    def _select_next_scenario(self) -> ScenarioType:
        """Select next scenario based on weights."""
        scenarios = list(self._configs.keys())
        weights = [self._configs[s].weight for s in scenarios]
        return random.choices(scenarios, weights=weights)[0]

    def tick(self) -> Dict:
        """
        Process one tick of the sequencer.

        Returns:
            Dict containing:
                - scenario: Current scenario type
                - phase: Progress within scenario (0.0 to 1.0)
                - elapsed_sec: Seconds since scenario start
                - remaining_sec: Seconds until scenario ends
                - is_transitioning: Whether in transition period
                - transition_progress: Transition progress (0.0 to 1.0)
        """
        now = time.time()
        elapsed = now - self._state.start_time

        # Check if scenario should end
        if elapsed >= self._state.duration:
            self._transition_to_next()
            elapsed = 0.0

        # Calculate transition progress
        is_transitioning = False
        transition_progress = 1.0

        if self._state.transition_start_time is not None:
            transition_elapsed = now - self._state.transition_start_time
            if transition_elapsed < self.TRANSITION_DURATION:
                is_transitioning = True
                transition_progress = transition_elapsed / self.TRANSITION_DURATION
            else:
                # Transition complete
                self._state.transition_start_time = None
                self._state.previous_scenario = None

        # Calculate phase within scenario
        phase = min(elapsed / self._state.duration, 1.0) if self._state.duration > 0 else 0.0

        return {
            "scenario": self._state.current_scenario.value,
            "phase": phase,
            "elapsed_sec": round(elapsed, 1),
            "remaining_sec": round(max(0, self._state.duration - elapsed), 1),
            "duration_sec": self._state.duration,
            "is_transitioning": is_transitioning,
            "transition_progress": round(transition_progress, 2),
            "previous_scenario": self._state.previous_scenario.value if self._state.previous_scenario else None,
        }

    def _transition_to_next(self):
        """Transition to next scenario."""
        self._state.previous_scenario = self._state.current_scenario
        self._state.current_scenario = self._select_next_scenario()
        self._state.start_time = time.time()
        self._state.duration = self._random_duration(self._state.current_scenario)
        self._state.transition_start_time = time.time()

    def force_scenario(self, scenario: ScenarioType, duration: Optional[int] = None):
        """
        Force a specific scenario (for testing/demo purposes).

        Args:
            scenario: Scenario to force
            duration: Optional duration override
        """
        self._state.previous_scenario = self._state.current_scenario
        self._state.current_scenario = scenario
        self._state.start_time = time.time()
        self._state.duration = duration or self._random_duration(scenario)
        self._state.transition_start_time = time.time()

    @property
    def current_scenario(self) -> ScenarioType:
        """Get current scenario type."""
        return self._state.current_scenario

    @property
    def scenario_config(self) -> ScenarioConfig:
        """Get current scenario configuration."""
        return self._configs[self._state.current_scenario]

    def get_scenario_info(self) -> Dict:
        """Get information about current scenario."""
        config = self._configs[self._state.current_scenario]
        return {
            "type": self._state.current_scenario.value,
            "description": config.description,
            "weight": config.weight,
            "duration_range": config.duration_range,
        }


# Convenience function for creating a global sequencer
_global_sequencer: Optional[ScenarioSequencer] = None


def get_scenario_sequencer() -> ScenarioSequencer:
    """Get or create global scenario sequencer singleton."""
    global _global_sequencer
    if _global_sequencer is None:
        _global_sequencer = ScenarioSequencer()
    return _global_sequencer


def reset_scenario_sequencer():
    """Reset the global scenario sequencer."""
    global _global_sequencer
    _global_sequencer = None
