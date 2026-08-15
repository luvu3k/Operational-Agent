"""
作用：
- 对 MDVRPTW-P 论文算例构建并求解精确 MILP（gurobipy），得到全局最优的补给舰路径方案。
- 目标口径与 `model.evaluate_solution` 完全一致：最小化 总航行时间 + 优先级违反惩罚。

建模要点：
- 节点 = 保障中心(depot) ∪ 无人机起飞点(launch)。弧 = depot->launch、launch->launch、launch->depot。
- x[i,j] 弧是否使用；lab[i] 起飞点 i 所属保障中心的“标签”（连续变量，被约束锁定为 depot 索引）；
  s[i] 到达起飞点 i 的时刻。
- 每个起飞点入度=出度=1；depot 出=入（发船=收船）且不超过每中心船数上限。
- 用连续 depot 标签沿弧传播（比 depot×弧 的二元传播省一半以上约束，可放进 size-limited license）：
  起始弧把 lab 锁定为出发 depot 索引，途中弧强制 lab 相等，收尾弧只允许在 lab==该 depot 时闭合，
  从而保证每条路径归属单一保障中心且返回原保障中心。
- 到达时刻按弧递推（big-M），s[j] ≤ latest_j 即硬时间窗；时刻沿弧严格增亦自动消除子回路。
- 优先级惩罚在“起飞点->起飞点”弧上线性化：L · max(0, τ_j − τ_i)，与评估口径一致。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parent))

from instance import build_instance
from model import build_nodes, distance_matrix, evaluate_solution


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

    def travel(i: int, j: int) -> float:
        return dist[(i, j)] / v1

    # 构造弧集合。
    dc_arcs = [(m, j) for m in depot_ids for j in launch_ids]          # depot -> launch
    cc_arcs = [(i, j) for i in launch_ids for j in launch_ids if i != j]  # launch -> launch
    cd_arcs = [(i, m) for i in launch_ids for m in depot_ids]          # launch -> depot
    all_arcs = dc_arcs + cc_arcs + cd_arcs

    model = gp.Model("MDVRPTW_P")
    model.Params.OutputFlag = 1 if verbose else 0
    model.Params.TimeLimit = time_limit

    x = model.addVars(all_arcs, vtype=GRB.BINARY, name="x")
    s = model.addVars(launch_ids, lb=0.0, name="s")
    # 连续 depot 标签：被约束锁定到出发保障中心的索引位置，用于保证单一归属并返回原点。
    depot_index = {m: idx for idx, m in enumerate(depot_ids)}
    lab = model.addVars(launch_ids, lb=0.0, ub=len(depot_ids) - 1, name="lab")

    # 大 M：最大时间窗 + 一段最长行程即足够。
    max_latest = max(float(nodes[i]["latest"]) for i in launch_ids)
    big_m = max_latest + max(travel(i, j) for (i, j) in all_arcs) + service + 10.0
    big_l = len(depot_ids) + 1.0  # 标签传播用的大 M

    # 每个起飞点入度=1、出度=1。
    for j in launch_ids:
        model.addConstr(gp.quicksum(x[a] for a in all_arcs if a[1] == j) == 1, name=f"in_{j}")
        model.addConstr(gp.quicksum(x[a] for a in all_arcs if a[0] == j) == 1, name=f"out_{j}")

    # depot 发船数=收船数，且不超过上限。
    for m in depot_ids:
        out_m = gp.quicksum(x[(m, j)] for j in launch_ids)
        in_m = gp.quicksum(x[(i, m)] for i in launch_ids)
        model.addConstr(out_m == in_m, name=f"depot_balance_{m}")
        model.addConstr(out_m <= max_veh, name=f"depot_cap_{m}")

    # depot 标签传播：起始弧锁定标签，途中弧强制相等，收尾弧仅在标签匹配时闭合。
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

    # 到达时刻递推 + 硬时间窗。
    for (m, j) in dc_arcs:
        model.addConstr(s[j] >= travel(m, j) - big_m * (1 - x[(m, j)]), name=f"t_dc_{m}_{j}")
    for (i, j) in cc_arcs:
        model.addConstr(s[j] >= s[i] + service + travel(i, j) - big_m * (1 - x[(i, j)]), name=f"t_cc_{i}_{j}")
    for j in launch_ids:
        model.addConstr(s[j] <= float(nodes[j]["latest"]), name=f"tw_{j}")

    # 目标：总航行时间 + 优先级违反惩罚。
    travel_term = gp.quicksum(travel(i, j) * x[(i, j)] for (i, j) in all_arcs)
    penalty_term = gp.quicksum(
        penalty_l * max(0.0, nodes[j]["priority"] - nodes[i]["priority"]) * x[(i, j)]
        for (i, j) in cc_arcs
    )
    model.setObjective(travel_term + penalty_term, GRB.MINIMIZE)

    model.optimize()

    status_map = {GRB.OPTIMAL: "OPTIMAL", GRB.TIME_LIMIT: "TIME_LIMIT", GRB.INFEASIBLE: "INFEASIBLE"}
    status_text = status_map.get(model.Status, str(model.Status))
    if model.SolCount == 0:
        return {"status": "error", "status_text": status_text, "feasible": False, "routes": [], "objective": None}

    # 从弧解中还原路径：每个 depot 的每条出弧起一条路径。
    used = {a for a in all_arcs if x[a].X > 0.5}
    routes: List[Dict[str, Any]] = []
    for m in depot_ids:
        starts = [j for j in launch_ids if (m, j) in used]
        for first in starts:
            sequence = [first]
            current = first
            while True:
                nxt = None
                for j in launch_ids:
                    if (current, j) in used and j not in sequence:
                        nxt = j
                        break
                if nxt is None:
                    break
                sequence.append(nxt)
                current = nxt
            routes.append({"depot": m, "sequence": sequence})

    evaluation = evaluate_solution(instance, routes)
    return {
        "status": "success" if evaluation["feasible"] else "error",
        "status_text": status_text,
        "method": "gurobi_exact",
        "objective": round(evaluation["objective"], 4),
        "gurobi_objval": round(model.ObjVal, 4),
        "mip_gap": round(model.MIPGap, 6) if model.SolCount else None,
        "travel_time": round(evaluation["travel_time"], 4),
        "priority_penalty": round(evaluation["priority_penalty"], 4),
        "feasible": evaluation["feasible"],
        "num_routes": evaluation["num_routes"],
        "routes": routes,
        "arrival_times": {str(k): round(v, 3) for k, v in evaluation["arrival_times"].items()},
    }


if __name__ == "__main__":
    print("=== gurobi_solver.py 本地测试 ===")
    inst = build_instance()
    result = solve_exact(inst, time_limit=120, verbose=False)
    print(f"status={result['status']} ({result['status_text']})")
    print(f"objective={result['objective']}  travel_time={result.get('travel_time')}  penalty={result.get('priority_penalty')}")
    print(f"gurobi_objval={result.get('gurobi_objval')}  mip_gap={result.get('mip_gap')}  num_routes={result.get('num_routes')}")
    for route in result["routes"]:
        print(f"  depot {route['depot']}: {route['sequence']}")
    Path("gurobi_result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print("已写入 gurobi_result.json")
