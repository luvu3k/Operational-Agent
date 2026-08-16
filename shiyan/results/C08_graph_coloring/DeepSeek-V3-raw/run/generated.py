import os as _os
_os.environ.setdefault('RESULT_PATH', '/Applications/yhy/Operational_Agent/shiyan/results/C08_graph_coloring/DeepSeek-V3-raw/run/result.json')
import pulp
import json
import os

# 问题数据
vertices = [1, 2, 3, 4, 5]
edges = [(1,2), (1,3), (2,3), (3,4), (4,5), (2,5)]
max_colors = len(vertices)  # 最多需要顶点数种颜色

# 创建模型
model = pulp.LpProblem("Graph_Coloring", pulp.LpMinimize)

# 变量：颜色使用指示器
color_used = pulp.LpVariable.dicts("color_used", range(1, max_colors+1), cat='Binary')
# 变量：顶点颜色分配
vertex_color = pulp.LpVariable.dicts("vertex_color", 
                                    [(v, c) for v in vertices for c in range(1, max_colors+1)], 
                                    cat='Binary')

# 目标：最小化使用的最大颜色编号
model += pulp.lpSum(color_used[c] for c in range(1, max_colors+1))

# 约束1：每个顶点必须使用一种颜色
for v in vertices:
    model += pulp.lpSum(vertex_color[(v, c)] for c in range(1, max_colors+1)) == 1

# 约束2：相邻顶点颜色不同
for u, v in edges:
    for c in range(1, max_colors+1):
        model += vertex_color[(u, c)] + vertex_color[(v, c)] <= 1

# 约束3：颜色使用顺序约束
for c in range(2, max_colors+1):
    model += pulp.lpSum(vertex_color[(v, c)] for v in vertices) <= \
             pulp.lpSum(vertex_color[(v, c-1)] for v in vertices)

# 求解
model.solve()

# 提取结果
solution = {}
for v in vertices:
    for c in range(1, max_colors+1):
        if pulp.value(vertex_color[(v, c)]) == 1:
            solution[v] = c
            break

result = {
    "objective": int(pulp.value(model.objective)),
    "solution": solution,
    "feasible": model.status == pulp.LpStatusOptimal
}

# 写入结果文件
with open(os.getenv('RESULT_PATH', 'result.json'), 'w') as f:
    json.dump(result, f)