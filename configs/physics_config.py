"""Settings for the three-constant thermal-resistance rule and its check points."""

from dataclasses import dataclass
import math
from pathlib import Path

DEFAULT_PHYSICS_OUTPUT = Path("results/physics")


@dataclass(frozen=True)
class PhysicsConfig:
    # Starting values (offset C, R0 C/W, K C/W, gamma); the best converged fit wins.
    # R0 is ignored by the three-constant rule and used only for the comparison.
    starts: tuple[tuple[float, float, float, float], ...] = (
        (5.0, 0.01, 0.02, 0.5), (0.0, 0.03, 0.01, 1.0), (10.0, 0.001, 0.04, 0.2),
    )
    max_abs_offset_C: float = 50.0
    max_resistance_C_per_W: float = 1.0
    min_gamma: float = 1e-3
    max_gamma: float = 5.0

    # Sobol check points over the reference input ranges: 2**check_point_power points.
    check_point_power: int = 7
    check_point_seed: int = 20261125

    # Sensitivity check only. Observations at or above this target are dominated by
    # CPU throttling; the main fit keeps every accepted observation.
    throttling_sensitivity_target_C: float = 93.5

    def __post_init__(self):
        if not self.starts or any(len(start) != 4 for start in self.starts):
            raise ValueError("starts must contain four values per starting point.")
        for name in ("max_abs_offset_C", "max_resistance_C_per_W", "min_gamma", "max_gamma",
                     "throttling_sensitivity_target_C"):
            value = getattr(self, name)
            if not math.isfinite(value) or value <= 0:
                raise ValueError(f"{name} must be finite and positive.")
        if self.min_gamma >= self.max_gamma:
            raise ValueError("min_gamma must be below max_gamma.")
        if self.check_point_power < 1:
            raise ValueError("check_point_power must be at least 1.")


DEFAULT_PHYSICS_CONFIG = PhysicsConfig()
