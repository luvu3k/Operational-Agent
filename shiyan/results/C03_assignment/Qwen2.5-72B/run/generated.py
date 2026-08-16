import os as _os
_os.environ.setdefault('RESULT_PATH', '/Applications/yhy/Operational_Agent/shiyan/results/C03_assignment/Qwen2.5-72B/run/result.json')
import os
import json
from pulp import LpProblem, LpMinimize, LpVariable, lpSum

# 成本矩阵
cost_matrix = [
    [9, 2, 7],
    [6, 4, 3],
    [5, 8, 1]
]

# 创建问题
prob = LpProblem("Assignment_Problem", LpMinimize)

# 创建决策变量
x = LpVariable.dicts("x", [(i, j) for i in range(3) for j in range(3)], cat='Binary')

# 目标函数
prob += lpSum(cost_matrix[i][j] * x[(i, j)] for i in range(3) for j in range(3))

# 约束条件
for i in range(3):
    prob += lpSum(x[(i, j)] for j in range(3)) == 1  # 每个工人恰好分配一项任务

for j in range(3):
    prob += lpSum(x[(i, j)] for i in range(3)) == 1  # 每项任务恰好由一个工人完成

# 求解
prob.solve()

# 获取结果
solution = {}
for i in range(3):
    for j in range(3):
        if x[(i, j)].value() == 1:
            solution[f"Worker {i+1}"] = f"Task {j+1}"

# 计算最小总成本
min_cost = sum(cost_matrix[i][j] * x[(i, j)].value() for i in range(3) for j in range(3))

# 写入结果文件
result_path = os.getenv("RESULT_PATH", "result.json")
with open(result_path, "w") as f:
    json.dump({"solution": solution, "min_cost": min_cost, "feasible": prob.status == 1}, f)

print("Solution written to", result_path)