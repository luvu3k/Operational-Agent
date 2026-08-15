"""
作用：
- 面向智能体暴露启发式求解工具，负责把结构化问题转换为可执行的启发式算法代码并运行。
- 当前针对岛礁应急补给场景生成“贪心 + 局部改进”的纯 Python 代码，保存代码文件、执行日志与结果 JSON，
  并把路径返回给用户。启发式不依赖任何商业求解器，适合大规模或无 license 场景。

调用关系：
- 被 `tools.tool_registry` 通过 `@tool` 自动扫描注册。
- 被 `core.tool_calling` 和 `core.react_agent` 调用。
- 调用 `solver.artifact_store` 完成代码落盘、子进程执行和结果读取。
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Tuple

from solver.artifact_store import (
    create_run_artifact,
    read_json,
    run_python_file,
    save_execution_logs,
    write_json,
    write_text,
)
from tools.tool_registry import tool


@tool(
    name="heuristic_solver",
    description="根据结构化问题生成并执行启发式（贪心+局部搜索）求解代码。",
    input_schema={
        "type": "object",
        "properties": {
            "problem_spec": {"type": "object", "description": "结构化后的优化问题定义。"}
        },
        "required": ["problem_spec"],
    },
    aliases=["@heuristic", "@hs"],
    tags=["solver", "heuristic"],
)
def run_heuristic_solver(problem_spec: dict) -> dict:
    """生成启发式求解代码、保存到文件、执行并返回结果。"""
    resources = problem_spec.get("resources", {}) or {}
    instance_data = resources.get("instance_data", {}) if isinstance(resources, dict) else {}

    if problem_spec.get("skill_name") != "emergency_island_supply":
        return _error_payload(problem_spec, "当前启发式求解工具仅实现了岛礁应急补给场景。", "UNSUPPORTED_SKILL")

    if not instance_data:
        return _error_payload(
            problem_spec,
            "缺少结构化实例数据，无法生成可执行启发式代码。请提供 depots、islands、routes。",
            "MISSING_INSTANCE_DATA",
        )

    depots, islands, routes = _normalize_instance_data(instance_data)
    validation_errors = _validate_instance(depots, islands, routes)
    if validation_errors:
        payload = _error_payload(problem_spec, "实例数据不完整，无法生成启发式代码。", "INVALID_INSTANCE_DATA")
        payload["validation_errors"] = validation_errors
        return payload

    artifact = create_run_artifact(problem_spec.get("skill_name", "task"), "heuristic")
    generated_code = _build_heuristic_code(
        problem_spec=problem_spec,
        depots=depots,
        islands=islands,
        routes=routes,
        result_path=str(artifact.result_path),
    )
    write_json(artifact.problem_spec_path, problem_spec)
    write_text(artifact.code_path, generated_code)

    execution = run_python_file(artifact.code_path, cwd=artifact.run_dir, timeout=120)
    save_execution_logs(artifact, execution)
    solution = read_json(artifact.result_path)
    if execution.get("returncode") != 0 and solution.get("status") != "success":
        solution.setdefault("status", "error")
        solution.setdefault("feasible", False)
        solution.setdefault("status_text", "EXECUTION_FAILED")
        solution.setdefault("message", "生成的启发式代码执行失败，详见 stderr 日志。")
        solution.setdefault("stderr", execution.get("stderr", ""))

    feasible = bool(solution.get("feasible"))
    message = solution.get("message") or ("已完成启发式求解。" if feasible else "启发式求解未得到可行解。")

    visualization = _render_outputs(artifact, solution, problem_spec)

    return {
        "mode": "heuristic",
        "status": "success" if feasible else "error",
        "selected_solver": "heuristic_solver",
        "message": message,
        "problem_spec": problem_spec,
        "generated_code": generated_code,
        "artifact": artifact.to_dict(),
        "code_path": str(artifact.code_path),
        "result_path": str(artifact.result_path),
        "stdout_path": str(artifact.stdout_path),
        "stderr_path": str(artifact.stderr_path),
        "route_graph_path": str(artifact.route_graph_path) if visualization.get("visualization_status") == "ok" else "",
        "answer_path": str(artifact.answer_path),
        "execution": execution,
        "model_summary": {
            "num_depots": len(depots),
            "num_islands": len(islands),
            "num_routes": len(routes),
            "strategy": "greedy_plus_local_search",
        },
        "solution": solution,
    }


def _render_outputs(artifact, solution: Dict[str, Any], problem_spec: Dict[str, Any]) -> Dict[str, Any]:
    """生成并落盘路径图 SVG 与结构化答案 Markdown，失败不影响主流程。"""
    try:
        from tools.visualization_tool import build_visualization

        visualization = build_visualization(solution, problem_spec=problem_spec, title="岛礁补给运输路径图（启发式）")
        if visualization.get("svg"):
            write_text(artifact.route_graph_path, visualization["svg"])
        if visualization.get("answer_markdown"):
            write_text(artifact.answer_path, visualization["answer_markdown"])
        return visualization
    except Exception as exc:  # pragma: no cover - 可视化失败不阻断求解
        return {"visualization_status": "error", "reason": str(exc)}


def _error_payload(problem_spec: Dict[str, Any], message: str, status_text: str) -> Dict[str, Any]:
    """构造统一错误返回，便于 ReAct 上层处理。"""
    return {
        "mode": "heuristic",
        "status": "error",
        "selected_solver": "heuristic_solver",
        "message": message,
        "problem_spec": problem_spec,
        "solution": {
            "status": "error",
            "objective_value": None,
            "feasible": False,
            "strategy": "heuristic",
            "status_text": status_text,
            "shipment_plan": [],
            "total_shipped": 0.0,
            "message": message,
        },
    }


def _normalize_instance_data(instance_data: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    """将实例数据统一规整为列表形式，便于建模。"""
    depots = instance_data.get("depots", [])
    islands = instance_data.get("islands", [])
    routes = instance_data.get("routes", [])

    if isinstance(depots, dict):
        depots = [{"name": name, **payload} for name, payload in depots.items()]
    if isinstance(islands, dict):
        islands = [{"name": name, **payload} for name, payload in islands.items()]

    normalized_routes: List[Dict[str, Any]] = []
    if isinstance(routes, dict):
        for route_name, payload in routes.items():
            normalized_routes.append({"name": route_name, **payload})
    else:
        normalized_routes = list(routes)

    for depot in depots:
        depot.setdefault("name", depot.get("id"))
        depot.setdefault("supply", 0)
    for island in islands:
        island.setdefault("name", island.get("id"))
        island.setdefault("demand", 0)
    for route in normalized_routes:
        route.setdefault("cost", route.get("time", 1))
        route.setdefault("capacity", route.get("max_capacity", 10**9))

    return depots, islands, normalized_routes


def _validate_instance(depots: List[Dict[str, Any]], islands: List[Dict[str, Any]], routes: List[Dict[str, Any]]) -> List[str]:
    """检查岛礁补给实例数据是否具备生成启发式代码的必要字段。"""
    errors: List[str] = []
    if not depots:
        errors.append("缺少 depots 仓库数据。")
    if not islands:
        errors.append("缺少 islands 岛礁需求数据。")
    if not routes:
        errors.append("缺少 routes 航线数据。")
    for route in routes:
        if not route.get("from") or not route.get("to"):
            errors.append(f"航线缺少 from/to: {route}")
        if "capacity" not in route:
            errors.append(f"航线缺少 capacity: {route}")
    return errors


def _build_heuristic_code(
    *,
    problem_spec: Dict[str, Any],
    depots: List[Dict[str, Any]],
    islands: List[Dict[str, Any]],
    routes: List[Dict[str, Any]],
    result_path: str,
) -> str:
    """生成可独立运行并写出 result.json 的启发式（贪心+局部搜索）代码。"""
    payload = {
        "problem_spec": problem_spec,
        "instance_data": {"depots": depots, "islands": islands, "routes": routes},
        "result_path": result_path,
    }
    payload_text = json.dumps(payload, ensure_ascii=False, indent=2)
    return f'''"""
自动生成文件：岛礁应急补给启发式求解代码（贪心构造 + 局部改进）。
该文件由 `tools.heuristic_solver_tool` 生成，可单独运行并输出 result.json。
不依赖任何外部求解器，适合大规模或无 Gurobi license 的场景。
"""

from __future__ import annotations

import json
import traceback
from pathlib import Path

PAYLOAD = json.loads(r"""{payload_text}""")


def write_result(payload):
    result_path = Path(PAYLOAD["result_path"])
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def evaluate(plan, cost):
    return sum(cost[(item["from"], item["to"])] * item["quantity"] for item in plan)


def solve():
    instance_data = PAYLOAD["instance_data"]
    depots = instance_data["depots"]
    islands = instance_data["islands"]
    routes = instance_data["routes"]

    supply = {{depot["name"]: float(depot.get("supply", 0)) for depot in depots}}
    demand = {{island["name"]: float(island.get("demand", 0)) for island in islands}}
    route_keys = [(route["from"], route["to"]) for route in routes]
    cost = {{(route["from"], route["to"]): float(route.get("cost", route.get("time", 1))) for route in routes}}
    capacity = {{(route["from"], route["to"]): float(route.get("capacity", 10**9)) for route in routes}}

    remaining_supply = dict(supply)
    remaining_demand = dict(demand)
    flow = {{key: 0.0 for key in route_keys}}

    # 贪心构造：按单位成本从低到高优先分配运量。
    for src, dst in sorted(route_keys, key=lambda k: cost[k]):
        if remaining_demand.get(dst, 0) <= 1e-9 or remaining_supply.get(src, 0) <= 1e-9:
            continue
        assignable = min(remaining_supply[src], remaining_demand[dst], capacity[(src, dst)])
        if assignable <= 1e-9:
            continue
        flow[(src, dst)] += assignable
        remaining_supply[src] -= assignable
        remaining_demand[dst] -= assignable

    unmet = {{island: qty for island, qty in remaining_demand.items() if qty > 1e-6}}
    feasible = not unmet

    # 局部改进：尝试将运量从高成本航线转移到同一岛礁的低成本航线上。
    improved = True
    while improved:
        improved = False
        for dst in demand:
            in_routes = [key for key in route_keys if key[1] == dst and flow[key] > 1e-9]
            candidate_routes = sorted([key for key in route_keys if key[1] == dst], key=lambda k: cost[k])
            for high in sorted(in_routes, key=lambda k: cost[k], reverse=True):
                for low in candidate_routes:
                    if low == high or cost[low] >= cost[high]:
                        continue
                    src_low = low[0]
                    movable = min(flow[high], remaining_supply.get(src_low, 0.0), capacity[low] - flow[low])
                    if movable <= 1e-9:
                        continue
                    flow[high] -= movable
                    flow[low] += movable
                    remaining_supply[high[0]] = remaining_supply.get(high[0], 0.0) + movable
                    remaining_supply[src_low] -= movable
                    improved = True

    shipment_plan = [
        {{"from": src, "to": dst, "quantity": round(flow[(src, dst)], 6)}}
        for (src, dst) in route_keys
        if flow[(src, dst)] > 1e-8
    ]
    total_shipped = round(sum(item["quantity"] for item in shipment_plan), 6)
    objective_value = round(evaluate(shipment_plan, cost), 6)

    write_result({{
        "status": "success" if feasible else "error",
        "feasible": feasible,
        "strategy": "greedy_plus_local_search",
        "solver_backend_used": "python_heuristic",
        "status_text": "FEASIBLE" if feasible else "INFEASIBLE",
        "objective_value": objective_value if feasible else None,
        "shipment_plan": shipment_plan,
        "total_shipped": total_shipped,
        "unmet_demand": unmet,
        "message": "已完成启发式求解（贪心+局部改进）。" if feasible else "启发式无法满足全部需求，请检查供给或航线容量。",
    }})


if __name__ == "__main__":
    try:
        solve()
    except Exception as exc:
        write_result({{
            "status": "error",
            "feasible": False,
            "status_text": "RUNTIME_ERROR",
            "objective_value": None,
            "shipment_plan": [],
            "total_shipped": 0.0,
            "message": "生成的启发式代码运行失败。",
            "error": str(exc),
            "traceback": traceback.format_exc(),
        }})
'''


if __name__ == "__main__":
    print("=== heuristic_solver_tool.py 本地测试 ===")
    sample_problem_spec = {
        "skill_name": "emergency_island_supply",
        "description": "岛礁应急物资补给启发式测试",
        "user_input": "请执行启发式求解工具测试",
        "objectives": ["最小化总运输成本"],
        "hard_constraints": ["必须满足所有岛礁需求"],
        "solver_preference": "heuristic",
        "resources": {
            "instance_data": {
                "depots": [
                    {"name": "warehouse_1", "supply": 70},
                    {"name": "warehouse_2", "supply": 50},
                ],
                "islands": [
                    {"name": "island_a", "demand": 30},
                    {"name": "island_b", "demand": 40},
                    {"name": "island_c", "demand": 20},
                ],
                "routes": [
                    {"from": "warehouse_1", "to": "island_a", "cost": 4, "capacity": 40},
                    {"from": "warehouse_1", "to": "island_b", "cost": 6, "capacity": 40},
                    {"from": "warehouse_1", "to": "island_c", "cost": 9, "capacity": 30},
                    {"from": "warehouse_2", "to": "island_a", "cost": 5, "capacity": 40},
                    {"from": "warehouse_2", "to": "island_b", "cost": 4, "capacity": 40},
                    {"from": "warehouse_2", "to": "island_c", "cost": 3, "capacity": 30},
                ],
            }
        },
    }
    print(json.dumps(run_heuristic_solver(sample_problem_spec), ensure_ascii=False, indent=2))
