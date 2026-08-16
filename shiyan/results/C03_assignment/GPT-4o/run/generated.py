import os as _os
_os.environ.setdefault('RESULT_PATH', '/Applications/yhy/Operational_Agent/shiyan/results/C03_assignment/GPT-4o/run/result.json')
import os
import json
from pulp import LpProblem, LpMinimize, LpVariable, lpSum, LpBinary, value

# Define the cost matrix
cost_matrix = [[9, 2, 7], [6, 4, 3], [5, 8, 1]]
num_workers = len(cost_matrix)
num_tasks = len(cost_matrix[0])

# Create the problem
problem = LpProblem("Assignment_Problem", LpMinimize)

# Define decision variables
x = [[LpVariable(f"x_{i}_{j}", cat=LpBinary) for j in range(num_tasks)] for i in range(num_workers)]

# Objective function
problem += lpSum(cost_matrix[i][j] * x[i][j] for i in range(num_workers) for j in range(num_tasks))

# Constraints: Each worker is assigned to exactly one task
for i in range(num_workers):
    problem += lpSum(x[i][j] for j in range(num_tasks)) == 1

# Constraints: Each task is assigned to exactly one worker
for j in range(num_tasks):
    problem += lpSum(x[i][j] for i in range(num_workers)) == 1

# Solve the problem
problem.solve()

# Extract the results
solution = []
total_cost = value(problem.objective)
for i in range(num_workers):
    for j in range(num_tasks):
        if x[i][j].varValue == 1:
            solution.append({"worker": i + 1, "task": j + 1, "cost": cost_matrix[i][j]})

# Prepare the result
result = {
    "objective": total_cost,
    "solution": solution,
    "feasible": problem.status == 1
}

# Write the result to a JSON file
result_path = os.getenv("RESULT_PATH", "result.json")
with open(result_path, "w") as f:
    json.dump(result, f, indent=4)