import os as _os
_os.environ.setdefault('RESULT_PATH', '/Applications/yhy/Operational_Agent/shiyan/results/C10_facility_location/GPT-4o/run/result.json')
import os
import json
from pulp import LpProblem, LpMinimize, LpVariable, lpSum, LpBinary, value

# Parameters
facility_costs = [4, 3, 5]
service_costs = [
    [2, 3, 1, 4],
    [5, 4, 2, 1],
    [3, 2, 4, 2]
]
num_facilities = len(facility_costs)
num_customers = len(service_costs[0])

# Problem definition
problem = LpProblem("Facility_Location", LpMinimize)

# Decision variables
x = [LpVariable(f"x_{i}", cat=LpBinary) for i in range(num_facilities)]
y = [[LpVariable(f"y_{i}_{j}", cat=LpBinary) for j in range(num_customers)] for i in range(num_facilities)]

# Objective function
problem += lpSum(facility_costs[i] * x[i] for i in range(num_facilities)) + \
           lpSum(service_costs[i][j] * y[i][j] for i in range(num_facilities) for j in range(num_customers))

# Constraints
# Each customer is served by exactly one facility
for j in range(num_customers):
    problem += lpSum(y[i][j] for i in range(num_facilities)) == 1

# A customer can only be served by an open facility
for i in range(num_facilities):
    for j in range(num_customers):
        problem += y[i][j] <= x[i]

# Solve the problem
problem.solve()

# Extract results
result = {
    "objective": value(problem.objective),
    "solution": {
        "facilities_open": [int(x[i].varValue) for i in range(num_facilities)],
        "customer_assignment": [
            [int(y[i][j].varValue) for j in range(num_customers)] for i in range(num_facilities)
        ]
    },
    "feasible": problem.status == 1
}

# Write results to JSON
result_path = os.getenv("RESULT_PATH", "result.json")
with open(result_path, "w") as f:
    json.dump(result, f)