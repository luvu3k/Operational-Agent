import os as _os
_os.environ.setdefault('RESULT_PATH', '/Applications/yhy/Operational_Agent/shiyan/results/C05_set_cover/DeepSeek-V3-raw/run/result.json')
import pulp
import json
import os

# 定义问题
prob = pulp.LpProblem("SetCovering", pulp.LpMinimize)

# 子集定义
subsets = {
    'S1': {1, 2, 3},
    'S2': {2, 4},
    'S3': {3, 4},
    'S4': {4, 5}
}

# 全集
universe = {1, 2, 3, 4, 5}

# 创建决策变量
x = {s: pulp.LpVariable(s, cat='Binary') for s in subsets}

# 目标函数：最小化选择的子集数量
prob += pulp.lpSum(x.values())

# 添加约束：每个元素至少被一个子集覆盖
for element in universe:
    covering_sets = [x[s] for s in subsets if element in subsets[s]]
    prob += pulp.lpSum(covering_sets) >= 1

# 求解问题
prob.solve()

# 准备结果
solution = {s: int(x[s].value()) for s in subsets}
selected_sets = [s for s in subsets if solution[s] == 1]

result = {
    "objective": int(pulp.value(prob.objective)),
    "solution": solution,
    "selected_sets": selected_sets,
    "feasible": prob.status == pulp.LpStatusOptimal
}

# 写入结果文件
with open(os.getenv('RESULT_PATH', 'result.json'), 'w') as f:
    json.dump(result, f)

print(f"Result saved to {os.getenv('RESULT_PATH', 'result.json')}")