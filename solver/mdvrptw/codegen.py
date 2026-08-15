"""
作用：
- 生成“可独立运行的完整求解脚本”：把实例数据 + 所选求解方法（gurobi / genetic）打包成单个 .py 文件。
- 用户保存该文件后可直接 `python xxx.py` 复现求解并写出 result.json，满足“把完整生成代码交给用户”的需求。
"""

from __future__ import annotations

import json
from typing import Any, Dict


def build_standalone_script(instance: Dict[str, Any], method: str, result_path: str = "result.json") -> str:
    """生成内嵌实例与求解逻辑的独立脚本文本。"""
    instance_json = json.dumps(instance, ensure_ascii=False, indent=4)
    method = method if method in {"gurobi", "genetic"} else "genetic"

    header = f'''"""
自动生成：MDVRPTW-P（带时间窗与优先级约束的多仓库车辆路径问题）求解脚本。
求解方法：{method}
目标口径：最小化 总航行时间 + 优先级违反惩罚；时间窗为硬约束。

用法：
    python {{此文件}}
运行后会在同目录写出 {result_path}，包含目标值、各补给舰路径、到达时刻。
{"精确求解需要安装 gurobipy 并配置 license；启发式无需外部依赖。" if method == "gurobi" else "本脚本为纯 Python 遗传算法，无需任何外部依赖。"}
"""

from __future__ import annotations

import json
import math
import random
from pathlib import Path

INSTANCE = json.loads(r"""{instance_json}""")
RESULT_PATH = r"{result_path}"
'''

    shared = '''

def _build_nodes(instance):
    nodes, depot_ids, launch_ids = {}, [], []
    for d in instance["depots"]:
        nodes[d["id"]] = {**d, "priority": 0.0, "latest": float("inf"), "is_depot": True}
        depot_ids.append(d["id"])
    for p in instance["launch_points"]:
        nodes[p["id"]] = {**p, "is_depot": False}
        launch_ids.append(p["id"])
    return nodes, depot_ids, launch_ids


def _dist_matrix(nodes):
    dist = {}
    ids = list(nodes.keys())
    for i in ids:
        for j in ids:
            if i != j:
                dist[(i, j)] = math.hypot(nodes[i]["x"] - nodes[j]["x"], nodes[i]["y"] - nodes[j]["y"])
    return dist


def evaluate(instance, routes):
    nodes, _, launch_ids = _build_nodes(instance)
    dist = _dist_matrix(nodes)
    p = instance["params"]
    v1, service, L = float(p["v1"]), float(p["service_time"]), float(p["priority_penalty_L"])
    total_distance = priority_penalty = tw_violation = 0.0
    arrival, visited = {}, []
    for route in routes:
        seq = route["sequence"]
        if not seq:
            continue
        current, clock = route["depot"], 0.0
        for idx, lid in enumerate(seq):
            leg = dist[(current, lid)]
            total_distance += leg
            clock += leg / v1
            arrival[lid] = clock
            visited.append(lid)
            if clock > float(nodes[lid]["latest"]) + 1e-6:
                tw_violation += clock - float(nodes[lid]["latest"])
            if idx > 0:
                delta = nodes[lid]["priority"] - nodes[seq[idx - 1]]["priority"]
                if delta > 0:
                    priority_penalty += L * delta
            clock += service
            current = lid
        total_distance += dist[(current, route["depot"])]
    travel_time = total_distance / v1
    served_ok = sorted(visited) == launch_ids and len(visited) == len(set(visited))
    return {
        "objective": travel_time + priority_penalty,
        "travel_time": travel_time,
        "priority_penalty": priority_penalty,
        "tw_violation": tw_violation,
        "feasible": served_ok and tw_violation <= 1e-6,
        "served_all": served_ok,
        "num_routes": len([r for r in routes if r["sequence"]]),
        "arrival_times": {str(k): round(v, 3) for k, v in arrival.items()},
    }
'''

    gurobi_body = '''

def solve():
    import gurobipy as gp
    from gurobipy import GRB
    nodes, depot_ids, launch_ids = _build_nodes(INSTANCE)
    dist = _dist_matrix(nodes)
    p = INSTANCE["params"]
    v1, service, max_veh = float(p["v1"]), float(p["service_time"]), int(p["max_vehicles_per_depot"])
    L = float(p["priority_penalty_L"])
    tr = lambda i, j: dist[(i, j)] / v1
    dc = [(m, j) for m in depot_ids for j in launch_ids]
    cc = [(i, j) for i in launch_ids for j in launch_ids if i != j]
    cd = [(i, m) for i in launch_ids for m in depot_ids]
    arcs = dc + cc + cd
    mdl = gp.Model("MDVRPTW_P")
    mdl.Params.OutputFlag = 0
    x = mdl.addVars(arcs, vtype=GRB.BINARY, name="x")
    s = mdl.addVars(launch_ids, lb=0.0, name="s")
    di = {m: k for k, m in enumerate(depot_ids)}
    lab = mdl.addVars(launch_ids, lb=0.0, ub=len(depot_ids) - 1, name="lab")
    max_latest = max(float(nodes[i]["latest"]) for i in launch_ids)
    M = max_latest + max(tr(i, j) for (i, j) in arcs) + service + 10.0
    Ml = len(depot_ids) + 1.0
    for j in launch_ids:
        mdl.addConstr(gp.quicksum(x[a] for a in arcs if a[1] == j) == 1)
        mdl.addConstr(gp.quicksum(x[a] for a in arcs if a[0] == j) == 1)
    for m in depot_ids:
        mdl.addConstr(gp.quicksum(x[(m, j)] for j in launch_ids) == gp.quicksum(x[(i, m)] for i in launch_ids))
        mdl.addConstr(gp.quicksum(x[(m, j)] for j in launch_ids) <= max_veh)
    for (m, j) in dc:
        mdl.addConstr(lab[j] >= di[m] - Ml * (1 - x[(m, j)]))
        mdl.addConstr(lab[j] <= di[m] + Ml * (1 - x[(m, j)]))
    for (i, j) in cc:
        mdl.addConstr(lab[j] >= lab[i] - Ml * (1 - x[(i, j)]))
        mdl.addConstr(lab[j] <= lab[i] + Ml * (1 - x[(i, j)]))
    for (i, m) in cd:
        mdl.addConstr(lab[i] >= di[m] - Ml * (1 - x[(i, m)]))
        mdl.addConstr(lab[i] <= di[m] + Ml * (1 - x[(i, m)]))
    for (m, j) in dc:
        mdl.addConstr(s[j] >= tr(m, j) - M * (1 - x[(m, j)]))
    for (i, j) in cc:
        mdl.addConstr(s[j] >= s[i] + service + tr(i, j) - M * (1 - x[(i, j)]))
    for j in launch_ids:
        mdl.addConstr(s[j] <= float(nodes[j]["latest"]))
    mdl.setObjective(
        gp.quicksum(tr(i, j) * x[(i, j)] for (i, j) in arcs)
        + gp.quicksum(L * max(0.0, nodes[j]["priority"] - nodes[i]["priority"]) * x[(i, j)] for (i, j) in cc),
        GRB.MINIMIZE,
    )
    mdl.optimize()
    used = {a for a in arcs if x[a].X > 0.5}
    routes = []
    for m in depot_ids:
        for first in [j for j in launch_ids if (m, j) in used]:
            seq, cur = [first], first
            while True:
                nxt = next((j for j in launch_ids if (cur, j) in used and j not in seq), None)
                if nxt is None:
                    break
                seq.append(nxt); cur = nxt
            routes.append({"depot": m, "sequence": seq})
    return routes
'''

    genetic_body = '''

def _decode(instance, depot_ids, dist, order, assign):
    p = instance["params"]; v1, service = float(p["v1"]), float(p["service_time"])
    nodes, _, _ = _build_nodes(instance)
    grouped = {m: [] for m in depot_ids}
    for lid in order:
        grouped[assign[lid]].append(lid)
    routes = []
    for m in depot_ids:
        cur_route, cur, clock = [], m, 0.0
        for lid in grouped[m]:
            arrive = clock + dist[(cur, lid)] / v1
            if cur_route and arrive > float(nodes[lid]["latest"]) + 1e-6:
                routes.append({"depot": m, "sequence": cur_route})
                cur_route, cur, clock = [lid], lid, dist[(m, lid)] / v1 + service
            else:
                cur_route.append(lid); cur = lid; clock = arrive + service
        if cur_route:
            routes.append({"depot": m, "sequence": cur_route})
    return routes


def _cost(ev):
    return ev["objective"] + 1000.0 * ev["tw_violation"] + (0.0 if ev["served_all"] else 5000.0)


def _local_search(instance, routes):
    routes = [{"depot": r["depot"], "sequence": list(r["sequence"])} for r in routes if r["sequence"]]
    c = lambda rs: _cost(evaluate(instance, rs))
    best = c(routes); improved = True
    while improved:
        improved = False
        for ri in range(len(routes)):
            seq = routes[ri]["sequence"]; done = False
            for a in range(len(seq) - 1):
                for b in range(a + 1, len(seq)):
                    t = [dict(r) for r in routes]
                    t[ri] = {"depot": routes[ri]["depot"], "sequence": seq[:a] + seq[a:b+1][::-1] + seq[b+1:]}
                    if c(t) < best - 1e-9:
                        routes, best, improved, done = t, c(t), True, True; break
                if done: break
            if done: break
        if improved: continue
        done = False
        for ri in range(len(routes)):
            for node in list(routes[ri]["sequence"]):
                for rj in range(len(routes)):
                    if ri == rj: continue
                    for pos in range(len(routes[rj]["sequence"]) + 1):
                        t = [{"depot": r["depot"], "sequence": list(r["sequence"])} for r in routes]
                        t[ri]["sequence"].remove(node); t[rj]["sequence"].insert(pos, node)
                        t = [r for r in t if r["sequence"]]
                        if c(t) < best - 1e-9:
                            routes, best, improved, done = t, c(t), True, True; break
                    if done: break
                if done: break
            if done: break
        if improved: continue
        done = False
        for ri in range(len(routes)):
            seq = routes[ri]["sequence"]
            if len(seq) < 2: continue
            for cut in range(1, len(seq)):
                t = [{"depot": r["depot"], "sequence": list(r["sequence"])} for r in routes]
                dep = routes[ri]["depot"]
                t[ri] = {"depot": dep, "sequence": seq[:cut]}; t.insert(ri + 1, {"depot": dep, "sequence": seq[cut:]})
                if c(t) < best - 1e-9:
                    routes, best, improved, done = t, c(t), True, True; break
            if done: break
    return routes


def _ox(p1, p2, rng):
    n = len(p1); a, b = sorted(rng.sample(range(n), 2))
    child = [None] * n; child[a:b+1] = p1[a:b+1]
    fill = [g for g in p2 if g not in child]; k = 0
    for i in range(n):
        if child[i] is None:
            child[i] = fill[k]; k += 1
    return child


def solve():
    rng = random.Random(42)
    nodes, depot_ids, launch_ids = _build_nodes(INSTANCE)
    dist = _dist_matrix(nodes)
    nearest = {j: min(depot_ids, key=lambda m: dist[(m, j)]) for j in launch_ids}
    def rand_ind(k):
        o = launch_ids[:]; rng.shuffle(o)
        a = {j: nearest[j] for j in launch_ids} if k else {j: rng.choice(depot_ids) for j in launch_ids}
        return o, a
    pop = [rand_ind(i < 30) for i in range(60)]
    best_cost, best_routes, no_imp = float("inf"), [], 0
    for gen in range(120):
        scored = []
        for o, a in pop:
            r = _decode(INSTANCE, depot_ids, dist, o, a)
            scored.append((_cost(evaluate(INSTANCE, r)), o, a, r))
        scored.sort(key=lambda t: t[0])
        improved = False
        refined = []
        for sc, o, a, r in scored[:3]:
            ls = _local_search(INSTANCE, r)
            lc = _cost(evaluate(INSTANCE, ls))
            refined.append((o, a))
            if lc < best_cost - 1e-9:
                best_cost, best_routes, improved = lc, ls, True
        no_imp = 0 if improved else no_imp + 1
        nxt = refined + [(scored[0][1], scored[0][2])]
        def tour():
            cs = rng.sample(scored, min(5, len(scored)))
            w = min(cs, key=lambda t: t[0]); return w[1], w[2]
        while len(nxt) < 60:
            (o1, a1), (o2, a2) = tour(), tour()
            co = _ox(o1, o2, rng)
            ca = {j: (a1[j] if rng.random() < 0.5 else a2[j]) for j in launch_ids}
            if rng.random() < 0.3:
                i, k = rng.sample(range(len(co)), 2); co[i], co[k] = co[k], co[i]
            if rng.random() < 0.3:
                j = rng.choice(launch_ids); ca[j] = nearest[j] if rng.random() < 0.5 else rng.choice(depot_ids)
            nxt.append((co, ca))
        pop = nxt
        if no_imp >= 25:
            break
    return _local_search(INSTANCE, best_routes)
'''

    footer = '''

def main():
    routes = solve()
    ev = evaluate(INSTANCE, routes)
    result = {
        "method": METHOD,
        "objective": round(ev["objective"], 4),
        "travel_time": round(ev["travel_time"], 4),
        "priority_penalty": round(ev["priority_penalty"], 4),
        "feasible": ev["feasible"],
        "num_routes": ev["num_routes"],
        "routes": routes,
        "arrival_times": ev["arrival_times"],
    }
    Path(RESULT_PATH).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print("objective =", result["objective"], "| feasible =", result["feasible"], "| routes =", result["num_routes"])
    for r in routes:
        print("  depot", r["depot"], "->", r["sequence"])


if __name__ == "__main__":
    main()
'''

    method_line = f'\nMETHOD = "{method}"\n'
    body = gurobi_body if method == "gurobi" else genetic_body
    return header + method_line + shared + body + footer


if __name__ == "__main__":
    from solver.mdvrptw.presets import paper_instance

    print("=== codegen.py 本地测试 ===")
    script = build_standalone_script(paper_instance(), "genetic")
    print(f"生成脚本长度: {len(script)} 字符")
