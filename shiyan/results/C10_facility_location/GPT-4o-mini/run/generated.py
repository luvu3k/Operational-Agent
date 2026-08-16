import os as _os
_os.environ.setdefault('RESULT_PATH', '/Applications/yhy/Operational_Agent/shiyan/results/C10_facility_location/GPT-4o-mini/run/result.json')
import json
import os
from pulp import LpProblem, LpMinimize, LpVariable, lpSum, LpStatus, LpBinary, value

# 定义数据
facility_costs = [4, 3, 5]
service_costs = [[2, 3, 1, 4], [5, 4, 2, 1], [3, 2, 4, 2]]
num_facilities = len(facility_costs)
num_customers = len(service_costs[0])

# 创建问题
problem = LpProblem("Facility_Location_Problem", LpMinimize)

# 定义变量
x = LpVariable.dicts("Open", range(num_facilities), cat=LpBinary)
y = LpVariable.dicts("Serve", (range(num_facilities), range(num_customers)), cat=LpBinary)

# 目标函数
problem += lpSum(facility_costs[i] * x[i] for i in range(num_facilities)) + \
           lpSum(service_costs[i][j] * y[i][j] for i in range(num_facilities) for j in range(num_customers))

# 约束条件
# 每个客户必须由一个设施服务
for j in range(num_customers):
    problem += lpSum(y[i][j] for i in range(num_facilities)) == 1

# 客户只能由开设的设施服务
for i in range(num_facilities):
    for j in range(num_customers):
        problem += y[i][j] <= x[i]

# 求解问题
problem.solve()

# 结果
result = {
    "objective": value(problem.objective),
    "solution": {f"Facility_{i}": int(x[i].varValue) for i in range(num_facilities)},
    "feasible": LpStatus[problem.status] == 'Optimal'
}

# 将结果写入 JSON 文件
result_path = os.getenv("RESULT_PATH", "result.json")
with open(result_path, 'w') as f:
    json.dump(result, f)