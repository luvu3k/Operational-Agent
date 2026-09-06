"""
作用：
- MDVRPTW-P 的 Gurobi 精确 MILP 求解器（通用实例版）。
- 目标口径与 `model.evaluate_solution` 完全一致：最小化 总航行时间 + 优先级违反惩罚。

建模：紧凑 depot 标签formulation，适配 size-limited license。详见 experiments/mdvrptw/gurobi_solver.py 的说明。
"""

from __future__ import annotations

from typing import Any, Dict, List

from solver.mdvrptw.model import build_nodes, distance_matrix, evaluate_solution


def solve_exact(instance: Dict[str, Any], *, time_limit: int = 120, verbose: bool = False) -> Dict[str, Any]:
    """构建并求解 MDVRPTW-P 精确 MILP，返回统一结构的解。"""
    import gurobipy as gp
    from gurobipy import GRB

    nodes, depot_ids, launch_ids = build_nodes(instance)
    dist = distance_matrix(nodes)
    params = instance["params"]
    v1 = float(params["v1"])
    service = float(params["service_time"])
    max_veh = int(params["max_vehicles_per_depot"])
    penalty_l = float(params["priority_penalty_L"])
    w1 = float(params.get("w1", 1.0))   # 总航行时间权重（论文算例取 0.8）
    w2 = float(params.get("w2", 1.0))   # 优先级惩罚权重（论文算例取 0.2）

    def travel(i: int, j: int) -> float:
        return dist[(i, j)] / v1

    dc_arcs = [(m, j) for m in depot_ids for j in launch_ids]
    cc_arcs = [(i, j) for i in launch_ids for j in launch_ids if i != j]
    cd_arcs = [(i, m) for i in launch_ids for m in depot_ids]
    all_arcs = dc_arcs + cc_arcs + cd_arcs

    model = gp.Model("MDVRPTW_P")
    model.Params.OutputFlag = 1 if verbose else 0
    model.Params.TimeLimit = time_limit

    x = model.addVars(all_arcs, vtype=GRB.BINARY, name="x")
    s = model.addVars(launch_ids, lb=0.0, name="s")
    depot_index = {m: idx for idx, m in enumerate(depot_ids)}
    lab = model.addVars(launch_ids, lb=0.0, ub=len(depot_ids) - 1, name="lab")

    max_latest = max(float(nodes[i]["latest"]) for i in launch_ids)
    big_m = max_latest + max(travel(i, j) for (i, j) in all_arcs) + service + 10.0
    big_l = len(depot_ids) + 1.0

    for j in launch_ids:
        model.addConstr(gp.quicksum(x[a] for a in all_arcs if a[1] == j) == 1, name=f"in_{j}")
        model.addConstr(gp.quicksum(x[a] for a in all_arcs if a[0] == j) == 1, name=f"out_{j}")

    for m in depot_ids:
        out_m = gp.quicksum(x[(m, j)] for j in launch_ids)
        in_m = gp.quicksum(x[(i, m)] for i in launch_ids)
        model.addConstr(out_m == in_m, name=f"depot_balance_{m}")
        model.addConstr(out_m <= max_veh, name=f"depot_cap_{m}")

    for (m, j) in dc_arcs:
        idx = depot_index[m]
        model.addConstr(lab[j] >= idx - big_l * (1 - x[(m, j)]), name=f"lab_dc_lo_{m}_{j}")
        model.addConstr(lab[j] <= idx + big_l * (1 - x[(m, j)]), name=f"lab_dc_hi_{m}_{j}")
    for (i, j) in cc_arcs:
        model.addConstr(lab[j] >= lab[i] - big_l * (1 - x[(i, j)]), name=f"lab_cc_lo_{i}_{j}")
        model.addConstr(lab[j] <= lab[i] + big_l * (1 - x[(i, j)]), name=f"lab_cc_hi_{i}_{j}")
    for (i, m) in cd_arcs:
        idx = depot_index[m]
        model.addConstr(lab[i] >= idx - big_l * (1 - x[(i, m)]), name=f"lab_cd_lo_{i}_{m}")
        model.addConstr(lab[i] <= idx + big_l * (1 - x[(i, m)]), name=f"lab_cd_hi_{i}_{m}")

    for (m, j) in dc_arcs:
        model.addConstr(s[j] >= travel(m, j) - big_m * (1 - x[(m, j)]), name=f"t_dc_{m}_{j}")
    for (i, j) in cc_arcs:
        model.addConstr(s[j] >= s[i] + service + travel(i, j) - big_m * (1 - x[(i, j)]), name=f"t_cc_{i}_{j}")
    for j in launch_ids:
        model.addConstr(s[j] <= float(nodes[j]["latest"]), name=f"tw_{j}")

    travel_term = gp.quicksum(travel(i, j) * x[(i, j)] for (i, j) in all_arcs)
    penalty_term = gp.quicksum(
        penalty_l * max(0.0, nodes[j]["priority"] - nodes[i]["priority"]) * x[(i, j)]
        for (i, j) in cc_arcs
    )
    model.setObjective(w1 * travel_term + w2 * penalty_term, GRB.MINIMIZE)
    model.optimize()

    status_map = {GRB.OPTIMAL: "OPTIMAL", GRB.TIME_LIMIT: "TIME_LIMIT", GRB.INFEASIBLE: "INFEASIBLE"}
    status_text = status_map.get(model.Status, str(model.Status))
    if model.SolCount == 0:
        return {"status": "error", "status_text": status_text, "feasible": False, "routes": [], "objective": None}

    used = {a for a in all_arcs if x[a].X > 0.5}
    routes: List[Dict[str, Any]] = []
    for m in depot_ids:
        for first in [j for j in launch_ids if (m, j) in used]:
            sequence = [first]
            current = first
            while True:
                nxt = next((j for j in launch_ids if (current, j) in used and j not in sequence), None)
                if nxt is None:
                    break
                sequence.append(nxt)
                current = nxt
            routes.append({"depot": m, "sequence": sequence})

    ev = evaluate_solution(instance, routes)
    return {
        "status": "success" if ev["feasible"] else "error",
        "status_text": status_text,
        "method": "gurobi_exact",
        "objective": round(ev["objective"], 4),
        "gurobi_objval": round(model.ObjVal, 4),
        "mip_gap": round(model.MIPGap, 6),
        "travel_time": round(ev["travel_time"], 4),
        "priority_penalty": round(ev["priority_penalty"], 4),
        "weighted_travel": round(ev["weighted_travel"], 4),
        "weighted_penalty": round(ev["weighted_penalty"], 4),
        "w1": ev["w1"],
        "w2": ev["w2"],
        "feasible": ev["feasible"],
        "num_routes": ev["num_routes"],
        "routes": routes,
        "arrival_times": {str(k): round(v, 3) for k, v in ev["arrival_times"].items()},
    }


if __name__ == "__main__":
    from solver.mdvrptw.presets import paper_instance

    print("=== exact.py 本地测试 ===")
    result = solve_exact(paper_instance(), time_limit=120)
    print(f"status={result['status']} ({result['status_text']}) objective={result['objective']} routes={result.get('num_routes')}")
