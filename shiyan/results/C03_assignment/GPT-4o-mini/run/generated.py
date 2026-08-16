import os as _os
_os.environ.setdefault('RESULT_PATH', '/Applications/yhy/Operational_Agent/shiyan/results/C03_assignment/GPT-4o-mini/run/result.json')
import json
from pulp import LpProblem, LpMinimize, LpVariable, lpSum, LpStatus, LpBinary, value
import os

# 成本矩阵
cost_matrix = [[9, 2, 7], [6, 4, 3], [5, 8, 1]]
num_workers = len(cost_matrix)
num_tasks = len(cost_matrix[0])

# 创建线性规划问题
problem = LpProblem("Assignment_Problem", LpMinimize)

# 创建决策变量
x = LpVariable.dicts("x", (range(num_workers), range(num_tasks)), cat=LpBinary)

# 目标函数
problem += lpSum(cost_matrix[i][j] * x[i][j] for i in range(num_workers) for j in range(num_tasks)), "Total_Cost"

# 每个工人只能分配给一个任务
for i in range(num_workers):
    problem += lpSum(x[i][j] for j in range(num_tasks)) == 1, f"Worker_{i}_assignment"

# 每个任务只能分配给一个工人
for j in range(num_tasks):
    problem += lpSum(x[i][j] for i in range(num_workers)) == 1, f"Task_{j}_assignment"

# 求解问题
problem.solve()

# 获取结果
solution = [[value(x[i][j]) for j in range(num_tasks)] for i in range(num_workers)]
objective = value(problem.objective)
feasible = (problem.status == 1)

# 将结果写入 JSON 文件
result = {
    "objective": objective,
    "solution": solution,
    "feasible": feasible
}

result_path = os.getenv("RESULT_PATH", "result.json")
with open(result_path, 'w') as f:
    json.dump(result, f)