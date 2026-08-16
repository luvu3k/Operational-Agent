import os as _os
_os.environ.setdefault('RESULT_PATH', '/Applications/yhy/Operational_Agent/shiyan/results/C10_facility_location/DeepSeek-V3-raw/run/result.json')
import pulp
import os
import json

# Problem data
facilities = [1, 2, 3]
customers = [1, 2, 3, 4]
fixed_costs = {1: 4, 2: 3, 3: 5}
service_costs = {
    1: {1: 2, 2: 3, 3: 1, 4: 4},
    2: {1: 5, 2: 4, 3: 2, 4: 1},
    3: {1: 3, 2: 2, 3: 4, 4: 2}
}

# Create the problem
prob = pulp.LpProblem("Facility_Location", pulp.LpMinimize)

# Decision variables
y = pulp.LpVariable.dicts("Open", facilities, cat='Binary')
x = pulp.LpVariable.dicts("Assign", 
                         [(i,j) for i in facilities for j in customers],
                         cat='Binary')

# Objective function
prob += pulp.lpSum(fixed_costs[i]*y[i] for i in facilities) + \
        pulp.lpSum(service_costs[i][j]*x[(i,j)] for i in facilities for j in customers)

# Constraints
for j in customers:
    prob += pulp.lpSum(x[(i,j)] for i in facilities) == 1

for i in facilities:
    for j in customers:
        prob += x[(i,j)] <= y[i]

# Solve
prob.solve()

# Prepare results
solution = {
    "objective": pulp.value(prob.objective),
    "solution": {
        "opened_facilities": [i for i in facilities if y[i].value() == 1],
        "assignments": {
            j: next(i for i in facilities if x[(i,j)].value() == 1)
            for j in customers
        }
    },
    "feasible": prob.status == pulp.LpStatusOptimal
}

# Write to JSON
result_path = os.getenv('RESULT_PATH', 'result.json')
with open(result_path, 'w') as f:
    json.dump(solution, f)

print(f"Results saved to {result_path}")