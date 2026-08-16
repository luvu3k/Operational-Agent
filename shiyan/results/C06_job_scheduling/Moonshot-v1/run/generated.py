import os as _os
_os.environ.setdefault('RESULT_PATH', '/Applications/yhy/Operational_Agent/shiyan/results/C06_job_scheduling/Moonshot-v1/run/result.json')
import pulp
import json
import os

# Define the problem
problem = pulp.LpProblem("Job_Scheduling", pulp.LpMinimize)

# Define the variables
jobs = ['A', 'B', 'C', 'D']
processing_times = {'A': 3, 'B': 1, 'C': 2, 'D': 4}
due_dates = {'A': 4, 'B': 2, 'C': 6, 'D': 8}
completion_times = pulp.LpVariable.dicts("Completion_Time", jobs, lowBound=0)
before_vars = pulp.LpVariable.dicts("Before", ((i, j) for i in jobs for j in jobs if i < j), cat='Binary')

# Define the objective function
problem += pulp.lpSum([completion_times[i] - due_dates[i] for i in jobs if completion_times[i] - due_dates[i] > 0])

# Define the constraints
for i in jobs:
    for j in jobs:
        if i != j:
            problem += completion_times[i] <= completion_times[j] + processing_times[j] - 1000 * (1 - before_vars[(i, j)])

for i in jobs:
    for j in jobs:
        if i != j:
            problem += before_vars[(i, j)] + before_vars[(j, i)] == 1

# Solve the problem
problem.solve()

# Write the result to a file
result = {
    "objective": pulp.value(problem.objective),
    "solution": {job: pulp.value(completion_times[job]) for job in jobs},
    "feasible": pulp.LpStatus[problem.status] == "Optimal"
}

with open(os.environ['RESULT_PATH'], 'w') as f:
    json.dump(result, f)