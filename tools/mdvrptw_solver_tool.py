"""
作用：
- 面向智能体暴露 MDVRPTW-P（带时间窗与优先级约束的多仓库车辆路径问题）求解工具。
- 支持精确（Gurobi）与启发式（遗传算法）两种方式：生成可独立运行的完整求解脚本并落盘，
  通过子进程执行得到 result.json，再渲染路线图与甘特图 SVG，最后把完整代码交还用户。

调用关系：
- 被 `tools.tool_registry` 通过 `@tool` 自动扫描注册。
- 被 `core.tool_calling` 和 `core.react_agent` 调用。
- 复用 `solver.mdvrptw` 求解包与 `solver.artifact_store` 落盘执行能力。
"""

from __future__ import annotations

from typing import Any, Dict

from solver.artifact_store import (
    create_run_artifact,
    read_json,
    run_python_file,
    save_execution_logs,
    write_json,
    write_text,
)
from solver.mdvrptw.codegen import build_standalone_script
from solver.mdvrptw.presets import normalize_instance, paper_instance
from solver.mdvrptw.viz import build_visualizations
from tools.tool_registry import tool


def _resolve_instance(problem_spec: Dict[str, Any]) -> Dict[str, Any]:
    """从 problem_spec 解析实例数据；无有效节点数据时回退论文算例，但仍应用用户覆盖的 params。"""
    resources = problem_spec.get("resources", {}) or {}
    instance_data = resources.get("instance_data", {}) if isinstance(resources, dict) else {}
    has_nodes = bool(instance_data.get("depots")) and bool(instance_data.get("launch_points") or instance_data.get("customers"))
    if has_nodes:
        return normalize_instance(instance_data)
    # 仅提供了 params（或没有实例）：用论文算例，并叠加用户覆盖的参数。
    instance = paper_instance()
    override_params = instance_data.get("params", {}) if isinstance(instance_data, dict) else {}
    for key, value in (override_params or {}).items():
        if key in instance["params"]:
            try:
                instance["params"][key] = float(value)
            except (TypeError, ValueError):
                pass
    return instance


def _pick_method(problem_spec: Dict[str, Any]) -> str:
    """根据求解偏好选择 gurobi / genetic。"""
    preference = str(problem_spec.get("solver_preference", "auto")).lower()
    backend = str(problem_spec.get("solver_backend", "auto")).lower()
    if preference == "exact" or backend == "gurobi":
        return "gurobi"
    if preference == "heuristic" or backend in {"genetic", "ga"}:
        return "genetic"
    return "gurobi"


@tool(
    name="mdvrptw_solver",
    description="求解带时间窗与优先级约束的多仓库车辆路径问题(MDVRPTW-P)，支持 Gurobi 精确或遗传算法启发式，返回目标值、补给舰路径、路线图与甘特图。",
    input_schema={
        "type": "object",
        "properties": {
            "problem_spec": {"type": "object", "description": "结构化 MDVRPTW-P 问题定义（含 resources.instance_data 与 solver_preference）。"}
        },
        "required": ["problem_spec"],
    },
    aliases=["@mdvrptw", "@vrp"],
    tags=["solver", "mdvrptw", "routing"],
)
def run_mdvrptw_solver(problem_spec: dict) -> dict:
    """生成完整求解脚本 -> 落盘执行 -> 解析结果 -> 渲染可视化。"""
    instance = _resolve_instance(problem_spec)
    method = _pick_method(problem_spec)

    artifact = create_run_artifact(problem_spec.get("skill_name", "mdvrptw"), method)
    script = build_standalone_script(instance, method, result_path=str(artifact.result_path))
    write_json(artifact.problem_spec_path, {"problem_spec": problem_spec, "instance": instance, "method": method})
    write_text(artifact.code_path, script)

    execution = run_python_file(artifact.code_path, cwd=artifact.run_dir, timeout=300)
    save_execution_logs(artifact, execution)
    solution = read_json(artifact.result_path)

    if execution.get("returncode") != 0 and solution.get("status") == "error":
        # Gurobi 缺失或运行失败：给出清晰信息，供 ReAct 决定改用遗传算法。
        solution.setdefault("feasible", False)
        solution.setdefault("message", "MDVRPTW 求解脚本执行失败，详见 stderr。若为 gurobipy 缺失，可改用遗传算法。")
        solution["stderr"] = execution.get("stderr", "")

    feasible = bool(solution.get("feasible"))
    # 渲染可视化（路线图 + 甘特图）。
    route_map_svg = ""
    gantt_svg = ""
    if solution.get("routes"):
        viz = build_visualizations(instance, {
            "routes": solution.get("routes", []),
            "arrival_times": solution.get("arrival_times", {}),
            "method": method,
        })
        route_map_svg = viz["route_map_svg"]
        gantt_svg = viz["gantt_svg"]
        write_text(artifact.route_graph_path, route_map_svg)
        gantt_path = artifact.run_dir / "gantt.svg"
        write_text(gantt_path, gantt_svg)

    message = solution.get("message") or (
        f"已完成 MDVRPTW-P {'精确(Gurobi)' if method == 'gurobi' else '遗传算法'}求解，"
        f"目标值 {solution.get('objective')}，共 {solution.get('num_routes')} 条补给舰路径。"
        if feasible else "MDVRPTW-P 求解未得到可行解。"
    )

    return {
        "mode": method,
        "status": "success" if feasible else "error",
        "selected_solver": "mdvrptw_solver",
        "message": message,
        "problem_spec": problem_spec,
        "instance_summary": {
            "num_depots": len(instance["depots"]),
            "num_launch_points": len(instance["launch_points"]),
            "source": instance.get("source", ""),
        },
        "generated_code": script,
        "artifact": artifact.to_dict(),
        "code_path": str(artifact.code_path),
        "result_path": str(artifact.result_path),
        "route_graph_path": str(artifact.route_graph_path) if route_map_svg else "",
        "gantt_path": str(artifact.run_dir / "gantt.svg") if gantt_svg else "",
        "route_map_svg": route_map_svg,
        "gantt_svg": gantt_svg,
        "execution": {"returncode": execution.get("returncode")},
        "solution": solution,
    }


if __name__ == "__main__":
    print("=== mdvrptw_solver_tool.py 本地测试 ===")
    sample_spec = {
        "skill_name": "mdvrptw_island_supply",
        "description": "论文 MDVRPTW-P 算例",
        "user_input": "用遗传算法求解论文算例",
        "objectives": ["最小化总航行时间加优先级惩罚"],
        "hard_constraints": ["时间窗", "每点服务一次"],
        "solver_preference": "heuristic",
        "solver_backend": "genetic",
    }
    result = run_mdvrptw_solver(sample_spec)
    print(f"status={result['status']} obj={result['solution'].get('objective')} routes={result['solution'].get('num_routes')}")
    print(f"code_path={result['code_path']}")
    print(f"route_graph_path={result['route_graph_path']}")
