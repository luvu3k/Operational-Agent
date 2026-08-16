import os as _os
_os.environ.setdefault('RESULT_PATH', '/Applications/yhy/Operational_Agent/shiyan/results/C10_facility_location/Moonshot-v1/run/result.json')
import pulp
import json
import os

# Define the problem
prob = pulp.LpProblem("Facility_Location", pulp.LpMinimize)

# Define the variables
x = pulp.LpVariable.dicts("x", (range(3), range(4)), cat='Binary')
y = pulp.LpVariable.dicts("y", range(3), cat='Binary')

# Define the costs
f = [4, 3, 5]  # Facility opening costs
c = [[2, 3, 1, 4], [5, 4, 2, 1], [3, 2, 4, 2]]  # Facility serving customer costs

# Objective function
prob += pulp.lpSum([f[i] * y[i] for i in range(3)]) + pulp.lpSum([c[i][j] * x[i][j] for i in range(3) for j in range(4)])

# Constraints
for j in range(4):
    prob += pulp.lpSum([x[i][j] for i in range(3)]) == 1

for i in range(3):
    for j in range(4):
        prob += x[i][j] <= y[i]

# Solve the problem
prob.solve()

# Write the result to a JSON file
result = {
    "objective": pulp.value(prob.objective),
    "solution": {"y": y, "x": x},
    "feasible": pulp.LpStatus[prob.status] == "Optimal"
}

with open(os.environ['RESULT_PATH'], 'w') as f:
    json.dump(result, f)