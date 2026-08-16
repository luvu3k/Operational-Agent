import os as _os
_os.environ.setdefault('RESULT_PATH', '/Applications/yhy/Operational_Agent/shiyan/results/C06_job_scheduling/Qwen2.5-72B/run/result.json')
import os
import json
from pulp import LpProblem, LpMinimize, LpVariable, lpSum, LpBinary

# 定义问题
prob = LpProblem("Minimize_Total_Delay", LpMinimize)

# 工件数量
n = 4

# 加工时间和交货期
processing_times = [3, 1, 2, 4]
due_dates = [4, 2, 6, 8]

# 决策变量
x = LpVariable.dicts("x", ((i, j) for i in range(n) for j in range(n)), cat=LpBinary)
C = LpVariable.dicts("C", range(n), lowBound=0, cat='Continuous')
T = LpVariable.dicts("T", range(n), lowBound=0, cat='Continuous')

# 目标函数
prob += lpSum(T[i] for i in range(n))

# 约束条件
for i in range(n):
    prob += lpSum(x[j][i] * processing_times[j] for j in range(n)) + processing_times[i] == C[i]
    prob += T[i] >= C[i] - due_dates[i]
    prob += T[i] >= 0
    prob += lpSum(x[i][j] for j in range(n) if j != i) == 1
    prob += lpSum(x[j][i] for j in range(n) if j != i) == 1

# 求解
prob.solve()

# 提取结果
solution = [i for i in range(n) if x[0][i].varValue == 1]
for i in range(1, n):
    for j in range(n):
        if x[solution[-1]][j].varValue == 1:
            solution.append(j)
            break

# 计算完工时间和延误时间
completion_times = [0] * n
total_delay = 0
for i in solution:
    completion_times[i] = sum(processing_times[j] for j in solution[:solution.index(i) + 1])
    total_delay += max(completion_times[i] - due_dates[i], 0)

# 输出结果
result = {
    "solution": solution,
    "completion_times": completion_times,
    "total_delay": total_delay,
    "feasible": prob.status == 1
}

# 写入结果文件
result_path = os.getenv("RESULT_PATH", "result.json")
with open(result_path, "w") as f:
    json.dump(result, f, indent=4)