import os as _os
_os.environ.setdefault('RESULT_PATH', '/Applications/yhy/Operational_Agent/shiyan/results/C05_set_cover/Qwen2.5-72B/run/result.json')
import os
import json
from pulp import LpProblem, LpVariable, LpMinimize, lpSum

# 定义全集和子集
U = {1, 2, 3, 4, 5}
S = {
    'S1': {1, 2, 3},
    'S2': {2, 4},
    'S3': {3, 4},
    'S4': {4, 5}
}

# 创建线性规划问题
prob = LpProblem("Set_Covering_Problem", LpMinimize)

# 定义二进制变量
x = {i: LpVariable(f'x_{i}', cat='Binary') for i in S}

# 目标函数
prob += lpSum(x[i] for i in S)

# 约束条件
for j in U:
    prob += lpSum(x[i] for i in S if j in S[i]) >= 1

# 求解
prob.solve()

# 获取结果
solution = {i: int(x[i].varValue) for i in S}
feasible = prob.status == 1  # 1 表示最优解
objective = prob.objective.value()

# 将结果写入 JSON 文件
result_path = os.getenv('RESULT_PATH', 'result.json')
result = {
    'objective': objective,
    'solution': solution,
    'feasible': feasible
}

with open(result_path, 'w') as f:
    json.dump(result, f, indent=4)

print(f"Objective: {objective}")
print(f"Solution: {solution}")
print(f"Feasible: {feasible}")