import os as _os
_os.environ.setdefault('RESULT_PATH', '/Applications/yhy/Operational_Agent/shiyan/results/C01_knapsack/DeepSeek-V3-raw/run/result.json')
import pulp
import json
import os

# 问题数据
weights = [2, 3, 4, 5, 9]
values = [3, 4, 5, 8, 10]
capacity = 20
n = len(weights)

# 创建问题实例
prob = pulp.LpProblem("Knapsack_Problem", pulp.LpMaximize)

# 创建决策变量
x = [pulp.LpVariable(f"x_{i}", cat="Binary") for i in range(n)]

# 目标函数
prob += pulp.lpSum([values[i] * x[i] for i in range(n)])

# 约束条件
prob += pulp.lpSum([weights[i] * x[i] for i in range(n)]) <= capacity

# 求解
prob.solve()

# 准备结果
solution = [int(pulp.value(x[i])) for i in range(n)]
selected_items = [i+1 for i in range(n) if solution[i]]
result = {
    "objective": int(pulp.value(prob.objective)),
    "solution": solution,
    "selected_items": selected_items,
    "feasible": prob.status == pulp.LpStatusOptimal
}

# 写入结果文件
result_path = os.getenv("RESULT_PATH", "result.json")
with open(result_path, "w") as f:
    json.dump(result, f)

print(f"Results saved to {result_path}")