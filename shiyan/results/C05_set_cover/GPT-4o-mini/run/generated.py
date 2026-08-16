import os as _os
_os.environ.setdefault('RESULT_PATH', '/Applications/yhy/Operational_Agent/shiyan/results/C05_set_cover/GPT-4o-mini/run/result.json')
import json
from pulp import LpProblem, LpVariable, LpMinimize, lpSum, LpStatus, LpBinary, value

# 定义问题
problem = LpProblem("SetCoveringProblem", LpMinimize)

# 定义变量
x1 = LpVariable('x1', cat=LpBinary)
x2 = LpVariable('x2', cat=LpBinary)
x3 = LpVariable('x3', cat=LpBinary)
x4 = LpVariable('x4', cat=LpBinary)

# 目标函数
problem += lpSum([x1, x2, x3, x4]), "MinimizeNumberOfSubsets"

# 约束条件
problem += x1 + x2 >= 1, "CoverElement1"
problem += x1 + x2 >= 1, "CoverElement2"
problem += x1 + x3 >= 1, "CoverElement3"
problem += x2 + x3 + x4 >= 1, "CoverElement4"
problem += x4 >= 1, "CoverElement5"

# 求解问题
problem.solve()

# 结果
result = {
    "objective": value(problem.objective),
    "solution": {
        "S1": int(x1.varValue),
        "S2": int(x2.varValue),
        "S3": int(x3.varValue),
        "S4": int(x4.varValue)
    },
    "feasible": LpStatus[problem.status] == 'Optimal'
}

# 将结果写入 JSON 文件
import os
RESULT_PATH = os.getenv('RESULT_PATH', 'result.json')
with open(RESULT_PATH, 'w') as f:
    json.dump(result, f)