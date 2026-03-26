"""
Role:
- Define the normalized representation of an objective function.

Called by:
- `Operational-Agent.problem_builder`
- `tools.validator_tool`
"""

from dataclasses import dataclass


@dataclass
class ObjectiveSpec:
    name: str
    expression: str
    sense: str = "min"
