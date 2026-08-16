import os as _os
_os.environ.setdefault('RESULT_PATH', '/Applications/yhy/Operational_Agent/shiyan/results/C09_max_flow/GPT-4o/run/result.json')
import os
import json
from pulp import LpProblem, LpMaximize, LpVariable, lpSum, value

# Define the problem
problem = LpProblem("MaxFlow", LpMaximize)

# Define variables
x_sa = LpVariable("x_sa", 0, 10)  # Flow from s to a
x_sb = LpVariable("x_sb", 0, 5)   # Flow from s to b
x_ab = LpVariable("x_ab", 0, 15)  # Flow from a to b
x_at = LpVariable("x_at", 0, 10)  # Flow from a to t
x_bt = LpVariable("x_bt", 0, 10)  # Flow from b to t
f = LpVariable("f", 0)            # Total flow from s to t

# Objective function: Maximize total flow f
problem += f, "Total_Flow"

# Constraints
problem += x_sa + x_sb == f, "Flow_Conservation_at_s"
problem += x_sa == x_ab + x_at, "Flow_Conservation_at_a"
problem += x_sb + x_ab == x_bt, "Flow_Conservation_at_b"

# Solve the problem
problem.solve()

# Extract results
result = {
    "objective": value(problem.objective),
    "solution": {
        "x_sa": value(x_sa),
        "x_sb": value(x_sb),
        "x_ab": value(x_ab),
        "x_at": value(x_at),
        "x_bt": value(x_bt),
    },
    "feasible": problem.status == 1
}

# Write results to result.json
result_path = os.getenv("RESULT_PATH", "result.json")
with open(result_path, "w") as f:
    json.dump(result, f)