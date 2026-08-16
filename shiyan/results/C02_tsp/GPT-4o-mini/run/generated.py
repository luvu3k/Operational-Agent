import os as _os
_os.environ.setdefault('RESULT_PATH', '/Applications/yhy/Operational_Agent/shiyan/results/C02_tsp/GPT-4o-mini/run/result.json')
import json
import itertools
import math
import os

# 计算欧氏距离
def euclidean_distance(p1, p2):
    return math.sqrt((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2)

# 城市坐标
cities = {
    'A': (0, 0),
    'B': (0, 4),
    'C': (4, 4),
    'D': (4, 0),
    'E': (2, 2)
}

# 计算所有城市之间的距离
distances = { (i, j): euclidean_distance(cities[i], cities[j]) for i, j in itertools.permutations(cities.keys(), 2) }

# 生成所有可能的巡回路线
city_names = list(cities.keys())
shortest_route = None
min_distance = float('inf')

# 计算每条路线的总距离
for perm in itertools.permutations(city_names[1:]):  # 不包括起点A
    route = ['A'] + list(perm) + ['A']
    total_distance = sum(distances[(route[i], route[i + 1])] for i in range(len(route) - 1))
    
    if total_distance < min_distance:
        min_distance = total_distance
        shortest_route = route

# 结果写入 JSON 文件
result = {
    "objective": min_distance,
    "solution": shortest_route,
    "feasible": True
}

result_path = os.getenv("RESULT_PATH", "result.json")
with open(result_path, 'w') as f:
    json.dump(result, f)