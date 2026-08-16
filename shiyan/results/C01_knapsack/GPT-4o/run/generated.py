import os as _os
_os.environ.setdefault('RESULT_PATH', '/Applications/yhy/Operational_Agent/shiyan/results/C01_knapsack/GPT-4o/run/result.json')
import os
import json
from pulp import LpMaximize, LpProblem, LpVariable, lpSum, value

# Problem data
weights = [2, 3, 4, 5, 9]
values = [3, 4, 5, 8, 10]
max_weight = 20
num_items = len(weights)

# Define the problem
problem = LpProblem("Knapsack_Problem", LpMaximize)

# Define decision variables
x = [LpVariable(f"x{i}", cat="Binary") for i in range(num_items)]

# Objective function
problem += lpSum(values[i] * x[i] for i in range(num_items)), "Total_Value"

# Weight constraint
problem += lpSum(weights[i] * x[i] for i in range(num_items)) <= max_weight, "Weight_Limit"

# Solve the problem
problem.solve()

# Extract results
selected_items = [i for i in range(num_items) if x[i].value() == 1]
total_value = value(problem.objective)
feasible = problem.status == 1

# Prepare result
result = {
    "objective": total_value,
    "solution": selected_items,
    "feasible": feasible
}

# Write result to JSON file
result_path = os.getenv("RESULT_PATH", "result.json")
with open(result_path, "w") as f:
    json.dump(result, f)