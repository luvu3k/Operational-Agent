import os as _os
_os.environ.setdefault('RESULT_PATH', '/Applications/yhy/Operational_Agent/shiyan/results/C04_bin_packing/DeepSeek-V3-raw/run/result.json')
from pulp import *
import json
import os

# Problem data
volumes = [4, 8, 1, 4, 2, 1]
capacity = 10
n_items = len(volumes)
n_bins = n_items  # worst case: each item in its own bin

# Create model
model = LpProblem("BinPacking", LpMinimize)

# Variables
y = [LpVariable(f"y_{j}", cat="Binary") for j in range(n_bins)]
x = [[LpVariable(f"x_{i}_{j}", cat="Binary") for j in range(n_bins)] for i in range(n_items)]

# Objective: minimize number of bins used
model += lpSum(y)

# Constraints
for i in range(n_items):
    model += lpSum(x[i][j] for j in range(n_bins)) == 1  # each item in exactly one bin

for j in range(n_bins):
    model += lpSum(volumes[i] * x[i][j] for i in range(n_items)) <= capacity * y[j]  # bin capacity

# Solve
model.solve(PULP_CBC_CMD(msg=False))

# Prepare result
solution = []
for j in range(n_bins):
    if y[j].value() == 1:
        bin_items = [i for i in range(n_items) if x[i][j].value() == 1]
        solution.append([volumes[i] for i in bin_items])

result = {
    "objective": int(value(model.objective)),
    "solution": solution,
    "feasible": model.status == 1
}

# Save result
with open(os.getenv('RESULT_PATH', 'result.json'), 'w') as f:
    json.dump(result, f)