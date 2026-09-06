"""
作用：
- 用用户提供的全精度算例（3 保障中心 + 22 无人机起飞点）与参数（speed=10, penalty=5, service=5）
  构建 MDVRPTW-P 实例，调用 solver.mdvrptw 的 Gurobi 精确求解与遗传算法求解。
- 目标口径与 main.pdf（SETP）式(21) 一致：最小化 R = w1·总航行时间 + w2·优先级违反惩罚，
  权重取 w1=0.8, w2=0.2；补给舰闭合路线（服务完毕返回保障中心）；时间窗为硬约束。
- Gurobi 精确解与 main.pdf 表 6 的基准（268.8）对照，验证复现一致性。

运行：
    PYTHONPATH=. python3 shiyan/mdvrptw_user_instance.py
产物：
    shiyan/results/mdvrptw_user/gurobi_result.json
    shiyan/results/mdvrptw_user/genetic_result.json
"""

from __future__ import annotations

import json
from pathlib import Path

from solver.mdvrptw.exact import solve_exact
from solver.mdvrptw.genetic import solve_genetic

# ---- 用户提供的全精度算例 ----
# 0-2 维为保障中心，其余为无人机起飞点。
DF = [
    [0, 0],
    [-160.93966063, 109.30314076],
    [-289.79604121, -44.58644132],
    [35.60040000000001, 167.9061725],
    [-305.38170125, -16.682147],
    [50.66618400000002, -92.461002],
    [-132.3592047759638, 24.65850317256403],
    [-273.5911082549474, -110.5014750522463],
    [-312.683821625, 108.0471196],
    [-134.5253323612808, 139.8734613464141],
    [-158.4991135392925, -247.2225893013349],
    [-97.35482368683678, 20.50788773673604],
    [-25.87161799999998, -66.544252],
    [-386.7238325, -225.141965],
    [-19.16128, -199.653575],
    [77.41319999999999, -193.93208],
    [-394.2807367199999, 140.330717],
    [87.77023999999997, 14.03907000000001],
    [-161.0899280413934, -16.64606347270195],
    [-116.9771239969166, -143.617771400833],
    [-234.434405, 158.1015875],
    [-410.0217736, 17.85571904],
    [-389.0070057934536, -115.9207666847336],
    [-289.898376206638, -209.5146086852976],
    [-1.762455686516148, 78.06077858596802],
]
PRIORITY = [0, 0, 0, 31.225637540413903, 28.274348063677998, 35.3494987268495, 21.7808646340332,
            32.2897647563159, 26.3119486979374, 34.6316778772019, 31.6615439422415, 36.1951950238587,
            24.6816879701525, 25.2160768126082, 32.4173968152891, 22.2251061207109, 36.1230349079251,
            23.8169650797088, 33.6936623924423, 42.7788837162159, 22.8930886551098, 30.1355953712795,
            39.2403978364406, 19.9916496318372, 3.47372555763585]
SERVICE_TIME = [0, 0, 0, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5]
READY_TIME = [0] * 25
DUE_TIME = [10000, 10000, 10000, 40, 30, 67, 92, 73, 100, 225, 80, 87, 56, 158, 202, 144, 48, 95,
            47, 42, 135, 124, 170, 84, 26]

SPEED = 10.0     # 补给舰行驶速度 v1
PENALTY = 5.0    # 违反优先级惩罚系数 L


def build_instance() -> dict:
    """把用户数据整理成 solver.mdvrptw 所需的标准实例结构。"""
    depots = []
    for i in range(3):
        depots.append({"id": i, "name": f"保障中心{i}", "x": float(DF[i][0]), "y": float(DF[i][1])})

    launch_points = []
    for i in range(3, 25):
        launch_points.append({
            "id": i,
            "x": float(DF[i][0]),
            "y": float(DF[i][1]),
            "priority": float(PRIORITY[i]),
            "latest": float(DUE_TIME[i]),
        })

    params = {
        "v1": SPEED,
        "service_time": float(SERVICE_TIME[3]),   # 起飞点统一服务时长 5
        "max_vehicles_per_depot": 8,
        "earliest": 0.0,
        "priority_penalty_L": PENALTY,
        "w1": 0.8,   # 总航行时间权重（main.pdf 式21）
        "w2": 0.2,   # 优先级惩罚权重（main.pdf 式21）
    }

    return {
        "name": "user_mdvrptw_3depot_22launch",
        "depots": depots,
        "launch_points": launch_points,
        "params": params,
        "source": "用户提供的全精度算例（speed=10, penalty=5, service=5）",
    }


def main() -> None:
    instance = build_instance()
    out_dir = Path(__file__).resolve().parent / "results" / "mdvrptw_user"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "instance.json").write_text(json.dumps(instance, ensure_ascii=False, indent=2), encoding="utf-8")

    print("=" * 60)
    print("MDVRPTW-P 用户算例：3 保障中心 + 22 无人机起飞点")
    print(f"speed(v1)={SPEED}  penalty(L)={PENALTY}  service={instance['params']['service_time']}")
    print(f"目标 R = 0.8·总航行时间 + 0.2·优先级惩罚（main.pdf 式21）")
    print("=" * 60)

    print("\n[1/2] Gurobi 精确求解 ...")
    gurobi = solve_exact(instance, time_limit=600, verbose=False)
    (out_dir / "gurobi_result.json").write_text(json.dumps(gurobi, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  status={gurobi.get('status_text')}  objective={gurobi.get('objective')}  (基准 268.8)")
    print(f"  总航行时间={gurobi.get('travel_time')}  优先级惩罚={gurobi.get('priority_penalty')}")
    print(f"  加权分解: 0.8·{gurobi.get('travel_time')} + 0.2·{gurobi.get('priority_penalty')} = {gurobi.get('objective')}")
    print(f"  num_routes={gurobi.get('num_routes')}  feasible={gurobi.get('feasible')}  gap={gurobi.get('mip_gap')}")
    print("  routes:")
    for r in gurobi.get("routes", []):
        if r["sequence"]:
            print(f"    depot {r['depot']}: {r['sequence']}")

    print("\n[2/2] 遗传算法求解 ...")
    genetic = solve_genetic(instance, seed=42)
    (out_dir / "genetic_result.json").write_text(json.dumps(genetic, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  status={genetic.get('status_text')}  objective={genetic.get('objective')}")
    print(f"  总航行时间={genetic.get('travel_time')}  优先级惩罚={genetic.get('priority_penalty')}")
    print(f"  num_routes={genetic.get('num_routes')}  feasible={genetic.get('feasible')}")

    print("\n完成。产物写入:", out_dir)


if __name__ == "__main__":
    main()
