"""
作用：
- 定义 MDVRPTW-P 的共享几何与目标评估逻辑，作为 Gurobi 精确求解与遗传算法求解的“唯一真相来源”。
- 只要两种方法都用本模块评估目标，就能保证它们在求解同一个问题（这是“求解正确性”验证的前提）。

自洽建模口径（论文式 1、式 2 的可复现简化，用户已确认不追求等于 268.8）：
- 目标 = 总运输时间 + 优先级违反惩罚。
- 总运输时间 = 所有补给舰航行总距离 / v1（论文式 3；本实例不含无人机末端 T2，因论文未给岛礁级坐标）。
- 优先级违反惩罚 = L · Σ_{同一路径内相邻起飞点 i->j} max(0, τ_j − τ_i)（式 2 的相邻弧线性化，
  即“紧接着高优先级节点排在低优先级节点之后”会被惩罚，depot 优先级视为 0 且不计 depot 弧）。
- 时间窗为硬约束：补给舰到达起飞点 i 的时刻 s_i ≤ latest_i；最早 e_i = 0；每节点服务时长 f。
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Tuple


def euclidean(a: Dict[str, Any], b: Dict[str, Any]) -> float:
    """两节点欧氏距离（论文式 3）。"""
    return math.hypot(a["x"] - b["x"], a["y"] - b["y"])


def build_nodes(instance: Dict[str, Any]) -> Tuple[Dict[int, Dict[str, Any]], List[int], List[int]]:
    """把实例整理成 id->node 字典，并返回 depot id 列表与 launch id 列表。"""
    nodes: Dict[int, Dict[str, Any]] = {}
    depot_ids: List[int] = []
    launch_ids: List[int] = []
    for depot in instance["depots"]:
        nodes[depot["id"]] = {**depot, "priority": 0.0, "latest": float("inf"), "is_depot": True}
        depot_ids.append(depot["id"])
    for point in instance["launch_points"]:
        nodes[point["id"]] = {**point, "is_depot": False}
        launch_ids.append(point["id"])
    return nodes, depot_ids, launch_ids


def distance_matrix(nodes: Dict[int, Dict[str, Any]]) -> Dict[Tuple[int, int], float]:
    """预计算全部节点对的距离。"""
    dist: Dict[Tuple[int, int], float] = {}
    ids = list(nodes.keys())
    for i in ids:
        for j in ids:
            if i != j:
                dist[(i, j)] = euclidean(nodes[i], nodes[j])
    return dist


def evaluate_solution(instance: Dict[str, Any], routes: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    评估一个解。routes 为若干条路径，每条为 {"depot": depot_id, "sequence": [launch_id, ...]}。
    返回目标值、总航行时间、优先级惩罚、时间窗违反量、是否可行以及每节点到达时刻。
    """
    nodes, _, launch_ids = build_nodes(instance)
    dist = distance_matrix(nodes)
    params = instance["params"]
    v1 = float(params["v1"])
    service = float(params["service_time"])
    penalty_l = float(params["priority_penalty_L"])

    total_distance = 0.0
    priority_penalty = 0.0
    tw_violation = 0.0
    arrival_times: Dict[int, float] = {}
    visited: List[int] = []

    for route in routes:
        depot_id = route["depot"]
        sequence = route["sequence"]
        if not sequence:
            continue
        current = depot_id
        clock = 0.0  # e_i = 0，任务启动时刻从 depot 出发
        for idx, launch_id in enumerate(sequence):
            leg = dist[(current, launch_id)]
            total_distance += leg
            clock += leg / v1
            arrival_times[launch_id] = clock
            visited.append(launch_id)
            # 时间窗硬约束：到达时刻不得晚于最晚服务时间
            latest = float(nodes[launch_id]["latest"])
            if clock > latest + 1e-6:
                tw_violation += clock - latest
            # 相邻起飞点优先级违反惩罚（式 2 相邻弧线性化）
            if idx > 0:
                prev_id = sequence[idx - 1]
                delta = nodes[launch_id]["priority"] - nodes[prev_id]["priority"]
                if delta > 0:
                    priority_penalty += penalty_l * delta
            clock += service
            current = launch_id
        # 返回 depot 的航程计入总距离（不产生时间窗/优先级约束）
        total_distance += dist[(current, depot_id)]

    travel_time = total_distance / v1
    # 完整性：所有起飞点被服务且恰好一次
    served_ok = sorted(visited) == launch_ids and len(visited) == len(set(visited))
    feasible = served_ok and tw_violation <= 1e-6
    objective = travel_time + priority_penalty

    return {
        "objective": objective,
        "travel_time": travel_time,
        "total_distance": total_distance,
        "priority_penalty": priority_penalty,
        "tw_violation": tw_violation,
        "feasible": feasible,
        "served_all": served_ok,
        "num_routes": len([r for r in routes if r["sequence"]]),
        "arrival_times": arrival_times,
    }


if __name__ == "__main__":
    from instance import build_instance

    inst = build_instance()
    # 一个演示解：把所有起飞点粗暴地塞进 3 条按 depot 划分的路径（可能不可行，仅测评估逻辑）。
    launches = [p["id"] for p in inst["launch_points"]]
    demo_routes = [
        {"depot": 0, "sequence": launches[0:8]},
        {"depot": 1, "sequence": launches[8:15]},
        {"depot": 2, "sequence": launches[15:22]},
    ]
    result = evaluate_solution(inst, demo_routes)
    print("=== model.py 本地测试 ===")
    for key in ["objective", "travel_time", "priority_penalty", "tw_violation", "feasible", "num_routes"]:
        print(f"{key}: {result[key]}")
