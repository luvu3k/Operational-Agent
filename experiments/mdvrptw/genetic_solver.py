"""
作用：
- 用遗传算法（GA）求解与 Gurobi 完全相同的 MDVRPTW-P 论文算例，作为“求解正确性”的交叉验证。
- 目标与可行性判定复用 `model.evaluate_solution`，保证与精确解口径一致。

编码与算子：
- 个体 = 起飞点访问序列的排列 + 每个起飞点的 depot 归属。解码时按 depot 分组，
  在每组内用“时间窗可行性驱动的分车”把序列切成多条补给舰路径（超时则新开一艘船）。
- 适应度 = -(目标 + 大惩罚·时间窗违反 + 大惩罚·未服务)，越大越好。
- 选择=锦标赛；交叉=次序交叉 OX（对序列）+ 均匀交叉（对归属）；变异=交换/重分配。
- 采用论文提到的“最近保障中心”先验做部分初始化，加速收敛（对应论文知识引导思想）。
"""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))

from instance import build_instance
from model import build_nodes, distance_matrix, evaluate_solution


def _nearest_depot(depot_ids, launch_id, dist) -> int:
    return min(depot_ids, key=lambda m: dist[(m, launch_id)])


def _decode(instance, nodes, depot_ids, dist, order: List[int], assign: Dict[int, int]) -> List[Dict[str, Any]]:
    """把（序列 + 归属）解码成按时间窗可行性分车的多条路径。"""
    params = instance["params"]
    v1 = float(params["v1"])
    service = float(params["service_time"])

    grouped: Dict[int, List[int]] = {m: [] for m in depot_ids}
    for launch_id in order:
        grouped[assign[launch_id]].append(launch_id)

    routes: List[Dict[str, Any]] = []
    for m in depot_ids:
        current_route: List[int] = []
        current = m
        clock = 0.0
        for launch_id in grouped[m]:
            arrive = clock + dist[(current, launch_id)] / v1
            latest = float(nodes[launch_id]["latest"])
            if current_route and arrive > latest + 1e-6:
                # 当前船无法及时到达，收尾并新开一艘船。
                routes.append({"depot": m, "sequence": current_route})
                current_route = [launch_id]
                current = launch_id
                clock = dist[(m, launch_id)] / v1 + service
            else:
                current_route.append(launch_id)
                current = launch_id
                clock = arrive + service
        if current_route:
            routes.append({"depot": m, "sequence": current_route})
    return routes


def _penalized_cost(ev: Dict[str, Any]) -> float:
    """统一的带罚成本：目标 + 时间窗违反大罚 + 未服务大罚。best 跟踪与局部搜索都用它，口径一致。"""
    return ev["objective"] + 1000.0 * ev["tw_violation"] + (0.0 if ev["served_all"] else 5000.0)


def _fitness(instance, nodes, depot_ids, dist, order, assign) -> Tuple[float, Dict[str, Any]]:
    routes = _decode(instance, nodes, depot_ids, dist, order, assign)
    ev = evaluate_solution(instance, routes)
    return -_penalized_cost(ev), {"routes": routes, "evaluation": ev}


def _genome_from_routes(routes: List[Dict[str, Any]], launch_ids: List[int]) -> Tuple[List[int], Dict[int, int]]:
    """把 routes 反解回 (order, assign) 基因，使局部搜索的改进能被 GA 继承。"""
    order: List[int] = []
    assign: Dict[int, int] = {}
    for route in routes:
        for launch_id in route["sequence"]:
            order.append(launch_id)
            assign[launch_id] = route["depot"]
    # 保险：补齐任何遗漏的起飞点。
    for launch_id in launch_ids:
        if launch_id not in assign:
            order.append(launch_id)
            assign[launch_id] = 0
    return order, assign


def _local_search(instance, launch_ids, routes) -> Dict[str, Any]:
    """
    记忆式局部搜索：对给定 routes 反复施加改进算子，直到无法再降本。
    算子：intra-route 2-opt、跨路径 relocate、路径切分(split，增车降惩罚)、空路径清理。
    直接在 routes 表示上工作并按带罚成本比较，避免与 genome 解码不一致。
    """
    routes = [{"depot": r["depot"], "sequence": list(r["sequence"])} for r in routes if r["sequence"]]

    def cost(rs: List[Dict[str, Any]]) -> float:
        return _penalized_cost(evaluate_solution(instance, rs))

    best_cost = cost(routes)
    improved = True
    while improved:
        improved = False

        # 1) intra-route 2-opt：翻转同一路径的一段。
        for ri in range(len(routes)):
            seq = routes[ri]["sequence"]
            done = False
            for a in range(len(seq) - 1):
                for b in range(a + 1, len(seq)):
                    new_seq = seq[:a] + seq[a:b + 1][::-1] + seq[b + 1:]
                    trial = [dict(r) for r in routes]
                    trial[ri] = {"depot": routes[ri]["depot"], "sequence": new_seq}
                    if cost(trial) < best_cost - 1e-9:
                        routes, best_cost, improved, done = trial, cost(trial), True, True
                        break
                if done:
                    break
            if done:
                break
        if improved:
            continue

        # 2) 跨路径 relocate：把一个起飞点移动到另一条路径的某位置。
        done = False
        for ri in range(len(routes)):
            for node in list(routes[ri]["sequence"]):
                for rj in range(len(routes)):
                    if ri == rj:
                        continue
                    for pos in range(len(routes[rj]["sequence"]) + 1):
                        trial = [{"depot": r["depot"], "sequence": list(r["sequence"])} for r in routes]
                        trial[ri]["sequence"].remove(node)
                        trial[rj]["sequence"].insert(pos, node)
                        trial = [r for r in trial if r["sequence"]]
                        if cost(trial) < best_cost - 1e-9:
                            routes, best_cost, improved, done = trial, cost(trial), True, True
                            break
                    if done:
                        break
                if done:
                    break
            if done:
                break
        if improved:
            continue

        # 3) split：在切点把一条路径拆成两条同 depot 路径（用更多补给舰换更低时间窗/优先级惩罚）。
        done = False
        for ri in range(len(routes)):
            seq = routes[ri]["sequence"]
            if len(seq) < 2:
                continue
            for cut in range(1, len(seq)):
                trial = [{"depot": r["depot"], "sequence": list(r["sequence"])} for r in routes]
                depot = routes[ri]["depot"]
                trial[ri] = {"depot": depot, "sequence": seq[:cut]}
                trial.insert(ri + 1, {"depot": depot, "sequence": seq[cut:]})
                if cost(trial) < best_cost - 1e-9:
                    routes, best_cost, improved, done = trial, cost(trial), True, True
                    break
            if done:
                break

    ev = evaluate_solution(instance, routes)
    return {"routes": routes, "evaluation": ev, "genome": _genome_from_routes(routes, launch_ids)}


def _ox(parent1: List[int], parent2: List[int], rng: random.Random) -> List[int]:
    """次序交叉 OX。"""
    size = len(parent1)
    a, b = sorted(rng.sample(range(size), 2))
    child = [None] * size
    child[a:b + 1] = parent1[a:b + 1]
    fill = [g for g in parent2 if g not in child]
    pos = 0
    for i in range(size):
        if child[i] is None:
            child[i] = fill[pos]
            pos += 1
    return child


def solve_genetic(
    instance: Dict[str, Any],
    *,
    population_size: int = 60,
    generations: int = 120,
    seed: int = 42,
    patience: int = 25,
    verbose: bool = False,
) -> Dict[str, Any]:
    """GA 求解 MDVRPTW-P，返回与 Gurobi 同口径的统一结构。"""
    rng = random.Random(seed)
    nodes, depot_ids, launch_ids = build_nodes(instance)
    dist = distance_matrix(nodes)
    nearest = {j: _nearest_depot(depot_ids, j, dist) for j in launch_ids}

    def random_individual(knowledge: bool) -> Tuple[List[int], Dict[int, int]]:
        order = launch_ids[:]
        rng.shuffle(order)
        if knowledge:
            assign = {j: nearest[j] for j in launch_ids}
        else:
            assign = {j: rng.choice(depot_ids) for j in launch_ids}
        return order, assign

    # 初始化：一半用最近保障中心先验，一半随机。
    population: List[Tuple[List[int], Dict[int, int]]] = [
        random_individual(knowledge=(i < population_size // 2)) for i in range(population_size)
    ]

    best_cost = float("inf")
    best_payload: Dict[str, Any] = {}
    best_genome: Tuple[List[int], Dict[int, int]] = (launch_ids[:], {j: nearest[j] for j in launch_ids})
    stagnation = 0
    no_improve = 0

    def consider(payload: Dict[str, Any], genome: Tuple[List[int], Dict[int, int]]) -> bool:
        """用统一带罚成本更新全局最优。"""
        nonlocal best_cost, best_payload, best_genome
        c = _penalized_cost(payload["evaluation"])
        if c < best_cost - 1e-9:
            best_cost, best_payload, best_genome = c, payload, genome
            return True
        return False

    for gen in range(generations):
        scored = []
        for order, assign in population:
            fit, payload = _fitness(instance, nodes, depot_ids, dist, order, assign)
            scored.append((fit, order, assign, payload))
            consider(payload, (order, assign))
        scored.sort(key=lambda t: t[0], reverse=True)

        # 记忆式局部搜索：对头部精英做深度改进，并把改进基因写回种群。
        refined_pop: List[Tuple[List[int], Dict[int, int]]] = []
        improved_this_gen = False
        for _fit, _order, _assign, payload in scored[:3]:
            ls = _local_search(instance, launch_ids, payload["routes"])
            refined_pop.append(ls["genome"])
            if consider({"routes": ls["routes"], "evaluation": ls["evaluation"]}, ls["genome"]):
                stagnation = -1
                improved_this_gen = True

        stagnation += 1
        no_improve = 0 if improved_this_gen else no_improve + 1
        # 精英保留（含局部搜索改进后的个体）。
        next_pop: List[Tuple[List[int], Dict[int, int]]] = refined_pop + [(scored[0][1], scored[0][2])]

        def tournament() -> Tuple[List[int], Dict[int, int]]:
            contenders = rng.sample(scored, min(5, len(scored)))
            winner = max(contenders, key=lambda t: t[0])
            return winner[1], winner[2]

        # 停滞时注入随机移民，跳出早熟收敛。
        if stagnation >= 30:
            for _ in range(population_size // 4):
                next_pop.append(random_individual(knowledge=rng.random() < 0.5))
            stagnation = 0

        while len(next_pop) < population_size:
            (o1, a1), (o2, a2) = tournament(), tournament()
            child_order = _ox(o1, o2, rng)
            child_assign = {j: (a1[j] if rng.random() < 0.5 else a2[j]) for j in launch_ids}
            # 变异：序列交换。
            if rng.random() < 0.3:
                i, k = rng.sample(range(len(child_order)), 2)
                child_order[i], child_order[k] = child_order[k], child_order[i]
            # 变异：重新分配某起飞点归属（偏向最近 depot）。
            if rng.random() < 0.3:
                j = rng.choice(launch_ids)
                child_assign[j] = nearest[j] if rng.random() < 0.5 else rng.choice(depot_ids)
            next_pop.append((child_order, child_assign))

        population = next_pop
        if verbose and gen % 20 == 0:
            ev = best_payload["evaluation"]
            print(f"gen {gen}: best_obj={ev['objective']:.4f} feasible={ev['feasible']} routes={ev['num_routes']}")

        # 早停：连续 patience 代无改进则提前结束（含一次移民尝试后仍无改进）。
        if no_improve >= patience:
            if verbose:
                print(f"早停于第 {gen} 代（连续 {no_improve} 代无改进）。")
            break

    # 收尾：对全局最优再做一次局部搜索，确保交付解已被充分改进。
    _fit, payload = _fitness(instance, nodes, depot_ids, dist, best_genome[0], best_genome[1])
    final = _local_search(instance, launch_ids, best_payload.get("routes", payload["routes"]))
    consider({"routes": final["routes"], "evaluation": final["evaluation"]}, final["genome"])

    ev = best_payload["evaluation"]
    routes = [r for r in best_payload["routes"] if r["sequence"]]
    return {
        "status": "success" if ev["feasible"] else "error",
        "status_text": "FEASIBLE" if ev["feasible"] else "INFEASIBLE",
        "method": "genetic_algorithm",
        "objective": round(ev["objective"], 4),
        "travel_time": round(ev["travel_time"], 4),
        "priority_penalty": round(ev["priority_penalty"], 4),
        "feasible": ev["feasible"],
        "num_routes": len(routes),
        "routes": routes,
        "arrival_times": {str(k): round(v, 3) for k, v in ev["arrival_times"].items()},
    }


if __name__ == "__main__":
    print("=== genetic_solver.py 本地测试 ===")
    inst = build_instance()
    result = solve_genetic(inst, population_size=60, generations=120, seed=42, verbose=True)
    print(f"status={result['status']} ({result['status_text']})")
    print(f"objective={result['objective']}  travel_time={result['travel_time']}  penalty={result['priority_penalty']}")
    print(f"num_routes={result['num_routes']}")
    for route in result["routes"]:
        print(f"  depot {route['depot']}: {route['sequence']}")
    Path("genetic_result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print("已写入 genetic_result.json")
