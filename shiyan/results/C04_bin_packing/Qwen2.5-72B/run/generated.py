import os as _os
_os.environ.setdefault('RESULT_PATH', '/Applications/yhy/Operational_Agent/shiyan/results/C04_bin_packing/Qwen2.5-72B/run/result.json')
import os
import json
from pulp import LpProblem, LpMinimize, LpVariable, lpSum, value

# 物品体积
item_volumes = [4, 8, 1, 4, 2, 1]
# 箱子容量
bin_capacity = 10
# 物品数量
num_items = len(item_volumes)
# 箱子数量（初始设为一个足够大的值）
num_bins = num_items

# 创建问题
prob = LpProblem("Bin_Packing_Problem", LpMinimize)

# 创建决策变量
x = LpVariable.dicts("x", ((i, j) for i in range(num_items) for j in range(num_bins)), cat='Binary')
y = LpVariable.dicts("y", range(num_bins), cat='Binary')

# 目标函数：最小化使用的箱子数量
prob += lpSum(y[j] for j in range(num_bins))

# 约束条件：每个物品必须被放入一个箱子中
for i in range(num_items):
    prob += lpSum(x[i][j] for j in range(num_bins)) == 1

# 约束条件：每个箱子内的物品体积之和不超过箱子的容量
for j in range(num_bins):
    prob += lpSum(item_volumes[i] * x[i][j] for i in range(num_items)) <= bin_capacity * y[j]

# 求解
prob.solve()

# 获取结果
objective_value = value(prob.objective)
solution = []
for j in range(num_bins):
    if y[j].varValue == 1:
        bin_items = [i for i in range(num_items) if x[i][j].varValue == 1]
        solution.append(bin_items)

# 写入结果文件
result_path = os.getenv('RESULT_PATH', 'result.json')
result = {
    'objective': objective_value,
    'solution': solution,
    'feasible': prob.status == 1
}
with open(result_path, 'w') as f:
    json.dump(result, f, indent=4)

print(f"Objective: {objective_value}")
print(f"Solution: {solution}")
print(f"Feasible: {prob.status == 1}")