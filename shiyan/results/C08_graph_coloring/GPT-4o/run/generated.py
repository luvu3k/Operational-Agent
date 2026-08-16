import os as _os
_os.environ.setdefault('RESULT_PATH', '/Applications/yhy/Operational_Agent/shiyan/results/C08_graph_coloring/GPT-4o/run/result.json')
import os
import json
from pulp import LpProblem, LpMinimize, LpVariable, lpSum, LpBinary, value

# Problem definition
problem = LpProblem("Graph_Coloring", LpMinimize)

# Data
vertices = [1, 2, 3, 4, 5]
edges = [(1, 2), (1, 3), (2, 3), (3, 4), (4, 5), (2, 5)]
max_colors = len(vertices)

# Variables
x = {(i, c): LpVariable(f"x_{i}_{c}", cat=LpBinary) for i in vertices for c in range(max_colors)}
y = {c: LpVariable(f"y_{c}", cat=LpBinary) for c in range(max_colors)}

# Objective: Minimize the number of colors used
problem += lpSum(y[c] for c in range(max_colors))

# Constraints
# Each vertex must have exactly one color
for i in vertices:
    problem += lpSum(x[i, c] for c in range(max_colors)) == 1

# Adjacent vertices cannot share the same color
for (i, j) in edges:
    for c in range(max_colors):
        problem += x[i, c] + x[j, c] <= 1

# If a vertex is assigned a color, that color must be marked as used
for i in vertices:
    for c in range(max_colors):
        problem += x[i, c] <= y[c]

# Solve the problem
problem.solve()

# Extract results
result = {
    "objective": value(problem.objective),
    "solution": {i: next(c for c in range(max_colors) if x[i, c].varValue == 1) for i in vertices},
    "feasible": problem.status == 1
}

# Write results to JSON
result_path = os.getenv("RESULT_PATH", "result.json")
with open(result_path, "w") as f:
    json.dump(result, f)