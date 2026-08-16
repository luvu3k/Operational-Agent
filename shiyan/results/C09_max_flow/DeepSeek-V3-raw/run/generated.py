import os as _os
_os.environ.setdefault('RESULT_PATH', '/Applications/yhy/Operational_Agent/shiyan/results/C09_max_flow/DeepSeek-V3-raw/run/result.json')
import pulp
import json
import os

# 创建问题
prob = pulp.LpProblem("Max_Flow", pulp.LpMaximize)

# 定义边和容量
edges = {
    ('s', 'a'): 10,
    ('s', 'b'): 5,
    ('a', 'b'): 15,
    ('a', 't'): 10,
    ('b', 't'): 10
}

# 创建变量
flow_vars = pulp.LpVariable.dicts("Flow", edges.keys(), lowBound=0, upBound=None)

# 目标函数：最大化从s流出的流量
prob += flow_vars[('s','a')] + flow_vars[('s','b')], "Total_Flow"

# 容量约束
for edge, cap in edges.items():
    prob += flow_vars[edge] <= cap, f"Cap_{edge[0]}_{edge[1]}"

# 流量守恒约束
prob += flow_vars[('s','a')] == flow_vars[('a','b')] + flow_vars[('a','t')], "Node_a_conservation"
prob += flow_vars[('s','b')] + flow_vars[('a','b')] == flow_vars[('b','t')], "Node_b_conservation"

# 求解
prob.solve()

# 准备结果
result = {
    "objective": pulp.value(prob.objective),
    "solution": {f"{k[0]}->{k[1]}": v.varValue for k, v in flow_vars.items()},
    "feasible": prob.status == pulp.LpStatusOptimal
}

# 写入文件
with open(os.getenv('RESULT_PATH', 'result.json'), 'w') as f:
    json.dump(result, f)