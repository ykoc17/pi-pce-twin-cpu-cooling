"""All time, input-stability, and thermal-stability thresholds for preprocessing.

Defaults are transparent selection heuristics for five-minute data, not calibrated
equilibrium criteria. Fan tolerances refer to the original unverified-unit signal.
"""

from dataclasses import dataclass
import math


@dataclass(frozen=True)
class PreprocessingConfig:
    """Thresholds applied to every CPU sensor and every accepted interval."""

    sample_interval_minutes: float = 5.0
    minimum_dwell_minutes: float = 30.0
    initial_settling_minutes: float = 20.0
    stability_window_minutes: float = 30.0

    # Compare persistent input levels on both sides of a possible transition.
    level_comparison_window_minutes: float = 15.0
    transition_guard_minutes: float = 15.0
    minimum_change_separation_minutes: float = 30.0
    use_workload_marker: bool = True
    workload_step_pct: float = 10.0
    workload_range_pct: float = 10.0

    # Differences between the two input-level medians define a change.
    cpu_power_step_abs_W: float = 80.0
    cpu_power_step_relative: float = 0.04
    inlet_temperature_step_C: float = 1.0
    fan_power_step_raw: float = 0.06

    # Peak-to-peak input limits: absolute + relative * abs(interval mean).
    cpu_power_range_abs_W: float = 40.0
    cpu_power_range_relative: float = 0.04
    inlet_temperature_range_C: float = 1.0
    fan_power_range_abs_raw: float = 0.025
    fan_power_range_relative: float = 0.03

    # Every CPU must pass these limits in every sliding window AND globally.
    # One-degree sensor readings can fluctuate at a stationary operating condition.
    cpu_temperature_std_C: float = 1.0
    cpu_temperature_range_C: float = 3.0
    # Short windows tolerate apparent slopes from 1 C sensor quantization;
    # the complete accepted interval must still pass the stricter drift limit.
    cpu_temperature_window_drift_C_per_minute: float = 0.08
    cpu_temperature_drift_C_per_minute: float = 0.03

    def __post_init__(self):
        if not isinstance(self.use_workload_marker, bool):
            raise ValueError("use_workload_marker must be a boolean.")
        for name, value in vars(self).items():
            if not math.isfinite(value) or value < 0:
                raise ValueError(f"{name} must be finite and nonnegative.")
        if self.sample_interval_minutes <= 0:
            raise ValueError("sample_interval_minutes must be positive.")
        if self.stability_window_minutes < 2 * self.sample_interval_minutes:
            raise ValueError("stability_window_minutes must span at least three samples.")
        if self.minimum_dwell_minutes < self.stability_window_minutes:
            raise ValueError("minimum_dwell_minutes must be at least stability_window_minutes.")
        if self.level_comparison_window_minutes < self.sample_interval_minutes:
            raise ValueError("level_comparison_window_minutes must span at least two samples.")
        if self.minimum_change_separation_minutes < self.sample_interval_minutes:
            raise ValueError("minimum_change_separation_minutes must be at least one sample interval.")


DEFAULT_PREPROCESSING_CONFIG = PreprocessingConfig()
