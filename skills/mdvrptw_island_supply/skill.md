# MDVRPTW-P 远海岛礁应急补给

带时间窗与优先级约束的多仓库车辆路径问题。当用户提到多保障中心/多仓库、补给舰、无人机起飞点、
时间窗、任务优先级、远海岛礁应急补给、MDVRPTW 等场景时匹配本技能。

## Problem Family
- mdvrptw_island_supply
- 多仓库（保障中心）派出车辆（补给舰）访问一组客户节点（无人机起飞点）后返回原仓库，
  受时间窗与优先级约束。属 NP-hard 组合优化，可用 MILP 精确求解或遗传算法启发式求解。

## Base Objective
- 最小化 `总航行时间 + 优先级违反惩罚`：
  `min  (Σ_routes Σ_arc dist / v1)  +  L · Σ_{相邻 i->j} max(0, τ_j − τ_i)`

## Base Constraints
- 每个起飞点被恰好一艘补给舰服务一次（入度=出度=1）。
- 每条路径归属单一保障中心，且从该中心出发、回到该中心。
- 每个保障中心派出的补给舰数量不超过上限。
- 时间窗硬约束：补给舰到达起飞点的时刻 ≤ 该点最晚服务时间 `latest`。
- 子回路消除（到达时刻沿弧递增）。

## Decision Variables
- `x[i,j]`：弧 i->j 是否被使用（0/1）。
- `s[i]`：补给舰到达起飞点 i 的时刻。
- 起飞点—保障中心归属（精确模型用 depot 标签，启发式用 assign 基因）。

## Required Parameters
- `depots[]`：保障中心，字段 `id, x, y`。
- `launch_points[]`：无人机起飞点（客户），字段 `id, x, y, priority(τ), latest(最晚服务时间)`。
- `params`：`v1`(补给舰航速), `service_time`(单点服务时长), `max_vehicles_per_depot`, `priority_penalty_L`。

## Optional Constraints
- 取消时间窗或优先级（消融实验）。
- 无人机航程 / 数量约束（可作为起飞点服务范围预处理）。

## Solver Hints
- `solver_preference=exact` -> Gurobi MILP（小规模秒级最优）。
- `solver_preference=heuristic` -> 记忆式遗传算法（GA + 2-opt/relocate/split，gap≈4%）。
- 无 Gurobi license 时用遗传算法。

## Confirmation Checklist
- 是否提供了 depots 与 launch_points 坐标？
- 每个起飞点是否有 priority 和 latest？
- 目标是最小化航行时间 + 优先级惩罚吗？
- 用精确（Gurobi）还是启发式（遗传算法）求解？

## Codegen Notes
- 求解工具生成可独立运行的完整 .py 脚本并落盘，运行写出 result.json。
- 结果含 objective / routes / arrival_times，并渲染路线图与甘特图 SVG。
- 数据来源：论文《基于知识引导的多智能体DRL求解远海岛礁应急物资补给规划》第 5 节真实算例。
