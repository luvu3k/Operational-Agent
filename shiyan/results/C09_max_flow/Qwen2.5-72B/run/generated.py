import os as _os
_os.environ.setdefault('RESULT_PATH', '/Applications/yhy/Operational_Agent/shiyan/results/C09_max_flow/Qwen2.5-72B/run/result.json')
import os
import pulp

# 定义环境变量
RESULT_PATH = os.getenv('RESULT_PATH', 'result.json')

# 创建问题
problem = pulp.LpProblem("MaxFlowProblem", pulp.LpMaximize)

# 定义变量
f_sa = pulp.LpVariable('f_sa', lowBound=0, cat='Continuous')
f_sb = pulp.LpVariable('f_sb', lowBound=0, cat='Continuous')
f_ab = pulp.LpVariable('f_ab', lowBound=0, cat='Continuous')
f_at = pulp.LpVariable('f_at', lowBound=0, cat='Continuous')
f_bt = pulp.LpVariable('f_bt', lowBound=0, cat='Continuous')

# 目标函数
problem += f_at + f_bt, "Maximize Flow from s to t"

# 约束条件
problem += f_sa + f_sb == f_at + f_bt, "Flow Conservation at s and t"
problem += f_sa <= 10, "Capacity of s to a"
problem += f_sb <= 5, "Capacity of s to b"
problem += f_ab <= 15, "Capacity of a to b"
problem += f_at <= 10, "Capacity of a to t"
problem += f_bt <= 10, "Capacity of b to t"

# 求解
problem.solve()

# 检查解的状态
feasible = pulp.LpStatus[problem.status] == "Optimal"

# 获取解
solution = {
    'f_sa': f_sa.varValue,
    'f_sb': f_sb.varValue,
    'f_ab': f_ab.varValue,
    'f_at': f_at.varValue,
    'f_bt': f_bt.varValue,
    'max_flow': f_at.varValue + f_bt.varValue,
    'feasible': feasible
}

# 写入结果文件
with open(RESULT_PATH, 'w') as f:
    f.write(str(solution))