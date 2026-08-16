import os as _os
_os.environ.setdefault('RESULT_PATH', '/Applications/yhy/Operational_Agent/shiyan/results/C08_graph_coloring/GPT-4o-mini/run/result.json')
import json
from pulp import LpProblem, LpVariable, LpMinimize, lpSum, LpBinary, LpStatusOptimal, LpStatus

# 定义图的顶点和边
vertices = [1, 2, 3, 4, 5]
edges = [(1, 2), (1, 3), (2, 3), (3, 4), (4, 5), (2, 5)]

# 创建线性规划问题
problem = LpProblem("Graph_Coloring", LpMinimize)

# 定义颜色数的变量
k = LpVariable("k", lowBound=1, cat='Integer')

# 定义着色变量
x = LpVariable.dicts("x", (vertices, range(1, 6)), cat=LpBinary)

# 目标函数：最小化颜色数
problem += k

# 每个顶点必须被着色
for v in vertices:
    problem += lpSum(x[v][j] for j in range(1, 6)) == 1

# 相邻顶点不能有相同的颜色
for (i, j) in edges:
    for color in range(1, 6):
        problem += x[i][color] + x[j][color] <= 1

# 颜色数的约束
for v in vertices:
    for color in range(1, 6):
        problem += x[v][color] <= k

# 求解问题
problem.solve()

# 提取结果
result = {
    "objective": problem.objective.value(),
    "solution": {v: [j for j in range(1, 6) if x[v][j].value() == 1][0] for v in vertices},
    "feasible": LpStatus[problem.status] == 'Optimal'
}

# 将结果写入 JSON 文件
import os
result_path = os.getenv("RESULT_PATH", "result.json")
with open(result_path, 'w') as f:
    json.dump(result, f)