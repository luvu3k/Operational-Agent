import os as _os
_os.environ.setdefault('RESULT_PATH', '/Applications/yhy/Operational_Agent/shiyan/results/C02_tsp/DeepSeek-V3-raw/run/result.json')
import math
import json
import os
from itertools import combinations
from pulp import LpProblem, LpMinimize, LpVariable, lpSum, LpBinary

# City coordinates and labels
cities = {
    0: (0, 0, 'A'),
    1: (0, 4, 'B'),
    2: (4, 4, 'C'),
    3: (4, 0, 'D'),
    4: (2, 2, 'E')
}

# Calculate distances
n = len(cities)
dist = [[0]*n for _ in range(n)]
for i in range(n):
    for j in range(n):
        if i != j:
            x1, y1, _ = cities[i]
            x2, y2, _ = cities[j]
            dist[i][j] = math.sqrt((x2-x1)**2 + (y2-y1)**2)

# Create problem
prob = LpProblem("TSP", LpMinimize)

# Variables
x = {}
for i in range(n):
    for j in range(n):
        if i != j:
            x[i,j] = LpVariable(f"x_{i}_{j}", cat=LpBinary)

# Objective
prob += lpSum(dist[i][j] * x[i,j] for i in range(n) for j in range(n) if i != j)

# Constraints
for k in range(n):
    prob += lpSum(x[i,k] for i in range(n) if i != k) == 1  # Enter each city once
    prob += lpSum(x[k,j] for j in range(n) if j != k) == 1  # Exit each city once

# Subtour elimination (MTZ formulation)
u = [LpVariable(f"u_{i}", lowBound=0, upBound=n-1) for i in range(n)]
prob += u[0] == 0
for i in range(1,n):
    for j in range(1,n):
        if i != j:
            prob += u[i] - u[j] + n*x[i,j] <= n-1

# Solve
prob.solve()

# Extract solution
tour = []
if prob.status == 1:
    current = 0
    visited = set()
    while True:
        for j in range(n):
            if j != current and x[current,j].value() == 1:
                tour.append(cities[current][2])
                visited.add(current)
                current = j
                break
        if current == 0 and len(visited) == n:
            break
    tour.append('A')

# Prepare result
result = {
    "objective": round(prob.objective.value(), 2),
    "solution": " -> ".join(tour),
    "feasible": True
}

# Save to file
with open(os.getenv('RESULT_PATH', 'result.json'), 'w') as f:
    json.dump(result, f)

print(result)