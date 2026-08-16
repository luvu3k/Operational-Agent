import os as _os
_os.environ.setdefault('RESULT_PATH', '/Applications/yhy/Operational_Agent/shiyan/results/C02_tsp/Moonshot-v1/run/result.json')
import pulp
import numpy as np
import json
import os

# Define the cities and their coordinates
cities = {
    'A': (0, 0),
    'B': (0, 4),
    'C': (4, 4),
    'D': (4, 0),
    'E': (2, 2)
}

# Calculate the distances between cities
distances = {(i, j): np.sqrt((cities[i][0] - cities[j][0])**2 + (cities[i][1] - cities[j][1])**2)
             for i in cities for j in cities if i != j}

# Create the problem
prob = pulp.LpProblem("TSP", pulp.LpMinimize)

# Create the variables
x = pulp.LpVariable.dicts("x", ((i, j) for i in cities for j in cities if i != j), cat='Binary')

# Objective function
prob += pulp.lpSum(distances[i, j] * x[(i, j)] for i in cities for j in cities if i != j)

# Constraints
for i in cities:
    prob += pulp.lpSum(x[(i, j)] for j in cities if i != j) == 1
    prob += pulp.lpSum(x[(j, i)] for j in cities if i != j) == 1

for i in cities:
    for j in cities:
        if i != j:
            prob += pulp.lpSum(x[(i, k)] - x[(k, i)] for k in cities if k != i and k != j) == 0

# Solve the problem
prob.solve()

# Save the result
result = {
    'objective': pulp.value(prob.objective),
    'solution': {(i, j): pulp.value(x[(i, j)]) for i in cities for j in cities if i != j},
    'feasible': pulp.LpStatus[prob.status] == 'Optimal'
}

with open(os.environ['RESULT_PATH'], 'w') as f:
    json.dump(result, f)