import os as _os
_os.environ.setdefault('RESULT_PATH', '/Applications/yhy/Operational_Agent/shiyan/results/C07_cvrp/DeepSeek-V3-raw/run/result.json')
import math
import json
import os
from pulp import *

# Problem data
customers = {
    0: {'x': 0, 'y': 0, 'demand': 0},
    1: {'x': 2, 'y': 3, 'demand': 5},
    2: {'x': 5, 'y': 4, 'demand': 4},
    3: {'x': -3, 'y': 5, 'demand': 3},
    4: {'x': -4, 'y': -2, 'demand': 6}
}
n_customers = len(customers) - 1
vehicle_capacity = 10
n_vehicles = math.ceil(sum(c['demand'] for c in customers.values()) / vehicle_capacity)

# Calculate distances
dist = {}
for i in customers:
    for j in customers:
        dx = customers[i]['x'] - customers[j]['x']
        dy = customers[i]['y'] - customers[j]['y']
        dist[(i,j)] = math.sqrt(dx**2 + dy**2)

# Create problem
prob = LpProblem("CVRP", LpMinimize)

# Decision variables
x = LpVariable.dicts("x", ((i,j,k) for i in customers for j in customers for k in range(n_vehicles)), cat='Binary')
u = LpVariable.dicts("u", ((i,k) for i in customers for k in range(n_vehicles)), lowBound=0)

# Objective function
prob += lpSum(dist[(i,j)] * x[(i,j,k)] for i in customers for j in customers for k in range(n_vehicles))

# Constraints
for j in range(1, n_customers+1):
    prob += lpSum(x[(i,j,k)] for i in customers for k in range(n_vehicles)) == 1

for k in range(n_vehicles):
    for j in customers:
        prob += lpSum(x[(i,j,k)] for i in customers) == lpSum(x[(j,i,k)] for i in customers)

for k in range(n_vehicles):
    prob += lpSum(x[(0,j,k)] for j in range(1, n_customers+1)) <= 1

for k in range(n_vehicles):
    prob += u[(0,k)] == 0

for k in range(n_vehicles):
    for i in customers:
        for j in customers:
            if i != j and j != 0:
                prob += u[(i,k)] + customers[j]['demand'] <= u[(j,k)] + vehicle_capacity*(1 - x[(i,j,k)])

for k in range(n_vehicles):
    for i in customers:
        prob += u[(i,k)] >= customers[i]['demand']
        prob += u[(i,k)] <= vehicle_capacity

# Solve
prob.solve(PULP_CBC_CMD(msg=False))

# Prepare results
solution = []
total_distance = 0
for k in range(n_vehicles):
    route = []
    current = 0
    while True:
        next_node = None
        for j in customers:
            if j != current and value(x[(current,j,k)]) > 0.5:
                next_node = j
                break
        if next_node is None:
            break
        route.append(next_node)
        total_distance += dist[(current, next_node)]
        current = next_node
    if route:
        solution.append([0] + route + [0])
        total_distance += dist[(current, 0)]

result = {
    "objective": total_distance,
    "solution": solution,
    "feasible": prob.status == LpStatusOptimal
}

# Save result
with open(os.getenv('RESULT_PATH', 'result.json'), 'w') as f:
    json.dump(result, f)