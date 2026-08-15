"""
作用：
- 提供 MDVRPTW-P 的预置算例（论文 3 保障中心 + 22 无人机起飞点）与实例归一化函数。
- 归一化让 LLM 抽取的 JSON 或用户自定义数据都能转成统一实例结构，缺省参数自动补齐。
"""

from __future__ import annotations

from typing import Any, Dict, List

# 论文表 4：3 个保障中心。
_PAPER_DEPOTS = [
    {"id": 0, "name": "保障中心0", "x": 0.00, "y": 0.00},
    {"id": 1, "name": "保障中心1", "x": -160.93, "y": 109.30},
    {"id": 2, "name": "保障中心2", "x": -289.79, "y": -44.58},
]

# 论文表 5：22 个无人机起飞点（id, x, y, priority, latest）。
_PAPER_LAUNCH = [
    {"id": 3, "x": 35.60, "y": 167.90, "priority": 31.22, "latest": 40},
    {"id": 4, "x": -305.38, "y": -16.68, "priority": 28.27, "latest": 30},
    {"id": 5, "x": 50.66, "y": -92.46, "priority": 35.34, "latest": 67},
    {"id": 6, "x": -132.35, "y": 24.65, "priority": 21.78, "latest": 92},
    {"id": 7, "x": -273.59, "y": -110.50, "priority": 32.28, "latest": 73},
    {"id": 8, "x": -312.68, "y": 108.04, "priority": 26.31, "latest": 100},
    {"id": 9, "x": -134.52, "y": 139.87, "priority": 34.63, "latest": 225},
    {"id": 10, "x": -158.49, "y": -247.22, "priority": 31.66, "latest": 80},
    {"id": 11, "x": -97.35, "y": 20.50, "priority": 36.19, "latest": 87},
    {"id": 12, "x": -25.87, "y": -66.54, "priority": 24.68, "latest": 56},
    {"id": 13, "x": -386.72, "y": -225.14, "priority": 25.21, "latest": 158},
    {"id": 14, "x": -19.16, "y": -199.65, "priority": 32.41, "latest": 202},
    {"id": 15, "x": 77.41, "y": -193.93, "priority": 22.22, "latest": 144},
    {"id": 16, "x": -394.28, "y": 140.33, "priority": 36.12, "latest": 48},
    {"id": 17, "x": 87.77, "y": 14.03, "priority": 23.81, "latest": 95},
    {"id": 18, "x": -161.08, "y": -16.64, "priority": 33.69, "latest": 47},
    {"id": 19, "x": -116.97, "y": -143.61, "priority": 42.77, "latest": 42},
    {"id": 20, "x": -234.43, "y": 158.10, "priority": 22.89, "latest": 135},
    {"id": 21, "x": -410.02, "y": 17.85, "priority": 30.13, "latest": 124},
    {"id": 22, "x": -389.01, "y": -115.92, "priority": 39.24, "latest": 170},
    {"id": 23, "x": -289.89, "y": -209.51, "priority": 19.99, "latest": 84},
    {"id": 24, "x": -1.76, "y": 78.06, "priority": 3.47, "latest": 26},
]

DEFAULT_PARAMS: Dict[str, Any] = {
    "v1": 40.0,
    "service_time": 0.5,
    "max_vehicles_per_depot": 8,
    "earliest": 0.0,
    "priority_penalty_L": 1.0,
}


def paper_instance() -> Dict[str, Any]:
    """论文真实算例（3 保障中心 + 22 无人机起飞点）。"""
    return {
        "name": "paper_mdvrptw_3depot_22launch",
        "depots": [dict(d) for d in _PAPER_DEPOTS],
        "launch_points": [dict(p) for p in _PAPER_LAUNCH],
        "params": dict(DEFAULT_PARAMS),
        "source": "SETP-paper-draft/main.tex 表4/表5（第5节真实地理算例）",
    }


def normalize_instance(raw: Dict[str, Any]) -> Dict[str, Any]:
    """
    把外部（LLM 抽取或用户）提供的实例 JSON 归一化为标准结构。
    - 若缺少 depots/launch_points，回退到论文算例。
    - 自动补 id、缺省 priority/latest、缺省 params。
    """
    if not isinstance(raw, dict):
        return paper_instance()
    depots_raw = raw.get("depots") or []
    launch_raw = raw.get("launch_points") or raw.get("customers") or raw.get("launches") or []
    if not depots_raw or not launch_raw:
        return paper_instance()

    depots: List[Dict[str, Any]] = []
    for idx, d in enumerate(depots_raw):
        depots.append({
            "id": int(d.get("id", idx)),
            "name": str(d.get("name", f"保障中心{idx}")),
            "x": float(d.get("x", 0.0)),
            "y": float(d.get("y", 0.0)),
        })

    next_id = max((d["id"] for d in depots), default=-1) + 1
    launches: List[Dict[str, Any]] = []
    for offset, p in enumerate(launch_raw):
        launches.append({
            "id": int(p.get("id", next_id + offset)),
            "x": float(p.get("x", 0.0)),
            "y": float(p.get("y", 0.0)),
            "priority": float(p.get("priority", p.get("tau", 0.0))),
            "latest": float(p.get("latest", p.get("due", 10_000))),
        })

    params = dict(DEFAULT_PARAMS)
    for key, value in (raw.get("params") or {}).items():
        if key in params:
            try:
                params[key] = float(value)
            except (TypeError, ValueError):
                pass

    return {
        "name": str(raw.get("name", "custom_mdvrptw")),
        "depots": depots,
        "launch_points": launches,
        "params": params,
        "source": raw.get("source", "user_provided"),
    }


if __name__ == "__main__":
    inst = paper_instance()
    print("=== presets.py 本地测试 ===")
    print("论文算例:", len(inst["depots"]), "保障中心,", len(inst["launch_points"]), "起飞点")
    custom = normalize_instance({"depots": [{"x": 0, "y": 0}], "launch_points": [{"x": 10, "y": 5, "latest": 30}]})
    print("归一化自定义:", len(custom["depots"]), "保障中心,", len(custom["launch_points"]), "起飞点")
