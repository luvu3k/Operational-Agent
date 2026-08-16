import os as _os
_os.environ.setdefault('RESULT_PATH', '/Applications/yhy/Operational_Agent/shiyan/results/C09_max_flow/GPT-4o-mini/run/result.json')
import json
from pulp import LpProblem, LpMaximize, LpVariable, lpSum, LpStatus

# 创建最大流问题
model = LpProblem("MaxFlow", LpMaximize)

# 定义变量
x_sa = LpVariable("x_sa", lowBound=0)  # s -> a
x_sb = LpVariable("x_sb", lowBound=0)  # s -> b
x_ab = LpVariable("x_ab", lowBound=0)  # a -> b
x_at = LpVariable("x_at", lowBound=0)  # a -> t
x_bt = LpVariable("x_bt", lowBound=0)  # b -> t

# 目标函数
model += x_at + x_bt, "Objective"

# 约束条件
model += x_sa + x_sb <= 15, "FlowOutOfSource"
model += x_sa + x_ab == x_at, "FlowIntoA"
model += x_sb + x_ab == x_bt, "FlowIntoB"
model += x_at <= 10, "CapacityAtTFromA"
model += x_bt <= 10, "CapacityAtTFromB"
model += x_sa <= 10, "CapacityFromSToA"
model += x_sb <= 5, "CapacityFromSToB"
model += x_ab <= 15, "CapacityFromAToB"

# 求解模型
model.solve()

# 结果
result = {
    "objective": model.objective.value(),
    "solution": {
        "x_sa": x_sa.varValue,
        "x_sb": x_sb.varValue,
        "x_ab": x_ab.varValue,
        "x_at": x_at.varValue,
        "x_bt": x_bt.varValue,
    },
    "feasible": LpStatus[model.status] == 'Optimal'
}

# 将结果写入 JSON 文件
import os
RESULT_PATH = os.getenv("RESULT_PATH", "result.json")
with open(RESULT_PATH, 'w') as f:
    json.dump(result, f)