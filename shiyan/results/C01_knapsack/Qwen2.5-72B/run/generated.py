import os as _os
_os.environ.setdefault('RESULT_PATH', '/Applications/yhy/Operational_Agent/shiyan/results/C01_knapsack/Qwen2.5-72B/run/result.json')
import os
import json
from pulp import LpProblem, LpMaximize, LpVariable, lpSum

# 定义问题
prob = LpProblem("Knapsack_Problem", LpMaximize)

# 定义物品的重量和价值
weights = [2, 3, 4, 5, 9]
values = [3, 4, 5, 8, 10]
max_weight = 20

# 定义决策变量
x = [LpVariable(f'x{i}', cat='Binary') for i in range(1, 6)]

# 定义目标函数
prob += lpSum([values[i] * x[i] for i in range(5)])

# 定义约束条件
prob += lpSum([weights[i] * x[i] for i in range(5)]) <= max_weight

# 求解
prob.solve()

# 获取结果
solution = [x[i].varValue for i in range(5)]
total_value = sum(values[i] * solution[i] for i in range(5))
total_weight = sum(weights[i] * solution[i] for i in range(5))
feasible = prob.status == 1  # 1 表示问题有解

# 将结果写入 JSON 文件
result = {
    "solution": solution,
    "total_value": total_value,
    "total_weight": total_weight,
    "feasible": feasible
}

result_path = os.environ.get('RESULT_PATH', 'result.json')
with open(result_path, 'w') as f:
    json.dump(result, f, indent=4)