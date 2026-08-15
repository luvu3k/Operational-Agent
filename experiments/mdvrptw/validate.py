"""
作用：
- “求解正确性”验证入口：对论文 MDVRPTW-P 算例分别运行 Gurobi 精确求解与遗传算法，
  校验两者是否求解同一问题、GA 是否收敛到接近最优，并生成可视化路线图/甘特图。
- 这是用户设定的“先保证问题求解正确，再做全栈”的 gate。

判定标准：
- Gurobi 达到 OPTIMAL 且解可行。
- GA 得到可行解，且相对最优的 gap 在阈值内（默认 ≤ 10%）。
- 两法目标口径一致（均由 model.evaluate_solution 评估）。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from genetic_solver import solve_genetic
from gurobi_solver import solve_exact
from instance import build_instance
from visualize import build_visualizations

GAP_THRESHOLD = 0.10  # GA 相对最优可接受 gap


def main() -> int:
    inst = build_instance()
    out_dir = Path(__file__).resolve().parent / "results"
    out_dir.mkdir(exist_ok=True)

    print("=" * 60)
    print("MDVRPTW-P 论文算例：3 保障中心 + 22 无人机起飞点")
    print("=" * 60)

    print("\n[1/2] Gurobi 精确求解 ...")
    exact = solve_exact(inst, time_limit=180, verbose=False)
    print(f"  status={exact['status']} ({exact['status_text']})  objective={exact['objective']}  "
          f"gap={exact.get('mip_gap')}  routes={exact.get('num_routes')}")

    print("\n[2/2] 遗传算法求解 ...")
    ga = solve_genetic(inst, population_size=60, generations=120, patience=25, seed=42, verbose=False)
    print(f"  status={ga['status']} ({ga['status_text']})  objective={ga['objective']}  routes={ga.get('num_routes')}")

    # 生成可视化。
    for tag, result in [("gurobi", exact), ("genetic", ga)]:
        if result.get("routes"):
            viz = build_visualizations(inst, result)
            (out_dir / f"{tag}_route_map.svg").write_text(viz["route_map_svg"], encoding="utf-8")
            (out_dir / f"{tag}_gantt.svg").write_text(viz["gantt_svg"], encoding="utf-8")
        (out_dir / f"{tag}_result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    # 判定。
    print("\n" + "=" * 60)
    print("验证结论")
    print("=" * 60)
    ok = True
    if not (exact["status"] == "success" and exact["status_text"] == "OPTIMAL"):
        print("✗ Gurobi 未达到最优/可行。")
        ok = False
    else:
        print(f"✓ Gurobi 最优可行，目标值 = {exact['objective']}")

    if not ga["feasible"]:
        print("✗ GA 未得到可行解。")
        ok = False
    else:
        gap = (ga["objective"] - exact["objective"]) / max(exact["objective"], 1e-9)
        print(f"✓ GA 可行，目标值 = {ga['objective']}，相对最优 gap = {gap * 100:.2f}%")
        if gap > GAP_THRESHOLD:
            print(f"✗ GA gap 超过阈值 {GAP_THRESHOLD * 100:.0f}%。")
            ok = False
        else:
            print(f"✓ GA gap 在阈值 {GAP_THRESHOLD * 100:.0f}% 内。")

    print(f"\n可视化与结果已写入: {out_dir}")
    print("\n最终判定:", "✅ 求解正确性验证通过" if ok else "❌ 未通过")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
