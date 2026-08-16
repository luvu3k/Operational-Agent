import os as _os
_os.environ.setdefault('RESULT_PATH', '/Applications/yhy/Operational_Agent/shiyan/results/C02_tsp/GPT-4o/run/result.json')
import json
import math
import os
from itertools import permutations
from pulp import LpProblem, LpMinimize, LpVariable, lpSum, LpStatus, value

# Coordinates of the cities
cities = {
    "A": (0, 0),
    "B": (0, 4),
    "C": (4, 4),
    "D": (4, 0),
    "E": (2, 2)
}

# Calculate Euclidean distance
def euclidean_distance(coord1, coord2):
    return math.sqrt((coord1[0] - coord2[0])**2 + (coord1[1] - coord2[1])**2)

# Distance matrix
distances = {
    (i, j): euclidean_distance(cities[i], cities[j]) for i in cities for j in cities if i != j
}

# Problem definition
problem = LpProblem("Traveling_Salesman_Problem", LpMinimize)

# Decision variables
x = LpVariable.dicts("x", distances, cat="Binary")

# Objective function
problem += lpSum(distances[i, j] * x[i, j] for i, j in distances)

# Constraints
for k in cities:
    problem += lpSum(x[i, k] for i in cities if i != k) == 1  # Enter each city once
    problem += lpSum(x[k, j] for j in cities if j != k) == 1  # Leave each city once

# Solve the problem
problem.solve()

# Extract the solution
route = []
if LpStatus[problem.status] == "Optimal":
    current_city = "A"
    visited = set()
    while len(visited) < len(cities):
        visited.add(current_city)
        for next_city in cities:
            if current_city != next_city and x[current_city, next_city].varValue == 1:
                route.append((current_city, next_city))
                current_city = next_city
                break
    route.append((current_city, "A"))  # Return to the starting city

# Output results
result = {
    "objective": value(problem.objective),
    "solution": route,
    "feasible": LpStatus[problem.status] == "Optimal"
}

result_path = os.getenv("RESULT_PATH", "result.json")
with open(result_path, "w") as f:
    json.dump(result, f)