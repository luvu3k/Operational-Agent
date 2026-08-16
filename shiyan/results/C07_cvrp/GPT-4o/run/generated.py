import os as _os
_os.environ.setdefault('RESULT_PATH', '/Applications/yhy/Operational_Agent/shiyan/results/C07_cvrp/GPT-4o/run/result.json')
import json
import math
import os
from pulp import LpProblem, LpMinimize, LpVariable, lpSum, LpBinary, value

# Data
coordinates = {0: (0, 0), 1: (2, 3), 2: (5, 4), 3: (-3, 5), 4: (-4, -2)}
demands = {0: 0, 1: 5, 2: 4, 3: 3, 4: 6}
vehicle_capacity = 10
num_vehicles = 4
nodes = list(coordinates.keys())

# Distance calculation
def euclidean_distance(i, j):
    return math.sqrt((coordinates[i][0] - coordinates[j][0])**2 + (coordinates[i][1] - coordinates[j][1])**2)

distances = {(i, j): euclidean_distance(i, j) for i in nodes for j in nodes if i != j}

# Problem
problem = LpProblem("Vehicle_Routing_Problem", LpMinimize)

# Decision variables
x = LpVariable.dicts("x", ((i, j, k) for i in nodes for j in nodes for k in range(num_vehicles) if i != j), cat=LpBinary)
u = LpVariable.dicts("u", ((i, k) for i in nodes for k in range(num_vehicles)), lowBound=0)

# Objective function
problem += lpSum(distances[i, j] * x[i, j, k] for i, j, k in x)

# Constraints
# Each customer is visited exactly once
for i in nodes[1:]:
    problem += lpSum(x[i, j, k] for j in nodes if i != j for k in range(num_vehicles)) == 1

# Flow conservation
for k in range(num_vehicles):
    for i in nodes:
        problem += lpSum(x[i, j, k] for j in nodes if i != j) == lpSum(x[j, i, k] for j in nodes if i != j)

# Vehicle capacity
for k in range(num_vehicles):
    for i in nodes:
        for j in nodes:
            if i != j:
                problem += u[i, k] + demands[j] * x[i, j, k] <= u[j, k] + vehicle_capacity * (1 - x[i, j, k])

# Subtour elimination
for k in range(num_vehicles):
    for i in nodes[1:]:
        problem += u[i, k] >= demands[i]

# Depot constraints
for k in range(num_vehicles):
    problem += u[0, k] == 0

# Solve
problem.solve()

# Extract results
routes = []
for k in range(num_vehicles):
    route = []
    current_node = 0
    while True:
        for j in nodes:
            if j != current_node and any(x[current_node, j, k].varValue > 0.5 for k in range(num_vehicles)):
                route.append(j)
                current_node = j
                break
        else:
            break
    if route:
        routes.append(route)

result = {
    "objective": value(problem.objective),
    "solution": routes,
    "feasible": problem.status == 1
}

# Write to result.json
result_path = os.getenv("RESULT_PATH", "result.json")
with open(result_path, "w") as f:
    json.dump(result, f)