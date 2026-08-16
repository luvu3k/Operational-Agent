import os as _os
_os.environ.setdefault('RESULT_PATH', '/Applications/yhy/Operational_Agent/shiyan/results/C01_knapsack/Moonshot-v1/run/result.json')
import pulp
import json
import os

# Define the problem
problem = pulp.LpProblem("KnapsackProblem", pulp.LpMaximize)

# Define the items
weights = [2, 3, 4, 5, 9]
values = [3, 4, 5, 8, 10]
items = list(range(1, len(values) + 1))

# Define the decision variables
x = pulp.LpVariable.dicts("x", items, cat='Binary')

# Define the objective function
problem += pulp.lpSum([values[i-1] * x[i] for i in items]), "TotalValue"

# Define the constraint
problem += pulp.lpSum([weights[i-1] * x[i] for i in items]) <= 20, "WeightConstraint"

# Solve the problem
problem.solve()

# Write the result to a JSON file
result = {
    "objective": pulp.value(problem.objective),
    "solution": {i: pulp.value(x[i]) for i in items},
    "feasible": pulp.LpStatus[problem.status] == "Optimal"
}

with open(os.environ['RESULT_PATH'], 'w') as f:
    json.dump(result, f)