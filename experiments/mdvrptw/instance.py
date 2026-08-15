"""
作用：
- 从论文《基于知识引导的多智能体DRL求解远海岛礁应急物资补给规划》第 5 节的真实地理算例
  （表 4 保障中心、表 5 无人机起飞点）中提取的标准 MDVRPTW-P 实例数据。
- 作为 Gurobi 精确求解与遗传算法求解共同使用的唯一数据源，保证两种方法求解同一问题。

说明（论文未显式给出、本文为自洽建模所作的显式假设）：
- v1（补给舰航速）= 40 km/h；节点服务时长 f = 0.5 h；每个保障中心可用补给舰上限 = 8。
- 时间单位为小时，坐标单位为公里，距离为欧氏距离（论文式 3）。
- 时间窗最早 e_i = 0（应急启动时刻），最晚 l_i 取表 5 的“最晚服务时间”。
"""

from __future__ import annotations

from typing import Any, Dict

# 论文表 4：3 个保障中心（仓库），坐标 (km)，优先级 0，最晚服务时间 10000。
DEPOTS = [
    {"id": 0, "name": "保障中心0", "x": 0.00, "y": 0.00},
    {"id": 1, "name": "保障中心1", "x": -160.93, "y": 109.30},
    {"id": 2, "name": "保障中心2", "x": -289.79, "y": -44.58},
]

# 论文表 5：22 个无人机起飞点（补给舰需访问的客户节点）。
# 字段：id, x, y, priority(τ 起飞点优先级), latest(l_i 最晚服务时间/h)。
LAUNCH_POINTS = [
    {"id": 3, "x": 35.60, "y": 167.90, "priority": 31.22, "latest": 40},
    {"id": 4, "x": -305.38, "y": -16.68, "priority": 28.27, "latest": 30},
    {"id": 5, "x": 50.66, "y": -92.46, "priority": 35.34, "latest": 67},
    {"id": 6, "x": -132.35, "y": 24.65, "priority": 21.78, "latest": 92},
    {"id": 7, "x": -273.59, "y": -110.50, "priority": 32.28, "latest": 73},
    {"id": 8, "x": -312.68, "y": 108.04, "priority": 26.31, "latest": 100},
    {"id": 9, "x": -134.52, "y": 139.87, "priority": 34.63, "latest": 225},
    {"id": 10, "x": -158.49, "y": -247.22, "priority": 31.66, "latest": 80},
    {"id": 11, "x": -97.35, "y": 20.50, "priority": 36.19, "latest": 87},
    {"id": 12, "x": -25.87, "y": -66.54, "priority": 24.68, "latest": 56},
    {"id": 13, "x": -386.72, "y": -225.14, "priority": 25.21, "latest": 158},
    {"id": 14, "x": -19.16, "y": -199.65, "priority": 32.41, "latest": 202},
    {"id": 15, "x": 77.41, "y": -193.93, "priority": 22.22, "latest": 144},
    {"id": 16, "x": -394.28, "y": 140.33, "priority": 36.12, "latest": 48},
    {"id": 17, "x": 87.77, "y": 14.03, "priority": 23.81, "latest": 95},
    {"id": 18, "x": -161.08, "y": -16.64, "priority": 33.69, "latest": 47},
    {"id": 19, "x": -116.97, "y": -143.61, "priority": 42.77, "latest": 42},
    {"id": 20, "x": -234.43, "y": 158.10, "priority": 22.89, "latest": 135},
    {"id": 21, "x": -410.02, "y": 17.85, "priority": 30.13, "latest": 124},
    {"id": 22, "x": -389.01, "y": -115.92, "priority": 39.24, "latest": 170},
    {"id": 23, "x": -289.89, "y": -209.51, "priority": 19.99, "latest": 84},
    {"id": 24, "x": -1.76, "y": 78.06, "priority": 3.47, "latest": 26},
]

# 自洽建模参数（论文未给出的显式假设）。
DEFAULT_PARAMS: Dict[str, Any] = {
    "v1": 40.0,                 # 补给舰航速 km/h
    "service_time": 0.5,        # 单节点服务时长 h
    "max_vehicles_per_depot": 8,
    "earliest": 0.0,            # e_i
    "priority_penalty_L": 1.0,  # 优先级违反惩罚系数 L（式 2）
}


def build_instance() -> Dict[str, Any]:
    """返回完整实例：depots / launch_points / params。"""
    return {
        "name": "paper_mdvrptw_3depot_22launch",
        "depots": [dict(d) for d in DEPOTS],
        "launch_points": [dict(p) for p in LAUNCH_POINTS],
        "params": dict(DEFAULT_PARAMS),
        "source": "SETP-paper-draft/main.tex 表4/表5（第5节真实地理算例）",
    }


if __name__ == "__main__":
    import json

    instance = build_instance()
    print("=== instance.py 本地测试 ===")
    print(f"保障中心数：{len(instance['depots'])}")
    print(f"无人机起飞点数：{len(instance['launch_points'])}")
    print(json.dumps(instance["params"], ensure_ascii=False, indent=2))
