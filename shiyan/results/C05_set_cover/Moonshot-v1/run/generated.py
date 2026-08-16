import os as _os
_os.environ.setdefault('RESULT_PATH', '/Applications/yhy/Operational_Agent/shiyan/results/C05_set_cover/Moonshot-v1/run/result.json')
import pulp
import json
import os

# Define the problem
problem = pulp.LpProblem("Minimum_Subset_Cover", pulp.LpMinimize)

# Define the binary variables
x = pulp.LpVariable.dicts("x", range(1, 5), cat='Binary')

# Define the objective function
problem += pulp.lpSum([x[i] for i in range(1, 5)])

# Define the constraints
problem += x[1] + x[2] >= 1  # to cover element 2
problem += x[1] + x[3] >= 1  # to cover element 3
problem += x[2] + x[3] + x[4] >= 1  # to cover element 4
problem += x[1] + x[4] >= 1  # to cover element 5

# Solve the problem
problem.solve()

# Store the result in a dictionary
result = {
    "objective": pulp.value(problem.objective),
    "solution": {i: pulp.value(x[i]) for i in range(1, 5)},
    "feasible": pulp.LpStatus[problem.status] == "Optimal"
}

# Write the result to a JSON file
with open(os.environ['RESULT_PATH'], 'w') as f:
    json.dump(result, f)