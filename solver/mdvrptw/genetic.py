"""
作用：
- MDVRPTW-P 的记忆式遗传算法（GA + 局部搜索）求解器（通用实例版）。
- 目标与可行性判定复用 `model.evaluate_solution`，与精确解口径一致。

算子：OX 次序交叉 + 归属均匀交叉 + 交换/重分配变异；局部搜索含 intra-route 2-opt、跨路径 relocate、
路径 split；停滞注入移民 + 早停。已在 experiments/mdvrptw 验证 gap≈4%。
"""

from __future__ import annotations

import random
from typing import Any, Dict, List, Tuple

from solver.mdvrptw.model import build_nodes, distance_matrix, evaluate_solution


def _nearest_depot(depot_ids, launch_id, dist) -> int:
    return min(depot_ids, key=lambda m: dist[(m, launch_id)])


def _decode(instance, depot_ids, dist, order: List[int], assign: Dict[int, int]) -> List[Dict[str, Any]]:
    """把（序列 + 归属）解码成按时间窗可行性分车的多条路径。"""
    params = instance["params"]
    v1 = float(params["v1"])
    service = float(params["service_time"])

    grouped: Dict[int, List[int]] = {m: [] for m in depot_ids}
    for launch_id in order:
        grouped[assign[launch_id]].append(launch_id)

    nodes, _, _ = build_nodes(instance)
    routes: List[Dict[str, Any]] = []
    for m in depot_ids:
        current_route: List[int] = []
        current = m
        clock = 0.0
        for launch_id in grouped[m]:
            arrive = clock + dist[(current, launch_id)] / v1
            latest = float(nodes[launch_id]["latest"])
            if current_route and arrive > latest + 1e-6:
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
    return ev["objective"] + 1000.0 * ev["tw_violation"] + (0.0 if ev["served_all"] else 5000.0)


def _fitness(instance, depot_ids, dist, order, assign) -> Tuple[float, Dict[str, Any]]:
    routes = _decode(instance, depot_ids, dist, order, assign)
    ev = evaluate_solution(instance, routes)
    return -_penalized_cost(ev), {"routes": routes, "evaluation": ev}


def _genome_from_routes(routes: List[Dict[str, Any]], launch_ids: List[int]) -> Tuple[List[int], Dict[int, int]]:
    order: List[int] = []
    assign: Dict[int, int] = {}
    for route in routes:
        for launch_id in route["sequence"]:
            order.append(launch_id)
            assign[launch_id] = route["depot"]
    for launch_id in launch_ids:
        if launch_id not in assign:
            order.append(launch_id)
            assign[launch_id] = 0
    return order, assign


def _local_search(instance, launch_ids, routes) -> Dict[str, Any]:
    """记忆式局部搜索：2-opt + relocate + split，直到无法降本。"""
    routes = [{"depot": r["depot"], "sequence": list(r["sequence"])} for r in routes if r["sequence"]]

    def cost(rs: List[Dict[str, Any]]) -> float:
        return _penalized_cost(evaluate_solution(instance, rs))

    best_cost = cost(routes)
    improved = True
    while improved:
        improved = False
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
    size = len(parent1)
    a, b = sorted(rng.sample(range(size), 2))
    child: List[Any] = [None] * size
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
    """GA 求解 MDVRPTW-P，返回与精确解同口径的统一结构。"""
    rng = random.Random(seed)
    nodes, depot_ids, launch_ids = build_nodes(instance)
    dist = distance_matrix(nodes)
    nearest = {j: _nearest_depot(depot_ids, j, dist) for j in launch_ids}

    def random_individual(knowledge: bool) -> Tuple[List[int], Dict[int, int]]:
        order = launch_ids[:]
        rng.shuffle(order)
        assign = {j: nearest[j] for j in launch_ids} if knowledge else {j: rng.choice(depot_ids) for j in launch_ids}
        return order, assign

    population = [random_individual(i < population_size // 2) for i in range(population_size)]

    best_cost = float("inf")
    best_payload: Dict[str, Any] = {}
    best_genome: Tuple[List[int], Dict[int, int]] = (launch_ids[:], {j: nearest[j] for j in launch_ids})
    stagnation = 0
    no_improve = 0

    def consider(payload: Dict[str, Any], genome) -> bool:
        nonlocal best_cost, best_payload, best_genome
        c = _penalized_cost(payload["evaluation"])
        if c < best_cost - 1e-9:
            best_cost, best_payload, best_genome = c, payload, genome
            return True
        return False

    for gen in range(generations):
        scored = []
        for order, assign in population:
            fit, payload = _fitness(instance, depot_ids, dist, order, assign)
            scored.append((fit, order, assign, payload))
            consider(payload, (order, assign))
        scored.sort(key=lambda t: t[0], reverse=True)

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
        next_pop = refined_pop + [(scored[0][1], scored[0][2])]

        def tournament():
            contenders = rng.sample(scored, min(5, len(scored)))
            winner = max(contenders, key=lambda t: t[0])
            return winner[1], winner[2]

        if stagnation >= 30:
            for _ in range(population_size // 4):
                next_pop.append(random_individual(rng.random() < 0.5))
            stagnation = 0

        while len(next_pop) < population_size:
            (o1, a1), (o2, a2) = tournament(), tournament()
            child_order = _ox(o1, o2, rng)
            child_assign = {j: (a1[j] if rng.random() < 0.5 else a2[j]) for j in launch_ids}
            if rng.random() < 0.3:
                i, k = rng.sample(range(len(child_order)), 2)
                child_order[i], child_order[k] = child_order[k], child_order[i]
            if rng.random() < 0.3:
                j = rng.choice(launch_ids)
                child_assign[j] = nearest[j] if rng.random() < 0.5 else rng.choice(depot_ids)
            next_pop.append((child_order, child_assign))

        population = next_pop
        if verbose and gen % 20 == 0:
            ev = best_payload["evaluation"]
            print(f"gen {gen}: best_obj={ev['objective']:.4f} feasible={ev['feasible']} routes={ev['num_routes']}")
        if no_improve >= patience:
            break

    _fit, payload = _fitness(instance, depot_ids, dist, best_genome[0], best_genome[1])
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
        "weighted_travel": round(ev["weighted_travel"], 4),
        "weighted_penalty": round(ev["weighted_penalty"], 4),
        "w1": ev["w1"],
        "w2": ev["w2"],
        "feasible": ev["feasible"],
        "num_routes": len(routes),
        "routes": routes,
        "arrival_times": {str(k): round(v, 3) for k, v in ev["arrival_times"].items()},
    }


if __name__ == "__main__":
    from solver.mdvrptw.presets import paper_instance

    print("=== genetic.py 本地测试 ===")
    result = solve_genetic(paper_instance(), verbose=True)
    print(f"status={result['status']} objective={result['objective']} routes={result['num_routes']}")
