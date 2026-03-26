"""
Role:
- Define the normalized representation of a solver result.

Called by:
- `solver.postprocess.parser`
- `solver.postprocess.evaluator`
- `tools.visualization_tool`
"""

from dataclasses import dataclass, field
from typing import Dict, Any


@dataclass
class SolutionSpec:
    objective_value: float = 0.0
    metrics: Dict[str, Any] = field(default_factory=dict)
