import os as _os
_os.environ.setdefault('RESULT_PATH', '/Applications/yhy/Operational_Agent/shiyan/results/C04_bin_packing/Moonshot-v1/run/result.json')
import pulp
import json
import os

# Define the problem
problem = pulp.LpProblem("Minimize_Bins", pulp.LpMinimize)

# Define the items and their volumes
items = [4, 8, 1, 4, 2, 1]
n_items = len(items)

# Define the box capacity
box_capacity = 10

# Define the binary variables for each item in each box
x = pulp.LpVariable.dicts("x", (range(n_items), range(n_items + 1)), cat='Binary')

# Define the binary variables for each box
y = pulp.LpVariable.dicts("y", (range(n_items + 1)), cat='Binary')

# Objective function: minimize the number of boxes used
problem += pulp.lpSum(y[i] for i in range(n_items + 1))

# Constraint 1: each item must be placed in exactly one box
for i in range(n_items):
    problem += pulp.lpSum(x[i][j] for j in range(n_items + 1)) == 1

# Constraint 2: the volume of items in each box must not exceed the box capacity
for j in range(n_items + 1):
    problem += pulp.lpSum(items[i] * x[i][j] for i in range(n_items)) <= box_capacity * y[j]

# Solve the problem
problem.solve()

# Store the result in a dictionary
result = {
    "objective": pulp.value(problem.objective),
    "solution": [],
    "feasible": pulp.LpStatus[problem.status] == "Optimal"
}

# Store the solution in the result dictionary
for i in range(n_items):
    for j in range(n_items + 1):
        if pulp.value(x[i][j]) == 1:
            result["solution"].append((i, j))

# Write the result to a JSON file
with open(os.environ['RESULT_PATH'], 'w') as f:
    json.dump(result, f)