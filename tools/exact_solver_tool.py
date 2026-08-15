"""
作用：
- 面向智能体暴露精确求解工具，负责把结构化问题转换为可执行的求解器代码并运行。
- 当前版本针对岛礁应急补给场景生成 `gurobipy` 代码，保存代码文件、执行日志和结果 JSON，并把路径返回给用户。

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
    name="exact_solver",
    description="根据结构化问题生成并执行精确求解流程。",
    input_schema={
        "type": "object",
        "properties": {
            "problem_spec": {"type": "object", "description": "结构化后的优化问题定义。"}
        },
        "required": ["problem_spec"],
    },
    aliases=["@exact", "@es"],
    tags=["solver", "exact"],
)
def run_exact_solver(problem_spec: dict) -> dict:
    """生成 `gurobipy` 求解代码、保存到文件、执行并返回结果。"""
    resources = problem_spec.get("resources", {}) or {}
    instance_data = resources.get("instance_data", {}) if isinstance(resources, dict) else {}
    solver_backend = str(problem_spec.get("solver_backend", "gurobi") or "gurobi").lower()

    if problem_spec.get("skill_name") != "emergency_island_supply":
        return _error_payload(problem_spec, "当前精确求解工具仅实现了岛礁应急补给场景。", "UNSUPPORTED_SKILL")

    if not instance_data:
        return _error_payload(
            problem_spec,
            "缺少结构化实例数据，无法生成可执行求解代码。请提供 depots、islands、routes。",
            "MISSING_INSTANCE_DATA",
        )

    depots, islands, routes = _normalize_instance_data(instance_data)
    validation_errors = _validate_instance(depots, islands, routes)
    if validation_errors:
        payload = _error_payload(problem_spec, "实例数据不完整，无法生成可执行求解代码。", "INVALID_INSTANCE_DATA")
        payload["validation_errors"] = validation_errors
        return payload

    artifact = create_run_artifact(problem_spec.get("skill_name", "task"), "exact_gurobi")
    generated_code = _build_gurobipy_code(
        problem_spec=problem_spec,
        depots=depots,
        islands=islands,
        routes=routes,
        result_path=str(artifact.result_path),
    )
    write_json(artifact.problem_spec_path, problem_spec)
    write_text(artifact.code_path, generated_code)

    execution = run_python_file(artifact.code_path, cwd=artifact.run_dir, timeout=180)
    save_execution_logs(artifact, execution)
    solution = read_json(artifact.result_path)
    if execution.get("returncode") != 0 and solution.get("status") != "success":
        solution.setdefault("status", "error")
        solution.setdefault("feasible", False)
        solution.setdefault("status_text", "EXECUTION_FAILED")
        solution.setdefault("message", "生成的求解代码执行失败，详见 stderr 日志。")
        solution.setdefault("stderr", execution.get("stderr", ""))

    feasible = bool(solution.get("feasible"))
    message = solution.get("message") or ("已完成 Gurobi 精确求解。" if feasible else "精确求解未得到可行解。")

    visualization = _render_outputs(artifact, solution, problem_spec)

    return {
        "mode": "exact",
        "status": "success" if feasible else "error",
        "selected_solver": "exact_solver",
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
            "solver_backend_requested": solver_backend,
            "solver_backend_used": "gurobi",
        },
        "solution": solution,
    }


def _render_outputs(artifact, solution: Dict[str, Any], problem_spec: Dict[str, Any]) -> Dict[str, Any]:
    """生成并落盘路径图 SVG 与结构化答案 Markdown，失败不影响主流程。"""
    try:
        from tools.visualization_tool import build_visualization

        visualization = build_visualization(solution, problem_spec=problem_spec, title="岛礁补给运输路径图")
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
        "mode": "exact",
        "status": "error",
        "selected_solver": "exact_solver",
        "message": message,
        "problem_spec": problem_spec,
        "solution": {
            "status": "error",
            "objective_value": None,
            "feasible": False,
            "strategy": "exact",
            "status_text": status_text,
            "solver_backend_used": "gurobi",
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
    """检查岛礁补给实例数据是否具备生成 Gurobi 模型的必要字段。"""
    errors: List[str] = []
    if not depots:
        errors.append("缺少 depots 仓库数据。")
    if not islands:
        errors.append("缺少 islands 岛礁需求数据。")
    if not routes:
        errors.append("缺少 routes 航线数据。")
    for depot in depots:
        if not depot.get("name"):
            errors.append(f"仓库缺少 name: {depot}")
        if "supply" not in depot:
            errors.append(f"仓库缺少 supply: {depot}")
    for island in islands:
        if not island.get("name"):
            errors.append(f"岛礁缺少 name: {island}")
        if "demand" not in island:
            errors.append(f"岛礁缺少 demand: {island}")
    for route in routes:
        if not route.get("from") or not route.get("to"):
            errors.append(f"航线缺少 from/to: {route}")
        if "cost" not in route and "time" not in route:
            errors.append(f"航线缺少 cost 或 time: {route}")
        if "capacity" not in route:
            errors.append(f"航线缺少 capacity: {route}")
    return errors


def _build_gurobipy_code(
    *,
    problem_spec: Dict[str, Any],
    depots: List[Dict[str, Any]],
    islands: List[Dict[str, Any]],
    routes: List[Dict[str, Any]],
    result_path: str,
) -> str:
    """生成可独立运行并写出 result.json 的 `gurobipy` 代码。"""
    payload = {
        "problem_spec": problem_spec,
        "instance_data": {
            "depots": depots,
            "islands": islands,
            "routes": routes,
        },
        "result_path": result_path,
    }
    payload_text = json.dumps(payload, ensure_ascii=False, indent=2)
    return f'''"""
自动生成文件：岛礁应急补给 Gurobi 精确求解代码。
该文件由 `tools.exact_solver_tool` 生成，可单独运行并输出 result.json。
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


def solve():
    try:
        import gurobipy as gp
        from gurobipy import GRB
    except Exception as exc:
        write_result({{
            "status": "error",
            "feasible": False,
            "status_text": "GUROBIPY_NOT_AVAILABLE",
            "objective_value": None,
            "shipment_plan": [],
            "total_shipped": 0.0,
            "message": "当前环境无法导入 gurobipy，请先安装 Gurobi Python 接口并配置 license。",
            "error": str(exc),
        }})
        return

    instance_data = PAYLOAD["instance_data"]
    depots = instance_data["depots"]
    islands = instance_data["islands"]
    routes = instance_data["routes"]

    depot_names = [depot["name"] for depot in depots]
    island_names = [island["name"] for island in islands]
    supply = {{depot["name"]: float(depot.get("supply", 0)) for depot in depots}}
    demand = {{island["name"]: float(island.get("demand", 0)) for island in islands}}
    route_keys = [(route["from"], route["to"]) for route in routes]
    cost = {{(route["from"], route["to"]): float(route.get("cost", route.get("time", 1))) for route in routes}}
    capacity = {{(route["from"], route["to"]): float(route.get("capacity", 10**9)) for route in routes}}

    model = gp.Model("EmergencyIslandSupply")
    model.Params.OutputFlag = 0
    x = model.addVars(route_keys, lb=0.0, name="x")

    model.setObjective(gp.quicksum(cost[key] * x[key] for key in route_keys), GRB.MINIMIZE)

    for depot in depot_names:
        model.addConstr(
            gp.quicksum(x[key] for key in route_keys if key[0] == depot) <= supply[depot],
            name=f"supply_{{depot}}",
        )

    for island in island_names:
        model.addConstr(
            gp.quicksum(x[key] for key in route_keys if key[1] == island) >= demand[island],
            name=f"demand_{{island}}",
        )

    for key in route_keys:
        model.addConstr(x[key] <= capacity[key], name=f"capacity_{{key[0]}}_{{key[1]}}")

    model.optimize()

    status_text = {{
        GRB.OPTIMAL: "OPTIMAL",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.UNBOUNDED: "UNBOUNDED",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.TIME_LIMIT: "TIME_LIMIT",
    }}.get(model.Status, str(model.Status))
    feasible = model.Status == GRB.OPTIMAL

    shipment_plan = []
    total_shipped = 0.0
    if feasible:
        for src, dst in route_keys:
            quantity = x[src, dst].X
            if quantity > 1e-8:
                shipment_plan.append({{"from": src, "to": dst, "quantity": round(float(quantity), 6)}})
                total_shipped += float(quantity)

    write_result({{
        "status": "success" if feasible else "error",
        "feasible": feasible,
        "strategy": "exact",
        "solver_backend_used": "gurobi",
        "status_text": status_text,
        "objective_value": float(model.ObjVal) if feasible else None,
        "shipment_plan": shipment_plan,
        "total_shipped": round(total_shipped, 6),
        "message": "已完成 Gurobi 精确求解。" if feasible else f"Gurobi 求解结束，但状态为 {{status_text}}。",
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
            "message": "生成的 Gurobi 求解代码运行失败。",
            "error": str(exc),
            "traceback": traceback.format_exc(),
        }})
'''


if __name__ == "__main__":
    print("=== exact_solver_tool.py 本地测试 ===")
    sample_problem_spec = {
        "skill_name": "emergency_island_supply",
        "description": "岛礁应急物资补给测试问题",
        "user_input": "请执行精确求解工具测试",
        "objectives": ["最小化总配送时间"],
        "hard_constraints": ["必须满足所有岛礁需求"],
        "solver_preference": "exact",
        "solver_backend": "gurobi",
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
                    {"from": "warehouse_1", "to": "island_a", "time": 4, "cost": 4, "capacity": 40},
                    {"from": "warehouse_1", "to": "island_b", "time": 6, "cost": 6, "capacity": 40},
                    {"from": "warehouse_1", "to": "island_c", "time": 9, "cost": 9, "capacity": 30},
                    {"from": "warehouse_2", "to": "island_a", "time": 5, "cost": 5, "capacity": 40},
                    {"from": "warehouse_2", "to": "island_b", "time": 4, "cost": 4, "capacity": 40},
                    {"from": "warehouse_2", "to": "island_c", "time": 3, "cost": 3, "capacity": 30},
                ],
            }
        },
    }
    print(run_exact_solver(sample_problem_spec))
