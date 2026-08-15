# Examples

## 示例 1：小规模岛礁补给（精确求解 + Gurobi）

输入：
```
请帮我求解一个岛礁应急物资补给问题，优先使用精确算法，并使用 Gurobi 求解器。
背景：2个仓库为3个岛礁补给。
决策变量：x[d,i] 表示从仓库 d 到岛礁 i 的补给量。
参数：supply[d] 表示仓库库存；demand[i] 表示岛礁需求；cost[d,i] 表示运输成本。
目标：最小化总运输成本。
约束：每个仓库发出量不超过库存；每个岛礁收到量满足需求；每条航线不超过容量。
数据如下：
```json
{
  "depots": [{"name": "warehouse_1", "supply": 70}, {"name": "warehouse_2", "supply": 50}],
  "islands": [{"name": "island_a", "demand": 30}, {"name": "island_b", "demand": 40}, {"name": "island_c", "demand": 20}],
  "routes": [
    {"from": "warehouse_1", "to": "island_a", "cost": 4, "capacity": 40},
    {"from": "warehouse_1", "to": "island_b", "cost": 6, "capacity": 40},
    {"from": "warehouse_1", "to": "island_c", "cost": 9, "capacity": 30},
    {"from": "warehouse_2", "to": "island_a", "cost": 5, "capacity": 40},
    {"from": "warehouse_2", "to": "island_b", "cost": 4, "capacity": 40},
    {"from": "warehouse_2", "to": "island_c", "cost": 3, "capacity": 30}
  ]
}
```
```

预期结构化摘要：
- solver_preference = exact
- solver_backend = gurobi
- objective_value ≈ 360（最优）

## 示例 2：启发式求解

输入：将上例中的“精确算法/Gurobi”改为“启发式算法”即可，
系统会生成贪心 + 局部搜索代码并返回可行方案。
