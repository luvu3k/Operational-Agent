import os as _os
_os.environ.setdefault('RESULT_PATH', '/Applications/yhy/Operational_Agent/shiyan/results/C04_bin_packing/GPT-4o-mini/run/result.json')
import json
import numpy as np
from pulp import LpProblem, LpMinimize, LpVariable, lpSum, LpBinary, LpStatus, value

# 物品体积
volumes = [4, 8, 1, 4, 2, 1]
capacity = 10
n = len(volumes)

# 创建模型
model = LpProblem("Bin_Packing", LpMinimize)

# 创建变量
k = LpVariable("k", lowBound=1, cat='Integer')  # 箱子数量
x = LpVariable.dicts("x", (range(n), range(100)), cat=LpBinary)  # 物品放入箱子的决策变量

# 目标函数：最小化箱子数量
model += k

# 每个物品必须放入一个箱子
for j in range(n):
    model += lpSum(x[j][i] for i in range(100)) == 1

# 每个箱子的体积限制
for i in range(100):
    model += lpSum(volumes[j] * x[j][i] for j in range(n)) <= capacity

# 最小化箱子数量的约束
for i in range(100):
    for j in range(n):
        model += x[j][i] <= k

# 求解模型
model.solve()

# 结果
result = {
    "objective": value(model.objective),
    "solution": {},
    "feasible": LpStatus[model.status] == 'Optimal'
}

# 提取装箱方案
for i in range(100):
    items_in_box = []
    for j in range(n):
        if value(x[j][i]) == 1:
            items_in_box.append(volumes[j])
    if items_in_box:
        result["solution"][f"Box {i+1}"] = items_in_box

# 写入结果到 JSON 文件
import os
RESULT_PATH = os.getenv("RESULT_PATH", "result.json")
with open(RESULT_PATH, 'w') as f:
    json.dump(result, f, indent=4)