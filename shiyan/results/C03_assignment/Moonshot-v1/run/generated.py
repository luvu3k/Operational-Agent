import os as _os
_os.environ.setdefault('RESULT_PATH', '/Applications/yhy/Operational_Agent/shiyan/results/C03_assignment/Moonshot-v1/run/result.json')
import pulp
import json
import os

# Define the problem
problem = pulp.LpProblem("Minimize_Cost", pulp.LpMinimize)

# Define the variables
x = pulp.LpVariable.dicts("x", (range(3), range(3)), cat='Binary')

# Define the cost matrix
cost_matrix = [[9, 2, 7], [6, 4, 3], [5, 8, 1]]

# Define the objective function
problem += pulp.lpSum([cost_matrix[i][j] * x[i][j] for i in range(3) for j in range(3)])

# Define the constraints
for i in range(3):
    problem += pulp.lpSum([x[i][j] for j in range(3)]) == 1
for j in range(3):
    problem += pulp.lpSum([x[i][j] for i in range(3)]) == 1

# Solve the problem
problem.solve()

# Write the result to a JSON file
result = {
    "objective": pulp.value(problem.objective),
    "solution": {i: {j: x[i][j].varValue for j in range(3)} for i in range(3)},
    "feasible": pulp.LpStatus[problem.status] == "Optimal"
}

result_path = os.environ.get('RESULT_PATH', 'result.json')
with open(result_path, 'w') as f:
    json.dump(result, f)