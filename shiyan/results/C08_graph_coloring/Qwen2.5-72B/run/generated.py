import os as _os
_os.environ.setdefault('RESULT_PATH', '/Applications/yhy/Operational_Agent/shiyan/results/C08_graph_coloring/Qwen2.5-72B/run/result.json')
import os
import pulp

# 定义图的顶点和边
vertices = [1, 2, 3, 4, 5]
edges = [(1, 2), (1, 3), (2, 3), (3, 4), (4, 5), (2, 5)]

# 定义颜色集合
colors = range(1, 6)

# 创建一个线性规划问题
prob = pulp.LpProblem("GraphColoring", pulp.LpMinimize)

# 定义决策变量
x = pulp.LpVariable.dicts("x", [(i, c) for i in vertices for c in colors], cat='Binary')
y = pulp.LpVariable.dicts("y", colors, cat='Binary')

# 定义目标函数
prob += pulp.lpSum(y[c] for c in colors)

# 定义约束条件
# 每个顶点必须被着色为一种颜色
for i in vertices:
    prob += pulp.lpSum(x[(i, c)] for c in colors) == 1

# 相邻顶点不能着相同颜色
for (i, j) in edges:
    for c in colors:
        prob += x[(i, c)] + x[(j, c)] <= 1

# 如果顶点 i 被着色为颜色 c，则颜色 c 必须被使用
for i in vertices:
    for c in colors:
        prob += x[(i, c)] <= y[c]

# 求解
prob.solve()

# 提取结果
solution = {i: None for i in vertices}
used_colors = 0

for i in vertices:
    for c in colors:
        if pulp.value(x[(i, c)]) == 1:
            solution[i] = c
            used_colors = max(used_colors, c)

# 写入结果文件
result_path = os.getenv('RESULT_PATH', 'result.json')
with open(result_path, 'w') as f:
    f.write(f'{{"objective": {used_colors}, "solution": {solution}, "feasible": {pulp.LpStatus[prob.status] == "Optimal"}}}')

print(f"Objective: {used_colors}")
print(f"Solution: {solution}")
print(f"Feasible: {pulp.LpStatus[prob.status] == 'Optimal'}")