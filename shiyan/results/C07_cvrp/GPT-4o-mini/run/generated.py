import os as _os
_os.environ.setdefault('RESULT_PATH', '/Applications/yhy/Operational_Agent/shiyan/results/C07_cvrp/GPT-4o-mini/run/result.json')
import json
import numpy as np
from pulp import LpProblem, LpMinimize, LpVariable, lpSum, LpStatus, LpStatusOptimal

# 客户坐标和需求
customers = {
    'C1': ((2, 3), 5),
    'C2': ((5, 4), 4),
    'C3': ((-3, 5), 3),
    'C4': ((-4, -2), 6)
}

# 配送中心坐标
depot = (0, 0)
capacity = 10

# 创建距离矩阵
distances = {c: np.sqrt((depot[0] - coords[0])**2 + (depot[1] - coords[1])**2) for c, (coords, _) in customers.items()}

# 创建问题
problem = LpProblem("Vehicle_Routing_Problem", LpMinimize)

# 变量
x = LpVariable.dicts("x", customers.keys(), lowBound=0, upBound=1, cat='Binary')

# 目标函数
problem += lpSum(distances[c] * x[c] for c in customers.keys()), "Total_Distance"

# 需求约束
for c, (coords, demand) in customers.items():
    problem += x[c] * demand <= capacity, f"Demand_{c}"

# 求解问题
problem.solve()

# 结果
result = {
    "objective": problem.objective.value(),
    "solution": {c: x[c].varValue for c in customers.keys()},
    "feasible": LpStatus[problem.status] == LpStatusOptimal
}

# 写入结果
import os
RESULT_PATH = os.getenv('RESULT_PATH', 'result.json')
with open(RESULT_PATH, 'w') as f:
    json.dump(result, f)