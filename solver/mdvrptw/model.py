"""
作用：
- MDVRPTW-P 的共享几何与目标评估逻辑，是精确解与启发式解的“唯一真相来源”。
- 通用化实例结构：depots / launch_points / params，可承载论文算例或用户自定义算例。

目标口径（与 experiments/mdvrptw 验证一致，可选加权系数与 main.pdf 式(21) 对齐）：
- 目标 = w1 · 总航行时间 + w2 · 优先级违反惩罚（默认 w1=w2=1.0；论文算例取 w1=0.8, w2=0.2）。
- 总航行时间 = 所有补给舰航行总距离 / v1（闭合路线，补给舰服务完毕返回保障中心）。
- 优先级惩罚 = L · Σ_{同路径相邻起飞点 i->j} max(0, τ_j − τ_i)。
- 时间窗为硬约束：到达起飞点时刻 ≤ latest；每节点服务时长 service。
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Tuple


def euclidean(a: Dict[str, Any], b: Dict[str, Any]) -> float:
    """两节点欧氏距离。"""
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
    """评估一个解，返回目标值、总航行时间、优先级惩罚、时间窗违反量、可行性与到达时刻。"""
    nodes, _, launch_ids = build_nodes(instance)
    dist = distance_matrix(nodes)
    params = instance["params"]
    v1 = float(params["v1"])
    service = float(params["service_time"])
    penalty_l = float(params["priority_penalty_L"])
    w1 = float(params.get("w1", 1.0))   # 总航行时间权重（论文算例取 0.8）
    w2 = float(params.get("w2", 1.0))   # 优先级惩罚权重（论文算例取 0.2）

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
        clock = 0.0
        for idx, launch_id in enumerate(sequence):
            leg = dist[(current, launch_id)]
            total_distance += leg
            clock += leg / v1
            arrival_times[launch_id] = clock
            visited.append(launch_id)
            latest = float(nodes[launch_id]["latest"])
            if clock > latest + 1e-6:
                tw_violation += clock - latest
            if idx > 0:
                prev_id = sequence[idx - 1]
                delta = nodes[launch_id]["priority"] - nodes[prev_id]["priority"]
                if delta > 0:
                    priority_penalty += penalty_l * delta
            clock += service
            current = launch_id
        total_distance += dist[(current, depot_id)]

    travel_time = total_distance / v1
    served_ok = sorted(visited) == launch_ids and len(visited) == len(set(visited))
    feasible = served_ok and tw_violation <= 1e-6
    objective = w1 * travel_time + w2 * priority_penalty

    return {
        "objective": objective,
        "travel_time": travel_time,
        "total_distance": total_distance,
        "priority_penalty": priority_penalty,
        "weighted_travel": w1 * travel_time,
        "weighted_penalty": w2 * priority_penalty,
        "w1": w1,
        "w2": w2,
        "tw_violation": tw_violation,
        "feasible": feasible,
        "served_all": served_ok,
        "num_routes": len([r for r in routes if r["sequence"]]),
        "arrival_times": arrival_times,
    }
