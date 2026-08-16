import os as _os
_os.environ.setdefault('RESULT_PATH', '/Applications/yhy/Operational_Agent/shiyan/results/C09_max_flow/Moonshot-v1/run/result.json')
import pulp
import json
import os

# Define the problem
prob = pulp.LpProblem("MaxFlow", pulp.LpMaximize)

# Define the variables
x_sa = pulp.LpVariable("x_sa", lowBound=0, upBound=10, cat='Continuous')
x_sb = pulp.LpVariable("x_sb", lowBound=0, upBound=5, cat='Continuous')
x_ab = pulp.LpVariable("x_ab", lowBound=0, upBound=15, cat='Continuous')
x_at = pulp.LpVariable("x_at", lowBound=0, upBound=10, cat='Continuous')
x_bt = pulp.LpVariable("x_bt", lowBound=0, upBound=10, cat='Continuous')

# Objective function
prob += x_at + x_bt, "Total Flow"

# Constraints
prob += x_sa - x_ab == x_at, "Flow conservation at a"
prob += x_sb - x_ab + x_bt == x_bt, "Flow conservation at b"

# Solve the problem
prob.solve()

# Write the result to a JSON file
result = {
    "objective": pulp.value(prob.objective),
    "solution": {
        "x_sa": pulp.value(x_sa),
        "x_sb": pulp.value(x_sb),
        "x_ab": pulp.value(x_ab),
        "x_at": pulp.value(x_at),
        "x_bt": pulp.value(x_bt)
    },
    "feasible": pulp.LpStatus[prob.status] == "Optimal"
}

with open(os.environ['RESULT_PATH'], 'w') as f:
    json.dump(result, f)