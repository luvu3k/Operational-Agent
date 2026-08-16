import os as _os
_os.environ.setdefault('RESULT_PATH', '/Applications/yhy/Operational_Agent/shiyan/results/C04_bin_packing/GPT-4o/run/result.json')
import os
import json
from pulp import LpProblem, LpMinimize, LpVariable, lpSum, LpBinary, value

# Data
volumes = [4, 8, 1, 4, 2, 1]
capacity = 10
num_items = len(volumes)
num_bins = num_items  # Worst case: each item in its own bin

# Problem
problem = LpProblem("Bin_Packing_Problem", LpMinimize)

# Variables
x = [[LpVariable(f"x_{i}_{j}", cat=LpBinary) for j in range(num_bins)] for i in range(num_items)]
y = [LpVariable(f"y_{j}", cat=LpBinary) for j in range(num_bins)]

# Objective: Minimize the number of bins used
problem += lpSum(y)

# Constraints
# Each item must be in exactly one bin
for i in range(num_items):
    problem += lpSum(x[i][j] for j in range(num_bins)) == 1

# Bin capacity constraints
for j in range(num_bins):
    problem += lpSum(volumes[i] * x[i][j] for i in range(num_items)) <= capacity * y[j]

# Solve
problem.solve()

# Extract results
solution = {
    "objective": value(problem.objective),
    "solution": [],
    "feasible": problem.status == 1
}

if solution["feasible"]:
    for j in range(num_bins):
        bin_items = [i for i in range(num_items) if x[i][j].varValue == 1]
        if bin_items:
            solution["solution"].append(bin_items)

# Write results to JSON
result_path = os.getenv("RESULT_PATH", "result.json")
with open(result_path, "w") as f:
    json.dump(solution, f)