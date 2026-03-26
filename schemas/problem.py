"""
Role:
- Define the canonical optimization problem structure used across the agent.

Called by:
- `Operational-Agent.problem_builder`
- `Operational-Agent.confirmation`
- `tools.validator_tool`
"""

from dataclasses import dataclass, field
from typing import List


@dataclass
class ProblemSpec:
    skill_name: str
    description: str
    objectives: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
