"""
作用：
- 把 MDVRPTW-P 求解结果渲染成可视化路径图（补给舰访问路线，对应论文图 8）与到达时间甘特图（对应论文图 9）。
- 采用零依赖纯 Python 生成 SVG，浏览器可直接渲染，无需 matplotlib/networkx。

调用关系：
- 被验证脚本 `validate.py` 和 agent 的 MDVRPTW 求解工具调用。
- 输入为 `gurobi_solver` / `genetic_solver` 返回的统一结构（含 depots/launch_points 坐标与 routes）。
"""

from __future__ import annotations

import html
import sys
from pathlib import Path
from typing import Any, Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parent))

from model import build_nodes

# 每条路径一个稳定的颜色。
_PALETTE = [
    "#e6194b", "#3cb44b", "#4363d8", "#f58231", "#911eb4", "#42d4f4",
    "#f032e6", "#bfef45", "#fabed4", "#469990", "#9a6324", "#800000",
]


def _scale(nodes: Dict[int, Dict[str, Any]], width: float, height: float, pad: float):
    xs = [n["x"] for n in nodes.values()]
    ys = [n["y"] for n in nodes.values()]
    min_x, max_x, min_y, max_y = min(xs), max(xs), min(ys), max(ys)
    span_x = max(max_x - min_x, 1e-6)
    span_y = max(max_y - min_y, 1e-6)

    def project(x: float, y: float):
        px = pad + (x - min_x) / span_x * (width - 2 * pad)
        # SVG y 轴向下，翻转使地理北在上。
        py = height - (pad + (y - min_y) / span_y * (height - 2 * pad))
        return px, py

    return project


def render_route_map_svg(instance: Dict[str, Any], routes: List[Dict[str, Any]], *, title: str = "补给舰访问路线图") -> str:
    """渲染补给舰路线图：depot 为方块，起飞点为圆点，每条路径不同颜色，箭头示意访问顺序。"""
    nodes, depot_ids, _ = build_nodes(instance)
    width, height, pad = 760.0, 560.0, 60.0
    project = _scale(nodes, width, height, pad)

    parts: List[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width:.0f}" height="{height:.0f}" '
        f'viewBox="0 0 {width:.0f} {height:.0f}" font-family="Helvetica, Arial, sans-serif">',
        f'<rect width="{width:.0f}" height="{height:.0f}" fill="#fbfcfe"/>',
        '<defs>',
    ]
    # 每种颜色一个箭头 marker。
    for idx, color in enumerate(_PALETTE):
        parts.append(
            f'<marker id="arw{idx}" markerWidth="9" markerHeight="9" refX="7" refY="3" '
            f'orient="auto" markerUnits="strokeWidth"><path d="M0,0 L7,3 L0,6 Z" fill="{color}"/></marker>'
        )
    parts.append('</defs>')
    parts.append(
        f'<text x="{width / 2:.0f}" y="34" text-anchor="middle" font-size="20" '
        f'fill="#1f2d3d" font-weight="bold">{html.escape(title)}</text>'
    )

    # 画每条路径：depot -> 依次起飞点 -> depot。
    for ri, route in enumerate(routes):
        color = _PALETTE[ri % len(_PALETTE)]
        depot_id = route["depot"]
        seq = route["sequence"]
        if not seq:
            continue
        path_nodes = [depot_id] + seq + [depot_id]
        for a, b in zip(path_nodes[:-1], path_nodes[1:]):
            x1, y1 = project(nodes[a]["x"], nodes[a]["y"])
            x2, y2 = project(nodes[b]["x"], nodes[b]["y"])
            parts.append(
                f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
                f'stroke="{color}" stroke-width="2" opacity="0.85" marker-end="url(#arw{ri % len(_PALETTE)})"/>'
            )

    # 画节点。
    for launch_id, node in nodes.items():
        px, py = project(node["x"], node["y"])
        if node["is_depot"]:
            parts.append(
                f'<rect x="{px - 9:.1f}" y="{py - 9:.1f}" width="18" height="18" rx="3" '
                f'fill="#2c3e50" stroke="#1a252f" stroke-width="1.5"/>'
            )
            parts.append(
                f'<text x="{px:.1f}" y="{py - 14:.1f}" text-anchor="middle" font-size="12" '
                f'fill="#2c3e50" font-weight="bold">中心{launch_id}</text>'
            )
        else:
            parts.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="6" fill="#ffffff" stroke="#5b6b7b" stroke-width="1.5"/>')
            parts.append(
                f'<text x="{px:.1f}" y="{py - 9:.1f}" text-anchor="middle" font-size="10" fill="#5b6b7b">{launch_id}</text>'
            )

    parts.append('</svg>')
    return "\n".join(parts)


def render_gantt_svg(instance: Dict[str, Any], routes: List[Dict[str, Any]], arrival_times: Dict[str, float], *, title: str = "补给舰访问时间甘特图") -> str:
    """渲染到达时间甘特图：每条路径一行，条形起点为到达时刻。"""
    nodes, _, _ = build_nodes(instance)
    active_routes = [r for r in routes if r["sequence"]]
    row_h = 34.0
    width = 760.0
    height = 90.0 + row_h * max(len(active_routes), 1)
    pad_left, pad_right = 90.0, 40.0

    max_time = 1.0
    for route in active_routes:
        for launch_id in route["sequence"]:
            max_time = max(max_time, float(arrival_times.get(str(launch_id), 0.0)))
    max_time *= 1.15

    def tx(t: float) -> float:
        return pad_left + t / max_time * (width - pad_left - pad_right)

    parts: List[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width:.0f}" height="{height:.0f}" '
        f'viewBox="0 0 {width:.0f} {height:.0f}" font-family="Helvetica, Arial, sans-serif">',
        f'<rect width="{width:.0f}" height="{height:.0f}" fill="#fbfcfe"/>',
        f'<text x="{width / 2:.0f}" y="30" text-anchor="middle" font-size="18" '
        f'fill="#1f2d3d" font-weight="bold">{html.escape(title)}</text>',
    ]
    # 时间轴。
    axis_y = height - 30
    parts.append(f'<line x1="{pad_left}" y1="{axis_y}" x2="{width - pad_right}" y2="{axis_y}" stroke="#9aa5b1" stroke-width="1"/>')
    for frac in range(0, 6):
        t = max_time * frac / 5
        x = tx(t)
        parts.append(f'<line x1="{x:.1f}" y1="55" x2="{x:.1f}" y2="{axis_y}" stroke="#edf0f3" stroke-width="1"/>')
        parts.append(f'<text x="{x:.1f}" y="{axis_y + 16:.1f}" text-anchor="middle" font-size="10" fill="#5b6b7b">{t:.0f}h</text>')

    for ri, route in enumerate(active_routes):
        color = _PALETTE[ri % len(_PALETTE)]
        y = 60 + ri * row_h
        parts.append(
            f'<text x="10" y="{y + row_h / 2:.1f}" font-size="11" fill="#2c3e50">中心{route["depot"]}·船{ri + 1}</text>'
        )
        prev_x = tx(0.0)
        for launch_id in route["sequence"]:
            t = float(arrival_times.get(str(launch_id), 0.0))
            x = tx(t)
            parts.append(
                f'<line x1="{prev_x:.1f}" y1="{y + row_h / 2:.1f}" x2="{x:.1f}" y2="{y + row_h / 2:.1f}" '
                f'stroke="{color}" stroke-width="3" opacity="0.6"/>'
            )
            parts.append(f'<circle cx="{x:.1f}" cy="{y + row_h / 2:.1f}" r="5" fill="{color}"/>')
            parts.append(
                f'<text x="{x:.1f}" y="{y + row_h / 2 - 8:.1f}" text-anchor="middle" font-size="9" fill="#2c3e50">{launch_id}</text>'
            )
            prev_x = x

    parts.append('</svg>')
    return "\n".join(parts)


def build_visualizations(instance: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, str]:
    """一次性生成路线图与甘特图 SVG。"""
    routes = result.get("routes", [])
    arrivals = result.get("arrival_times", {})
    method = result.get("method", "")
    return {
        "route_map_svg": render_route_map_svg(instance, routes, title=f"补给舰访问路线图（{method}）"),
        "gantt_svg": render_gantt_svg(instance, routes, arrivals, title=f"补给舰到达时间甘特图（{method}）"),
    }


if __name__ == "__main__":
    import json

    from instance import build_instance

    print("=== visualize.py 本地测试 ===")
    inst = build_instance()
    result_path = Path("gurobi_result.json")
    if result_path.exists():
        result = json.loads(result_path.read_text(encoding="utf-8"))
    else:
        result = {"routes": [{"depot": 0, "sequence": [3, 24]}], "arrival_times": {"3": 4.2, "24": 2.0}, "method": "demo"}
    viz = build_visualizations(inst, result)
    Path("route_map.svg").write_text(viz["route_map_svg"], encoding="utf-8")
    Path("gantt.svg").write_text(viz["gantt_svg"], encoding="utf-8")
    print(f"route_map.svg 长度: {len(viz['route_map_svg'])}")
    print(f"gantt.svg 长度: {len(viz['gantt_svg'])}")
