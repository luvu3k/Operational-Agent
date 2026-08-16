import os as _os
_os.environ.setdefault('RESULT_PATH', '/Applications/yhy/Operational_Agent/shiyan/results/C03_assignment/DeepSeek-V3-raw/run/result.json')
import pulp
import os
import json

# 问题数据
costs = [[9, 2, 7],
         [6, 4, 3],
         [5, 8, 1]]
workers = range(len(costs))
tasks = range(len(costs[0]))

# 创建问题实例
prob = pulp.LpProblem("Worker_Task_Assignment", pulp.LpMinimize)

# 创建决策变量
x = pulp.LpVariable.dicts("assign", 
                         ((i, j) for i in workers for j in tasks),
                         cat='Binary')

# 目标函数
prob += pulp.lpSum(x[i,j] * costs[i][j] for i in workers for j in tasks)

# 约束条件
for i in workers:
    prob += pulp.lpSum(x[i,j] for j in tasks) == 1

for j in tasks:
    prob += pulp.lpSum(x[i,j] for i in workers) == 1

# 求解
prob.solve()

# 收集结果
solution = [[0]*len(tasks) for _ in workers]
for i in workers:
    for j in tasks:
        if pulp.value(x[i,j]) == 1:
            solution[i][j] = 1

result = {
    "objective": pulp.value(prob.objective),
    "solution": solution,
    "feasible": prob.status == pulp.LpStatusOptimal
}

# 写入结果文件
with open(os.getenv('RESULT_PATH', 'result.json'), 'w') as f:
    json.dump(result, f)