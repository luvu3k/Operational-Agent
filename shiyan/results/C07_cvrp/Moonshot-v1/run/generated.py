import os as _os
_os.environ.setdefault('RESULT_PATH', '/Applications/yhy/Operational_Agent/shiyan/results/C07_cvrp/Moonshot-v1/run/result.json')
import pulp
import numpy as np
import json
import os

# Define the problem
prob = pulp.LpProblem("Vehicle_Routing_Problem", pulp.LpMinimize)

# Define the depot and customers
depot = (0, 0)
customers = [(2, 3, 5), (5, 4, 4), (-3, 5, 3), (-4, -2, 6)]

# Define the number of vehicles and their capacity
num_vehicles = 4
vehicle_capacity = 10

# Define the distance function
def distance(p1, p2):
    return np.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)

# Create the decision variables
x = pulp.LpVariable.dicts("x", (range(num_vehicles), range(len(customers))), cat='Binary')
y = pulp.LpVariable.dicts("y", range(num_vehicles), cat='Binary')

# Objective function
prob += pulp.lpSum([distance(depot, customer[:2]) * x[i][j] * 2 for i in range(num_vehicles) for j in range(len(customers))])

# Constraints
for j in range(len(customers)):
    prob += pulp.lpSum([x[i][j] for i in range(num_vehicles)]) == 1

for i in range(num_vehicles):
    prob += pulp.lpSum([customers[j][2] * x[i][j] for j in range(len(customers))]) <= vehicle_capacity * y[i]

for i in range(num_vehicles):
    for j in range(len(customers)):
        prob += x[i][j] <= y[i]

# Solve the problem
prob.solve()

# Save the result to a JSON file
result = {
    "objective": pulp.value(prob.objective),
    "solution": [],
    "feasible": pulp.LpStatus[prob.status] == "Optimal"
}

for i in range(num_vehicles):
    if pulp.value(y[i]) == 1:
        route = []
        for j in range(len(customers)):
            if pulp.value(x[i][j]) == 1:
                route.append(customers[j][:2])
        result["solution"].append(route)

with open(os.environ['RESULT_PATH'], 'w') as f:
    json.dump(result, f)