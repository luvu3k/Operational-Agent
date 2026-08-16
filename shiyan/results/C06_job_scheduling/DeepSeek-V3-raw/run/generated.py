import os as _os
_os.environ.setdefault('RESULT_PATH', '/Applications/yhy/Operational_Agent/shiyan/results/C06_job_scheduling/DeepSeek-V3-raw/run/result.json')
import pulp
import json
import os

# 问题数据
jobs = [1, 2, 3, 4]
processing_time = {1:3, 2:1, 3:2, 4:4}
due_date = {1:4, 2:2, 3:6, 4:8}
M = sum(processing_time.values())  # 大M值

# 创建模型
model = pulp.LpProblem("Single_Machine_Scheduling", pulp.LpMinimize)

# 决策变量
x = pulp.LpVariable.dicts("precede", [(i,j) for i in jobs for j in jobs if i != j], cat='Binary')
C = pulp.LpVariable.dicts("completion_time", jobs, lowBound=0)

# 目标函数：总延误
model += pulp.lpSum([pulp.lpSum([C[i] - due_date[i] for i in jobs if C[i].value() > due_date[i]])])

# 约束条件
for i in jobs:
    for j in jobs:
        if i != j:
            model += C[i] >= C[j] + processing_time[i] - M*(1 - x[(i,j)])
    
for i in jobs:
    for j in jobs:
        if i < j:
            model += x[(i,j)] + x[(j,i)] == 1

for i in jobs:
    model += C[i] >= processing_time[i]

# 求解
model.solve()

# 提取结果
solution = [i for i in jobs]
solution.sort(key=lambda i: C[i].value())

result = {
    "objective": pulp.value(model.objective),
    "solution": solution,
    "feasible": model.status == pulp.LpStatusOptimal
}

# 写入结果文件
with open(os.getenv('RESULT_PATH', 'result.json'), 'w') as f:
    json.dump(result, f)