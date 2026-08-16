import os as _os
_os.environ.setdefault('RESULT_PATH', '/Applications/yhy/Operational_Agent/shiyan/results/C10_facility_location/Qwen2.5-72B/run/result.json')
import os
import json
from pulp import LpProblem, LpMinimize, LpVariable, lpSum, value

# 定义问题
prob = LpProblem("Facility_Location_Problem", LpMinimize)

# 定义设施和客户的集合
facilities = [1, 2, 3]
customers = [1, 2, 3, 4]

# 定义开设成本和服务成本
opening_costs = {1: 4, 2: 3, 3: 5}
service_costs = {
    1: {1: 2, 2: 3, 3: 1, 4: 4},
    2: {1: 5, 2: 4, 3: 2, 4: 1},
    3: {1: 3, 2: 2, 3: 4, 4: 2}
}

# 定义决策变量
y = LpVariable.dicts("Facility", facilities, cat="Binary")
x = LpVariable.dicts("Service", [(i, j) for i in facilities for j in customers], cat="Binary")

# 定义目标函数
prob += lpSum([service_costs[i][j] * x[(i, j)] for i in facilities for j in customers]) + lpSum([opening_costs[i] * y[i] for i in facilities])

# 定义约束条件
for j in customers:
    prob += lpSum([x[(i, j)] for i in facilities]) == 1

for i in facilities:
    for j in customers:
        prob += x[(i, j)] <= y[i]

# 求解
prob.solve()

# 获取结果
solution = {
    "objective": value(prob.objective),
    "facilities_opened": {i: int(y[i].varValue) for i in facilities},
    "service_assignment": {j: [i for i in facilities if x[(i, j)].varValue == 1][0] for j in customers}
}

# 写入结果文件
result_path = os.environ.get("RESULT_PATH", "result.json")
with open(result_path, "w") as f:
    json.dump(solution, f, indent=4)

print("Solution written to", result_path)