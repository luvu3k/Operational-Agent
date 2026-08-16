import os as _os
_os.environ.setdefault('RESULT_PATH', '/Applications/yhy/Operational_Agent/shiyan/results/C01_knapsack/GPT-4o-mini/run/result.json')
import json
from pulp import LpProblem, LpMaximize, LpVariable, lpSum, LpStatus

# 创建问题
problem = LpProblem("Knapsack_Problem", LpMaximize)

# 定义物品的重量和价值
weights = [2, 3, 4, 5, 9]
values = [3, 4, 5, 8, 10]
n = len(weights)

# 定义决策变量
x = [LpVariable(f'x{i}', cat='Binary') for i in range(n)]

# 目标函数
problem += lpSum(values[i] * x[i] for i in range(n)), "Total_Value"

# 约束条件
problem += lpSum(weights[i] * x[i] for i in range(n)) <= 20, "Weight_Constraint"

# 求解问题
problem.solve()

# 获取结果
solution = [int(x[i].varValue) for i in range(n)]
objective = problem.objective.value()
feasible = LpStatus[problem.status] == 'Optimal'

# 将结果写入 JSON 文件
result = {
    "objective": objective,
    "solution": solution,
    "feasible": feasible
}

import os
RESULT_PATH = os.getenv('RESULT_PATH', 'result.json')
with open(RESULT_PATH, 'w') as f:
    json.dump(result, f)