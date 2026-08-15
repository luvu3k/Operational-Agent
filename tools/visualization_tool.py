"""
作用：
- 将求解结果中的运输/路径方案渲染成可直接查看的路径图（SVG）与结构化答案摘要。
- 采用零依赖的纯 Python 生成 SVG，保证在没有 matplotlib / networkx 的环境下也能产出路径图。

调用关系：
- 被 `tools.exact_solver_tool`、`tools.heuristic_solver_tool` 在求解完成后调用。
- 也可被 `core.react_agent` 或未来报告层单独调用。
- 输入为求解工具产出的 `solution`（含 shipment_plan / objective_value 等字段）。
"""

from __future__ import annotations

import html
from typing import Any, Dict, List, Tuple


def _collect_nodes(shipment_plan: List[Dict[str, Any]]) -> Tuple[List[str], List[str]]:
    """从运输方案中拆出「起点（仓库）」与「终点（岛礁/客户）」两类节点，保持出现顺序。"""
    sources: List[str] = []
    targets: List[str] = []
    for leg in shipment_plan:
        src = str(leg.get("from", ""))
        dst = str(leg.get("to", ""))
        if src and src not in sources:
            sources.append(src)
        if dst and dst not in targets:
            targets.append(dst)
    return sources, targets


def _layout_positions(sources: List[str], targets: List[str]) -> Dict[str, Tuple[float, float]]:
    """把仓库放在左列、岛礁放在右列，纵向均匀分布，返回每个节点的坐标。"""
    positions: Dict[str, Tuple[float, float]] = {}
    left_x, right_x = 140.0, 560.0
    top, gap = 90.0, 110.0
    for index, name in enumerate(sources):
        positions[name] = (left_x, top + index * gap)
    for index, name in enumerate(targets):
        positions[name] = (right_x, top + index * gap)
    return positions


def render_route_graph_svg(solution: Dict[str, Any], *, title: str = "运输路径图") -> str:
    """把求解方案渲染成 SVG 字符串：仓库->岛礁的运量用带标注的有向边表示。"""
    shipment_plan = solution.get("shipment_plan", []) or []
    sources, targets = _collect_nodes(shipment_plan)
    positions = _layout_positions(sources, targets)

    height = int(max(len(sources), len(targets), 1) * 110 + 160)
    width = 720
    objective = solution.get("objective_value")
    status_text = solution.get("status_text", solution.get("status", ""))

    parts: List[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" font-family="Helvetica, Arial, sans-serif">',
        f'<rect x="0" y="0" width="{width}" height="{height}" fill="#ffffff"/>',
        '<defs><marker id="arrow" markerWidth="10" markerHeight="10" refX="9" refY="3" '
        'orient="auto" markerUnits="strokeWidth">'
        '<path d="M0,0 L9,3 L0,6 Z" fill="#5b6b7b"/></marker></defs>',
        f'<text x="{width / 2}" y="40" text-anchor="middle" font-size="20" '
        f'fill="#1f2d3d" font-weight="bold">{html.escape(title)}</text>',
    ]

    subtitle = f"目标函数值: {objective}" if objective is not None else "目标函数值: N/A"
    if status_text:
        subtitle += f"    状态: {html.escape(str(status_text))}"
    parts.append(
        f'<text x="{width / 2}" y="66" text-anchor="middle" font-size="14" fill="#5b6b7b">{subtitle}</text>'
    )

    # 先画边，再画节点，保证节点覆盖在边之上。
    for leg in shipment_plan:
        src, dst = str(leg.get("from", "")), str(leg.get("to", ""))
        if src not in positions or dst not in positions:
            continue
        (x1, y1), (x2, y2) = positions[src], positions[dst]
        qty = leg.get("quantity", leg.get("flow", ""))
        mid_x, mid_y = (x1 + x2) / 2, (y1 + y2) / 2
        parts.append(
            f'<line x1="{x1 + 28:.1f}" y1="{y1:.1f}" x2="{x2 - 30:.1f}" y2="{y2:.1f}" '
            f'stroke="#5b6b7b" stroke-width="2" marker-end="url(#arrow)"/>'
        )
        parts.append(
            f'<text x="{mid_x:.1f}" y="{mid_y - 6:.1f}" text-anchor="middle" font-size="12" '
            f'fill="#c0392b">{html.escape(str(qty))}</text>'
        )

    def _draw_node(name: str, x: float, y: float, fill: str) -> None:
        parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="26" fill="{fill}" stroke="#2c3e50" stroke-width="2"/>')
        parts.append(
            f'<text x="{x:.1f}" y="{y + 44:.1f}" text-anchor="middle" font-size="12" '
            f'fill="#2c3e50">{html.escape(name)}</text>'
        )

    for name in sources:
        x, y = positions[name]
        _draw_node(name, x, y, "#aed6f1")
    for name in targets:
        x, y = positions[name]
        _draw_node(name, x, y, "#f9e79f")

    parts.append('<text x="140" y="{0}" text-anchor="middle" font-size="12" fill="#2874a6">仓库</text>'.format(height - 30))
    parts.append('<text x="560" y="{0}" text-anchor="middle" font-size="12" fill="#b7950b">需求点</text>'.format(height - 30))
    parts.append("</svg>")
    return "\n".join(parts)


def render_answer_markdown(solution: Dict[str, Any], *, problem_spec: Dict[str, Any] | None = None) -> str:
    """把求解结果整理成人类可读的结构化答案（Markdown）。"""
    problem_spec = problem_spec or {}
    lines: List[str] = ["# 求解答案", ""]
    lines.append(f"- 问题类型: {problem_spec.get('skill_name', 'unknown')}")
    lines.append(f"- 求解策略: {solution.get('strategy', problem_spec.get('solver_preference', 'unknown'))}")
    lines.append(f"- 求解后端: {solution.get('solver_backend_used', problem_spec.get('solver_backend', 'unknown'))}")
    lines.append(f"- 是否可行: {solution.get('feasible')}")
    lines.append(f"- 求解状态: {solution.get('status_text', solution.get('status', 'unknown'))}")
    lines.append(f"- **目标函数值: {solution.get('objective_value')}**")
    lines.append(f"- 总运输量: {solution.get('total_shipped')}")
    lines.append("")

    shipment_plan = solution.get("shipment_plan", []) or []
    if shipment_plan:
        lines.append("## 运输/路径方案")
        lines.append("")
        lines.append("| 起点 | 终点 | 运量 |")
        lines.append("| --- | --- | --- |")
        for leg in shipment_plan:
            qty = leg.get("quantity", leg.get("flow", ""))
            lines.append(f"| {leg.get('from', '')} | {leg.get('to', '')} | {qty} |")
        lines.append("")

    unmet = solution.get("unmet_demand")
    if unmet:
        lines.append(f"> 注意：存在未满足需求 {unmet}")
        lines.append("")

    lines.append("路径图见同目录 `route_graph.svg`。")
    return "\n".join(lines)


def build_visualization(solution: dict, *, problem_spec: dict | None = None, title: str = "运输路径图") -> dict:
    """生成路径图 SVG 与答案 Markdown 文本，返回给调用方决定如何落盘。"""
    if not isinstance(solution, dict) or not solution.get("shipment_plan"):
        return {
            "visualization_status": "skipped",
            "reason": "求解结果中没有可用于绘图的 shipment_plan。",
            "svg": "",
            "answer_markdown": render_answer_markdown(solution or {}, problem_spec=problem_spec),
        }
    return {
        "visualization_status": "ok",
        "svg": render_route_graph_svg(solution, title=title),
        "answer_markdown": render_answer_markdown(solution, problem_spec=problem_spec),
    }


if __name__ == "__main__":
    print("=== visualization_tool.py 本地测试 ===")
    demo_solution = {
        "objective_value": 360.0,
        "status_text": "OPTIMAL",
        "feasible": True,
        "strategy": "exact",
        "solver_backend_used": "gurobi",
        "total_shipped": 90.0,
        "shipment_plan": [
            {"from": "warehouse_1", "to": "island_a", "quantity": 30},
            {"from": "warehouse_1", "to": "island_b", "quantity": 40},
            {"from": "warehouse_2", "to": "island_c", "quantity": 20},
        ],
    }
    viz = build_visualization(demo_solution, problem_spec={"skill_name": "emergency_island_supply"})
    print("visualization_status:", viz["visualization_status"])
    print("svg 长度:", len(viz["svg"]))
    print(viz["answer_markdown"])
