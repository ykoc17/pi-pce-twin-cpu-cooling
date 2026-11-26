"""Predeclared PCE comparison: degrees 1/2, with or without monotonicity constraints."""

from dataclasses import dataclass
from pathlib import Path

DEFAULT_PCE_OUTPUT = Path("results/monotonic_pce")


@dataclass(frozen=True)
class PCEConfig:
    degrees: tuple[int, ...] = (1, 2)
    max_iterations: int = 3000
    solver_tolerance: float = 1e-12
    feasibility_tolerance: float = 1e-6  # C per normalized input coordinate

    def __post_init__(self):
        if not self.degrees or len(set(self.degrees)) != len(self.degrees) or any(
            degree not in (1, 2) for degree in self.degrees
        ):
            raise ValueError("Only unique total degrees 1 and 2 are supported.")
        if self.max_iterations < 1 or not 0 < self.solver_tolerance < 1 or not 0 < self.feasibility_tolerance < 1:
            raise ValueError("Solver limits and tolerances must be positive and finite.")


DEFAULT_PCE_CONFIG = PCEConfig()
