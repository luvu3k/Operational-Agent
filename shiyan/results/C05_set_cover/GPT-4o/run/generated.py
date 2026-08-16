import os as _os
_os.environ.setdefault('RESULT_PATH', '/Applications/yhy/Operational_Agent/shiyan/results/C05_set_cover/GPT-4o/run/result.json')
import os
import json
from pulp import LpProblem, LpVariable, lpSum, LpMinimize, LpStatus

# Define the problem
problem = LpProblem("Set_Cover_Problem", LpMinimize)

# Subsets and their elements
subsets = {
    1: {1, 2, 3},
    2: {2, 4},
    3: {3, 4},
    4: {4, 5}
}
universe = {1, 2, 3, 4, 5}

# Decision variables
x = {i: LpVariable(f"x_{i}", cat="Binary") for i in subsets}

# Objective function: Minimize the number of selected subsets
problem += lpSum(x[i] for i in subsets), "Minimize_Subsets"

# Constraints: Every element in the universe must be covered
for element in universe:
    problem += lpSum(x[i] for i in subsets if element in subsets[i]) >= 1, f"Cover_{element}"

# Solve the problem
problem.solve()

# Extract results
result = {
    "objective": None,
    "solution": [],
    "feasible": LpStatus[problem.status] == "Optimal"
}

if result["feasible"]:
    result["objective"] = int(sum(x[i].varValue for i in subsets))
    result["solution"] = [i for i in subsets if x[i].varValue == 1]

# Write results to JSON file
result_path = os.getenv("RESULT_PATH", "result.json")
with open(result_path, "w") as f:
    json.dump(result, f)