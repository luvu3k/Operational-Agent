import os as _os
_os.environ.setdefault('RESULT_PATH', '/Applications/yhy/Operational_Agent/shiyan/results/C06_job_scheduling/GPT-4o/run/result.json')
import os
import json
from pulp import LpProblem, LpMinimize, LpVariable, lpSum, LpBinary, value

# Parameters
processing_times = [3, 1, 2, 4]
due_dates = [4, 2, 6, 8]
num_jobs = len(processing_times)

# Problem definition
prob = LpProblem("Minimize_Total_Delay", LpMinimize)

# Decision variables
x = [[LpVariable(f"x_{i}_{j}", cat=LpBinary) for j in range(num_jobs)] for i in range(num_jobs)]
C = [LpVariable(f"C_{i}", lowBound=0) for i in range(num_jobs)]
L = [LpVariable(f"L_{i}", lowBound=0) for i in range(num_jobs)]

# Objective function: Minimize total delay
prob += lpSum(L)

# Constraints
# Each job is assigned to exactly one position
for i in range(num_jobs):
    prob += lpSum(x[i][j] for j in range(num_jobs)) == 1

# Each position is assigned to exactly one job
for j in range(num_jobs):
    prob += lpSum(x[i][j] for i in range(num_jobs)) == 1

# Completion time constraints
for i in range(num_jobs):
    prob += C[i] == lpSum(processing_times[k] * x[k][j] for k in range(num_jobs) for j in range(i + 1))

# Lateness constraints
for i in range(num_jobs):
    prob += L[i] >= C[i] - due_dates[i]
    prob += L[i] >= 0

# Solve the problem
prob.solve()

# Extract results
solution = [j for i in range(num_jobs) for j in range(num_jobs) if x[i][j].varValue == 1]
completion_times = [value(C[i]) for i in range(num_jobs)]
lateness = [value(L[i]) for i in range(num_jobs)]
total_delay = sum(lateness)

# Output results
result = {
    "objective": total_delay,
    "solution": solution,
    "feasible": prob.status == 1,
    "completion_times": completion_times,
    "lateness": lateness
}

result_path = os.getenv("RESULT_PATH", "result.json")
with open(result_path, "w") as f:
    json.dump(result, f)