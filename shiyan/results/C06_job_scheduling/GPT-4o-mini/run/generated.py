import os as _os
_os.environ.setdefault('RESULT_PATH', '/Applications/yhy/Operational_Agent/shiyan/results/C06_job_scheduling/GPT-4o-mini/run/result.json')
import itertools
import json
import os

# 工件加工时间和交货期
processing_times = [3, 1, 2, 4]
due_dates = [4, 2, 6, 8]

# 计算总延误
def calculate_total_delay(order):
    completion_times = []
    total_delay = 0
    current_time = 0
    
    for i in order:
        current_time += processing_times[i]
        completion_times.append(current_time)
        delay = max(0, current_time - due_dates[i])
        total_delay += delay
    
    return total_delay, completion_times

# 所有可能的工件顺序
orders = list(itertools.permutations(range(4)))
min_delay = float('inf')
best_order = None
best_completion_times = None

# 遍历所有工件顺序，寻找最小总延误
for order in orders:
    total_delay, completion_times = calculate_total_delay(order)
    if total_delay < min_delay:
        min_delay = total_delay
        best_order = order
        best_completion_times = completion_times

# 结果写入 JSON 文件
result = {
    "objective": min_delay,
    "solution": list(best_order),
    "feasible": True
}

result_path = os.getenv("RESULT_PATH", "result.json")
with open(result_path, 'w') as f:
    json.dump(result, f)