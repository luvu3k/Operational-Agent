# Emergency Island Supply

用于岛礁应急物资补给的调度与运输优化。当用户提到岛礁、仓库、补给、应急运输、库存分配等场景时匹配本技能。

## Problem Family
- emergency_island_supply
- 属于运输/分配类问题，通常可用最小成本流或运输模型精确建模，也可用贪心 + 局部搜索启发式求解。

## Base Objective
- 最小化总运输成本（或总运输时间）：`minimize sum(cost[d,i] * x[d,i] for (d,i) in routes)`

## Base Constraints
- 供给约束：每个仓库发出的总量不超过其库存 `sum_i x[d,i] <= supply[d]`
- 需求约束：每个岛礁收到的总量不少于其需求 `sum_d x[d,i] >= demand[i]`
- 容量约束：每条航线运输量不超过容量 `x[d,i] <= capacity[d,i]`
- 非负约束：`x[d,i] >= 0`

## Decision Variables
- `x[d,i]`：从仓库 d 运往岛礁 i 的物资数量（连续变量，默认 >= 0）

## Required Parameters
- `supply[d]`：仓库 d 的可用库存
- `demand[i]`：岛礁 i 的需求
- `cost[d,i]`：航线 d->i 的单位运输成本（缺省时可用 time 代替）
- `capacity[d,i]`：航线 d->i 的最大运输量

## Optional Constraints
- 优先保障：指定岛礁必须优先满足（可建为硬约束或高权重软约束）
- 时间窗：限定送达时间（需要额外时间参数）
- 船舶载重：多船只资源约束

## Solver Hints
- 小规模（节点数 < 200）优先用精确求解器（Gurobi / PuLP-CBC）。
- 大规模或无 license 时使用启发式求解（贪心 + 局部搜索）。

## Confirmation Checklist
- 是否提供了 depots / islands / routes 三类数据？
- 目标是最小化成本还是时间？
- 是否有优先保障或时间窗等附加约束？

## Codegen Notes
- 实例数据约定字段：`depots[].name/supply`、`islands[].name/demand`、`routes[].from/to/cost/capacity`。
- 生成代码需将结果写入 result.json，包含 objective_value、shipment_plan、feasible、status_text。
