import os as _os
_os.environ.setdefault('RESULT_PATH', '/Applications/yhy/Operational_Agent/shiyan/results/C08_graph_coloring/Moonshot-v1/run/result.json')
import pulp
import json
import os

# Define the problem
prob = pulp.LpProblem("Graph_Coloring", pulp.LpMinimize)

# Define the variables
colors = [pulp.LpVariable(f"x_{i}", 1, 5, cat='Binary') for i in range(1, 6)]

# Define the objective function
prob += max(colors)

# Define the constraints
prob += (colors[0] != colors[1])
prob += (colors[0] != colors[2])
prob += (colors[1] != colors[2])
prob += (colors[2] != colors[3])
prob += (colors[3] != colors[4])
prob += (colors[1] != colors[4])

# Solve the problem
prob.solve()

# Create the result dictionary
result = {
    "objective": pulp.value(prob.objective),
    "solution": {f"x_{i+1}": pulp.value(colors[i]) for i in range(5)},
    "feasible": pulp.LpStatus[prob.status] == "Optimal"
}

# Write the result to a JSON file
with open(os.environ['RESULT_PATH'], 'w') as f:
    json.dump(result, f)